"""Build a checked compact-font extension and an optional initial-menu specimen."""

import argparse
from functools import lru_cache
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from tools.bps import create_patch
from tools.compact_font import ASSET, encode, load_font, measure, pack_font
from tools.review_fonts import LABEL_BYTES, LABEL_END, LABEL_OFFSET, LABEL_POINTER
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.rom_build import RomBuild

OUTPUT = ROOT / "build/compact-font"
FONT_OFFSET = 0x00800000
HOOK_OFFSET = 0x00800BE0
HOOK_BYTES = 128
HOOK_SITE = 0x1A04
HOOK_EXPECTED = bytes.fromhex("0004010c0023044a")


@lru_cache(maxsize=2)
def assemble_hook(compact_numbers=False):
    aliases = f'''
    ldr r2, =0x{0x08000000 + HOOK_OFFSET + HOOK_BYTES:08X}
numeric_loop:
    ldr r3, [r2]
    cmp r3, 0
    beq native_lookup
    cmp r1, r3
    beq numeric_found
    add r2, 8
    b numeric_loop
numeric_found:
    ldr r0, [r2, 4]
    bx lr
native_lookup:
''' if compact_numbers else ''
    source = f'''.gba
.create "hook.bin", 0x{0x08000000 + HOOK_OFFSET:08X}
.thumb
.area {HOOK_BYTES}, 0xFF
    lsl r0, r0, 16
    lsr r1, r0, 16
    ldr r2, =0xF020
    cmp r1, r2
    blo original_lookup
    ldr r3, =0xF07E
    cmp r1, r3
    bhi original_lookup
    sub r1, r1, r2
    lsl r0, r1, 5
    ldr r1, =0x{0x08000000 + FONT_OFFSET:08X}
    add r0, r0, r1
    bx lr
original_lookup:
{aliases}
    mov r3, 0
    ldr r2, =0x0812B5A8
    ldr r0, =0x08001A0D
    bx r0
    .align 4
    .pool
.endarea
.close
'''
    with tempfile.TemporaryDirectory(prefix="compact-font-asm-") as directory:
        folder = Path(directory)
        (folder / "hook.asm").write_text(source)
        subprocess.run([str(ROOT / ".tools/bin/armips"), "hook.asm"], cwd=folder, check=True)
        data = (folder / "hook.bin").read_bytes()
    require(len(data) == HOOK_BYTES, "Font hook exceeded its allocation")
    return data, source


def add_font(build, asset=ASSET, compact_numbers=False):
    """Add the font to a shared ledger before other localization resources."""
    font = load_font(asset)
    require(build.allocate("english-font", pack_font(font), "compact-english") == FONT_OFFSET, "Font allocation moved")
    hook, source = assemble_hook(compact_numbers)
    require(build.allocate("english-font-lookup", hook, "compact-english") == HOOK_OFFSET, "Hook allocation moved")
    if compact_numbers:
        from tools.numeric_font import resource
        offset = HOOK_OFFSET + HOOK_BYTES
        require(build.allocate('compact-numeric-aliases', resource(font, offset), 'compact-english') == offset,
                'Numeric alias allocation moved')
    # Thumb ldr r3,[pc,#0]; bx r3; literal points to the appended Thumb helper.
    jump = bytes.fromhex("004b1847") + struct.pack("<I", 0x08000000 + HOOK_OFFSET + 1)
    build.patch("font-lookup-entry", HOOK_SITE, HOOK_EXPECTED, jump, "compact-english")
    return {"font_asset_sha256": digest(asset.read_bytes()), "font_codes": [0xF020, 0xF07E],
            "shared_allocator": True, "hook_source": source, "compact_numbers": compact_numbers}


def build_rom(sample=None):
    original, font = load_base(), load_font()
    require(original[LABEL_OFFSET:LABEL_END] == LABEL_BYTES, "Original specimen label differs")
    build = RomBuild(original)
    metadata = add_font(build)
    if sample is not None:
        require("\n" not in sample and measure(" " + sample, font) <= 96, "Specimen exceeds the observed menu width")
        label = build.allocate("font-specimen-label", encode(" " + sample), "compact-font-specimen")
        build.patch("font-specimen-pointer", LABEL_POINTER, struct.pack("<I", 0x08000000 + LABEL_OFFSET),
                    struct.pack("<I", 0x08000000 + label), "compact-font-specimen")
    data, report = build.finish()
    report.update(metadata, sample=sample,
                  scope="Compact English font extension; original text uses original glyphs. Only the optional title-menu specimen is English.")
    return data, report


def build(output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    data, report = build_rom("Start adventure")
    rom = output / "torneko-2-compact-font.gba"
    rom.write_bytes(data)
    report["output_rom"] = str(rom.relative_to(ROOT)) if rom.is_relative_to(ROOT) else str(rom)
    (output / "font.bin").write_bytes(pack_font(load_font()))
    (output / "lookup-hook.asm").write_text(report["hook_source"])
    report["bps"] = create_patch(default_rom(), rom, output / "torneko-2-compact-font.bps")
    (output / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(rom)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    build(parser.parse_args().output.resolve())
