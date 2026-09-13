"""Game-independent mGBA controls adapted from Torneko 3's Session/ReaderTrace.

Use native debugger callbacks because mGBA 0.10.5's high-level breakpoint
wrapper has an outdated signature. All callback objects live until detach.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

import mgba.core
import mgba.image
import mgba.vfs
from mgba._pylib import ffi, lib

from tools.rom import digest, require

BIOS = "mGBA built-in BIOS; no external BIOS loaded"


def version():
    return ffi.string(lib.projectVersion).decode()


def battery_snapshot(core):
    pointer = ffi.new("void**")
    size = core._core.savedataClone(core._core, pointer)
    try:
        return bytes(ffi.buffer(pointer[0], size)) if size else b""
    finally:
        if pointer[0] != ffi.NULL:
            lib.free(pointer[0])


@dataclass(frozen=True)
class Snapshot:
    state: bytes
    battery: bytes
    keys: int
    rom_sha256: str
    emulator: str

    def save(self, prefix):
        prefix = Path(prefix)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        Path(str(prefix) + ".state").write_bytes(self.state)
        Path(str(prefix) + ".sav").write_bytes(self.battery)
        Path(str(prefix) + ".json").write_text(json.dumps({
            "format": "torneko-mgba-raw-v1", "rom_sha256": self.rom_sha256,
            "emulator": self.emulator, "bios": BIOS, "keys": self.keys,
            "state_sha256": digest(self.state), "battery_sha256": digest(self.battery),
        }, indent=2) + "\n")

    @classmethod
    def load(cls, prefix):
        prefix = str(prefix)
        report = json.loads(Path(prefix + ".json").read_text())
        require(report["format"] == "torneko-mgba-raw-v1" and report["bios"] == BIOS,
                "Unsupported fixture format or BIOS")
        state, battery = Path(prefix + ".state").read_bytes(), Path(prefix + ".sav").read_bytes()
        require(digest(state) == report["state_sha256"], "Fixture core-state hash mismatch")
        require(digest(battery) == report["battery_sha256"], "Fixture battery hash mismatch")
        return cls(state, battery, report["keys"], report["rom_sha256"], report["emulator"])


class Session:
    """Run a disposable cartridge with a native, file-backed battery save."""

    def __init__(self, rom_data, output, initial_save=None):
        self.rom_data, self.output = bytes(rom_data), Path(output)
        self.initial_save = initial_save
        self.rom_sha256 = digest(self.rom_data)
        self.inputs = []
        self.core = None
        self.debugger = None
        self.disk_save = b""

    def __enter__(self):
        self.output.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="cartridge-", dir=self.output)
        self.rom_path = Path(self.temporary.name) / "game.gba"
        self.save_path = self.rom_path.with_suffix(".sav")
        try:
            self.rom_path.write_bytes(self.rom_data)
            if self.initial_save is not None:
                self.save_path.write_bytes(self.initial_save)
            self.core = mgba.core.load_path(str(self.rom_path))
            require(self.core is not None, "Could not load GBA cartridge")
            require(self.core.autoload_save(), "Could not open native cartridge save")
            self.screen = mgba.image.Image(*self.core.desired_video_dimensions())
            self.core.set_video_buffer(self.screen)
            self.core.reset()
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        try:
            if self.debugger is not None:
                self.debugger.close()
            if self.core is not None:
                ffi.release(self.core._core)
                self.core = None
            self.disk_save = self.save_path.read_bytes() if self.save_path.exists() else b""
        finally:
            self.temporary.cleanup()

    def _advance(self, count):
        require(isinstance(count, int) and count >= 0, "Frames must be a nonnegative integer")
        before = self.core.frame_counter
        target = before + count
        # Native debugger stepping can cross more than one frame during HLE
        # startup. Count actual frames, not calls to mDebuggerRunFrame.
        while self.core.frame_counter < target:
            if self.debugger is not None:
                lib.mDebuggerRunFrame(self.debugger.native)
                self.debugger.check_errors()
            else:
                self.core.run_frame()
        require(self.core.frame_counter - before == count, "Frame count mismatch")

    def frames(self, count):
        before = self.core.frame_counter
        self._advance(count)
        self.inputs.append({"frames": count, "start_frame": before, "end_frame": self.core.frame_counter})

    def press(self, key, wait=120, hold=3):
        require(isinstance(hold, int) and hold > 0, "Hold must be positive")
        require(isinstance(wait, int) and wait >= 0, "Wait must be nonnegative")
        code = getattr(self.core, "KEY_" + key.upper())
        before = self.core.frame_counter
        self.core.set_keys(code)
        try:
            require(self.core._core.getKeys(self.core._core) == 1 << code, "Key press failed")
            self._advance(hold)
        finally:
            self.core.clear_keys(code)
        require(self.core._core.getKeys(self.core._core) == 0, "Key release failed")
        self._advance(wait)
        self.inputs.append({"key": key.upper(), "hold": hold, "released": wait,
                            "start_frame": before, "end_frame": self.core.frame_counter})

    def capture(self, name):
        require(Path(name).name == name and name not in ("", ".", ".."), "Capture name must be a filename")
        picture = self.screen.to_pil().convert("RGB")
        picture.save(self.output / (name + ".png"))
        return picture

    def snapshot(self):
        state = self.core.save_raw_state()
        require(state is not None, "Could not save raw core state")
        return Snapshot(bytes(ffi.buffer(state)), battery_snapshot(self.core),
                        int(self.core._core.getKeys(self.core._core)), self.rom_sha256, version())

    def restore(self, snapshot):
        require(snapshot.rom_sha256 == self.rom_sha256, "Fixture ROM hash mismatch")
        require(snapshot.emulator == version(), "Fixture emulator version mismatch")
        require(self.core.load_raw_state(snapshot.state), "Could not restore raw state")
        if snapshot.battery:
            require(self.core._core.savedataRestore(self.core._core, snapshot.battery,
                                                   len(snapshot.battery), False), "Could not restore battery")
        self.core._core.setKeys(self.core._core, snapshot.keys)
        self.inputs.append({"restore_state_sha256": digest(snapshot.state),
                            "frame": self.core.frame_counter})

    def save_native_state(self, path):
        """Write a desktop-compatible mGBA state, including save data and RTC."""
        vf = mgba.vfs.open_path(str(path), "wb")
        require(vf is not None, "Could not open native state output")
        try:
            require(lib.mCoreSaveStateNamed(self.core._core, vf.handle, 1 | 2 | 8),
                    "Could not save native mGBA state")
        finally:
            vf.close()

    def load_native_state(self, path):
        """Load a GUI state into this disposable session; raw fixtures use restore()."""
        vf = mgba.vfs.open_path(str(path), "rb")
        require(vf is not None, "Could not open native state")
        try:
            require(lib.mCoreLoadStateNamed(self.core._core, vf.handle, 1 | 2 | 8),
                    "Could not load native mGBA state")
        finally:
            vf.close()
        self.core._core.setKeys(self.core._core, 0)
        self.inputs.append({"native_state_sha256": digest(Path(path).read_bytes()),
                            "frame": self.core.frame_counter})

    def fingerprint(self):
        return {
            "pixels": digest(self.screen.to_pil().convert("RGB").tobytes()),
            "ewram": digest(bytes(self.core.memory[0x02000000:0x02040000])),
            "iwram": digest(bytes(self.core.memory[0x03000000:0x03008000])),
            "battery": digest(battery_snapshot(self.core)),
            "frame": self.core.frame_counter,
        }


class Debugger:
    """One native debugger per session, with caller-supplied game addresses."""

    def __init__(self, session, callback=None, max_events=10000):
        require(session.debugger is None, "Session already has a debugger")
        self.session, self.handler = session, callback
        self.events, self.errors = [], []
        self.max_events, self.closed = max_events, False
        self.callback = ffi.callback(
            "void(struct mDebugger*, enum mDebuggerEntryReason, struct mDebuggerEntryInfo*)",
            self._entered)
        self.native = ffi.new("struct mDebugger*")
        self.native.type, self.native.entered = lib.DEBUGGER_CUSTOM, self.callback
        lib.mDebuggerAttach(self.native, session.core._core)
        session.debugger = self

    def _entered(self, native, reason, info):
        try:
            if info == ffi.NULL or reason not in (lib.DEBUGGER_ENTER_BREAKPOINT, lib.DEBUGGER_ENTER_WATCHPOINT):
                return
            require(len(self.events) < self.max_events, "Debugger event limit exceeded")
            cpu = ffi.cast("struct ARMCore*", self.session.core._core.cpu)
            event = {"kind": "breakpoint" if reason == lib.DEBUGGER_ENTER_BREAKPOINT else "watchpoint",
                     "address": int(info.address), "frame": self.session.core.frame_counter,
                     "registers": [int(r) & 0xFFFFFFFF for r in cpu.gprs],
                     "thumb": bool(cpu.cpsr.packed & 0x20)}
            self.events.append(event)
            if self.handler is not None:
                self.handler(event)
        except Exception as error:
            if not self.errors:
                self.errors.append(error)
        finally:
            native.state = lib.DEBUGGER_RUNNING

    def breakpoint(self, address):
        point = ffi.new("struct mBreakpoint*")
        point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
        ident = self.native.platform.setBreakpoint(self.native.platform, point)
        require(ident >= 0, "Could not install execution breakpoint")
        return int(ident)

    def watchpoint(self, address, access="read"):
        kind = {"read": lib.WATCHPOINT_READ, "write": lib.WATCHPOINT_WRITE, "rw": lib.WATCHPOINT_RW}[access]
        point = ffi.new("struct mWatchpoint*")
        point.address, point.segment, point.type = address, -1, kind
        ident = self.native.platform.setWatchpoint(self.native.platform, point)
        require(ident >= 0, "Could not install memory watchpoint")
        return int(ident)

    def clear(self, ident):
        require(self.native.platform.clearBreakpoint(self.native.platform, ident), "Could not clear debugger point")

    def check_errors(self):
        if self.errors:
            raise RuntimeError("Native debugger callback failed") from self.errors[0]

    def run_until(self, predicate, max_steps=100000):
        for _ in range(max_steps):
            lib.mDebuggerRun(self.native)
            self.check_errors()
            if predicate(self.events):
                return
        raise TimeoutError(f"Debugger condition not reached in {max_steps} steps")

    def close(self):
        if not self.closed:
            self.session.core._core.detachDebugger(self.session.core._core)
            self.session.debugger = None
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
