#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
TORNEKO_GRAPHICS_TMP="$(mktemp -d /tmp/torneko-graphics-browser.XXXXXX)"
trap 'rm -rf "$TORNEKO_GRAPHICS_TMP"' EXIT
clang -fobjc-arc -framework Cocoa -framework WebKit tools/verify_graphics_audition.m -o "$TORNEKO_GRAPHICS_TMP/check"
for TORNEKO_GRAPHICS_FAMILY in credits arrival-cards; do
  "$TORNEKO_GRAPHICS_TMP/check" "$PWD/build/$TORNEKO_GRAPHICS_FAMILY/audition/index.html" "$PWD/tools/check_graphics_audition.js" "$PWD/build/$TORNEKO_GRAPHICS_FAMILY/audition"
done
.venv/bin/python - <<'PY'
import json
from tools.rom import ROOT, digest, require
for family in ('credits', 'arrival-cards'):
    folder=ROOT/'build'/family/'audition'
    report=json.loads((folder/'browser-checks.json').read_text())
    require(report['passed'], 'Browser checks failed')
    (folder/'all-font-budgets.csv').write_text(report.pop('all_font_budgets_csv'))
    report['html_sha256']=digest((folder/'index.html').read_bytes())
    report['checks_sha256']=digest((ROOT/'tools/check_graphics_audition.js').read_bytes())
    (folder/'browser-checks.json').write_text(json.dumps(report,indent=2)+'\n')
PY
