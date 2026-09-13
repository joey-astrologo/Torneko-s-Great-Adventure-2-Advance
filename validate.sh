#!/bin/bash
set -euo pipefail
TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TORNEKO_ROOT"
.venv/bin/python -m tools.rom
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.verify_toolchain
.venv/bin/python -m tools.verify_mgba
bash tools/verify_ghidra.sh
echo 'All checks passed. Reports: build/toolchain-validation/'
