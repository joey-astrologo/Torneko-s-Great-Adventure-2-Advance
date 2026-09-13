#!/bin/bash
set -euo pipefail
TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TORNEKO_ROOT"
export PATH="$TORNEKO_ROOT/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cmake -S .tools/src/armips -B .tools/build/armips -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build .tools/build/armips --target armips-bin --parallel 4
mkdir -p .tools/bin
ln -sfn ../build/armips/armips .tools/bin/armips
