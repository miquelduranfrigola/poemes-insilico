"""Fold amino-acid sequences into 3D structures with the free ESMFold API.

Uses the public ESM Atlas endpoint (https://api.esmatlas.com/foldSequence/v1/pdb/),
which folds a single sequence with ESMFold (no MSA) and returns a PDB whose B-factor
column holds the per-residue pLDDT confidence. No API key, no local model.

Results are cached on disk by sequence hash, so re-runs are instant and we never
re-hit the API for a sequence we've already folded. The endpoint is occasionally
flaky (SSL / downtime) and caps sequences at ~400 residues, so callers should keep
sequences short (we fold per poem/verse) and tolerate the odd ``None`` return.
"""

from __future__ import annotations

import hashlib
import time
import warnings
from pathlib import Path

import requests

ESMATLAS_URL = "https://api.esmatlas.com/foldSequence/v1/pdb/"
MAX_RESIDUES = 400  # ESM Atlas fold endpoint length cap
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / "cache" / "pdb"


def _seq_hash(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()[:16]


def fold_sequence(
    sequence: str,
    cache_dir: Path = DEFAULT_CACHE,
    timeout: int = 120,
    retries: int = 3,
    pause: float = 1.0,
) -> str | None:
    """Fold one sequence to a PDB string, or return None on failure.

    Cached by sequence hash under ``cache_dir``. Sequences longer than the API cap
    are rejected (return None) — chunk them upstream. Retries transient errors and
    falls back to an unverified TLS connection if the server's certificate fails
    (a known intermittent issue with this endpoint).
    """
    sequence = sequence.strip().upper()
    if not sequence:
        return None
    if len(sequence) > MAX_RESIDUES:
        warnings.warn(
            f"sequence of {len(sequence)} > {MAX_RESIDUES} residues; skipping "
            "(chunk it before folding)",
            stacklevel=2,
        )
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{_seq_hash(sequence)}.pdb"
    if cached.exists():
        return cached.read_text()

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        for verify in (True, False):  # retry once without TLS verification if needed
            try:
                if not verify:
                    warnings.warn("retrying ESM Atlas call with TLS verification off",
                                  stacklevel=2)
                    requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]
                resp = requests.post(
                    ESMATLAS_URL, data=sequence, timeout=timeout, verify=verify
                )
                if resp.status_code == 200 and resp.text.lstrip().startswith(
                    ("ATOM", "HEADER", "PARENT", "TER", "MODEL")
                ):
                    cached.write_text(resp.text)
                    return resp.text
                last_err = RuntimeError(
                    f"HTTP {resp.status_code}: {resp.text[:120]!r}"
                )
                break  # a real HTTP response (not TLS) -> don't try verify=False
            except requests.exceptions.SSLError as err:
                last_err = err
                continue  # try verify=False
            except requests.exceptions.RequestException as err:
                last_err = err
                break
        time.sleep(pause * attempt)  # linear backoff
    warnings.warn(f"folding failed after {retries} attempts: {last_err}", stacklevel=2)
    return None
