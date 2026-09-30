# Credits and arrival-card auditions

The user reopened this work on 2026-09-29. These studios follow Torneko 3's
offline comparison, settings and export workflow, using Torneko 2's own sources
and layouts. The user subsequently approved Shiren arrival insertion on
2026-09-30. The [native gallery and insertion report](ARRIVAL_INSERTION.md)
cover all 13 location cards and Level; original English credits are preserved.

**Decision, 2026-09-30:** keep the original English GBA credit artwork
unchanged. The credits viewer now starts on the exact original bitmap;
replacement typography controls are inactive unless opening a historical
experiment. The user nominated the
Shiren SNES revamp project; its [source lettering and budgets](SHIREN_ARRIVAL_FONT.md)
are available as a separate candidate with no fallback font. Those default
arrival settings are now inserted; alternative fonts/settings remain auditions.

- [Open both studios](../build/graphics-audition/index.html)
- [Ending credits](../build/credits/audition/index.html)
- [Arrival and dungeon cards](../build/arrival-cards/audition/index.html)
- [Actual inserted cards in mGBA](../build/arrival-cards/inserted/index.html)
- [Original credit roll](../build/credits/original-roll.png)
- [Original arrival atlas](../build/arrival-cards/original-atlas.png)

## What was discovered

The **GBA ending credits are already English**. They are a compressed 240×2080
bitmap containing **67 visible lines in 15 sections**, rather than the ordinary
dialogue font. Names, roles and the 1993/1999/2001 copyright notice are preserved
in the audition. The source says `EXECTIVE PRODUCER`; the audition retains that
spelling. Text spacing in the manual raster transcription is a transcription
judgment, not an encoded string. `EMIKO TANAKA` was checked in an enlarged source
crop. The older ASCII credits at ROM `0006DF04` belong to a different resource;
they omit GBA staff and include an opening-movie section. They are not used to
populate this studio.

The arrival atlas provides **13 nonempty location-name rectangles**, with
separate artwork for digits 0–9, `F` and `レベル` (Level). The Well uses Level and
suppresses the whole card above level10. English labels come from the reviewed
save-preview destination catalog. Each main label's original region is 24px
high; its width is recorded below. No extra item-name rows or changes to the
approved dialogue/menu font are involved.

| ID | Current English name | Original name region |
|---:|---|---:|
| 0 | Banker's Mansion | 208×24px |
| 1 | Cemetery Dungeon | 192×24px |
| 2 | Castle Dungeon | 208×24px |
| 3 | Lost Forest | 112×24px |
| 4 | Mt. Fiery | 96×24px |
| 5 | Toro Ruins | 96×24px |
| 6 | Magic Dungeon | 224×24px |
| 7 | More Magic Dungeon | 224×24px |
| 8 | Ordeal Mansion | 96×24px |
| 9 | Sword Dungeon | 176×24px |
| 10 | Mage Dungeon | 176×24px |
| 11 | Mysterious Meadow | 224×24px |
| 12 | Well | 64×24px |

These are the original rectangle budgets, not the maximum space a future
redesigned atlas might support. Ordeal Mansion needs 130px at native Shiren
scale, exceeding its original 96px region. Its approved insertion now uses
136×24px and passes native rendering checks. The studio measures that inserted
region, displays the original width separately, and reports zero overflows
for the approved defaults. Other candidate overflows remain explicit.

**Separate town cards are still unconfirmed.** The earlier first castle/home
routes fade into their scenes without a separate card. Their footage remains
in [the arrival frame viewer](../build/arrival-research/index.html). The new
studio covers the identified dungeon/Well family, not every town transition.

## Using the studios

Open either `index.html` directly; it embeds the images, bitmap fonts and scripts
and needs no server or network. Compare the original with the candidate at
native size and in the enlarged view. The credits studio also scrolls the full
roll and shows every complete section, including the long staff sections.

The eight candidates are T2 compact English, T2 native serif Latin, directly
recovered Shiren source lettering with a derived period, and five
explicitly labelled comparisons from T3's audition assets: Shiren reconstruction,
Papyrus Regular, Papyrus Condensed, Rounded, and credits-derived small capitals.
The older T3 Shiren candidate retains its marked substitute glyphs. The new
source-only candidate covers all current arrival names, retains original T2
floor digits by default, and reports missing letters instead of substituting
another font. Its [reference gallery](../build/arrival-cards/shiren/index.html)
shows all 28 original Shiren titles and the reconstructed alphabet subset.
T3's bitmap comparison
assets are copied locally with source hashes; neither T3 ROM addresses nor
insertion rules are reused.

Controls include font, uniform pixel height, tracking, four-shade/crisp edges and
colours. Credits have separate role/staff fonts and optional centred alignment.
Arrival labels support explicit wording/line-break experiments and floor samples
1–999. The Well's Level prefix is English in the candidate, including when its
original number artwork is selected. Unsupported glyphs and width/height overflow
are visible failures, not dropped characters or automatic fitting.

Save/load settings JSON, export native or 3× PNGs, a comparison, all sections/cards,
or the full credit roll. Settings carry the mode, base-ROM, font-data and renderer
hashes; stale or wrong-studio settings are rejected before changing the controls.
Keep the JSON with selected PNGs. Settings are not automatically saved.

`Export budgets` exports the current candidate. `All font budgets` measures every
candidate at the current heights, spacing, wording and sample floor, preserving
the current settings. CSV records advances, width limits, complete regions,
fit, missing characters and substitute glyphs. The browser verifier also writes
the starting comparison tables:

- [Credit budgets for all fonts](../build/credits/audition/all-font-budgets.csv)
- [Arrival budgets for all fonts](../build/arrival-cards/audition/all-font-budgets.csv)

These are geometry/bitmap comparisons. The approved Shiren arrival insertion
has separate [tile/ownership and native evidence](ARRIVAL_INSERTION.md).
Other font, colour, size and wording choices require their own packing,
budget, ownership and native checks before insertion. Preview canvases are
offline renderings; actual patched-game screenshots are in the native gallery.
Arbitrary colours combined with retained original floor artwork may
require palette remapping; the PNG export is not an insertion-ready tile pack.

## Validation and its limits

The [credits native report](../build/credits/research/report.json) pins the
Japanese ROM, a disposable fresh-title fixture, actual frame schedule and every
override. It enters the original ending setup, skips the save operation and five
story scenes, and runs the original credits decoder and renderer. Surrounding
scene-update calls are replaced with native VBlank waits, with explicit blank
tile/map, BG3-only, backdrop and blend setup. All **2,241 unique source tiles**
match their native uploads. **121 exact 240×160 frame comparisons** cover all
67 visible credit lines, including copyright. Renderer ABI/stack guard and the
fixture battery remain unchanged.

This establishes the decoded text layer and its native rendering. It does not
establish ordinary ending access, untouched scene/window behavior, initial
lead-in/fade correctness or subsequent ending artwork. Eight blank/lead-in/fade
captures are explicitly excluded from the full-frame matches. Direct reads of
write-only GBA scroll/blend registers are recorded diagnostics, not reliable
register values. Full natural ending playback remains a later test.

The [arrival report](../build/arrival-cards/native/report.json) passes **18 cases**:
all13 IDs at floor1, ordinary floors10/99/999, and Well levels10/11. Original
rectangle selections agree exactly, and all38,400 pixels per case match under
the recorded palette conversion. The controller stops its fade at step1, so
native cards are darker than the studio's stored-palette reconstruction; the
colour mapping is measured, not a completed fade/calibration model. The source
fixture naturally selects ID11/floor1; other selectors are controlled probes,
not claims of ordinary story access. Source ROM and battery files are preserved.

WebKit checks all eight font candidates in both studios, settings roundtrip,
six invalid-import cases, explicit overflow, floor variants/suppression, multiline
artwork candidates, nonblank canvases and export wiring. Browser screenshots and
hash-bound reports are in each `audition/` directory. All-font exports restore
the selected settings. It also checks unchanged original credit pixels across
15 section previews, source-only Shiren coverage for the current names and
errors for absent glyphs. The combined receipt checks all 43 recovered Shiren
crops and unchanged compressed credit artwork in the development ROM.
These checks do not validate a future arrival-font ROM patch.

## Reproduction

Use the project's local Python. The arrival native research requires the
original departure fixture from `tools.trace_graphics_sources` if it is absent.

```sh
.venv/bin/python -m tools.extract_graphics_audition
.venv/bin/python -m tools.research_credits
.venv/bin/python -m tools.research_arrival_cards
.venv/bin/python -m tools.build_shiren_arrival_font
.venv/bin/python -m tools.build_graphics_audition
bash tools/verify_graphics_audition.sh
.venv/bin/python -m tools.accept_graphics_audition
```

`config/credits-audition.json` holds the raster transcription. Source ownership,
reader addresses and limits are recorded in [MEMORY_MAP.md](MEMORY_MAP.md).
The original discovery/audition stage did not alter the ROM. The subsequent
approved insertion adds 14 graphics while retaining the 3,770 text-resource count.
The [combined receipt](../build/graphics-audition/acceptance.json) binds the
current studios and input files to the native/browser reports. It records
candidate overflows explicitly and is separate from ROM-release acceptance.
