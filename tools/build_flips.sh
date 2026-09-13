#!/bin/bash
set -euo pipefail
TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TORNEKO_ROOT"
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from tools.rom import digest, require
manifest=json.loads(Path('tools/flips-toolchain.json').read_text())
source=Path(manifest['source_directory'])
for entry in manifest['source_files']:
    require(digest((source/entry['path']).read_bytes())==entry['sha256'], 'Flips source mismatch: '+entry['path'])
PY
make -C .tools/src/flips-local TARGET=cli CFLAGS=-O2 CXX=clang++ COMMIT_COUNT=
mkdir -p .tools/bin
install -m 755 .tools/src/flips-local/flips .tools/bin/flips
