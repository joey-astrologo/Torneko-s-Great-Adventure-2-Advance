#!/bin/bash
set -euo pipefail

TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$TORNEKO_ROOT"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
export GRADLE_USER_HOME="$TORNEKO_ROOT/.tools/gradle-user"
TORNEKO_LOADER_PATCH="$TORNEKO_ROOT/tools/patches/gba-loader-remove-unused-jython-import.patch"
if ! git -C .tools/src/gba-ghidra-loader apply --reverse --check "$TORNEKO_LOADER_PATCH" 2>/dev/null; then
  git -C .tools/src/gba-ghidra-loader apply --check "$TORNEKO_LOADER_PATCH"
  git -C .tools/src/gba-ghidra-loader apply "$TORNEKO_LOADER_PATCH"
fi
/opt/homebrew/bin/gradle --no-daemon -p .tools/src/gba-ghidra-loader \
  -PGHIDRA_INSTALL_DIR="/opt/homebrew/opt/ghidra/libexec" buildExtension
