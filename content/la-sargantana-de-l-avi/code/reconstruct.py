"""Maximum-likelihood reconstruction of the extinct Banyoles lizard's mitogenome.

The poem's lizard is the *last common ancestor* of the common wall lizard
(Podarcis muralis) and the water monitor (Varanus salvator) — the deep Episquamata
node, roughly Jurassic (~170 My). We cannot dig up its DNA; no ancient DNA survives
that long. So we do what ancestral sequence reconstruction (ASR) actually does in
the lab: infer the ancestor's sequence from its living descendants, under an
explicit model of molecular evolution.

The reconstructed object is the whole mitochondrial genome (13 protein-coding
genes + 12S/16S rRNA + tRNAs, control region omitted): the features are aligned
separately and concatenated (`align.build_alignment`), and this engine runs once
over the ~15 kb supermatrix. The code is sequence-agnostic, so nothing here changed
when we grew from one gene to the genome.

Method
------
1. **Tree.** A fixed topology from the squamate literature (Toxicofera hypothesis),
   rooted *at the ancestral node itself* so that node is a trifurcation of its
   three surrounding subtrees — the standard identifiable unrooted representation,
   and exactly the node we want to read off:

       (Lacertoidea, Toxicofera, Gekko)                      <- the ancestor R
         Lacertoidea = (Podarcis, Lacerta)
         Toxicofera  = (Anolis, (Varanus salvator, Heloderma))

2. **Model.** HKY85 nucleotide substitution: empirical base frequencies + one
   transition/transversion parameter kappa. Time-reversible, so the likelihood is
   independent of where we root — which is why rooting at R is free.

3. **Likelihood.** Felsenstein's pruning algorithm, vectorised over all sites.
   All nine branch lengths and kappa are fitted by maximum likelihood
   (L-BFGS-B). Transition matrices come from an eigendecomposition of the rate
   matrix, P(t) = V exp(Λ t) V⁻¹.

4. **Reconstruction (the poem).** At the root we read the *marginal posterior*
   over {A,C,G,T} per site: P(ancestor base | data, tree, model). The most
   probable base is the reconstructed nucleotide; the posterior is our confidence.
   Deep time means many sites are near-uniform haze — and that uncertainty is the
   poem. Gaps in the alignment enter as missing data (a uniform tip likelihood).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from align import build_alignment, Partition
from fetch_sequences import MITO_TABLE
from Bio.Seq import Seq

BASES = "ACGT"
BASE_INDEX = {b: i for i, b in enumerate(BASES)}
PURINES, PYRIMIDINES = {0, 2}, {1, 3}  # A,G  and  C,T
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# Vertebrate mitochondrial stop codons (table 2) and the sense codons we may
# substitute for them during reading-frame repair (see repair_cds_stops).
STOP_CODONS = {"TAA", "TAG", "AGA", "AGG"}
_SENSE_CODONS = [a + b + c for a in BASES for b in BASES for c in BASES
                 if a + b + c not in STOP_CODONS]


# --- Tree -------------------------------------------------------------------

@dataclass
class Node:
    """A tree node. Leaves carry a species name; internals carry children."""

    name: str | None = None
    children: list[tuple["Node", int]] = field(default_factory=list)  # (child, branch)

    @property
    def is_leaf(self) -> bool:
        return self.name is not None


def build_tree() -> tuple[Node, int, list[str]]:
    """Return (root, n_branches, edge_labels), rooted at the ancestral node R.

    The root R is the reconstructed ancestor: the trifurcation joining the
    wall-lizard side (Lacertoidea), the dragon side (Toxicofera) and the gecko
    outgroup. Branch indices are assigned in construction order.
    """
    labels: list[str] = []

    def edge(child: Node, label: str) -> tuple[Node, int]:
        labels.append(label)
        return child, len(labels) - 1

    lacertoidea = Node(children=[
        edge(Node(name="Podarcis muralis"), "R->Podarcis side / Podarcis"),
        edge(Node(name="Lacerta viridis"), "Lacerta"),
    ])
    anguimorpha = Node(children=[
        edge(Node(name="Varanus salvator"), "Varanus"),
        edge(Node(name="Heloderma suspectum"), "Heloderma"),
    ])
    toxicofera = Node(children=[
        edge(Node(name="Anolis carolinensis"), "Anolis"),
        edge(anguimorpha, "Toxicofera->Anguimorpha"),
    ])
    root = Node(children=[
        edge(lacertoidea, "R->Lacertoidea"),
        edge(toxicofera, "R->Toxicofera"),
        edge(Node(name="Gekko gecko"), "R->Gekko (outgroup)"),
    ])
    return root, len(labels), labels


# --- HKY85 model ------------------------------------------------------------

def _is_transition(i: int, j: int) -> bool:
    return {i, j} in ({0, 2}, {1, 3})


def rate_matrix(kappa: float, pi: np.ndarray) -> np.ndarray:
    """HKY85 rate matrix Q, scaled to one expected substitution per unit time."""
    q = np.zeros((4, 4))
    for i in range(4):
        for j in range(4):
            if i != j:
                q[i, j] = pi[j] * (kappa if _is_transition(i, j) else 1.0)
        q[i, i] = -q[i].sum()
    scale = -(pi * np.diag(q)).sum()
    return q / scale


def transition_matrices(q: np.ndarray, lengths: np.ndarray) -> list[np.ndarray]:
    """P(t) = V exp(Λ t) V⁻¹ for each branch length, via one eigendecomposition."""
    evals, evecs = np.linalg.eig(q)
    evecs_inv = np.linalg.inv(evecs)
    mats = []
    for t in lengths:
        p = (evecs * np.exp(evals * t)) @ evecs_inv
        mats.append(np.clip(p.real, 0.0, 1.0))
    return mats


# --- Likelihood (Felsenstein pruning) ---------------------------------------

def tip_likelihoods(alignment: dict[str, str]) -> dict[str, np.ndarray]:
    """Per-leaf conditional-likelihood arrays, shape (4, n_sites).

    A known base is a one-hot column; a gap or ambiguous base is all-ones
    (missing data contributes no information).
    """
    n_sites = len(next(iter(alignment.values())))
    tips: dict[str, np.ndarray] = {}
    for species, seq in alignment.items():
        mat = np.ones((4, n_sites))
        for pos, base in enumerate(seq):
            idx = BASE_INDEX.get(base)
            if idx is not None:
                mat[:, pos] = 0.0
                mat[idx, pos] = 1.0
        tips[species] = mat
    return tips


def _partial(node: Node, mats: list[np.ndarray],
             tips: dict[str, np.ndarray]) -> np.ndarray:
    """Conditional likelihood at `node` given the subtree below it, (4, n_sites)."""
    if node.is_leaf:
        return tips[node.name]
    n_sites = tips[next(iter(tips))].shape[1]
    result = np.ones((4, n_sites))
    for child, branch in node.children:
        below = _partial(child, mats, tips)   # (4, n_sites)
        result *= mats[branch] @ below        # message up this branch
    return result


def log_likelihood(params: np.ndarray, root: Node, tips: dict[str, np.ndarray],
                   pi: np.ndarray) -> float:
    kappa, lengths = params[0], params[1:]
    q = rate_matrix(kappa, pi)
    mats = transition_matrices(q, lengths)
    root_partial = _partial(root, mats, tips)           # (4, n_sites)
    site_lik = pi @ root_partial                        # (n_sites,)
    return float(np.log(np.clip(site_lik, 1e-300, None)).sum())


# --- Fit + reconstruct ------------------------------------------------------

@dataclass
class Reconstruction:
    map_bases: str                 # MAP nucleotide per site
    posteriors: np.ndarray         # (n_sites,) posterior of the MAP base
    full_posterior: np.ndarray     # (4, n_sites)
    kappa: float
    lengths: np.ndarray
    pi: np.ndarray
    log_likelihood: float
    edge_labels: list[str]


def empirical_frequencies(alignment: dict[str, str]) -> np.ndarray:
    counts = np.zeros(4)
    for seq in alignment.values():
        for base in seq:
            idx = BASE_INDEX.get(base)
            if idx is not None:
                counts[idx] += 1
    return counts / counts.sum()


def fit_and_reconstruct(alignment: dict[str, str]) -> Reconstruction:
    root, n_branches, labels = build_tree()
    tips = tip_likelihoods(alignment)
    pi = empirical_frequencies(alignment)

    x0 = np.array([2.0] + [0.1] * n_branches)          # kappa, branch lengths
    bounds = [(0.05, 50.0)] + [(1e-6, 10.0)] * n_branches
    result = minimize(
        lambda p: -log_likelihood(p, root, tips, pi),
        x0, method="L-BFGS-B", bounds=bounds,
    )
    kappa, lengths = result.x[0], result.x[1:]

    # Marginal posterior at the root = the reconstructed ancestor.
    mats = transition_matrices(rate_matrix(kappa, pi), lengths)
    root_partial = _partial(root, mats, tips)          # (4, n_sites)
    joint = pi[:, None] * root_partial                 # π(x)·P(data | root=x)
    posterior = joint / joint.sum(axis=0, keepdims=True)

    map_idx = posterior.argmax(axis=0)
    map_bases = "".join(BASES[i] for i in map_idx)
    map_posterior = posterior[map_idx, np.arange(posterior.shape[1])]

    return Reconstruction(
        map_bases=map_bases,
        posteriors=map_posterior,
        full_posterior=posterior,
        kappa=float(kappa),
        lengths=lengths,
        pi=pi,
        log_likelihood=-result.fun,
        edge_labels=labels,
    )


def repair_cds_stops(rec: Reconstruction, partitions: list[Partition]) -> int:
    """Resolve reading-frame stop codons in reconstructed protein-coding genes.

    Site-independent marginal reconstruction optimises each base on its own and so
    ignores the reading frame; at an uncertain codon the per-site argmax can spell
    a premature stop. A protein-coding gene must not contain one, so at each such
    codon we substitute the sense codon of highest *joint* posterior (product of
    the three per-site posteriors) and record its (lower) posterior — the site
    stays honestly uncertain. Mutates `rec`; returns how many codons were fixed.
    """
    bases = list(rec.map_bases)
    post = rec.posteriors.copy()
    fp = rec.full_posterior
    repaired = 0
    for part in partitions:
        if part.kind != "CDS":
            continue
        for i in range(part.start, part.end, 3):
            if "".join(bases[i : i + 3]) not in STOP_CODONS:
                continue
            best = max(_SENSE_CODONS, key=lambda cod: float(
                fp[BASE_INDEX[cod[0]], i]
                * fp[BASE_INDEX[cod[1]], i + 1]
                * fp[BASE_INDEX[cod[2]], i + 2]))
            for k, base in enumerate(best):
                bases[i + k] = base
                post[i + k] = fp[BASE_INDEX[base], i + k]
            repaired += 1
    rec.map_bases = "".join(bases)
    rec.posteriors = post
    return repaired


def _feature_per_site(partitions: list[Partition], n_sites: int) -> list[str]:
    labels = [""] * n_sites
    for part in partitions:
        for pos in range(part.start, part.end):
            labels[pos] = part.name
    return labels


def _cds_has_internal_stop(rec: Reconstruction, part: Partition) -> bool:
    nt = rec.map_bases[part.start : part.end]
    protein = str(Seq(nt).translate(table=MITO_TABLE)).rstrip("*")
    return "*" in protein


def _write_outputs(rec: Reconstruction, partitions: list[Partition]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    features = _feature_per_site(partitions, len(rec.map_bases))

    (RESULTS_DIR / "ancestor.fasta").write_text(
        ">ancestor_Podarcis-Varanus mitogenome | ML reconstruction (HKY85), "
        f"{len(rec.map_bases)} bp, {len(partitions)} features, "
        f"mean posterior {rec.posteriors.mean():.3f}\n{rec.map_bases}\n"
    )

    with (RESULTS_DIR / "reconstruction.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["site", "feature", "map_base",
                         "posterior", "pA", "pC", "pG", "pT"])
        for pos in range(len(rec.map_bases)):
            pa, pc, pg, pt = rec.full_posterior[:, pos]
            writer.writerow([
                pos + 1, features[pos], rec.map_bases[pos],
                f"{rec.posteriors[pos]:.4f}",
                f"{pa:.4f}", f"{pc:.4f}", f"{pg:.4f}", f"{pt:.4f}",
            ])

    with (RESULTS_DIR / "model.txt").open("w") as fh:
        fh.write(f"log-likelihood: {rec.log_likelihood:.3f}\n")
        fh.write(f"kappa (ti/tv): {rec.kappa:.3f}\n")
        fh.write(f"base frequencies A C G T: "
                 f"{' '.join(f'{p:.3f}' for p in rec.pi)}\n")
        fh.write(f"reconstructed length: {len(rec.map_bases)} bp "
                 f"across {len(partitions)} features\n\n")
        fh.write("branch lengths (expected substitutions/site):\n")
        for label, length in zip(rec.edge_labels, rec.lengths):
            fh.write(f"  {label:<28} {length:.4f}\n")
        fh.write("\nper-feature mean posterior (conserved -> variable):\n")
        rows = []
        for part in partitions:
            post = rec.posteriors[part.start : part.end].mean()
            stop = (" internal-stop!" if part.kind == "CDS"
                    and _cds_has_internal_stop(rec, part) else "")
            rows.append((post, f"  {part.name:<8} {part.kind:<5} "
                               f"{part.end - part.start:>4} bp   {post:.3f}{stop}"))
        for _, line in sorted(rows):
            fh.write(line + "\n")


def summarise(rec: Reconstruction, partitions: list[Partition]) -> None:
    post = rec.posteriors
    cds = [p for p in partitions if p.kind == "CDS"]
    stops = sum(_cds_has_internal_stop(rec, p) for p in cds)
    print(f"log-likelihood        {rec.log_likelihood:.1f}")
    print(f"kappa (ti/tv)         {rec.kappa:.2f}")
    print(f"mean posterior        {post.mean():.3f}")
    print(f"confident sites >=.80 {(post >= 0.80).mean():.1%}")
    print(f"haze sites <.50       {(post < 0.50).mean():.1%}")
    print(f"reconstructed length  {len(rec.map_bases)} bp, {len(partitions)} features")
    print(f"CDS with internal stop {stops}/{len(cds)}")


def main() -> None:
    _, alignment, partitions = build_alignment()
    rec = fit_and_reconstruct(alignment)
    repaired = repair_cds_stops(rec, partitions)
    print(f"reading-frame repair fixed {repaired} stop codon(s) in coding genes")
    _write_outputs(rec, partitions)
    summarise(rec, partitions)
    print(f"\nWrote ancestor.fasta, reconstruction.csv, model.txt to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
