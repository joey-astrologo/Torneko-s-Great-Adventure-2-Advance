"""Replay a JSON input route, capture screens, and save research checkpoints."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.rom import ROOT, default_rom, digest, inspect, load_base, require


def run(args):
    mgba.log.silence()
    data = load_base(args.rom)
    route_bytes = args.route.read_bytes()
    route = json.loads(route_bytes)
    initial_save = args.save.read_bytes() if args.save else None
    inputs = {args.rom.resolve(): digest(data), args.route.resolve(): digest(route_bytes)}
    if args.save:
        inputs[args.save.resolve()] = digest(initial_save)
    if args.native_state:
        inputs[args.native_state.resolve()] = digest(args.native_state.read_bytes())
    fixture = Snapshot.load(args.fixture) if args.fixture else None
    if args.fixture:
        for suffix in (".json", ".state", ".sav"):
            path = Path(str(args.fixture) + suffix).resolve()
            inputs[path] = digest(path.read_bytes())
    output_names = {"final.state", "final.sav", "final.json", "final.ss0", "report.json"}
    output_names.update(step["capture"] + ".png" for step in route["steps"] if "capture" in step)
    require(not ({(args.output / name).resolve() for name in output_names} & inputs.keys()),
            "Capture output would overwrite an input; choose a different output directory")
    with Session(data, args.output, initial_save) as session:
        if fixture:
            session.restore(fixture)
        if args.native_state:
            session.load_native_state(args.native_state)
        trace = Debugger(session) if args.breakpoint or args.watch_read else None
        try:
            if trace:
                for address in args.breakpoint:
                    trace.breakpoint(address)
                for address in args.watch_read:
                    trace.watchpoint(address)
            screenshots = []
            for step in route["steps"]:
                require(sum(key in step for key in ("frames", "press", "capture")) == 1,
                        "Each route step needs exactly one frames, press, or capture action")
                if "frames" in step:
                    session.frames(step["frames"])
                elif "press" in step:
                    session.press(step["press"], wait=step.get("wait", 120), hold=step.get("hold", 3))
                else:
                    picture = session.capture(step["capture"])
                    screenshots.append({"file": step["capture"] + ".png", "rgb_sha256": digest(picture.tobytes()),
                                        "frame": session.core.frame_counter})
            session.snapshot().save(args.output / "final")
            session.save_native_state(args.output / "final.ss0")
            report = {"rom": inspect(data), "emulator": version(), "bios": BIOS,
                      "initial_save_sha256": digest(initial_save) if initial_save is not None else None,
                      "route_sha256": digest(route_bytes), "route": route,
                      "inputs": session.inputs, "screenshots": screenshots,
                      "trace": trace.events if trace else [], "fingerprint": session.fingerprint()}
        finally:
            if trace:
                trace.close()
    for path, expected in inputs.items():
        require(digest(path.read_bytes()) == expected, f"Input changed: {path}")
    report["inputs_unchanged"] = True
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(args.output.resolve() / "report.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=default_rom())
    parser.add_argument("--route", type=Path, default=ROOT / "config/routes/title.json")
    parser.add_argument("--output", type=Path, default=ROOT / "build/captures/title")
    parser.add_argument("--save", type=Path)
    state = parser.add_mutually_exclusive_group()
    state.add_argument("--fixture", type=Path, help="Raw checkpoint prefix (without .json/.state/.sav)")
    state.add_argument("--native-state", type=Path, help="Desktop .ss0 state")
    parser.add_argument("--breakpoint", type=lambda value: int(value, 0), action="append", default=[])
    parser.add_argument("--watch-read", type=lambda value: int(value, 0), action="append", default=[])
    run(parser.parse_args())
