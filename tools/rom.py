"""Identify and validate the supplied Japanese base without modifying it."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/rom.json"
ROM_BASE = 0x08000000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def manifest():
    return json.loads(MANIFEST.read_text())


def default_rom():
    return ROOT / manifest()["filename"]


def inspect(data):
    require(len(data) >= 0xC0, "Truncated GBA header")
    branch = int.from_bytes(data[:4], "little")
    require(branch >> 24 == 0xEA, "Expected an ARM branch at cartridge entry")
    displacement = branch & 0xFFFFFF
    if displacement & 0x800000:
        displacement -= 0x1000000
    entry = ROM_BASE + 8 + displacement * 4
    checksum = (-sum(data[0xA0:0xBD]) - 0x19) & 255
    require(data[0xB2] == 0x96, "Invalid GBA fixed header byte")
    require(data[0xBD] == checksum, "Invalid GBA header checksum")
    require(ROM_BASE <= entry < ROM_BASE + len(data), "Entry outside cartridge")
    return {
        "sha256": digest(data), "size": len(data),
        "title": data[0xA0:0xAC].rstrip(b"\0").decode("ascii"),
        "game_code": data[0xAC:0xB0].decode("ascii"),
        "maker_code": data[0xB0:0xB2].decode("ascii"),
        "revision": data[0xBC], "header_checksum": f"0x{checksum:02X}",
        "entry": f"0x{entry:08X}", "header_valid": True,
    }


def load_base(path=None):
    path = Path(path) if path is not None else default_rom()
    data = path.read_bytes()
    report = inspect(data)
    for key in ("sha256", "size", "title", "game_code", "maker_code", "revision"):
        require(report[key] == manifest()[key], f"Base ROM {key} mismatch: {path}")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=default_rom())
    args = parser.parse_args()
    print(json.dumps(inspect(load_base(args.rom)), indent=2))


if __name__ == "__main__":
    main()
