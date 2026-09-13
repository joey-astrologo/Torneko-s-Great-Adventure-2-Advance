"""Prepare a separate ROM/save pair for desktop mGBA; never open the originals."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from tools.rom import ROOT, default_rom, digest, load_base


def prepare(rom, save=None):
    data = load_base(rom)
    output = ROOT / "build/playtest"
    output.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-"), dir=output))
    target = folder / "torneko-2-japanese.gba"
    target.write_bytes(data)
    battery = save.read_bytes() if save else None
    if battery is not None:
        target.with_suffix(".sav").write_bytes(battery)
    (folder / "source.json").write_text(json.dumps({
        "source_rom": str(rom.resolve()), "rom_sha256": digest(data),
        "source_save": str(save.resolve()) if save else None,
        "initial_save_sha256": digest(battery) if battery is not None else None,
    }, indent=2) + "\n")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=default_rom())
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    print(prepare(args.rom, args.save))
