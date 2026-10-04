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

To follow verified bounded jump tables during caller discovery:

```bash
.venv/bin/python -m tools.audit_source_readers --computed-switches --output build/caller-branches/source-readers-final.json
.venv/bin/python -m tools.audit_switch_readers --output build/caller-branches/switch-readers-final.json
.venv/bin/python -m tools.audit_switch_readers --guard 0x080147F8 --budget 800000 --maximum-path 8192 --output build/caller-branches/save-switch-expanded.json
.venv/bin/python -m tools.verify_tutorial_script_routes --source build/english
```

The switch scans retain unknown data flow and budget/path limits; guard seeds
do not establish ordinary reachability. The script verifier controls bank/map/NPC
setup, executes native NPC selection and original tutorial opcode handlers, and
records its host dispatch/WAIT exclusion. See [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md)
for the two repaired tutorial configurations and their original-ROM evidence.

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

## Current research work

Follow [the plan](LOCALIZATION_PLAN.md) and [coverage matrix](COVERAGE_AUDIT.md).
The opening, books, mansion, storage and bakery milestones are already covered
by their recorded routes; they are not the next discovery tasks.

Start with the unresolved shared/town sources, event fragments, tutorial mappings
and exact static-analysis stops listed in the matrix. Disassemble verified Thumb
entries, follow source tables and RAM producers, and compare original/compiled
callers. A missing bounded reference is not proof of dead code. Capture the active
bank, selector and upstream state in targeted native probes.

Use assisted access when a later scene needs it: a disposable save/state,
controlled scene entry or a documented invincibility/damage patch is appropriate.
Do not make surviving a dungeon a prerequisite for investigating its code. No
invincibility implementation is supplied by this guide. Establish and record
any patch's addresses, expected bytes, purpose and limits before applying it to
a research copy; never alter the supplied ROM/save or silently add research
assistance to the release build. Turn assistance off for damage/death branches.

Prefer entering the native caller and letting it select and render its resources.
Direct renderer calls are useful for bounds but leave upstream selection untested.
Observe all reader/glyph output, inspect full frames and transitions, and retain
inputs, overrides, build/save hashes and unchanged source hashes. Label ordinary,
assisted and direct-handler evidence separately. Frame capture and checking can
be automated; code discovery does not require a full manual playthrough.

Reuse `tools.rom_build.RomBuild` for production insertion and record discoveries
in [MEMORY_MAP.md](MEMORY_MAP.md), with explicit ownership and exclusive ranges.
Earlier route recipes remain in the family guides for reproduction, not as an
instruction to redo completed progression.

`Session.press(("A", "B"), hold=3, wait=30)` sends simultaneous buttons and
records a `keys` array in the input receipt. Single-button records keep `key`.
The native KEYINPUT read at `08000F00` verifies both held and released masks;
use a breakpoint after that read rather than reading a watched I/O register
from its own watchpoint callback, which would recursively trigger the watch.

## Original event and NPC script references

For the newer credits and arrival-graphics workflow, see
[GRAPHICS_AUDITION.md](GRAPHICS_AUDITION.md). `tools.extract_graphics_audition`
decodes the sources, `tools.research_credits` and `tools.research_arrival_cards`
retain controlled native evidence, and `tools.build_graphics_audition` packages
the offline studios. These do not modify or build the release ROM.

The newer `TEXT_PROGRESS.md` supersedes the early milestone counts above.
The script-reference audit is read-only with respect to ROM/save data. Run its
steps in order; the last two consume the preceding source-pinned reports:

```sh
.venv/bin/python -m tools.text_inventory
# Required only if original opening traces are absent:
.venv/bin/python -m tools.trace_opening_events
.venv/bin/python -m tools.research_event_script_refs
.venv/bin/python -m tools.research_npc_script_refs
.venv/bin/python -m tools.research_npc_control_flow
.venv/bin/python -m tools.research_event_menu_refs
```

Reports go to `build/event-script-audit/`. They cover the seven uncompressed
script banks, seven compressed NPC resources, original actor-selector address
arithmetic, opcode lengths, flag/choice branches, and custom help-menu selectors.
The original opening trace supplies 54 independently observed source matches.
All reports pin the base ROM. These are research reports: successful execution
does **not** mean every root is reachable or every reference is valid. Bank2
contains malformed/out-of-range roots; two original help configurations select
incompatible text banks. The JSON retains those failures and their exact offsets.
No source is classified unused from absence of an audited reference alone.
See the September29 event-script sections in `MEMORY_MAP.md` for native
confirmation of the two still-Japanese placeholders and the explicit exclusions.

## Continued caller and custom-name audit

After compiling the current English ROM and refreshing the text inventory:

```sh
.venv/bin/python -m tools.verify_custom_items --source build/english
.venv/bin/python -m tools.audit_source_readers --output build/localization-closure/source-readers-deep.json
.venv/bin/python -m tools.audit_storage_readers
.venv/bin/python -m tools.audit_buffer_producers
.venv/bin/python -m tools.research_event_stubs
```

The producer audit consumes the deep reader report and the matching cumulative
`queue-notice-validation/report.json`, including copied-string cases. Static
reports retain unresolved arguments, path/budget cutoffs and the distinction
between a candidate producer and verified final output. The event-stub tool
uses a controlled native bank/selector/handler driver, with every override
recorded. It does not establish ordinary map access.

Further ordinary-input screen audits use retained, hash-checked native saves:

```sh
.venv/bin/python -m tools.replay_quest_audit
.venv/bin/python -m tools.audit_castle_continuation
```

The first replays the recorded mansion/castle attempt in
`build/localization-closure/later-quest-retry/report.json`, then verifies the
defeat/results/retry branch. The second requires the ordinarily earned native
castle suspend and its exact input/write provenance in
`build/localization-closure/castle-earned-suspend/`. It cold-loads that save on
the English ROM and reaches the flame, lock repair and first storage round trip.
Neither report claims uninterrupted English completion of the whole castle
quest. See [LOCALIZATION_CLOSURE.md](LOCALIZATION_CLOSURE.md) for evidence and
the two incomplete-source editorial decisions.


Computed-reader follow-up and regression checks:

```bash
.venv/bin/python -m tools.verify_wind
.venv/bin/python -m tools.verify_town_overview
```

These execute the original owners and computed selectors. Wind controls the
existing stage/name fields; overview additionally scopes key state to its callback
to isolate the fixture's concurrent town movement. Both record every override.
The [continued audit](LOCALIZATION_CLOSURE.md) separates these checks from ordinary
quest progression and documents the wind and overview sources missed by the
bounded automatic scan.

## Reproduce tutorial entry and exact scan-stop dispositions

```sh
.venv/bin/python -m tools.audit_tutorial_reachability
.venv/bin/python -m tools.audit_switch_readers --output build/caller-branches/all-switch-stop-details.json
.venv/bin/python -m tools.audit_switch_readers --guard 0x080147F8 --budget 800000 --maximum-path 8192 --output build/caller-branches/save-switch-stop-details.json
.venv/bin/python -m tools.audit_save_menu_rows
.venv/bin/python -m tools.audit_switch_stop_dispositions
```

The tutorial audit requires the hash-checked original `script-text-refs.json`
produced by the script research above. It scans complete NPC payloads and event
instruction regions independently of traversal, retaining misaligned byte motifs.
These are research commands, not additional dependencies of a clean ROM build.
Stop observations record exact addresses/bytes and loop repetition; they preserve
the tracer's conservative decisions. Their dispositions concern those scan exits,
not a proof that all readers or branches have been discovered.

## Computed bases, scene assets and complete ending

```sh
.venv/bin/python -m tools.audit_computed_table_losses
.venv/bin/python -m tools.audit_scene_backgrounds
.venv/bin/python -m tools.audit_town_graphics
.venv/bin/python -m tools.audit_ending_sequence --output build/ending-sequence-guarded
```

The computed-base audit consumes `build/caller-branches/source-readers-final.json`
from the existing source-reader scan and checks allocation ownership for the
relocated sites. It retains trace budget/path limits. Graphics tools decode the
complete bounded descriptor tables and execute controlled native loaders/getters;
visual findings are recorded separately. The town and ending tools cold-prepare
the earned storage-save fixture through `tools.verify_storage.SAVE`.

The ending probe redirects one bank call into the complete original ending owner.
Saving, scene staging, movement, fades, dialogue, credits and the final artwork
then run natively; normal A inputs dismiss waits. Its report requires complete
stage order, return, preserved caller ABI/stack guard and no unfiltered text-audit
findings. The disposable ending battery may change; source ROM/save must not.
This tests integration after controlled entry, not ordinary endgame qualification.
