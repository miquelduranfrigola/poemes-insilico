#!/usr/bin/env python3
"""Download large assets referenced in a `drive-manifest.yml` from Google Drive.

Usage:
    python scripts/fetch_assets.py path/to/drive-manifest.yml

The manifest is a YAML list of entries:
    - name: raw-audio
      path: assets/raw-audio.wav      # destination, relative to the manifest's folder
      url: https://drive.google.com/uc?id=FILE_ID
      bytes: 5242880                  # optional

Downloaded files are placed next to the manifest and are gitignored. Existing
files are skipped unless --force is given. Requires `gdown` and `pyyaml`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("error: pyyaml is required (pip install pyyaml)")


def load_manifest(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        sys.exit(f"error: manifest not found: {manifest_path}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if data is None:
        return []
    if not isinstance(data, list):
        sys.exit("error: manifest must be a YAML list of asset entries")
    return data


def fetch(manifest_path: Path, force: bool) -> None:
    entries = load_manifest(manifest_path)
    if not entries:
        print(f"No assets listed in {manifest_path}")
        return

    try:
        import gdown
    except ImportError:
        sys.exit("error: gdown is required (pip install gdown)")

    base = manifest_path.resolve().parent
    for entry in entries:
        name = entry.get("name", "<unnamed>")
        url = entry.get("url")
        rel_path = entry.get("path")
        if not url or not rel_path:
            print(f"skip {name}: missing 'url' or 'path'")
            continue

        dest = (base / rel_path).resolve()
        if dest.exists() and not force:
            print(f"skip {name}: already present at {rel_path}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name} -> {rel_path}")
        gdown.download(url, str(dest), quiet=False, fuzzy=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to a drive-manifest.yml")
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if the file exists"
    )
    args = parser.parse_args()
    fetch(args.manifest, force=args.force)


if __name__ == "__main__":
    main()
