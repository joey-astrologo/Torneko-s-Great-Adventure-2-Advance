#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
TORNEKO_BROWSER_TMP="$(mktemp -d /tmp/torneko-font-browser.XXXXXX)"
trap 'rm -rf "$TORNEKO_BROWSER_TMP"' EXIT
clang -fobjc-arc -framework Cocoa -framework WebKit tools/verify_font_audition.m -o "$TORNEKO_BROWSER_TMP/check"
"$TORNEKO_BROWSER_TMP/check" "$PWD/build/font-audition/index.html" "$PWD/tools/check_font_audition.js" "$PWD/build/font-audition"
.venv/bin/python - <<'PY'
import json
from tools.rom import ROOT,digest
root=ROOT/'build/font-audition';path=root/'browser-checks.json'
report=json.loads(path.read_text())
report['page_sha256']=digest((root/'index.html').read_bytes())
report['checks_sha256']=digest((ROOT/'tools/check_font_audition.js').read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n')
PY
