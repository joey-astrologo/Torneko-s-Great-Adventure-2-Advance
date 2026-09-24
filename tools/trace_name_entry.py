"""Verify the Japanese opening name editor's limit using normal button input."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.compact_font import encode, measure
from tools.emulator import BIOS, Debugger, Session, version
from tools.rom import ROOT, default_rom, digest, load_base, require

OUTPUT = ROOT / "build/name-entry/base-trace"
STORED = 0x02003B46
EDIT = 0x0200CCF4
DEFAULT = bytes.fromhex("759e656b010101010000000000000000")


def run(output=OUTPUT):
    mgba.log.silence()
    original = load_base()
    source_save = default_rom().with_suffix(".sav")
    save_hash = digest(source_save.read_bytes()) if source_save.exists() else None
    require(original[0x14BE6:0x14BEA] == bytes.fromhex("06220b23"),
            "Opening name-editor arguments differ")
    require(original[0x63D60:0x63D65] == b"%s" + "村".encode("cp932") + b"\0",
            "Opening name display format differs")
    entries, displays, copies, states, screenshots = [], [], [], [], []

    with Session(original, output / "native") as game:
        memory = game.core.memory

        def callback(event):
            regs, address = event["registers"], event["address"]
            evidence = {"frame": event["frame"], "address": address,
                        "registers": regs}
            if address == 0x0801545C:
                require(regs[1:4] == [0x08063D60, 6, 11], "Unexpected editor call")
                entries.append(evidence)
            elif address == 0x0801557E:
                # Immediately before the name display's call to the reader.
                raw = bytes(memory[regs[1]:regs[1] + 15])
                require(raw[-1] == 0 and raw[-3:-1] == "村".encode("cp932"),
                        "Unexpected six-character name display")
                descriptor = bytes(memory[regs[0]:regs[0] + 24])
                require(descriptor[4:7] == bytes((13, 1, 14)),
                        "Name window dimensions/fixed advance differ")
                displays.append(dict(evidence, raw_hex=raw.hex(),
                                     japanese=raw[:-1].decode("cp932"),
                                     window_hex=descriptor.hex()))
            else:
                require(address == 0x0801567C and regs[:3] == [STORED, EDIT, 16],
                        "Name confirmation copy differs")
                copies.append(dict(evidence, source_hex=bytes(memory[EDIT:EDIT + 16]).hex()))

        def state(label, expected, position, selection):
            actual = bytes(memory[EDIT:EDIT + 16])
            require(actual == expected, f"Unexpected name after {label}")
            require(memory.u32[0x0200CCF0] == position and
                    memory.u32[0x0200CCEC] == selection, f"Unexpected cursor after {label}")
            stored = bytes(memory[STORED:STORED + 16])
            states.append({"label": label, "frame": game.core.frame_counter,
                           "editor_hex": actual.hex(), "stored_hex": stored.hex(),
                           "position": position, "selection": selection})
            picture = game.capture(label)
            screenshots.append({"file": "native/" + label + ".png",
                                "rgb_sha256": digest(picture.tobytes())})

        with Debugger(game, callback) as trace:
            for address in (0x0801545C, 0x0801557E, 0x0801567C):
                trace.breakpoint(address)
            game.frames(600)
            game.press("START", wait=180)
            game.press("A", wait=180)
            state("default", DEFAULT, 4, 4)
            game.snapshot().save(output / "fixtures" / "default")
            game.press("A", wait=30)
            five = DEFAULT[:4] + b"\x16" + DEFAULT[5:]
            state("five-characters", five, 5, 4)
            game.press("A", wait=30)
            six = five[:5] + b"\x16" + five[6:]
            state("six-characters-finish-selected", six, 5, 3)
            game.press("DOWN", wait=30)
            game.press("A", wait=30)
            replaced = six[:5] + b"\x32" + six[6:]
            state("sixth-replaced-no-seventh", replaced, 5, 3)
            require(all(s["stored_hex"] == DEFAULT.hex() for s in states),
                    "Unconfirmed editing changed stored name")
            game.press("START", wait=30)
            game.press("A", wait=30)
            require(bytes(memory[STORED:STORED + 16]) == replaced,
                    "Confirmation did not copy the full indexed name")
            game.frames(600)
            game.capture("after-confirmation")
        require(len(entries) == len(copies) == 1 and len(displays) == 4,
                "Unexpected native editor trace coverage")
        inputs = game.inputs

    require(digest(load_base()) == digest(original), "Original ROM changed")
    require((digest(source_save.read_bytes()) if source_save.exists() else None) == save_hash,
            "Original save changed")
    report = {"passed": True, "source_rom_sha256": digest(original),
              "source_save_sha256": save_hash, "original_files_unchanged": True,
              "emulator": version(), "bios": BIOS, "inputs": inputs,
              "editor_entries": entries, "native_displays": displays,
              "confirmation_copies": copies, "states": states, "screenshots": screenshots,
              "original_character_limit": 6, "original_fixed_advance": 14,
              "original_window_pixels": 104,
              "localization_requirement": {"minimum_characters": 7, "name": "Torneko",
                  "compact_font_advance_pixels": measure("Torneko"),
                  "encoded_hex": encode("Torneko").hex(),
                  "implemented_in_editor": False},
              "scope": "Unmodified Japanese editor; normal buttons and observational breakpoints. "
                       "Confirms entry limit and RAM copy, not battery persistence or English support."}
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": True, "original_character_limit": 6,
                      "native_displays": len(displays), "original_files_unchanged": True}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.output.resolve())
