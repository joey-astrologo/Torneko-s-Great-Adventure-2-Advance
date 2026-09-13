# Torneko 2 Advance localization research

The Torneko 3 research toolchain is reproduced here and validated against the
supplied Japanese Torneko 2 ROM. This project is ready for code, text and font
investigation. [The compact English font is complete](docs/COMPACT_FONT.md):
the original capitals and digits plus matching lowercase and missing symbols.
All 95 printable ASCII glyphs pass native mGBA verification. A test ROM changes
the first menu label to “Start adventure”; the rest of the game is Japanese.

The [localization plan](docs/LOCALIZATION_PLAN.md) records the agreed translation
rules, extraction and coverage workflow, build requirements, graphics auditions,
playtesting, and the first opening-area milestone.

Open the [interactive font review](build/compact-font/index.html) or
[glyph sheet](build/compact-font/compact-english.png). Rebuild and verify it with:

```bash
.venv/bin/python -m tools.build_compact_font
.venv/bin/python -m tools.verify_compact_font
.venv/bin/python -m tools.review_compact_font
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
