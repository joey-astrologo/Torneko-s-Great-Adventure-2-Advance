#!/bin/bash
set -euo pipefail

TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TORNEKO_ROOT"
export PATH="$TORNEKO_ROOT/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PKG_CONFIG_PATH="/opt/homebrew/opt/libedit/lib/pkgconfig:/opt/homebrew/opt/libffi/lib/pkgconfig"
TORNEKO_MGBA_PATCH="$TORNEKO_ROOT/tools/patches/mgba-0.10.5-optional-ereader.patch"
if ! git -C .tools/src/mgba apply --reverse --check "$TORNEKO_MGBA_PATCH" 2>/dev/null; then
  git -C .tools/src/mgba apply --check "$TORNEKO_MGBA_PATCH"
  git -C .tools/src/mgba apply "$TORNEKO_MGBA_PATCH"
fi
TORNEKO_PYTHON_LIBRARY="/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/Python"
test -f "$TORNEKO_PYTHON_LIBRARY"

cmake -S .tools/src/mgba -B .tools/build/mgba \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_POLICY_DEFAULT_CMP0148=OLD \
  '-DCMAKE_PREFIX_PATH=/opt/homebrew;/opt/homebrew/opt/libedit;/opt/homebrew/opt/libffi' \
  -DCMAKE_IGNORE_PREFIX_PATH=/usr/local \
  -DBUILD_PYTHON=ON -DBUILD_SHARED=ON \
  -DBUILD_QT=OFF -DBUILD_SDL=OFF -DBUILD_GL=OFF \
  -DUSE_FFMPEG=OFF -DUSE_DISCORD_RPC=OFF \
  -DUSE_DEBUGGERS=ON -DUSE_GDB_STUB=ON -DENABLE_SCRIPTING=ON -DUSE_LUA=OFF \
  -DUSE_PYTHON_VERSION=3.11 \
  -DPYTHON_EXECUTABLE="$TORNEKO_ROOT/.venv/bin/python" \
  -DPYTHON_INCLUDE_DIR="$(python -c 'import sysconfig; print(sysconfig.get_path("include"))')" \
  -DPYTHON_LIBRARY="$TORNEKO_PYTHON_LIBRARY"
cmake --build .tools/build/mgba --target mgba-py --parallel 4

python - <<'PY'
from pathlib import Path
import sysconfig

build = Path('.tools/build/mgba/python').resolve()
packages = [path for path in build.glob('lib*') if (path / 'mgba' / '__init__.py').is_file()]
if len(packages) != 1:
    raise SystemExit(f'Expected one built mgba package; found {packages}')
site_packages = Path(sysconfig.get_path('purelib'))
(site_packages / 'torneko-mgba.pth').write_text(str(packages[0]) + '\n')
print('Registered mGBA package:', packages[0])
PY
python -c 'import mgba.core, mgba.image; print(mgba.core.__file__)'
