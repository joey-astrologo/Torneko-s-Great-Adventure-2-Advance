# Torneko 2 research workflow

Use the local `.venv/bin/python` and the commands in `README.md` and
`docs/EXPLORATION.md`. Native mGBA uses the project build; desktop mGBA and
Ghidra are shared installations. Read `docs/TOOLING.md` before changing pins.

Follow `docs/LOCALIZATION_PLAN.md` for the agreed translation source,
terminology/prose rules, coverage reporting and localization work sequence.

Use `config/rom.json` as the Japanese base identity. Preserve the supplied ROM
and save. Emulation uses `tools.emulator.Session` or a separate desktop copy
from `tools.prepare_playtest`; never run write-producing experiments on source
files. Keep source hashes and actual input schedules with research artifacts.

Record ROM/RAM/save discoveries in `docs/MEMORY_MAP.md`, with address space,
exclusive ranges, evidence and certainty. Original bytes, unidentified gaps,
padding and relocated text are not automatically free space. Before future
insertion, establish ownership, expected source bytes and shared allocation/
overlap checks. The compact English extension has explicit patch/resource
ownership in `docs/MEMORY_MAP.md` and uses `tools.rom_build.RomBuild`. Reuse that
allocator for future resources; it does not establish ownership of other source
ranges or any new RAM/save storage.

Torneko 3 is a tooling reference. Its encoding, addresses, fonts, expansion,
translation catalogs and gameplay/save assumptions do not apply until verified
in Torneko 2. Distinguish controlled emulator probes from native gameplay
observations and verified insertion from reviewed translation.

Run the relevant checks after changes. `./validate.sh` covers toolchain and
fresh-save acceptance. It does not establish full game or translation coverage.
