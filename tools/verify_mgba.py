"""Validate native mGBA, isolated saves, input replay, callbacks and GUI states."""

import argparse
import json
from pathlib import Path

import mgba.log
from mgba._pylib import ffi

from tools.emulator import BIOS, Debugger, Session, Snapshot, battery_snapshot, version
from tools.rom import ROOT, default_rom, digest, inspect, load_base, require


def verify_debugger(session, entry):
    with Debugger(session) as trace:
        point = trace.breakpoint(entry)
        trace.run_until(lambda events: bool(events))
        require(trace.events[0]["address"] == entry, "Wrong cartridge entry breakpoint")
        trace.clear(point)
        entry_event = trace.events[0]

    # This is an isolated adapter probe, not a game function or RAM reservation.
    # ARM ldr r0,[r1]; b . reads one known word. Restore the whole snapshot below.
    snapshot = session.snapshot()
    memory = session.core.memory
    memory.u32[0x02000000] = 0xE5910000
    memory.u32[0x02000004] = 0xEAFFFFFE
    memory.u32[0x02000020] = 0x1234ABCD
    for register, value in ((b"cpsr", 0xD3), (b"r1", 0x02000020), (b"pc", 0x02000000)):
        require(session.core._core.writeRegister(session.core._core, register, ffi.new("uint32_t*", value)),
                "Could not set controlled probe register")
    try:
        with Debugger(session) as trace:
            point = trace.watchpoint(0x02000020)
            trace.run_until(lambda events: bool(events))
            require(trace.events[0]["kind"] == "watchpoint" and trace.events[0]["address"] == 0x02000020,
                    "Native read watchpoint failed")
            trace.clear(point)
            watch_event = trace.events[0]
    finally:
        session.restore(snapshot)
    return {"entry": entry_event, "controlled_read": watch_event,
            "controlled_probe": "Temporary EWRAM instructions/data; full snapshot restored before boot."}


def verify(rom, output, initial_save=None):
    mgba.log.silence()
    data = load_base(rom)
    save_bytes = initial_save.read_bytes() if initial_save else None
    source_hash, save_hash = digest(data), digest(save_bytes) if save_bytes is not None else None
    require(save_bytes is None or len(save_bytes) == 65536, "Expected a 64 KiB supplied battery save")
    output.mkdir(parents=True, exist_ok=True)
    with Session(data, output, save_bytes) as session:
        initial = session.snapshot()
        debugger = verify_debugger(session, int(inspect(data)["entry"], 0))
        session.restore(initial)
        address = 0x02000000
        original_word = session.core.memory.u32[address]
        for width, value in ((8, 0xA5), (16, 0xBEEF), (32, 0x12345678)):
            view = getattr(session.core.memory, f"u{width}")
            view[address] = value
            require(view[address] == value, f"{width}-bit memory access failed")
        session.core.memory.u32[address] = original_word
        session.frames(600)
        picture = session.capture("boot")
        require(picture.size == (240, 160) and len(picture.getcolors(38400)) > 1, "Blank or invalid video buffer")
        snapshot = session.snapshot()
        snapshot.save(output / "boot")
        session.save_native_state(output / "boot.ss0")
        session.press("START", wait=180)
        session.capture("after-start")
        first = session.fingerprint()
        session.restore(Snapshot.load(output / "boot"))
        session.press("START", wait=180)
        require(session.fingerprint() == first, "Raw fixture replay changed pixels, RAM, battery or frame")
        session.load_native_state(output / "boot.ss0")
        session.press("START", wait=180)
        require(session.fingerprint() == first, "Native GUI-state replay changed pixels, RAM, battery or frame")
        battery = battery_snapshot(session.core)
        report = {"passed": True, "rom": inspect(data), "emulator": version(), "bios": BIOS,
                  "binding_path": mgba.core.__file__, "initial_save_sha256": save_hash,
                  "screen_size": list(picture.size), "boot_frames": 600, "replay_frames": 183,
                  "debugger": debugger, "memory_access_widths": [8, 16, 32],
                  "raw_state_bytes": len(snapshot.state), "battery_save_bytes": len(battery),
                  "save_type": int(session.core._native.memory.savedata.type),
                  "raw_replay_identical": True, "native_state_replay_identical": True,
                  "fingerprint": first, "inputs": session.inputs}
    require(session.disk_save == battery, "Native battery data did not persist to the temporary save file")
    with Session(data, output, session.disk_save) as reloaded:
        reloaded.frames(600)
        require(battery_snapshot(reloaded.core) == battery, "Cold boot changed saved battery data")
        reloaded.capture("cold-reload")
    require(digest(rom.read_bytes()) == source_hash, "Source ROM changed")
    if initial_save:
        require(digest(initial_save.read_bytes()) == save_hash, "Supplied save changed")
    report.update(source_rom_unchanged=True, supplied_save_unchanged=True if initial_save else None,
                  native_save_persisted=True, cold_reload_battery_identical=True)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("passed", "emulator", "rom", "battery_save_bytes",
                                                 "raw_replay_identical", "native_state_replay_identical")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=default_rom())
    parser.add_argument("--output", type=Path, default=ROOT / "build/toolchain-validation/mgba")
    parser.add_argument("--save", type=Path, help="Read an initial save into an isolated copy")
    args = parser.parse_args()
    verify(args.rom.resolve(), args.output.resolve(), args.save.resolve() if args.save else None)
