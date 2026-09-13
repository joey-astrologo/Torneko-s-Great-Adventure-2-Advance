"""Prepare independent pinned source checkouts, optionally from Torneko 3."""

import argparse
from pathlib import Path
import shutil
import subprocess

from tools.rom import ROOT, require

SOURCES = {
    "mgba": ("https://github.com/mgba-emu/mgba.git", "26b7884bc25a5933960f3cdcd98bac1ae14d42e2"),
    "armips": ("https://github.com/Kingcom/armips.git", "156f78f6bccfc07498578ac491ce7fe2a1e807a6"),
    "gba-ghidra-loader": ("https://github.com/pudii/gba-ghidra-loader.git", "9bfb2d1fe891aa78bab7093a328feb3a52318ab7"),
    "flips-local": ("https://github.com/Sir-Walrus/Flips.git", "ff216a75df0987047a67d7923567dc4482ce07ac"),
}


def prepare(reference=None):
    base = ROOT / ".tools/src"
    base.mkdir(parents=True, exist_ok=True)
    for name, (url, commit) in SOURCES.items():
        target = base / name
        if not target.exists():
            if reference:
                source = reference.resolve() / ".tools/src" / name
                # Copy, including Git objects, to avoid linked worktrees or shared objects.
                shutil.copytree(source, target, ignore=shutil.ignore_patterns("build", "dist", ".gradle", "__pycache__"))
            else:
                target.mkdir()
                subprocess.run(["git", "init", str(target)], check=True)
                subprocess.run(["git", "-C", str(target), "remote", "add", "origin", url], check=True)
                subprocess.run(["git", "-C", str(target), "fetch", "--depth=1", "origin", commit], check=True)
                subprocess.run(["git", "-C", str(target), "checkout", "--detach", commit], check=True)
        if name == "flips-local" and not (target / ".git").exists():
            # Torneko 3 downloaded an exact source snapshot; build_flips checks every file.
            continue
        actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
        require(actual == commit, f"Unexpected source revision: {name}: {actual}")
        print(f"{name}: {actual}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    prepare(args.reference)
