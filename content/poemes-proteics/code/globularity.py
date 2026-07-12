"""Score how globular a folded structure is, from its PDB.

Given an ESMFold PDB, we read the Cα trace and the per-residue pLDDT and derive a
few shape descriptors:

- **Radius of gyration** ``Rg`` vs. the empirical globular expectation
  ``Rg0 ≈ 2.2 · N^0.38`` Å (Dima & Thirumalai). A compact globule has ``Rg ≈ Rg0``;
  an extended chain has ``Rg ≫ Rg0``.
- **Relative shape anisotropy** ``κ²`` from the gyration tensor eigenvalues: 0 for a
  perfect sphere, 1 for a straight rod. Low ``κ²`` ⇒ globular.
- **Mean pLDDT** — ESMFold's own confidence; low values flag sequences that don't
  fold into anything ordered (as encoded poems often won't).

These combine into a single ``score`` in [0, 1]; higher ⇒ more globular *and*
confidently folded. The weights are deliberately simple and easy to re-tune.
"""

from __future__ import annotations

import numpy as np

# Combined-score weights (sphericity, compactness, confidence). Tune freely.
W_SPHERICITY = 0.4
W_COMPACTNESS = 0.3
W_CONFIDENCE = 0.3


def parse_ca(pdb_text: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (Nx3 Cα coordinates, N pLDDT values) parsed from a PDB string.

    pLDDT is read from the B-factor column and normalised to 0–100 (the ESM Atlas
    endpoint reports it on a 0–1 scale).
    """
    coords: list[tuple[float, float, float]] = []
    plddt: list[float] = []
    for line in pdb_text.splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
            plddt.append(float(line[60:66]))
    xyz = np.asarray(coords, dtype=float)
    b = np.asarray(plddt, dtype=float)
    if b.size and b.max() <= 1.0:  # 0–1 scale -> percent
        b = b * 100.0
    return xyz, b


def _gyration(coords: np.ndarray) -> tuple[float, float]:
    """Return (radius of gyration, relative shape anisotropy κ²)."""
    centered = coords - coords.mean(axis=0)
    tensor = (centered.T @ centered) / len(centered)
    eig = np.sort(np.linalg.eigvalsh(tensor))  # λ1 ≤ λ2 ≤ λ3
    rg2 = float(eig.sum())
    kappa2 = 1.5 * float((eig**2).sum()) / (rg2**2) - 0.5 if rg2 > 0 else 0.0
    return np.sqrt(rg2), float(np.clip(kappa2, 0.0, 1.0))


def score_structure(pdb_text: str) -> dict[str, float] | None:
    """Compute globularity descriptors + a combined score, or None if unparsable."""
    coords, plddt = parse_ca(pdb_text)
    n = len(coords)
    if n < 3:
        return None

    rg, anisotropy = _gyration(coords)
    rg_expected = 2.2 * (n**0.38)
    compactness = float(np.clip(rg_expected / rg, 0.0, 1.0)) if rg > 0 else 0.0
    sphericity = 1.0 - anisotropy
    mean_plddt = float(plddt.mean()) if plddt.size else 0.0

    score = (
        W_SPHERICITY * sphericity
        + W_COMPACTNESS * compactness
        + W_CONFIDENCE * (mean_plddt / 100.0)
    )
    return {
        "n_residues": n,
        "rg": round(rg, 2),
        "rg_expected": round(rg_expected, 2),
        "compactness": round(compactness, 3),
        "anisotropy": round(anisotropy, 3),
        "sphericity": round(sphericity, 3),
        "mean_plddt": round(mean_plddt, 1),
        "score": round(score, 3),
    }
