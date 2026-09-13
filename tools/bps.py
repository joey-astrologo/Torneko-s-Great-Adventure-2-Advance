"""Create a BPS patch only after applying it reproduces the target exactly."""

import argparse
from pathlib import Path
import subprocess
import tempfile

from tools.rom import ROOT, digest, require


def create_patch(source, target, output):
    source, target, output = (Path(p).resolve() for p in (source, target, output))
    require(output not in (source, target), "Patch output must differ from both inputs")
    original, translated = source.read_bytes(), target.read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    with tempfile.TemporaryDirectory(prefix="bps-", dir=output.parent) as directory:
        folder = Path(directory)
        clean, changed = folder / "source.bin", folder / "target.bin"
        clean.write_bytes(original)
        changed.write_bytes(translated)
        patch, applied = folder / "patch.bps", folder / "applied.bin"
        for encoder in ("--bps-linear", "--bps-delta"):
            # The pinned linear encoder has an append-only edge case. Validate
            # both paths, falling back to upstream delta without changing pins.
            made = subprocess.run([str(ROOT / ".tools/bin/flips"), "--create", "--exact", encoder,
                                   str(clean), str(changed), str(patch)], capture_output=True)
            if made.returncode == 0:
                checked = subprocess.run([str(ROOT / ".tools/bin/flips"), "--apply", "--exact",
                                          str(patch), str(clean), str(applied)], capture_output=True)
                if checked.returncode == 0 and applied.read_bytes() == translated:
                    require(source.read_bytes() == original and target.read_bytes() == translated,
                            "BPS input changed during creation")
                    patch_hash = digest(patch.read_bytes())
                    patch.replace(output)
                    return {"encoder": encoder, "source_sha256": digest(original),
                            "target_sha256": digest(translated), "patch_sha256": patch_hash,
                            "apply_matches_target": True, "fallback_from": failures}
            failures.append(encoder)
    raise RuntimeError("Neither BPS encoder produced a verified patch")


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(create_patch(args.source, args.target, args.output), indent=2))
