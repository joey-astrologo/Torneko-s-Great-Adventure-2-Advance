"""Record installed tools and verify assembler output plus BPS round trips."""

from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile

import mgba.core

from tools.emulator import version
from tools.bps import create_patch
from tools.prepare_sources import SOURCES
from tools.rom import ROOT, digest, inspect, load_base, require


def command(*args):
    return subprocess.check_output(args, text=True, cwd=ROOT).strip()


def verify():
    output = ROOT / "build/toolchain-validation"
    output.mkdir(parents=True, exist_ok=True)
    packages = {}
    for line in (ROOT / "docs/python-toolchain.lock.txt").read_text().splitlines():
        name, pin = line.split("==")
        actual = importlib.metadata.version(name)
        require(actual == pin, f"Python package version differs: {name}: {actual}")
        packages[name] = actual
    require(platform.machine() == "arm64" and sys.version_info[:2] == (3, 11), "Expected native arm64 Python 3.11")
    require(Path(mgba.core.__file__).resolve().is_relative_to(ROOT / ".tools/build/mgba"),
            "mGBA bindings resolve outside this project")
    require(version() == "0.10.5", "Wrong mGBA native library version")
    with Path("/Applications/mGBA.app/Contents/Info.plist").open("rb") as file:
        desktop = plistlib.load(file)["CFBundleShortVersionString"]
    require(desktop == version(), "Desktop and Python mGBA versions differ")
    sources = {}
    for name, (url, pin) in SOURCES.items():
        source = ROOT / ".tools/src" / name
        if (source / ".git").exists():
            actual = command("git", "-C", str(source), "rev-parse", "HEAD")
            require(actual == pin, f"Wrong source commit: {name}")
            sources[name] = {"commit": actual, "repository": url,
                             "tracked_diff_sha256": digest(command("git", "-C", str(source), "diff", "HEAD").encode())}
        else:
            require(name == "flips-local", f"Missing source checkout: {source}")
            manifest = json.loads((ROOT / "tools/flips-toolchain.json").read_text())
            require(manifest["commit"] == pin, "Flips source pin changed")
            for entry in manifest["source_files"]:
                require(digest((source / entry["path"]).read_bytes()) == entry["sha256"],
                        f"Flips source mismatch: {entry['path']}")
            sources[name] = {"commit": pin, "repository": url, "verified_source_files": len(manifest["source_files"])}
    with tempfile.TemporaryDirectory(prefix="assembly-", dir=output) as directory:
        directory = Path(directory)
        assembly = directory / "smoke.asm"
        assembly.write_text('.gba\n.create "smoke.bin", 0\n.arm\nmov r0, 1\nbx lr\n.thumb\nmov r0, 2\nbx lr\n.close\n')
        subprocess.run([str(ROOT / ".tools/bin/armips"), str(assembly)], cwd=directory, check=True)
        assembled = (directory / "smoke.bin").read_bytes()
        require(assembled.hex() == "0100a0e31eff2fe102207047", "ARM/Thumb assembly bytes differ")
        (output / "armips-smoke.asm").write_text(assembly.read_text())
        (output / "armips-smoke.bin").write_bytes(assembled)
        # Synthetic buffers exercise packaging without asserting any ROM insertion.
        source, target = directory / "source.bin", directory / "target.bin"
        source.write_bytes(bytes(range(256)) * 4)
        target.write_bytes(source.read_bytes() + b"Torneko 2 tooling check\0")
        patch, applied = directory / "test.bps", directory / "applied.bin"
        append_only = create_patch(source, target, patch)
        changed = bytearray(target.read_bytes())
        changed[100:113] = b"changed bytes"
        target.write_bytes(changed)
        changed_and_expanded = create_patch(source, target, patch)
        subprocess.run([str(ROOT / ".tools/bin/flips"), "--apply", "--exact", str(patch), str(source), str(applied)], check=True)
        require(applied.read_bytes() == target.read_bytes(), "BPS apply round trip differs")
        source.write_bytes(b"incorrect input")
        rejected = subprocess.run([str(ROOT / ".tools/bin/flips"), "--apply", str(patch), str(source), str(applied)], capture_output=True)
        require(rejected.returncode != 0, "BPS accepted an incorrect source")
    ghidra_properties = Path("/opt/homebrew/opt/ghidra/libexec/Ghidra/application.properties").read_text()
    require("application.version=12.1.3\n" in ghidra_properties, "Ghidra version differs from pin")
    extension = Path("/opt/homebrew/opt/ghidra/libexec/Ghidra/Extensions/gba-ghidra-loader/extension.properties").read_text()
    require("version=12.1.3" in extension, "GBA loader version differs from installed Ghidra")
    report = {"passed": True, "checked_at": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": sys.version, "packages": packages,
              "mgba": {"python": version(), "desktop": desktop, "binding_path": mgba.core.__file__},
              "ghidra": {"version": "12.1.3", "loader_version": "12.1.3"},
              "sources": sources, "rom": inspect(load_base()),
              "armips_expected_bytes": assembled.hex(), "bps_roundtrip": True,
              "bps_probes": {"append_only": append_only, "changed_and_expanded": changed_and_expanded},
              "bps_wrong_source_rejected": True,
              "executables": {name: digest((ROOT / ".tools/bin" / name).read_bytes()) for name in ("armips", "flips")},
              "patches": {p.name: digest(p.read_bytes()) for p in (ROOT / "tools/patches").glob("*.patch")}}
    (output / "toolchain.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Toolchain, ARM/Thumb assembly, and BPS verification passed.")


if __name__ == "__main__":
    verify()
