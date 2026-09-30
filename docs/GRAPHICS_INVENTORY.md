# Graphics discovery queue

Updated 2026-09-30. This records native resource discoveries and work still to
investigate. Exact ranges and evidence are in [MEMORY_MAP.md](MEMORY_MAP.md).
Discovering an asset does not authorize overwriting it or establish complete
graphics coverage.

| Family | Current evidence | Remaining work |
|---|---|---|
| Main title artwork/logo | Approved wood-and-gold title inserted; native full-screen, palette and startup-transition checks pass. Original footer exact. | [Inserted gallery and acceptance](TITLE_INSERTION.md). Full-game playtesting remains open. |
| Menu/name-entry logo appearance | All five floating-logo backgrounds approved and inserted. Ordinary menu/name/cancel/reopen routes pass; surrounding pixels and 16 UI palette entries remain exact. | [Actual screenshots](../build/title-insertion/index.html). Later logo occurrences remain open. |
| Town and opening backgrounds | [Opening scene](../build/opening-text/native/opening-1.png) and flashback captures in the recorded route | Decode the actual graphics families; inspect lettering, overlays and animated variants separately. |
| Dungeon arrival lettering | 13 English Shiren name graphics and Level inserted, including wider Ordeal Mansion; 30 native pixel/upload/return cases pass. Original digits/F retained. | [Native inserted-card gallery](../build/arrival-cards/inserted/index.html). Natural routes beyond the first entry remain open; [insertion evidence](ARRIVAL_INSERTION.md). |
| Separate town arrival cards | [Frame viewer](../build/arrival-research/index.html): the first scripted castle arrival and return home fade directly into their scenes; no separate card observed on those routes | Trace other town entries and later story states before deciding whether a separate card family exists. |
| Signs and other baked-in text | No completed asset audit | Inspect decoded scenes and sprite/object layers at native resolution. |
| Ending credits and surrounding artwork | GBA scrolling bitmap decoded: 67 English lines / 15 sections; all visible lines covered by controlled native text-layer comparisons. User approved keeping this artwork unchanged on September 30. | [Original credits viewer](../build/credits/audition/index.html). Natural ending playback, surrounding artwork and untouched scene transitions remain open. |

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
compact English extension. Its English area-name decision and artwork remain
pending in this initial discovery pass; the newer audition uses the existing
reviewed destination name Mysterious Meadow.

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
