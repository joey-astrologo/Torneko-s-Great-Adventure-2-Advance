"""Replay the Japanese opening and tie native reads to original ROM resources."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import BIOS, Debugger, Session, version
from tools.opening_text import BANK_RAM, banks, manifest
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.text_codec import readable, source_bytes, tokenize

OUTPUT = ROOT / "build/opening-text"
ROUTE = ROOT / "config/routes/opening.json"


def run(output=OUTPUT, route_path=ROUTE):
    mgba.log.silence()
    original = load_base()
    route_bytes = route_path.read_bytes()
    route = json.loads(route_bytes)
    require(route["source_rom_sha256"] == digest(original), "Route base mismatch")
    source_save = default_rom().with_suffix(".sav")
    save_hash = digest(source_save.read_bytes()) if source_save.exists() else None
    entries, reads, dynamic, loads, calls, screenshots = {}, [], [], [], [], []
    active, pending = None, None
    known = {0x08000000 + b["rom_offset"]: b for b in banks()}
    output.mkdir(parents=True, exist_ok=True)

    with Session(original, output / "native") as game:
        def callback(event):
            nonlocal active, pending
            regs, address = event["registers"], event["address"]
            if address == 0x0804D722:
                require(regs[0] in known and regs[1] == BANK_RAM, "Unexpected natural bank call")
                game.snapshot().save(output / "fixtures" / "bank-load")
                return
            if address == 0x0805B48C:
                if regs[1] == BANK_RAM and regs[0] in known:
                    pending = known[regs[0]]
                    require(regs[4] == 0x08000000 + pending["pointer_offset"], "Bank table index differs")
                    loads.append({"bank": pending["id"], "frame": event["frame"], "source": regs[0],
                                  "destination": regs[1], "pointer_word": regs[4], "caller_return": regs[14]})
                return
            if address == 0x0804D726:
                require(pending is not None, "Unattributed bank load")
                native = bytes(game.core.memory[BANK_RAM:BANK_RAM + len(pending["data"])])
                require(native == pending["data"], "Python/native event-bank decompression differs")
                loads[-1].update(native_decompression_match=True, output_sha256=digest(native))
                active, pending = pending, None
                return
            if address == 0x08015A50:
                calls.append({"frame": event["frame"], "source": regs[0], "caller_return": regs[14],
                              "registers": regs, "bank": active["id"] if active else None})
                return
            pointer = regs[1]
            evidence = {"frame": event["frame"], "reader": address, "source": pointer,
                        "caller_return": regs[14], "window": regs[0],
                        "window_hex": bytes(game.core.memory[regs[0]:regs[0] + 24]).hex()}
            if 0x08000000 <= pointer < 0x08800000:
                start = pointer - 0x08000000
                tokens, end = tokenize(original, start, min(len(original), start + 65536))
                ident = f"rom.{start:08x}"
                source = {"kind": "rom", "offset": start, "end_exclusive": end}
            elif active and BANK_RAM <= pointer < BANK_RAM + len(active["data"]):
                start = pointer - BANK_RAM
                tokens, end = tokenize(active["data"], start)
                ident = f"{active['id']}.{start:04x}"
                source = {"kind": "compressed-bank", "bank": active["id"], "offset": start,
                          "end_exclusive": end, "compressed_rom_offset": active["rom_offset"]}
            else:
                if 0x02000000 <= pointer < 0x02040000 or 0x03000000 <= pointer < 0x03008000:
                    boundary = 0x02040000 if pointer < 0x03000000 else 0x03008000
                    raw = bytes(game.core.memory[pointer:min(pointer + 4096, boundary)])
                    try:
                        tokens, end = tokenize(raw)
                        dynamic.append(dict(evidence, raw_hex=raw[:end].hex(), text=readable(tokens),
                                            disposition="runtime-text; producer not yet attributed"))
                    except ValueError as error:
                        dynamic.append(dict(evidence, prefix_hex=raw[:64].hex(), error=str(error)))
                else:
                    dynamic.append(dict(evidence, disposition="unclassified address space"))
                return
            raw = source_bytes(tokens)
            require(raw == bytes(game.core.memory[pointer:pointer + len(raw)]), "Native text differs from original source")
            row = entries.setdefault(ident, {"id": ident, "source": source, "raw_hex": raw.hex(),
                                             "source_sha256": digest(raw), "tokens": tokens, "japanese": readable(tokens),
                                             "evidence": [], "status": "native-source-verified; insertion ownership pending"})
            row["evidence"].append(evidence)
            reads.append(dict(evidence, source_id=ident, native_bytes_match=True))

        with Debugger(game, callback, max_events=100000) as trace:
            for address in (0x0804D722, 0x0805B48C, 0x0804D726, 0x08015A50, 0x080021B4):
                trace.breakpoint(address)
            for step in route["steps"]:
                if "frames" in step:
                    game.frames(step["frames"])
                elif "press" in step:
                    game.press(step["press"], wait=step.get("wait", 120), hold=step.get("hold", 3))
                else:
                    picture = game.capture(step["capture"])
                    screenshots.append({"file": "native/" + step["capture"] + ".png", "frame": game.core.frame_counter,
                                        "rgb_sha256": digest(picture.tobytes())})
                    if step["capture"] in ("new-game", "opening-1", "first-dungeon", "first-movement"):
                        game.snapshot().save(output / "fixtures" / step["capture"])
        fingerprint = game.fingerprint()
        inputs = game.inputs
    require(digest(load_base()) == digest(original), "Original ROM changed")
    require((digest(source_save.read_bytes()) if source_save.exists() else None) == save_hash, "Original save changed")
    report = {"passed": True, "source_rom_sha256": digest(original), "source_save_sha256": save_hash,
              "original_files_unchanged": True, "emulator": version(), "bios": BIOS,
              "route": route, "route_sha256": digest(route_bytes), "inputs": inputs, "fingerprint": fingerprint,
              "bank_resources": manifest(), "native_bank_loads": loads, "native_reads": reads,
              "story_calls": calls, "runtime_text_pending_provenance": dynamic, "screenshots": screenshots,
              "entries": list(entries.values()), "verified_source_count": len(entries),
              "scope": "One recorded opening route and its actual source reads; no whole-game coverage or insertion claim."}
    (output / "trace.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": True, "sources": len(entries), "native_reads": len(reads),
                      "unattributed_runtime_reads": len(dynamic), "native_bank_loads": len(loads), "frames": fingerprint["frame"]}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--route", type=Path, default=ROUTE)
    args = parser.parse_args()
    run(args.output.resolve(), args.route.resolve())
