# Inserted title and five corner logos

All six images were approved for insertion on 2026-09-30. The main title uses
the approved wooden sign and gold lettering. The five menu backgrounds use
floating gold/red lettering with **no wooden backing**. The original title's
bottom 24 rows, including `Push START!`, and every background pixel outside its
76×36 corner rectangle remain exact. The original English credits are unchanged.

- [Actual in-game screenshots](../build/title-insertion/index.html)
- [Latest English ROM](../build/torneko-2-english.gba)
- [Latest BPS patch](../build/torneko-2-english.bps)
- [Native validation](../build/title-insertion/native-report.json)
- [Insertion acceptance](../build/title-insertion/acceptance.json)
- [Frozen artwork approval](../assets/title-screen/approved.json)

The current ROM SHA-256 is
`bd61d3f6f2db7af8119ecc6ee757f7560808d55ddec192c670368523a2708ab3`.
It contains **3,770 inserted text resources and 20 English graphics**:
14 arrival graphics and these six title/background images. This is still a
development build; graphics insertion does not change text-review percentages.

## Palette fitting and ownership

Each native image is 240×160, with a 512-byte stored palette followed by
38,400 bytes of tiled 8bpp pixels. The title uses 256 palette entries; the
backgrounds use 240, leaving the final 16 entries for UI. Native colour
calibration differs between the title and menus. Merely reducing RGB to five
bits does not reproduce the game's displayed colours.

`tools.pack_title_art` fits the frozen rasters to colours reachable through
the native calibration functions. It locks every original palette index and
colour used outside the edited region. The fitted images therefore preserve
the surrounding scenes and title footer, including under existing calibration
settings. The available palette slots are 193 for the title and 49/23/34/54/50
for backgrounds 13/18/19/20/21. Small colour differences inside the edited
regions are expected from this native palette conversion. The final PNGs and
error measurements are in `assets/title-screen/packed/`.

`tools.title_art` appends six private 38,912-byte resources through `RomBuild`
and redirects the six background-descriptor pointers. It checks all 20 original
descriptor bytes, original resource hashes, approved raster hashes, packed
resource hashes and generator hashes before insertion. No original artwork is
overwritten. Instructions, other descriptor fields, RAM/save layout and all
earlier text/arrival allocations remain unchanged. Exact ranges and native
palette observations are recorded in [MEMORY_MAP.md](MEMORY_MAP.md).

## Native checks and limits

The five backgrounds are reached through ordinary inputs on disposable fresh
saves. After frame 600, START delays of 4/7/0/2/1 frames select backgrounds
13/18/19/20/21. Each route captures the title, menu, name editor, cancellation,
reopening and return. A sixth route uses a disposable copy of the supplied save:
**36 stable scene snapshots** in total. Actual input schedules, source hashes,
loader/copy traces and screenshots accompany the report.

Checks cover complete tile uploads, all 600 visible map entries, calibrated
palettes, full title pixels and unobscured corner pixels. Every unedited screen
pixel, UI VRAM and OAM byte matches the pre-insertion ROM under identical inputs;
the menu UI palette also matches exactly. Each route captures 50 consecutive
startup-transition frames and checks full title pixels while its layer is
visible. Separate controlled native function calls validate **640 colour
conversions** across the two used gamma rows, five levels and colour/monochrome
functions, restoring the snapshot afterward. These are function probes, not
claims of ordinary gameplay through every display setting.

The final ROM also passes all 30 arrival-card cases, both opening-dialogue
branches, 69-character name-entry checks, native English save/cold resume, and
the tested Japanese-save import route. All 135 unit tests pass. Packing and the
ROM/BPS pair reproduce exactly; independent BPS application matches the ROM.
The audition still passes its separate 85 browser checks.

The name editor naturally covers part of the original corner-logo area; this
existing overlap is preserved. Natural late-game routes, full-game playtesting
and discovery of any additional logo appearances remain outside these checks.
The English GBA credits are preserved byte for byte.

## Reproduction

The normal build includes the packed, hash-checked assets by default:

```bash
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.verify_title_art
.venv/bin/python -m tools.accept_title_art
.venv/bin/python -m tools.verify_arrival_art
.venv/bin/python -m tools.accept_arrival_art
```

`./build.sh` also includes these checks in its cumulative validation workflow.
For palette regeneration, run `.venv/bin/python -m tools.pack_title_art` first;
it uses the frozen approved rasters and the historical native palette captures
documented in [TITLE_AUDITION.md](TITLE_AUDITION.md). No image generation occurs
during packing or building.

The pre-insertion ROM/BPS and ledger are archived in
`build/title-insertion/pre-insertion/`, with ROM hash
`c6cf871bcb20060b91ca226d203bdf78713d89aa8cb1643170286e0b011f96c5`.
The audition tools use that archive for original-art references. Native
verification independently rebuilds a comparison ROM from the current text and
arrival assets with `include_title_art=False`, saving it under
`build/title-insertion/comparison/`. This currently reproduces the archived ROM
exactly and also lets future text batches run the graphics checks. Acceptance
restores only the six new allocations and pointer patches and requires exact
equality with this comparison ROM; unrelated byte changes fail acceptance.
