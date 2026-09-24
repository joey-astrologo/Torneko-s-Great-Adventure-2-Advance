# Torneko 2 Advance localization research

The Torneko 3 research toolchain is reproduced here and validated against the
supplied Japanese Torneko 2 ROM. The cumulative development build now includes
both English opening branches, the flashback, introductory dungeon tutorials,
resume/stair menus, the King's first audience, five nearby castle NPCs, and the
first destination menu, the first evening/morning home scenes, and three nearby
village NPCs with both Ed choices. It also covers the red-book tips, broken-storehouse
blue-book/save flows, mansion safe recovery, family choices and the bank-opening scene.
The home scene includes dynamic sale proceeds.
[The selected font](docs/FONT_AUDITION.md) is the readable Torneko 2 compact
English extension, with all 95 printable ASCII glyphs validated in native mGBA.
[Original-sized early menus](docs/MENU_LAYOUTS.md) add main commands and eighteen
item/ground actions through 25 reviewed menu resources. The first panels now
have 34/36 usable pixels and the original 8 px border gaps; the Option/status UI, bank transactions and 206 identified item names have separate native checks.
Open the [native menu gallery](build/menu-resize/index.html) and
[typography corrections](build/typography/index.html) to review the result.
[Service batches](docs/SERVICE_BATCHES.md) cover dungeon UI, core banking, the first
item names/descriptions, bakery purchases and repaired storage with saved deposit/cold-reload checks.
Open the [service gallery](build/services/index.html) and
[current acceptance receipt](docs/english-services-validation.json). Ordinary bakery
unlocking and later service coverage remain open. [Text progress](docs/TEXT_PROGRESS.md)
tracks the accepted 2,500-resource build and subsequent town-service
work. Stable ROM/BPS copies are retained in `build/accepted/2159/`, alongside the
preceding 2,115-, 2,010-, 1,934-, 1,887-, 1,848-, 1,676- and 774-resource milestones.

The [localization plan](docs/LOCALIZATION_PLAN.md) records the agreed translation
rules, extraction and coverage workflow, build requirements, graphics auditions,
playtesting, and the first opening-area milestone.

The native-observation catalog records 147 Japanese sources. The broader text
inventory and separate review catalogs track discovered, reviewed, inserted and
controlled-tested resources without treating those counts as ordinary gameplay
coverage.
The [initial discovery report](docs/OPENING_TEXT.md) preserves the earlier scope.
Open the
[searchable catalog](build/text-extraction/index.html) to inspect verified text
and the separate candidate queue. All seven known event tables and the shared
town table (300 pointers / 204 sources) are enumerated;
this is not a whole-game coverage percentage.

[English name entry](docs/NAME_ENTRY.md) now supports seven characters, including
`Torneko`, with normal-input editing and native save/cold-load validation. Run
`./build.sh` for the [cumulative English build](docs/BUILD.md), verified BPS patch
and emulator checks. The latest compiled ROM and patch are exported to
`build/torneko-2-english.gba` and `build/torneko-2-english.bps`, with matching
hashes and development status in `build/torneko-2-english.release.json`.
See [the English batch and acceptance scope](docs/OPENING_ENGLISH.md)
for routes, language review, native name substitutions and remaining Japanese text.
The [home-book/banker batch](docs/HOME_BOOKS.md) adds the shared town text bank,
native save/cold-load checks and the mansion entrance. The earlier
[home-return batch](docs/HOME_RETURN.md) establishes bank-one insertion;
[graphics research](docs/GRAPHICS_INVENTORY.md) now identifies the first dungeon
card and the distinct title/menu background resources.

The [mansion quest batch](docs/MANSION_QUEST.md) covers the Imp, recovered safe,
return scenes and bank opening, with four family branches and seven-character
name checks. [View the native preview](build/english/mansion-preview.png).
The current cumulative build also translates the audited bank transactions,
item labels and core combat messages; additional consumers remain in progress.

Open the [side-by-side font audition](build/font-audition/index.html),
[per-font menu budgets](build/font-audition/contexts.csv), or selected
[glyph sheet](build/font-audition/native/compact-english.png). Rebuild with:

```bash
.venv/bin/python -m tools.build_compact_font --output build/font-audition/native
.venv/bin/python -m tools.verify_compact_font --output build/font-audition/native
.venv/bin/python -m tools.review_compact_font --output build/font-audition/native
.venv/bin/python -m tools.audition_fonts
```

The [original-font research](docs/FONTS.md) documents the compact and larger
Latin glyphs already present in the supplied ROM.

From this directory:

```bash
./validate.sh
.venv/bin/python -m tools.capture
```

Validation covers the pinned ROM/header, native mGBA execution breakpoints and
read watchpoints, 8/16/32-bit memory access, frame/input control, screenshots,
raw and desktop-format state replay, native save persistence, Ghidra import,
ARM/Thumb assembly, and verified BPS creation. Results are in
`build/toolchain-validation/`. Captures are in `build/captures/title/`.

Open the prepared analysis project with Ghidra:

```bash
/opt/homebrew/bin/ghidraRun build/ghidra/Torneko2.gpr
```

The project contains the imported cartridge and startup disassembly. Full ROM
auto-analysis has not been run. If the generated project was removed, recreate
it with `bash tools/ghidra.sh import`; this command refuses to overwrite an
existing analysis project.

For desktop mGBA, prepare a separate ROM/save pair and open the printed path:

```bash
.venv/bin/python -m tools.prepare_playtest
# Optional: add --save 'path/to/your.sav' to copy an existing save.
open -a /Applications/mGBA.app 'the/printed/path/torneko-2-japanese.gba'
```

Each preparation creates a new directory under `build/playtest/`. Playtest saves
belong beside that copy. The supplied source ROM and save are preserved.

See [the exploration workflow](docs/EXPLORATION.md),
[installation and tool pins](docs/TOOLING.md), and
[the initial memory map](docs/MEMORY_MAP.md).

To reproduce the local environment from the already-installed Torneko 3 project:

```bash
./setup.sh ../torneko-3-gba
./validate.sh
```

This creates this project's own venv, source copies and native builds. Installed
Ghidra, its GBA loader, Java, Homebrew libraries and desktop mGBA are shared
system dependencies. ROMs, saves, native tools and generated research artifacts
are excluded by `.gitignore`.
