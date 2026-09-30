# Inserted arrival cards

Approved and implemented on 2026-09-30. All 13 identified location cards use
the selected Shiren source lettering at native pixel scale, plus the derived
period in `Mt. Fiery`. The Well uses an English `Level` prefix. Original floor
digits, `F`, palette, timing and fades are retained. The original English GBA
credits are unchanged.

- [Actual patched-ROM screenshots: all 30 native cases](../build/arrival-cards/inserted/index.html)
- [Latest English ROM](../build/torneko-2-english.gba)
- [Latest BPS patch](../build/torneko-2-english.bps)
- [Native report](../build/arrival-cards/inserted/report.json)
- [Insertion acceptance and byte delta](../build/arrival-cards/inserted/acceptance.json)

Arrival-validation ROM SHA-256: `bd61d3f6f2db7af8119ecc6ee757f7560808d55ddec192c670368523a2708ab3`.
BPS SHA-256: `c3b97e07cb143c7072b48e450baea605a0b4ed32afc4d4af8a5b2b5ee3a99bbc`.
All 30 cases were rerun after [title/background insertion](TITLE_INSERTION.md).
The latest root build additionally includes the [menu-banner fix](LOCATION_BANNER.md),
which preserves every arrival graphics byte. These native reports retain their
original validation-ROM hash.
The original arrival-only build is archived in `build/title-insertion/pre-insertion/`.
The release remains a development build: text discovery and full-game
playtesting are still in progress. Counts are **3,770 inserted text resources
plus 20 English graphics** (14 arrival, one title and five backgrounds); graphics
do not increase the script-review percentage.

## Layout and ownership

Ordeal Mansion's 130px text now fits a **136×24px source rectangle**, widened
from 96×24px. All other name rectangles retain their original sizes. Placement
preserves the approved preview's screen centering, native glyph pixels and
spacing; no smaller font, squeezed letters or extra lines are used. The studio
now measures the inserted 136px region and reports no default overflows.

`tools.arrival_art` appends a private 224×600-pixel 4bpp atlas and a private copy
of the 25 rectangle descriptors through `tools.rom_build.RomBuild`. The copied
atlas retains all original bytes as its prefix; 14 new 224×24 rows hold the
English names and prefix. Original digits/F retain their exact source pixels
and rectangles. The six original literal redirects are checked against expected
bytes and share the project allocation/overlap ledger. Original source artwork,
descriptor tables, palette and credit stream stay untouched.

The renderer keeps its native 28-tile source stride and copies only the selected
rectangles into VRAM. No instructions, RAM/save layout, formatter buffers or
controller logic change. The blank initial tile still comes from the original
asset. Bounds and exact source ranges are in [MEMORY_MAP.md](MEMORY_MAP.md).

`config/arrival-art.json` pins the approved font hash, names, native size and
Ordeal width. Font provenance remains in [SHIREN_ARRIVAL_FONT.md](SHIREN_ARRIVAL_FONT.md).
Unapproved missing characters or out-of-region ink fail the build. The existing
dialogue/menu font is unaffected.

## Native validation

`tools.verify_arrival_art` cold-boots the current ROM with a disposable fresh
save, enters `Torneko` through the ordinary editor and reaches the first
departure through ordinary opening inputs. Its checkpoint and actual input
schedule are recorded under `build/arrival-cards/inserted/fixture/` and bound to
this exact ROM. No Japanese or older-English raw state is relabelled for reuse.

The 30 cases cover:

- Every location selector 0–12 at floor 1.
- Ordeal Mansion at floors 2–10, 99, 100 and 999, exercising every digit and
  one-, two- and three-digit fields beside the widened name.
- Mysterious Meadow at floors 10, 99 and 999, including the largest tile upload.
- Well levels 10 and 11; level 11 correctly suppresses the entire card.

Each case matches all **38,400 screen pixels** against independently placed
font glyphs and retained original floor artwork: **1,152,000 pixels total**.
Expected colours use the recorded original controller's step-1 fade conversion;
the native controller never reaches the studio's full stored white. This is a
comparison at the visible card frame, not a claim to have compared every fade
frame. Original fade-in, hold, fade-out and return execute normally in every case.

At compositor return, all **96KiB of VRAM** must equal the previous contents
plus precisely the expected tile uploads and tile-map writes. This catches
clipping, wrong atlas rows, bad tile packing, stray map writes and changes to
surrounding VRAM. The maximum upload is 108 tiles, with tile zero reserved,
within the existing 512-tile character region. Compositor/controller preserved
registers, stack guards and battery contents also pass.

**Mysterious Meadow 1F is the natural route**, with no field/register/PC
overrides. Its three-page English tutorial completes with 128 glyph checks,
and ordinary movement succeeds afterward. The other cases temporarily set only
the dungeon selector and/or floor at the original controller entry, restore
those fields before its caller resumes, and run the real patched renderer.

The remaining risk is **natural late-game progression and scene integration**:
these checks do not play through each dungeon's unlocking, entrance route or
later story state. They establish that every identified card renders correctly
through its native controller. Separate town-card families and unrelated title,
background and ending scenes are outside this change.

## Build and regression evidence

All previous text allocations, original patches and other ROM bytes are
identical to the archived text-only 3,770 build. The delta consists of two new
appended resources and six four-byte pointer patches. Disabling the arrival
insertion in `build_rom` reproduces the previous ROM exactly. No original gaps
or unknown padding were claimed as free space.

Both fresh opening branches pass (2,861/2,956 glyph checks, 29 reads each), all
135 unit tests pass, and both WebKit studios pass with zero default arrival
overflows. The final build reproduces the staged ROM and BPS byte-for-byte;
the release exporter independently applies the BPS and compares the entire ROM.
The supplied Japanese ROM/save remain unchanged. Logs are under
`build/arrival-cards/insertion/`. This is focused acceptance of the graphics
delta; full cumulative text acceptance remains at the documented 3,768 milestone.

## Reproduction

```sh
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.verify_arrival_art
.venv/bin/python -m tools.accept_arrival_art
.venv/bin/python -m tools.build_graphics_audition
bash tools/verify_graphics_audition.sh
.venv/bin/python -m tools.accept_graphics_audition
```

`build.sh` includes native arrival verification and acceptance. To reproduce
this specific isolated delta check, add
`--baseline build/arrival-cards/pre-insertion` to `tools.accept_arrival_art`.
Future unrelated text changes will require a new appropriate baseline.
