#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
TORNEKO_TITLE_TMP="$(mktemp -d /tmp/torneko-title-browser.XXXXXX)"
trap 'rm -rf "$TORNEKO_TITLE_TMP"' EXIT
clang -fobjc-arc -framework Cocoa -framework WebKit tools/verify_title_audition.m -o "$TORNEKO_TITLE_TMP/check"
"$TORNEKO_TITLE_TMP/check" "$PWD/build/title-audition/index.html" "$PWD/tools/title_audition/read_checks.js" "$PWD/build/title-audition"
.venv/bin/python -m tools.verify_title_audition
