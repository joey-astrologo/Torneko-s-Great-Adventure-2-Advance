#!/bin/bash
set -euo pipefail
TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$TORNEKO_ROOT/tools/ghidra.sh" verify "$@"
