# Shiren source lettering for Torneko 2 arrival cards

The user requested this reference on 2026-09-30. The project is
`../Shiren/shiren-revamp-fixes`. Its area titles use packed English bitmap
artwork in `gfx/fonts/area_title_font.2bpp`, not a complete character font or
an outline font. The source typeface has not been identified.

**Inserted on 2026-09-30 after user approval.** All 13 cards and the English
Level prefix pass 30 native cases. See [actual screenshots and limits](ARRIVAL_INSERTION.md).
The source-recovery details below remain unchanged.

- [Original Shiren titles and recovered alphabet](../build/arrival-cards/shiren/index.html)
- [Torneko 2 arrival studio](../build/arrival-cards/audition/index.html)
- [Reusable bitmap data](../assets/fonts/shiren-arrival.json)
- [All candidate budgets](../build/arrival-cards/audition/all-font-budgets.csv)

## What is recovered

`tools.extract_shiren_arrival_reference` reads the source asset directly.
`data/demos/demos.asm` has 194 title-chunk pointers at `Data_db6000`.
`code/bank_05.asm` has 30 ten-byte area records at `UNREACH_C5CDCE`, of which
28 contain labelled artwork. Each chunk is nine SNES 2bpp tiles arranged
3×3, making a 24×24-pixel piece. The decoder assembles complete title strips
before cropping any letters. Every used pixel index is 0 or 1.

The reference gallery shows those 28 intact titles, left aligned and white
on black. It is a source decode, not an emulator screenshot or reproduction
of Shiren's native positioning, colours or floor numbers.

`config/shiren-arrival-font.json` pins all three source hashes and the 43
character crops. The crop selections came from Torneko 3's earlier research;
they were redecoded from Shiren here, and all 43 match the previously archived
T3 glyph pixels and metrics. The new local asset does not depend on the T3
checkout or a system font to rebuild.

The recovered glyphs are:

```text
BCDFGIJLMNOPRSTUVW
abcdefghiklmnoprstuvwyz
'-
```

That is 41 letters and two punctuation marks. The period in `Mt. Fiery` is
new punctuation: the existing three-row dot above `i` is placed at the
baseline without reshaping its pixels. The alphabet sheet marks it amber;
source crops are white. Letter advances are ink width plus one pixel and
the word-space advance is six pixels, inherited from the earlier bitmap
audition. These advances are newly assigned, not recovered font metrics.
The 17px size setting renders the stored glyphs at 1:1; capitals vary slightly
in actual ink height. No horizontal squeezing is used.

This **45-entry bitmap subset**, including space and the derived period,
covers all 13 current Torneko 2 location names and the Well's `Level` prefix.
It is not a complete alphabet: `AEHKQXYZjqx` are absent from the verified
source titles, and no Latin digits are recovered from those titles. Shiren's
area renderer loads floor numbers separately through `LoadKointaiFontTiles`;
those are not claimed as part of this recovered Latin face. The new audition
retains original T2 floor digits and `F` by default. Missing glyphs remain
visible errors if wording or the floor-font option requires them.

The older `T3 audition: Shiren recovered + marked supplements` candidate
remains a separate comparison. It uses Papyrus Condensed to fill missing
characters, which does not establish that Shiren's lettering is Papyrus.
The new `Shiren source pixels + derived period` candidate has no such fallback.

## Measured Torneko 2 budgets

At the selected 17px size, zero extra tracking and original floor digits, the
original Japanese rectangle budgets were:

| Label | Advance | Original region width | Fits width and height |
|---|---:|---:|---|
| Banker's Mansion | 150px | 208px | Yes |
| Cemetery Dungeon | 159px | 192px | Yes |
| Castle Dungeon | 136px | 208px | Yes |
| Lost Forest | 107px | 112px | Yes |
| Mt. Fiery | 78px | 96px | Yes |
| Toro Ruins | 93px | 96px | Yes |
| Magic Dungeon | 124px | 224px | Yes |
| More Magic Dungeon | 169px | 224px | Yes |
| Ordeal Mansion | 130px | 96px | **No** |
| Sword Dungeon | 129px | 176px | Yes |
| Mage Dungeon | 119px | 176px | Yes |
| Mysterious Meadow | 166px | 224px | Yes |
| Well | 32px | 64px | Yes |
| Level prefix | 44px | 64px | Yes |

All regions are 24px high. The approved insertion widens Ordeal Mansion to
**136px**, which fits its 130px advance and complete ink bounds. All other
rectangle sizes stay as listed. The updated studio uses those insertion
budgets and reports all defaults fitting. The name, glyph scale and spacing
are preserved; the wider rectangle passes native tile-map and pixel checks.

## Reproduction and validation

```sh
.venv/bin/python -m tools.build_shiren_arrival_font
.venv/bin/python -m tools.build_graphics_audition
bash tools/verify_graphics_audition.sh
.venv/bin/python -m tools.accept_graphics_audition
```

The first command regenerates source strips, the source manifest, character
data and alphabet proof. Changes to the nominated Shiren files fail their
pinned hashes until explicitly reviewed. Generated artifacts stay in T2;
the sibling source project is only read. The studio embeds the bitmap font
so browsing it needs neither the sibling checkout nor network access.

The acceptance receipt verifies all 43 crops, source/generator hashes and
browser receipts. WebKit checks current-name coverage, missing-character
errors, all eight candidate budgets, exports and settings. The existing
controlled mGBA research checks establish T2's original graphics/layout.
The subsequent [insertion checks](ARRIVAL_INSERTION.md) validate the actual
patched Shiren cards. Source recovery itself makes no ROM or RAM/save changes.

The user also approved keeping the original English GBA credit artwork
unchanged on 2026-09-30. The credits viewer now opens on those source pixels;
historical replacement experiments are unselected. Credit artwork is unchanged
in the ROM that now contains the approved arrival cards.
