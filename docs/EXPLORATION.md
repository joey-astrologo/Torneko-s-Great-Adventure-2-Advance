# Exploring Torneko 2

## Source and first observations

`config/rom.json` pins the user's 8 MiB Japanese ROM: title `TORUNEKO2`, game code
`AT2J`, maker `B4`, revision 0. The header checksum is `21` and the cartridge's
ARM branch targets `080000C0`. This is local identity/header verification; no
external dump database has been consulted.

The baseline route boots 600 frames, then presses Start for 3 frames and releases
it for 180 frames. The captures show the Japanese title screen and initial menu
with `はじめから`. Native mGBA reports FLASH512 storage (65,536 bytes). Validation
also booted an isolated copy of the supplied 64 KiB save and checked its hash
afterward. This does not establish the game's logical save-record layout or
verify creating an adventure through gameplay.

## Static analysis

```bash
bash tools/ghidra.sh verify
bash tools/ghidra.sh import
bash tools/ghidra.sh functions build/disassembly/startup-thumb.txt 0x08000354
bash tools/ghidra.sh range build/disassembly/startup-range.txt 0x08000354 0x08000380
```

The import command creates `build/ghidra/Torneko2.gpr` only if absent. The other
commands use temporary projects and leave annotations in the persistent project
alone. Ghidra's settings/cache are under `.tools/ghidra-home`. Scripts run with
auto-analysis disabled and validate an explicit success marker, since Java
script failures do not always make the headless process exit unsuccessfully.

`functions` accepts one or more **Thumb** function entry addresses; `range`
accepts start/exclusive-end pairs. Use even GBA CPU addresses, not ROM file
offsets. A Thumb pointer may carry bit 0; clear it for the disassembly address.
Function exports contain assembly and provisional C. Range exports retain
undisassembled halfwords instead of assuming all bytes are instructions.
These scripts are intended for verified Thumb entries. Inspect ARM routines
in the persistent Ghidra project with the appropriate instruction mode.

The startup export is a tested example: the ARM startup loads literal
`08000355` from ROM `00000100` and branches via `bx r1` at `080000EC`.
The breakpoint at `08000354` confirms Thumb execution. The subsequent
[font investigation](FONTS.md) identifies the menu reader and existing Latin
glyphs through static analysis and native traces.

## Scripted emulator research

```bash
.venv/bin/python -m tools.capture
.venv/bin/python -m tools.capture --breakpoint 0x08000354 --output build/captures/startup
```

`config/routes/title.json` is the initial route. Make a new JSON file containing
`steps` with `frames`, `press` (optional `hold`/`wait`), and `capture` actions.
Pass it with `--route path/to/route.json`. `--watch-read 0xADDRESS` observes a
native memory read; repeat either debugger option for multiple addresses.
Only supply addresses being investigated in Torneko 2. The default trace cap
is 10,000 events; narrowly chosen probes keep traces useful.

Each run uses a temporary ROM and native file-backed save. Use `--save path.sav`
to seed that temporary cartridge. The report includes ROM/save/route hashes,
actual input timing, captures, register traces, and RAM/pixel hashes.
Snapshots contain `final.state`, `final.sav`, and `final.json` together; keep
all three. `final.ss0` is also exported for desktop mGBA.

For later investigation, `--fixture prefix` restores a raw checkpoint and
`--native-state path.ss0` loads a GUI state. Choose a new output directory and
a route appropriate for the restored scene. Raw fixtures verify ROM, mGBA
version, BIOS label and content hashes before restore. GUI states use mGBA's
own compatibility checks. Raw state bytes are not interchangeable with `.ss0`.
After loading a raw state, advance frames before capturing: the external video
buffer is refreshed by rendering, not by loading the raw core snapshot.

The reusable Python API is in `tools/emulator.py`:

```python
from tools.emulator import Debugger, Session
from tools.rom import load_base

with Session(load_base(), "build/research/example") as game:
    game.frames(600)
    game.press("START", wait=180)
    game.capture("menu")
    game.snapshot().save("build/research/example/menu")
    # Read memory with game.core.memory.u8/u16/u32[address].
    # Use Debugger(game) as a context manager for verified addresses.
```

Debugger callbacks retain their CFFI objects until detachment and report Python
callback errors to the caller. Frame stepping counts the native frame counter;
startup under the built-in BIOS can cross two frames in one debugger call.
Requests that cannot end at exactly the requested frame fail explicitly.

## Next research work

Follow the [localization plan](LOCALIZATION_PLAN.md) for the agreed terminology
and prose rules, work sequence, coverage criteria and first integrated milestone.

The [opening-text discovery pass](OPENING_TEXT.md) records a natural route into
the first dungeon, 30 verified text sources, seven event-bank decodes and the
separate broad-scan queue. Use its reproduction commands for the source catalog
and native decoder checks. The [English opening build](OPENING_ENGLISH.md) now
covers name entry, both opening branches, resume prompts, first-dungeon tutorials,
the first royal audience, nearby castle NPCs and the first destination menu.
The [home-return batch](HOME_RETURN.md) adds the first evening/morning, sale
proceeds and three neighbouring NPCs with both Ed choices. The accumulated
catalog has 86 native sources and 79 reviewed/inserted resources. Bank one has
checked insertion and all 214 getters validated in both ROMs. The
[home-book/banker batch](HOME_BOOKS.md) adds the shared town bank, red-book tips,
blue-book/save flows and the first mansion entrance. Green-book contents and
repaired-storehouse flows remain open. Next, follow the mansion safe-recovery
route and its item/message families; broader coverage remains ongoing.
The [graphics inventory](GRAPHICS_INVENTORY.md) now identifies the first dungeon
arrival card and the distinct title/menu background families, without artwork
changes.

The initial-menu string, reader, pointer and Latin glyph lookup are verified in
[FONTS.md](FONTS.md). The [compact English extension](COMPACT_FONT.md) adds the
missing lowercase and symbols, verifies all 95 printable ASCII characters,
and relocates one menu specimen into checked appended ROM space. Its 16 MiB
cartridge and unchanged Japanese fallback pass the tested menu route.

Next, map other text readers, window widths, command syntax and string tables
before translating more content. Reuse `tools.rom_build.RomBuild` for insertion
ownership, checked source patches and appended allocation; do not allocate
independent overlapping regions. Record discoveries in `MEMORY_MAP.md` before
insertion. Later gameplay and other expansion-sensitive paths still need route evidence.
The name fields and native first-floor save/cold resume are documented in
[NAME_ENTRY.md](NAME_ENTRY.md).

For a future patch, `python -m tools.bps source.gba target.gba output.bps`
checks that applying the patch reproduces every target byte before replacing
the output. This helper does not build a translation or authorize ROM ranges.

`Session.press(("A", "B"), hold=3, wait=30)` sends simultaneous buttons and
records a `keys` array in the input receipt. Single-button records keep `key`.
The native KEYINPUT read at `08000F00` verifies both held and released masks;
use a breakpoint after that read rather than reading a watched I/O register
from its own watchpoint callback, which would recursively trigger the watch.
