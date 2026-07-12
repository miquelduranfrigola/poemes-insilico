"""Render folded structures as David-Goodsell-style space-filling illustrations.

The "Molecule of the Month" look: every heavy atom is a flat-filled sphere with a
dark outline, drawn back-to-front (painter's algorithm) with depth shading, no
specular highlights. Each poem-protein gets its own muted hue.

Reads the cached PDB for every poem in ``data/poems`` (folding is cached, so this is
offline once ``pipeline.py`` has run) and writes a PNG per poem to
``results/snapshots/``. Import ``render_pdb`` to draw a single structure.
"""

from __future__ import annotations

import colorsys
import subprocess
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from folding import DEFAULT_CACHE, _seq_hash, fold_sequence  # noqa: E402
from globularity import parse_ca  # noqa: E402
from pipeline import poem_chunks, to_sequence  # noqa: E402

PYMOL_BIN = "pymol"

POEM_ROOT = Path(__file__).resolve().parent.parent

VDW = {"C": 1.7, "N": 1.55, "O": 1.52, "S": 1.8, "P": 1.8, "H": 1.1}

# One muted hue per poem (RGB 0-1), in the Goodsell register.
HUES = [
    (0.36, 0.54, 0.47),  # teal-green
    (0.79, 0.55, 0.24),  # ochre
    (0.55, 0.36, 0.49),  # dusty plum
    (0.35, 0.45, 0.62),  # slate blue
    (0.72, 0.40, 0.34),  # terracotta
]


def _parse_atoms(pdb_text: str) -> tuple[np.ndarray, list[str]]:
    """Return (Mx3 heavy-atom coords, element symbols)."""
    coords: list[tuple[float, float, float]] = []
    elements: list[str] = []
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        elem = line[76:78].strip() or line[12:16].strip()[:1]
        if elem == "H":
            continue
        coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
        elements.append(elem)
    return np.asarray(coords, dtype=float), elements


def _orient(coords: np.ndarray) -> np.ndarray:
    """Center and rotate onto principal axes (largest spread -> x, then y, depth z)."""
    centered = coords - coords.mean(axis=0)
    _, vecs = np.linalg.eigh(np.cov(centered.T))
    return centered @ vecs[:, ::-1]  # columns ordered by descending eigenvalue


def _shade(rgb: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    """Darken toward black by ``factor`` (1 = front/full, small = far/dark)."""
    h, l, s = colorsys.rgb_to_hls(*rgb)
    return colorsys.hls_to_rgb(h, max(0.0, l * factor), s * (0.6 + 0.4 * factor))


def render_pdb(pdb_text: str, out_path: Path, hue: tuple[float, float, float],
               size: float = 6.0, dpi: int = 220) -> None:
    """Draw one structure as a Goodsell-style space-filling PNG (transparent bg)."""
    coords, elements = _parse_atoms(pdb_text)
    xyz = _orient(coords)
    order = np.argsort(xyz[:, 2])  # back (low z) to front

    depth = xyz[:, 2]
    d_lo, d_hi = depth.min(), depth.max()
    span = (d_hi - d_lo) or 1.0

    fig, ax = plt.subplots(figsize=(size, size), dpi=dpi)
    for idx in order:
        x, y, z = xyz[idx]
        r = VDW.get(elements[idx], 1.6) * 0.98
        f = 0.55 + 0.45 * ((z - d_lo) / span)  # depth cue
        face = _shade(hue, f)
        edge = _shade(hue, f * 0.45)
        ax.add_patch(Circle((x, y), r, facecolor=face, edgecolor=edge,
                            linewidth=0.6, zorder=idx))

    pad = 3.0
    ax.set_xlim(xyz[:, 0].min() - pad, xyz[:, 0].max() + pad)
    ax.set_ylim(xyz[:, 1].min() - pad, xyz[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0.0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def _catmull_rom(points: np.ndarray, samples: int = 16) -> np.ndarray:
    """Smooth Catmull-Rom spline through ``points`` (Nx3), for a ribbon backbone."""
    pts = np.vstack([points[0], points, points[-1]])  # pad ends
    curve: list[np.ndarray] = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in np.linspace(0.0, 1.0, samples, endpoint=False):
            t2, t3 = t * t, t * t * t
            curve.append(0.5 * (
                (2 * p1)
                + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
            ))
    curve.append(points[-1])
    return np.asarray(curve)


def render_ribbon(pdb_text: str, out_path: Path, size: float = 6.0, dpi: int = 220,
                  cmap: str = "turbo") -> None:
    """Draw the Cα backbone as a smooth ribbon, coloured N→C with depth shading."""
    coords, _ = parse_ca(pdb_text)
    if len(coords) < 4:
        return
    curve = _catmull_rom(_orient(coords))
    pts2 = curve[:, :2]
    segs = np.stack([pts2[:-1], pts2[1:]], axis=1)  # (S, 2, 2)

    zmid = 0.5 * (curve[:-1, 2] + curve[1:, 2])
    d_lo, span = zmid.min(), (zmid.max() - zmid.min()) or 1.0
    depth_f = 0.55 + 0.45 * ((zmid - d_lo) / span)

    spectrum = plt.get_cmap(cmap)(np.linspace(0.0, 1.0, len(segs)))[:, :3]
    colors = spectrum * depth_f[:, None]  # shade toward black with depth

    order = np.argsort(zmid)  # painter's: back-to-front
    segs_o, colors_o = segs[order], colors[order]

    fig, ax = plt.subplots(figsize=(size, size), dpi=dpi)
    lw = size * 1.9
    ax.add_collection(LineCollection(segs_o, colors=(0.09, 0.09, 0.10),
                                    linewidths=lw + 4.0, capstyle="round",
                                    joinstyle="round"))
    ax.add_collection(LineCollection(segs_o, colors=colors_o, linewidths=lw,
                                    capstyle="round", joinstyle="round"))
    pad = 3.0
    ax.set_xlim(curve[:, 0].min() - pad, curve[:, 0].max() + pad)
    ax.set_ylim(curve[:, 1].min() - pad, curve[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0.0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def _pdb_path_for(seq: str) -> Path:
    return DEFAULT_CACHE / f"{_seq_hash(seq.strip().upper())}.pdb"


# Shared PyMOL cartoon look (ray-traced cartoon with a black outline).
_BASE = """hide everything
dss mol
show cartoon, mol
set cartoon_fancy_helices, 1
set cartoon_highlight_color, grey50
set ray_shadows, 1
set ambient, 0.42
set specular, 0.2
set antialias, 2
set ray_trace_mode, 1
set ray_trace_color, black
"""

# Colour schemes. "spectrum" = rainbow N->C; "ss" = by secondary structure so
# beta sheets (gold) and helices (red) read at a glance, loops recede (grey).
_COLOR = {
    "spectrum": "spectrum resi, rainbow, mol\n",
    "ss": ("color 0xCCD0CB, mol\n"
           "color 0xC7513B, mol and ss H\n"
           "color 0xE3A72F, mol and ss S\n"),
}


def _settings(color: str) -> str:
    return _BASE + _COLOR.get(color, _COLOR["spectrum"])


def _pml_still(pdb_path: Path, out_png: Path, color: str, size: int = 1500) -> str:
    """Ray-trace one structure as a still cartoon ribbon (transparent background)."""
    return f"""reinitialize
load {pdb_path}, mol
{_settings(color)}bg_color white
set ray_opaque_background, 0
orient mol
zoom mol, 1, complete=1
ray {size}, {size}
png {out_png}, dpi=300
"""


def _pml_rotation(pdb_path: Path, frames_dir: Path, frames: int, size: int,
                  color: str, bg: str = "white") -> str:
    """Ray-trace a full 360deg Y-rotation into numbered frames (opaque background)."""
    return f"""reinitialize
load {pdb_path}, mol
{_settings(color)}bg_color {bg}
set ray_opaque_background, 1
orient mol
zoom mol, 1, complete=1
python
from pymol import cmd
n = {frames}
for i in range(n):
    cmd.turn('y', 360.0 / n)
    cmd.ray({size}, {size})
    cmd.png(r'{frames_dir}/f_%03d.png' % i, dpi=150)
python end
"""


def _domain_jobs(only: set[str] | None = None):
    """Yield (poem_stem, domain_index, pdb_path) for every folded domain.

    ``only`` optionally restricts to a set of poem stems.
    """
    for path in sorted((POEM_ROOT / "data" / "poems").glob("*.txt")):
        if only and path.stem not in only:
            continue
        chunks = poem_chunks(path.read_text(encoding="utf-8"))
        for i, seq in enumerate(chunks, start=1):
            if fold_sequence(seq) is None:  # ensures the cached PDB exists
                print(f"! fold failed: {path.stem} domain {i}", file=sys.stderr)
                continue
            yield path.stem, i, _pdb_path_for(seq)


def render_poems_pymol(color: str = "spectrum", only: set[str] | None = None,
                       size: int = 1500) -> None:
    """Ray-trace a still cartoon ribbon per domain into results/snapshots/."""
    out_dir = POEM_ROOT / "results" / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    blocks, produced = [], []
    for stem, i, pdb in _domain_jobs(only):
        out = out_dir / f"{stem}__d{i}.png"
        blocks.append(_pml_still(pdb, out, color, size))
        produced.append(out)

    script = out_dir / "_render.pml"
    script.write_text("\n".join(blocks))
    print(f"rendering {len(produced)} domains ({color}) with PyMOL ...", file=sys.stderr)
    subprocess.run([PYMOL_BIN, "-cq", str(script)], check=True)
    script.unlink(missing_ok=True)
    for out in produced:
        print(f"  {out.relative_to(POEM_ROOT)} {'ok' if out.exists() else 'MISSING'}")


def render_rotation_videos(frames: int = 36, size: int = 520, fps: int = 24,
                           color: str = "spectrum", bg: str = "white",
                           only: set[str] | None = None) -> None:
    """Render a 360deg rotation MP4 per domain into results/videos/ (needs ffmpeg).

    ``bg`` is the (opaque) background; use the page colour (e.g. "0xf0ebe6") so the
    looping clip sits seamlessly on the site with no fringing.
    """
    out_dir = POEM_ROOT / "results" / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)

    for stem, i, pdb in _domain_jobs(only):
        name = f"{stem}__d{i}"
        frames_dir = out_dir / "_frames" / name
        if frames_dir.exists():
            for f in frames_dir.glob("*.png"):
                f.unlink()
        frames_dir.mkdir(parents=True, exist_ok=True)

        script = frames_dir / "_rot.pml"
        script.write_text(_pml_rotation(pdb, frames_dir, frames, size, color, bg))
        print(f"spinning {name} ({frames} frames) ...", file=sys.stderr)
        subprocess.run([PYMOL_BIN, "-cq", str(script)], check=True)

        mp4 = out_dir / f"{name}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
            "-i", str(frames_dir / "f_%03d.png"),
            "-vf", f"scale={size}:{size}:flags=lanczos,format=yuv420p",
            "-c:v", "libx264", "-crf", "23", "-movflags", "+faststart", str(mp4),
        ], check=True)
        for f in frames_dir.glob("*.png"):
            f.unlink()
        script.unlink(missing_ok=True)
        print(f"  {mp4.relative_to(POEM_ROOT)} {'ok' if mp4.exists() else 'MISSING'}")

    frames_root = out_dir / "_frames"
    if frames_root.exists():
        for d in sorted(frames_root.glob("*"), reverse=True):
            d.rmdir()
        frames_root.rmdir()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", action="store_true",
                        help="render 360deg rotation MP4s instead of still images")
    parser.add_argument("--color", choices=("spectrum", "ss"), default="spectrum",
                        help="rainbow N->C (spectrum) or by secondary structure (ss)")
    parser.add_argument("--only", default=None,
                        help="comma-separated poem stems to restrict rendering to")
    args = parser.parse_args()
    only = set(args.only.split(",")) if args.only else None
    if args.video:
        render_rotation_videos(color=args.color, only=only)
    else:
        render_poems_pymol(color=args.color, only=only)


if __name__ == "__main__":
    main()
