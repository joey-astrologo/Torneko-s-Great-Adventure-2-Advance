"""Pack the authored compact English font and measure its native glyph advances."""

import json
from pathlib import Path
import struct

from tools.review_fonts import extract
from tools.rom import ROOT, digest, load_base, require

ASSET = ROOT / "assets/fonts/compact-english.json"
FIRST_CODE = 0xF020
LAST_CODE = 0xF07E


def load_font(path=ASSET):
    original = load_base()
    font = json.loads(Path(path).read_text())
    require(font["schema"] == 1, "Unsupported font schema")
    require(font["base_rom_sha256"] == digest(original), "Font asset is for another base ROM")
    require(set(font["glyphs"]) == set(map(chr, range(32, 127))), "Font must cover all printable ASCII")
    for char, glyph in font["glyphs"].items():
        expected_origin = "rom" if ord(char) < 0x60 and char != "\\" else "new"
        require(glyph["origin"] == expected_origin, "Original/new glyph ownership differs")
        width, rows = glyph["advance"], glyph["rows"]
        require(1 <= width <= 6 and len(rows) == 14, "Invalid compact glyph dimensions")
        require(all(len(row) == width and set(row) <= {".", "#"} for row in rows), "Invalid glyph bitmap")
        require(char == " " or any("#" in row for row in rows), "Missing visible glyph")
        if glyph["origin"] == "rom":
            source = extract(original, ord(char))
            require(glyph["rom_offset"] == source["rom_offset"] and glyph["source_hex"] == source["source_hex"],
                    "Original glyph provenance differs")
            require(width == source["width"], "Original glyph advance changed")
            require(pack_glyph(glyph) == bytes.fromhex(source["source_hex"]), "Original glyph bytes changed")
        else:
            require(glyph["origin"] == "new", "Unknown glyph origin")
    return font


def pack_glyph(glyph):
    metadata = bytes.fromhex(glyph["source_hex"])[:4] if glyph["origin"] == "rom" else bytes((glyph["advance"], 0, 0, 0))
    rows = [sum(0x8000 >> x for x, bit in enumerate(row) if bit == "#") for row in glyph["rows"]]
    return metadata + struct.pack(">14H", *rows)


def pack_font(font):
    return b"".join(pack_glyph(font["glyphs"][chr(code)]) for code in range(32, 127))


def encode(text):
    """Use new two-byte glyph codes so original ASCII/control parsing is preserved."""
    output = bytearray()
    for char in text:
        if char == "\n":
            output.append(13)
        else:
            require(32 <= ord(char) <= 126, f"Unsupported English character: {char!r}")
            output.extend((0xF0, ord(char)))
    output.append(0)
    return bytes(output)


def measure(text, font=None):
    font = font or load_font()
    require(all(char in font["glyphs"] for char in text), "Measure one printable-ASCII line at a time")
    return sum(font["glyphs"][char]["advance"] for char in text)
