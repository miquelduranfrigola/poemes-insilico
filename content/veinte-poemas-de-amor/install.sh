#!/usr/bin/env bash
# Portable, self-contained setup for a single poem.
# Creates an isolated virtualenv, installs this poem's dependencies and pulls
# its large assets from Google Drive. Run from inside the poem's folder.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

cd "$HERE"

# 1. Isolated environment for this poem.
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip

# 2. This poem's own dependencies (optional; needed only to re-run the chain).
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# 3. Rebuild the self-contained despoetization gallery (no third-party deps).
if [ -f code/build_gallery.py ]; then
  python code/build_gallery.py
fi

# 4. Pull large assets referenced in the Drive manifest (optional).
if [ -f assets/drive-manifest.yml ]; then
  pip install gdown pyyaml >/dev/null
  python "$REPO_ROOT/scripts/fetch_assets.py" assets/drive-manifest.yml
fi

echo "Done. Activate with: source .venv/bin/activate"
