"""Pack the authored compact English font and measure its native glyph advances."""

import json
import copy
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import struct

from tools.review_fonts import extract
from tools.rom import ROOT, digest, load_base, require

COMPACT_ASSET = ROOT / "assets/fonts/compact-english.json"
TORNEKO3_ASSET = ROOT / "assets/fonts/torneko3-english.json"
ASSET = COMPACT_ASSET
FIRST_CODE = 0xF020
LAST_CODE = 0xF07E
_SNAPSHOT = ContextVar('torneko_font_validation_snapshot', default=None)


@contextmanager
def font_snapshot():
    """Validate immutable font inputs once for one build, then recheck sources.

    Nothing persists between builds. Each caller still receives an independent
    object, and changes to the ROM or an observed asset abort before export.
    """
    original = load_base()
    snapshot = {'original': original, 'fonts': {}}
    token = _SNAPSHOT.set(snapshot)
    try:
        yield
        require(load_base() == original, 'Base ROM changed during font snapshot')
        for path, (raw, _) in snapshot['fonts'].items():
            require(path.read_bytes() == raw, 'Font asset changed during build: ' + str(path))
    finally:
        _SNAPSHOT.reset(token)


def with_font_snapshot(function):
    @wraps(function)
    def run(*args, **kwargs):
        with font_snapshot():
            return function(*args, **kwargs)
    return run


def load_font(path=ASSET):
    snapshot = _SNAPSHOT.get()
    if snapshot is None:
        return _validate_font(load_base(), Path(path).read_bytes())
    path = Path(path).resolve()
    if path not in snapshot['fonts']:
        raw = path.read_bytes()
        snapshot['fonts'][path] = raw, _validate_font(snapshot['original'], raw)
    return copy.deepcopy(snapshot['fonts'][path][1])


def _validate_font(original, raw):
    font = json.loads(raw)
    require(font["schema"] in (1,2), "Unsupported font schema")
    require(font["base_rom_sha256"] == digest(original), "Font asset is for another base ROM")
    require(set(font["glyphs"]) == set(map(chr, range(32, 127))), "Font must cover all printable ASCII")
    if font['schema'] == 2:
        from tools.import_torneko3_font import SOURCE_SHA, convert_glyph
        require(font['source_rom_sha256'] == SOURCE_SHA and font['source_font'] == 0,
                'Imported font source differs')
        records = bytearray()
        for char in map(chr,range(32,127)):
            glyph = font['glyphs'][char]
            record,bitmap = bytes.fromhex(glyph['source_descriptor_hex']),bytes.fromhex(glyph['source_bitmap_hex'])
            records.extend(record+bitmap)
            advance,rows = convert_glyph(record,bitmap)
            require(glyph['origin'] == 'torneko3-rom' and glyph['advance'] == advance and glyph['rows'] == rows,
                    'Imported source shape, advance or ownership changed')
        expected = '9c4a1302da0e4075cb91cc2fbe6d23843795367638326ee60b569138f8d9b5f6'
        require(digest(records) == font['source_records_sha256'] == expected,'Imported source records changed')
        return font
    for char, glyph in font["glyphs"].items():
        expected_origin = "adapted-rom" if char == " " else "rom" if ord(char) < 0x60 and char != "\\" else "new"
        require(glyph["origin"] == expected_origin, "Original/new glyph ownership differs")
        width, rows = glyph["advance"], glyph["rows"]
        require(1 <= width <= 6 and len(rows) == 14, "Invalid compact glyph dimensions")
        require(all(len(row) == width and set(row) <= {".", "#"} for row in rows), "Invalid glyph bitmap")
        require(char == " " or any("#" in row for row in rows), "Missing visible glyph")
        if glyph["origin"] in ("rom", "adapted-rom"):
            source = extract(original, ord(char))
            require(glyph["rom_offset"] == source["rom_offset"] and glyph["source_hex"] == source["source_hex"],
                    "Original glyph provenance differs")
            if glyph["origin"] == "adapted-rom":
                require(char == " " and width == 3 and rows == ["..."] * 14, "Invalid adapted word space")
            else:
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
