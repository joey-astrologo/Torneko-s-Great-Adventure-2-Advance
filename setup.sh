#!/bin/bash
set -euo pipefail
TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TORNEKO_ROOT"
TORNEKO_PYTHON="/opt/homebrew/opt/python@3.11/bin/python3.11"
TORNEKO_REFERENCE="${1:-}"
[[ $# -le 1 ]] || { echo 'Usage: ./setup.sh [path/to/torneko-3-gba]' >&2; exit 2; }
if [[ -n "$TORNEKO_REFERENCE" ]]; then
  TORNEKO_REFERENCE="$("$TORNEKO_PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=True))' "$TORNEKO_REFERENCE")"
fi
[[ -x .venv/bin/python ]] || "$TORNEKO_PYTHON" -m venv .venv
mkdir -p .tools/wheels build/toolchain-validation
if [[ -n "$TORNEKO_REFERENCE" ]]; then
  .venv/bin/python -m tools.repack_installed_wheels "$TORNEKO_REFERENCE"
  .venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir --no-index --find-links .tools/wheels -r docs/python-toolchain.lock.txt
  .venv/bin/python -m tools.prepare_sources --reference "$TORNEKO_REFERENCE"
else
  .venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir -r docs/python-toolchain.lock.txt
  .venv/bin/python -m tools.prepare_sources
fi
bash tools/build_mgba.sh > build/toolchain-validation/mgba-build.log 2>&1 || { tail -n 60 build/toolchain-validation/mgba-build.log; exit 1; }
bash tools/build_armips.sh > build/toolchain-validation/armips-build.log 2>&1 || { tail -n 60 build/toolchain-validation/armips-build.log; exit 1; }
bash tools/build_flips.sh > build/toolchain-validation/flips-build.log 2>&1 || { tail -n 60 build/toolchain-validation/flips-build.log; exit 1; }
echo 'Local tools built. Run ./validate.sh for ROM and emulator acceptance.'
