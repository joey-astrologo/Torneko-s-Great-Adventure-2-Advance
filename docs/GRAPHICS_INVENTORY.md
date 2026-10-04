# Graphics discovery queue

Current text/graphics counts and build identity are in [the coverage matrix](COVERAGE_AUDIT.md).
Lead remaining discovery with scene loaders, decompression and atlas consumers,
then inspect decoded assets and native frames. An ordinary playthrough is not
required; record controlled or assisted scene entry separately.

Updated 2026-10-03. This records native resource discoveries and work still to
investigate. Exact ranges and evidence are in [MEMORY_MAP.md](MEMORY_MAP.md).
Discovering an asset does not authorize overwriting it or establish complete
graphics coverage.

| Family | Current evidence | Remaining work |
|---|---|---|
| Main title artwork/logo | Approved wood-and-gold title inserted; native full-screen, palette and startup-transition checks pass. Original footer exact. | [Inserted gallery and acceptance](TITLE_INSERTION.md). Additional scene consumers remain outside these title checks. |
| Menu/name-entry logo appearance | All five floating-logo backgrounds approved and inserted. Ordinary menu/name/cancel/reopen routes pass; surrounding pixels and 16 UI palette entries remain exact. | [Actual screenshots](../build/title-insertion/index.html). Later logo occurrences remain open. |
| Full-screen backgrounds | All 22 records, 19 unique bases and nine foreground records decoded; all 22 native tile/map uploads pass. Existing six title/logo replacements account for the Japanese lettering in this table. | [Decoded layers and native evidence](../build/graphics-discovery/backgrounds/index.html). Other loaders remain separate. |
| Scrolling town backgrounds | All 28 records / 23 unique bases, 11 flag replacements and 14 door records decoded; 53 selector states / 377 native calls pass. | [Scene assets and selector evidence](../build/graphics-discovery/town/index.html). Controlled selectors establish these assets, not ordinary access to every story state. |
| Dungeon arrival lettering | 13 English Shiren name graphics and Level inserted, including wider Ordeal Mansion; 30 native pixel/upload/return cases pass. Original digits/F retained. | [Native inserted-card gallery](../build/arrival-cards/inserted/index.html). Later entry/scene integration remains open; use traced callers and assisted access; [insertion evidence](ARRIVAL_INSERTION.md). |
| Separate town arrival cards | [Frame viewer](../build/arrival-research/index.html): the first scripted castle arrival and return home fade directly into their scenes; no separate card observed on those routes | Trace other town entries and later story states before deciding whether a separate card family exists. |
| Signs and static scene objects | All 85 static object instances / 79 distinct images from the scrolling table decoded with native palette lookup. Visual review of these and the scene layers found no additional Japanese lettering. | Independently animated actors and other atlas consumers remain outside this bounded inventory. |
| Ending credits and surrounding artwork | Original 67-line English roll preserved. A complete controlled ending now runs all five scenes, native save, fades, credits and END artwork through return; all 57 ending sources appear, with 71 reads / 3,338 glyphs and no unexpected Japanese or layout violations. | [Full sequence and native receipt](../build/ending-sequence-guarded/index.html). One bank-call entry override; original fixture name retained. Ordinary ending access and other entry-state combinations remain unproved. |

The user reopened credits/arrival discovery and auditions on 2026-09-29.
See [GRAPHICS_AUDITION.md](GRAPHICS_AUDITION.md) for reproduction, budgets and
the distinction between decoded artwork and controlled native evidence.
On September 30 the user nominated Shiren's SNES revamp lettering for arrival
cards. Its [43 recovered glyphs and derived period](SHIREN_ARRIVAL_FONT.md)
cover the current location names. The user then approved insertion, and
Ordeal Mansion now fits its widened 136px rectangle at native pixel scale.
The Shiren arrival style is selected. The user next requested the title audition
on September 30, then approved the main title and five floating corner logos
for insertion. All six resources are now inserted with native palette fitting,
checked pointer ownership and ordinary menu/name/cancel/reopen validation. See
[TITLE_INSERTION.md](TITLE_INSERTION.md) for evidence and remaining limits.
Later auditions should show native-size output and native palette/tile
constraints, preserve selected artwork/settings, and use one consistent English
logo treatment across every verified occurrence.

## First arrival capture follow-up

The [frame viewer](../build/arrival-research/index.html) contains 600 consecutive
frames of the first dungeon entry, 300 consecutive frames after the first
dungeon exit choice, 60 ten-frame samples while walking out of the castle,
and 120 five-frame samples after choosing Home. The castle
exit opens a destination menu; it is text UI rather than arrival artwork.
The English build now localizes that menu separately.

[Replay verification](../build/arrival-research/replay-verification.json) compares
the earlier 480 PNG files against fresh native replays: every file matches byte for byte.
The [new dungeon-entry receipt](../build/arrival-research/first-dungeon/report.json)
separately checks all 600 new frames against a second native replay.
This is evidence for these particular transitions, not proof that all towns or
dungeons lack cards. The first dungeon does have a separate card; no separate
town card was observed on the two earlier town routes. The newer credits/arrival
audition research extends this early capture inventory as described above.
No graphics insertion ownership is claimed from screenshots.

## Confirmed resource formats

The October 3 loader audit follows the full-screen table at ROM
`[0013EC14,0013EDCC)` and the separate scrolling table at
`[0013E674,0013E914)`. The latter includes flag-controlled replacement rectangles,
door images and static objects; those are no longer an unexamined graphics family.
The decoded layers are not complete gameplay screenshots. The ending gallery
separately records actual composed frames without replacing scene updates,
display registers or the credit renderer. Its saved Japanese player name is
intentional user data and is checked by exact substitution, not a blanket glyph
exception. Source ROM/save files remain unchanged; native ending saving affects
only the disposable session.

Reproduce these bounded audits:

```bash
.venv/bin/python -m tools.audit_scene_backgrounds
.venv/bin/python -m tools.audit_town_graphics
.venv/bin/python -m tools.audit_ending_sequence --output build/ending-sequence-guarded
```

Visual-review receipts are stored beside the background/town reports. They
record visual findings separately from the automated byte/selector checks.

The main title is one 240×160 tiled image: 512 stored palette bytes and 38,400
8bpp pixel bytes, with a map synthesized by the native loader. The large logo,
landscape and existing `Push START!` are part of that image. The menu uses a
different image containing its smaller corner logo. Its selected image persists
behind the name editor. This establishes reuse for that menu/editor pair, not
one universal logo asset.

The [arrival atlas](../build/arrival-research/first-dungeon/atlas-native-palette.png)
is 4bpp artwork, 224×264 pixels, containing Japanese area labels and floor
symbols. Dungeon ID 11 selects its 224×24 **ちょっと不思議の草原** rectangle;
the compositor adds `1F` separately. It does not use the story font or the
compact English extension. That original atlas is retained. Its selected English replacement, Mysterious
Meadow, is now approved, inserted and natively verified; see
[the insertion guide](ARRIVAL_INSERTION.md).

[Native graphics report](../build/graphics-research/report.json) ·
[Title/background sources](../build/graphics-research/title/report.json) ·
[First dungeon source/capture report](../build/arrival-research/first-dungeon/report.json)

Reproduce source tracing and regenerate the viewer:

```bash
# Uses the original opening-1 fixture produced by tools.trace_opening.
.venv/bin/python -m tools.trace_graphics_sources
.venv/bin/python -m tools.review_arrivals
```

Regenerate the viewer and its replay routes with:

```bash
.venv/bin/python -m tools.review_arrivals
```

Each generated `route.json` names its checked raw fixture prefix. For example:

```bash
.venv/bin/python -m tools.capture \
  --fixture build/arrival-research/first-castle/stairs \
  --route build/arrival-research/first-castle/route.json \
  --output build/arrival-research/replay-first-castle
```

The original Japanese fixture chain begins with `tools.trace_first_dungeon
--castle --output build/castle-arrival/research`; source and fixture hashes are
retained alongside the captures. These research checkpoints are separate from
the checkpoint-free English ROM build.
