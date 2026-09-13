#!/bin/bash
set -euo pipefail
TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TORNEKO_ROOT"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Duser.home=$TORNEKO_ROOT/.tools/ghidra-home"
TORNEKO_HEADLESS="/opt/homebrew/opt/ghidra/libexec/support/analyzeHeadless"
TORNEKO_ACTION="${1:-verify}"
if [[ $# -gt 0 ]]; then shift; fi
TORNEKO_ROM="$(.venv/bin/python -c 'from tools.rom import default_rom,load_base; load_base(); print(default_rom())')"
mkdir -p build/toolchain-validation build/disassembly build/ghidra .tools/ghidra-home
case "$TORNEKO_ACTION" in
  verify)
    [[ $# -eq 0 ]] || { echo 'verify takes no arguments' >&2; exit 2; }
    TORNEKO_SCRIPT=VerifyGbaImport.java
    TORNEKO_MARKER=TORNEKO_GBA_IMPORT_OK
    ;;
  import)
    [[ $# -eq 0 ]] || { echo 'import takes no arguments' >&2; exit 2; }
    if [[ -e build/ghidra/Torneko2.gpr || -e build/ghidra/Torneko2.rep ]]; then
      echo 'Project already exists: open build/ghidra/Torneko2.gpr in Ghidra.' >&2
      exit 1
    fi
    TORNEKO_SCRIPT=VerifyGbaImport.java
    TORNEKO_MARKER=TORNEKO_GBA_IMPORT_OK
    ;;
  functions|range)
    [[ $# -ge 2 ]] || { echo 'Usage: tools/ghidra.sh functions|range output.txt addresses...' >&2; exit 2; }
    TORNEKO_OUTPUT="$(.venv/bin/python -c 'from pathlib import Path; import sys; p=Path(sys.argv[1]).resolve(); p.parent.mkdir(parents=True,exist_ok=True); print(p)' "$1")"
    shift
    if [[ "$TORNEKO_ACTION" == functions ]]; then
      TORNEKO_SCRIPT=InspectThumbFunctions.java
      TORNEKO_MARKER=TORNEKO_THUMB_INSPECTION_OK
    else
      TORNEKO_SCRIPT=InspectThumbRange.java
      TORNEKO_MARKER=TORNEKO_THUMB_RANGES_OK
    fi
    ;;
  *) echo 'Usage: tools/ghidra.sh verify|import|functions|range ...' >&2; exit 2 ;;
esac
if [[ "$TORNEKO_ACTION" == import ]]; then
  TORNEKO_PROJECT_DIR="$TORNEKO_ROOT/build/ghidra"
else
  TORNEKO_PROJECT_DIR="$(mktemp -d "$TORNEKO_ROOT/build/toolchain-validation/ghidra.XXXXXX")"
  trap 'rmdir "$TORNEKO_PROJECT_DIR" 2>/dev/null || true' EXIT
fi
TORNEKO_LOG="$TORNEKO_ROOT/build/toolchain-validation/ghidra-$TORNEKO_ACTION.log"
TORNEKO_COMMAND=("$TORNEKO_HEADLESS" "$TORNEKO_PROJECT_DIR" Torneko2
  -import "$TORNEKO_ROM" -loader GBALoader -noanalysis
  -scriptPath "$TORNEKO_ROOT/tools/ghidra_scripts" -postScript "$TORNEKO_SCRIPT")
if [[ "$TORNEKO_ACTION" == functions || "$TORNEKO_ACTION" == range ]]; then
  TORNEKO_COMMAND+=("$TORNEKO_OUTPUT" "$@")
fi
if [[ "$TORNEKO_ACTION" != import ]]; then TORNEKO_COMMAND+=(-deleteProject); fi
if ! "${TORNEKO_COMMAND[@]}" > "$TORNEKO_LOG" 2>&1; then
  tail -n 65 "$TORNEKO_LOG" >&2
  exit 1
fi
# Script exceptions do not reliably change analyzeHeadless's exit status.
if ! rg -F "$TORNEKO_MARKER" "$TORNEKO_LOG"; then
  tail -n 65 "$TORNEKO_LOG" >&2
  exit 1
fi
