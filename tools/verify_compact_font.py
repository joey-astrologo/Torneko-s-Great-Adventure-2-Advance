"""Verify the built font with native mGBA drawing and controlled ABI probes."""

import argparse
import json
from pathlib import Path

import mgba.log
from mgba._pylib import ffi

from tools.build_compact_font import FONT_OFFSET, OUTPUT, build_rom
from tools.compact_font import FIRST_CODE, LAST_CODE, load_font, measure
from tools.emulator import BIOS, Debugger, Session, version
from tools.review_fonts import BASE, lookup
from tools.rom import ROOT, default_rom, digest, load_base, require


def capture_sample(output, ident, text, font):
    data, build = build_rom(text)
    calls, prepared, finished = [], [], []
    with Session(data, output / ident) as game:
        game.frames(600)

        def callback(event):
            regs = event["registers"]
            if event["address"] == 0x08001BC4:
                code, window = regs[1], regs[0]
                require(FIRST_CODE <= code <= LAST_CODE, "Unexpected specimen code")
                context = bytes(game.core.memory[window:window + 24])
                calls.append({"code": code, "character": chr(code & 255), "x": context[2],
                              "window": window, "context_hex": context.hex(), "window_width": context[4] * 8,
                              "fixed_advance": context[6], "spacing": context[8], "frame": event["frame"]})
            elif event["address"] == 0x08001C14:
                code = regs[4]
                glyph = font["glyphs"][chr(code & 255)]
                address = BASE + FONT_OFFSET + (code - FIRST_CODE) * 32
                require(regs[0] == address, "Native glyph address differs from allocated record")
                context = bytes(game.core.memory[regs[5]:regs[5] + 24])
                foreground = game.core.memory.u8[0x020000C2]
                background = 4 if context[9] & 1 else 7
                pixels = bytes(foreground if bit == "#" else (7 if y < 2 else background)
                               for y, row in enumerate(glyph["rows"]) for bit in row)
                pixels += bytes([background]) * glyph["advance"]
                native = bytes(game.core.memory[0x02036430:0x02036430 + len(pixels)])
                require(native == pixels, "Native pixels differ from authored glyph rows")
                prepared.append({"code": code, "rom_address": address, "advance": glyph["advance"],
                                 "native_pixels_match": True, "native_buffer_sha256": digest(native)})
            elif event["address"] == 0x08001C68:
                finished.append({"code": regs[4], "cursor_after": regs[0] & 255})

        with Debugger(game, callback=callback) as trace:
            for address in (0x08001BC4, 0x08001C14, 0x08001C68):
                trace.breakpoint(address)
            game.press("START", wait=180)
        picture = game.capture("menu")
        expected = [0xF000 + ord(c) for c in " " + text]
        for actual in (calls, prepared, finished):
            require([item["code"] for item in actual] == expected, "Missing or reordered native glyphs")
        for begin, end in zip(calls, finished):
            glyph = font["glyphs"][begin["character"]]
            advance = glyph["advance"]
            require(begin["fixed_advance"] == begin["spacing"] == 0, "Unexpected width override")
            require(end["cursor_after"] == begin["x"] + advance, "Native cursor advance differs")
            require(end["cursor_after"] <= begin["window_width"], "Specimen exceeds the window")
            context = bytes.fromhex(begin["context_hex"])
            require(context[:2] == bytes((8, 8)) and context[3] == 0, "Menu scanout origin changed")
            for y, row in enumerate(glyph["rows"] + ["." * advance]):
                for x, bit in enumerate(row):
                    white = picture.getpixel((8 + begin["x"] + x, 8 + y)) == (255, 255, 255)
                    require(white == (bit == "#"), "Final screen pixels differ from the font")
        require(finished[-1]["cursor_after"] == measure(" " + text, font), "Total advance differs")
        # Call the game's own string-width routine on the actual appended label.
        # This is a separate controlled probe, after the untouched gameplay capture.
        pointer = BASE + next(a["start"] for a in build["allocations"] if a["id"] == "font-specimen-label")
        width = call_thumb(game, 0x08001C84, pointer)
        require(width["r0"] == measure(" " + text, font), "Native string measurement differs")
        report = {"id": ident, "text": text, "build": build, "passed": True,
                  "native_menu_register_overrides": [], "calls": calls, "glyphs": prepared,
                  "final_screen_glyph_pixels_match": True,
                  "cursor_returns": finished, "controlled_string_width_probe": width,
                  "inputs": game.inputs, "image_rgb_sha256": digest(picture.tobytes())}
    (output / ident / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def call_thumb(game, address, argument):
    """Redirect a disposable snapshot to a function; restore every change afterward."""
    snapshot = game.snapshot()
    try:
        cpu = game.core.cpu
        sentinels = [0x23450000 + i for i in range(4, 12)]
        for i, value in enumerate(sentinels, 4):
            cpu.gprs[i] = value
        stack = int(cpu.gprs[13]) & 0xFFFFFFFF
        cpu.gprs[0] = argument
        cpu.gprs[14] = 0x08000355
        for register, value in ((b"cpsr", int(cpu.cpsr.packed) | 0x20), (b"pc", address)):
            require(game.core._core.writeRegister(game.core._core, register, ffi.new("uint32_t*", value)),
                    "Could not set controlled-probe register")
        with Debugger(game) as trace:
            trace.breakpoint(0x08000354)
            trace.run_until(lambda events: bool(events))
        result = trace.events[-1]["registers"]
        require(result[4:12] == sentinels and result[13] == stack, "Function violated callee-saved ABI")
        return {"function": address, "argument": argument, "r0": result[0], "callee_saved_and_sp_preserved": True}
    finally:
        game.restore(snapshot)


def fallback_check(output):
    original = load_base()
    extended, _ = build_rom()
    fingerprints, lookups = {}, []
    # Same real inputs on both ROMs, with the original Japanese label intact.
    for name, data in (("original", original), ("extended", extended)):
        with Session(data, output / ("fallback-" + name)) as game:
            game.frames(600)
            game.press("START", wait=180)
            game.capture("menu")
            fingerprints[name] = game.fingerprint()
            if name == "extended":
                for code in (0, 0x20, 0x41, 0x5C, 0x8140, 0x82CD, 0x8260, 0x8281,
                             0x92D9, 0x987E, 0x9AE2, 0xF01F, 0xF020, 0xF07E, 0xF07F, 0xFFFF, 0x1234F061):
                    result = call_thumb(game, 0x08001A04, code)
                    masked = code & 0xFFFF
                    expected = (FONT_OFFSET + (masked - FIRST_CODE) * 32 if FIRST_CODE <= masked <= LAST_CODE
                                else lookup(original, masked))
                    require(result["r0"] == BASE + expected, "Lookup fallback/boundary probe failed")
                    lookups.append(result)
    # Code timing and cartridge size may affect scratch RAM; the visible scene,
    # frame schedule and persisted data must remain identical.
    for key in ("pixels", "battery", "frame"):
        require(fingerprints["original"][key] == fingerprints["extended"][key], "Original menu regression: " + key)
    return {"passed": True, "fingerprints": fingerprints, "lookup_probes": lookups,
            "menu_pixels_battery_frame_identical": True}


def verify(output=OUTPUT):
    mgba.log.silence()
    output.mkdir(parents=True, exist_ok=True)
    original_hash = digest(load_base())
    save = default_rom().with_suffix(".sav")
    save_hash = digest(save.read_bytes()) if save.exists() else None
    font, samples = load_font(), []
    sample = ""
    for code in range(32, 127):
        char = chr(code)
        if measure(" " + sample + char, font) > 96:
            samples.append(sample)
            sample = ""
        sample += char
    samples.append(sample)
    reports = [capture_sample(output, "mixed-case", "Start adventure", font)]
    for i, sample in enumerate(samples, 1):
        reports.append(capture_sample(output, f"charset-{i}", sample, font))
    fallback = fallback_check(output)
    covered = sorted({g["code"] for report in reports for g in report["glyphs"]})
    require(covered == list(range(FIRST_CODE, LAST_CODE + 1)), "Incomplete native font coverage")
    require(digest(load_base()) == original_hash and (digest(save.read_bytes()) if save.exists() else None) == save_hash,
            "Original ROM/save changed")
    report = {"passed": True, "emulator": version(), "bios": BIOS, "source_rom_sha256": original_hash,
              "source_save_sha256": save_hash, "original_files_unchanged": True,
              "glyph_count": len(covered), "new_glyphs": sum(g["origin"] == "new" for g in font["glyphs"].values()),
              "native_sample_count": len(reports), "samples": reports, "fallback": fallback,
              "scope": "Initial-menu draws and controlled lookup/string-width calls; other text paths remain unverified."}
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("passed", "glyph_count", "new_glyphs", "native_sample_count", "original_files_unchanged")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    verify(parser.parse_args().output.resolve())
