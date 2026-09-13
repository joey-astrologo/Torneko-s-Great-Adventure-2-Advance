"""Extract Torneko 2's existing Latin glyphs and verify diagnostic native draws.

Address evidence and temporary label ownership are in docs/MEMORY_MAP.md.
The original ROM and save are never modified. No font or renderer bytes change.
"""

import argparse
import json
from pathlib import Path
import string
import struct

import mgba.log
from PIL import Image, ImageDraw

from tools.emulator import BIOS, Debugger, Session, version
from tools.rom import ROOT, default_rom, digest, load_base, require

BASE = 0x08000000
FONT_BASE = 0x180000
LOOKUP_TABLE = 0x12B5A8
LABEL_OFFSET = 0x61D04
LABEL_END = 0x61D10
LABEL_POINTER = 0x141314
LABEL_BYTES = bytes.fromhex("20 82 cd 82 b6 82 df 82 a9 82 e7 00")
OUTPUT = ROOT / "build/font-research/review"


def code_for(character):
    """Use the existing fullwidth SJIS Latin identity, retaining ordinary space."""
    if character == " ":
        return 0x20
    require(character in string.ascii_letters + string.digits, "Not a Latin letter/digit")
    return int.from_bytes(chr(ord(character) + 0xFEE0).encode("cp932"), "big")


def lookup(data, code):
    """Model the verified 08001A04 routine, including its single code alias."""
    code &= 0xFFFF
    if code == 0x9AE2:
        code = 0x92D9
    index = 0
    if code <= 0x987E:
        for offset in range(LOOKUP_TABLE, 0x12B66C, 4):
            threshold, first = struct.unpack_from("<HH", data, offset)
            if threshold == 0:
                break
            if code >= threshold:
                index = code - threshold + first
                break
    offset = FONT_BASE + index * 32
    require(offset + 32 <= len(data), "Glyph lookup outside ROM")
    return offset


def extract(data, code):
    offset = lookup(data, code)
    raw = data[offset:offset + 32]
    width = raw[0] & 15
    pixels = [[int(bool(int.from_bytes(raw[4 + y * 2:6 + y * 2], "big") & (0x8000 >> x)))
               for x in range(width)] for y in range(14)]
    occupied = [(x, y) for y, row in enumerate(pixels) for x, bit in enumerate(row) if bit]
    bounds = ([min(x for x, y in occupied), min(y for x, y in occupied),
               max(x for x, y in occupied) + 1, max(y for x, y in occupied) + 1] if occupied else None)
    return {"code": code, "rom_offset": offset, "rom_end_exclusive": offset + 32,
            "width": width, "pixels": pixels, "ink_bounds": bounds, "source_hex": raw.hex()}


def extract_sets(data):
    sets = [
        {"id": "narrow", "name": "Compact capitals, digits and punctuation", "characters": "".join(map(chr, range(32, 96)))},
        {"id": "upper", "name": "Serif uppercase", "characters": string.ascii_uppercase},
        {"id": "lower", "name": "Serif lowercase", "characters": string.ascii_lowercase},
        {"id": "digits", "name": "Larger digits", "characters": string.digits},
    ]
    for family in sets:
        family["glyphs"] = {c: extract(data, ord(c) if family["id"] == "narrow" else code_for(c))
                            for c in family["characters"]}
    return sets


def label_probe(original, text, encoding):
    require(original[LABEL_OFFSET:LABEL_END] == LABEL_BYTES, "Original menu label changed")
    require(struct.unpack_from("<I", original, LABEL_POINTER)[0] == BASE + LABEL_OFFSET,
            "Original menu pointer changed")
    payload = b" "
    for char in text:
        code = code_for(char) if encoding == "sjis" else ord(char)
        payload += code.to_bytes(2 if code > 255 else 1, "big")
    payload += b"\0"
    require(len(payload) <= len(LABEL_BYTES), "Diagnostic label exceeds its verified field")
    payload = payload.ljust(len(LABEL_BYTES), b"\0")
    data = original[:LABEL_OFFSET] + payload + original[LABEL_END:]
    require(data[:LABEL_OFFSET] == original[:LABEL_OFFSET] and data[LABEL_END:] == original[LABEL_END:],
            "Unexpected diagnostic ROM change")
    return data, {"offset": LABEL_OFFSET, "end_exclusive": LABEL_END,
                  "before_hex": LABEL_BYTES.hex(), "after_hex": payload.hex(),
                  "source_rom_sha256": digest(original), "diagnostic_rom_sha256": digest(data),
                  "output_rom": None, "temporary_cartridge_only": True}


def capture_sample(original, output, ident, text, encoding="sjis", narrow=False):
    data, patch = label_probe(original, text, encoding)
    calls, prepared, finished, overrides = [], [], [], []
    with Session(data, output / ident) as game:
        game.frames(600)

        def callback(event):
            regs = event["registers"]
            if event["address"] == 0x08001BC4:
                code, window = regs[1], regs[0]
                if narrow and 0x8260 <= code <= 0x8279:
                    new_code = code - 0x821F
                    game.core.cpu.gprs[1] = new_code
                    overrides.append({"from": code, "to": new_code})
                    code = new_code
                context = bytes(game.core.memory[window:window + 24])
                calls.append({"code": code, "window": window, "context_hex": context.hex(),
                              "x": context[2], "origin": list(context[:2]), "row": context[3],
                              "window_width": context[4] * 8, "fixed_advance": context[6],
                              "spacing": context[8], "style": context[9], "frame": event["frame"]})
            elif event["address"] == 0x08001C14:
                glyph = extract(original, regs[4])
                require(regs[0] == BASE + glyph["rom_offset"], "Native glyph address differs from lookup model")
                context = bytes(game.core.memory[regs[5]:regs[5] + 24])
                foreground = game.core.memory.u8[0x020000C2]
                background = 4 if context[9] & 1 else 7
                pixels = bytes(foreground if bit else (7 if y < 2 else background)
                               for y, row in enumerate(glyph["pixels"]) for bit in row)
                pixels += bytes([background]) * glyph["width"]
                native = bytes(game.core.memory[0x02036430:0x02036430 + len(pixels)])
                require(native == pixels, "Extracted font pixels differ from native glyph preparation")
                prepared.append({"code": regs[4], "rom_offset": glyph["rom_offset"], "width": glyph["width"],
                                 "native_pixels_match": True, "native_buffer_sha256": digest(native)})
            elif event["address"] == 0x08001C68:
                finished.append({"code": regs[4], "cursor_after": regs[0] & 255})

        with Debugger(game, callback=callback) as trace:
            for address in (0x08001BC4, 0x08001C14, 0x08001C68):
                trace.breakpoint(address)
            game.press("START", wait=180)
        image = game.capture("menu")
        require(len(calls) == len(finished), "Unpaired glyph entry/return trace")
        expected = [] if encoding == "ascii-lower" else [ord(c) if narrow else code_for(c) for c in text]
        require([item["code"] for item in calls] == [0x20] + expected, "Unexpected native glyph sequence")
        for begin, end in zip(calls, finished):
            width = 6 if begin["code"] == 0x20 else extract(original, begin["code"])["width"]
            require(begin["fixed_advance"] == 0 and begin["spacing"] == 0, "Unexpected menu width override")
            require(end["cursor_after"] == begin["x"] + width, "Native cursor advance differs from font width")
            require(end["cursor_after"] <= begin["window_width"], "Diagnostic text clips the window")
        report = {"id": ident, "text": text, "encoding": encoding, "patch": patch,
                  "glyph_code_overrides": overrides, "calls": calls, "glyphs": prepared,
                  "cursor_returns": finished, "inputs": game.inputs,
                  "image_rgb_sha256": digest(image.tobytes()), "emulator": version(), "bios": BIOS}
    (output / ident / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, image


def atlas(sets, output):
    result = Image.new("RGB", (680, 1050), "#152033")
    draw = ImageDraw.Draw(result)
    y = 14
    for family in sets:
        draw.text((14, y), family["name"] + " (label: character / advance)", fill="white")
        y += 26
        for i, (char, glyph) in enumerate(family["glyphs"].items()):
            x, row_y = 14 + i % 13 * 51, y + i // 13 * 68
            draw.text((x, row_y), f"{char} {glyph['width']}", fill="#aac0da")
            cell = Image.new("RGB", (16, 14), "#293750")
            for py, row in enumerate(glyph["pixels"]):
                for px, bit in enumerate(row):
                    if bit:
                        cell.putpixel((px, py), (255, 255, 255))
            result.paste(cell.resize((48, 42), Image.Resampling.NEAREST), (x, row_y + 14))
        y += (len(family["glyphs"]) + 12) // 13 * 68 + 18
    result.crop((0, 0, 680, y)).save(output / "latin-glyphs.png")


def review(output=OUTPUT):
    mgba.log.silence()
    original = load_base()
    save_path = default_rom().with_suffix(".sav")
    save_hash = digest(save_path.read_bytes()) if save_path.exists() else None
    output.mkdir(parents=True, exist_ok=True)
    sets = extract_sets(original)
    atlas(sets, output)
    reports, pictures = [], {}
    for family in ("upper", "lower", "digits"):
        chars = next(item["characters"] for item in sets if item["id"] == family)
        for i in range(0, len(chars), 5):
            ident = f"{family}-{i // 5 + 1}"
            report, _ = capture_sample(original, output, ident, chars[i:i + 5])
            reports.append(report)
    for ident, text, encoding, narrow in (
        ("mixed-start", "Start", "sjis", False),
        ("ascii-upper", "START", "ascii", False),
        ("ascii-lower", "abcde", "ascii-lower", False),
        ("compact-upper", "START", "ascii", True),
    ):
        report, picture = capture_sample(original, output, ident, text, encoding, narrow)
        reports.append(report)
        pictures[ident] = picture
    found = {item["code"] for report in reports for item in report["glyphs"]}
    require({code_for(c) for c in string.ascii_letters + string.digits} <= found,
            "Latin/digit glyphs lack native rendering verification")
    require(digest(default_rom().read_bytes()) == digest(original), "Original ROM changed")
    if save_hash is not None:
        require(digest(save_path.read_bytes()) == save_hash, "Original save changed")
    report = {"passed": True, "source_rom_sha256": digest(original), "output_rom": None,
              "source_save_sha256": save_hash, "original_files_unchanged": True,
              "font_sets": sets, "sample_reports": [f"{item['id']}/report.json" for item in reports],
              "native_sample_count": len(reports), "latin_letters_digits_verified": 62,
              "native_prepared_glyphs": sum(len(item["glyphs"]) for item in reports),
              "ascii_upper_uses_serif": True, "ascii_lowercase_ignored_in_test": True,
              "two_byte_lowercase_renders": True,
              "width_ranges": {item["id"]: [min(g["width"] for g in item["glyphs"].values()),
                                             max(g["width"] for g in item["glyphs"].values())] for item in sets}}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    # Pixel art stays at integer scale; annotations use the host font only outside the game images.
    comparison = Image.new("RGB", (1000, 396), "#152033")
    draw = ImageDraw.Draw(comparison)
    for i, (ident, title) in enumerate((("mixed-start", "Two-byte codes: Start"),
                                       ("compact-upper", "Compact glyph override: START"))):
        x = 12 + i * 496
        draw.text((x, 14), title, fill="white")
        comparison.paste(pictures[ident].resize((480, 320), Image.Resampling.NEAREST), (x, 42))
    comparison.save(output / "native-comparison.png")
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Torneko 2 original Latin font</title><style>body{max-width:1050px;margin:32px auto;padding:0 20px;background:#152033;color:#edf4ff;font:17px/1.5 system-ui}img{max-width:100%;image-rendering:pixelated}figure{margin:24px 0}a{color:#acd5ff}</style>
<h1>Original Latin glyphs found in Torneko 2</h1><p>All 26 uppercase letters, 26 lowercase letters and ten larger digits were checked through the native glyph renderer. Original font bytes are unchanged.</p>
<p>The serif letters use 7–13 pixel advances. Compact capitals use 6 pixels. The menu reader converts ASCII capitals to serif glyphs and ignores lowercase ASCII; existing two-byte codes render lowercase correctly. The compact specimen bypasses the uppercase mapping using a diagnostic register override.</p>
<figure><img src="native-comparison.png" alt="Native menu specimens"><figcaption>Temporary label probes in the original game renderer. These are font tests, not a translation build.</figcaption></figure>
<figure><img src="latin-glyphs.png" alt="Extracted original Latin glyphs and widths"></figure>
<p><a href="report.json">Source ranges, glyph bytes, widths and verification report</a></p></html>'''
    (output / "index.html").write_text(page)
    print(json.dumps({key: report[key] for key in ("passed", "native_sample_count", "latin_letters_digits_verified",
                                                 "width_ranges", "original_files_unchanged")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    review(parser.parse_args().output.resolve())
