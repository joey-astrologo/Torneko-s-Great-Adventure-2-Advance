"""Failure-path checks for original-ROM identity and emulator fixture safety."""

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.rom import inspect, load_base


class ResearchToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mgba.log.silence()
        cls.rom = load_base()

    def test_header_corruption_rejected(self):
        changed = bytearray(self.rom)
        changed[0xAC] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            inspect(changed)

    def test_modified_game_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.gba"
            changed = bytearray(self.rom)
            changed[-1] ^= 1
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "sha256"):
                load_base(path)

    def test_truncated_rom_rejected(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            inspect(b"\0" * 100)

    def test_wrong_rom_and_emulator_fixtures_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as directory, Session(self.rom, directory) as session:
            snapshot = session.snapshot()
            before = session.snapshot()
            for changed in (replace(snapshot, rom_sha256="wrong"), replace(snapshot, emulator="wrong")):
                with self.assertRaisesRegex(ValueError, "Fixture"):
                    session.restore(changed)
            self.assertEqual(before, session.snapshot())

    def test_corrupted_fixture_files_rejected(self):
        with tempfile.TemporaryDirectory() as directory, Session(self.rom, directory) as session:
            prefix = Path(directory) / "fixture"
            snapshot = session.snapshot()
            for suffix in (".state", ".sav"):
                snapshot.save(prefix)
                path = Path(str(prefix) + suffix)
                path.write_bytes(path.read_bytes() + b"bad")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    Snapshot.load(prefix)

    def test_callback_failure_surfaces_and_detaches(self):
        def fail(event):
            raise ValueError("probe callback failed")
        with tempfile.TemporaryDirectory() as directory, Session(self.rom, directory) as session:
            with self.assertRaisesRegex(RuntimeError, "callback failed"):
                with Debugger(session, callback=fail) as trace:
                    trace.breakpoint(int(inspect(self.rom)["entry"], 0))
                    trace.run_until(lambda events: bool(events))
            self.assertIsNone(session.debugger)
            session.frames(1)

    def test_invalid_input_does_not_advance_or_hold_buttons(self):
        with tempfile.TemporaryDirectory() as directory, Session(self.rom, directory) as session:
            frame = session.core.frame_counter
            for action in (lambda: session.frames(-1), lambda: session.press("A", wait=-1),
                           lambda: session.press("A", hold=0)):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual(frame, session.core.frame_counter)
            self.assertEqual(0, session.core._core.getKeys(session.core._core))

    def test_boot_breakpoint_keeps_requested_route_frame_count(self):
        with tempfile.TemporaryDirectory() as directory, Session(self.rom, directory) as session:
            with Debugger(session) as trace:
                trace.breakpoint(int(inspect(self.rom)["entry"], 0))
                session.frames(600)
                session.press("START", wait=180)
                self.assertEqual(783, session.core.frame_counter)
                self.assertEqual([0x080000C0], [event["address"] for event in trace.events])

    def test_combined_buttons_reach_native_key_register_and_release(self):
        with tempfile.TemporaryDirectory() as directory, Session(self.rom, directory) as session:
            session.frames(600)
            sampled = []
            with Debugger(session, lambda event: sampled.append(event['registers'][1] & 3)) as trace:
                # Native ldrh at 08000F00 has just read KEYINPUT into r1.
                # Reading the watched I/O address from a watch callback recurses.
                trace.breakpoint(0x08000F02)
                session.press(('A', 'B'), hold=3, wait=3)
            self.assertIn(0, sampled)  # GBA KEYINPUT is active-low: both held.
            self.assertEqual(sampled[-1], 3)
            self.assertEqual(session.inputs[-1]['keys'], ['A', 'B'])


if __name__ == "__main__":
    unittest.main()
