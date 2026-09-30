# Font choice and menu audition

**Torneko 2's compact English font is restored as the build default.** The
approved shorter labels fit the original early-menu window geometry, preserving
the 8-pixel gaps between borders. Torneko 3's original Latin font 0 remains a comparison asset.
See [corrected menus and validation](MENU_LAYOUTS.md) for the completed four batches.

[Interactive audition](../build/font-audition/index.html) ·
[Every context/font budget](../build/font-audition/contexts.csv) ·
[Label measurements](../build/font-audition/budgets.csv) ·
[Dynamic name budgets](../build/font-audition/dynamic-budgets.csv) ·
[Native before/after](../build/menu-resize/index.html)

The offline page compares exact glyph pixels at 1×–4×, accepts editable labels,
exports PNG previews and lists advance, ink edge and remaining pixels. It has
additional status, Option, bank and first-cohort item contexts plus four dynamic
name cases; the generated report records exact current counts. Original
and current contexts are kept separately: old overflows remain visible rather
than disappearing from the evidence. All selected-font current labels fit.
Native captures are separate from simulated panels.

## Current allowances

| Context | Usable text pixels |
|---|---:|
| Dungeon main commands (original geometry) | 34 |
| Dungeon-menu location banner (one line) | 168 |
| Inventory/ground actions (original geometry) | 36 |
| Complete inventory row while actions are open | 162, including every field |
| Complete inventory row without actions | 162, including every field |
| Bank verb before amount column | 52 |
| Options label before toggle column | 65 |
| Full-width options row | 186 |
| Initial/resume menu | 88 |
| Stair choices | 90 |
| Broken-storehouse blue book | 112 |
| Travel label, including name substitution | 140 |
| Story dialogue | 216 |

These are pixel regions, not character counts or storage capacities. Current
actions retain a 256-byte combined buffer plus 64-byte scratch buffer;
main commands have 64 bytes. Other producers require separate byte audits.
The 112 px native bank editor keeps eight 12px selection cells, now containing
matching compact digits. Proportional bank balances use six-pixel digits.
The bank labels now include attached colons in a 57px region.
See [typography corrections](TYPOGRAPHY.md) for native numeric/spacing checks.

## Preserved assets

`assets/fonts/compact-english.json` retains 62 original compact glyphs, adapts the blank word-space
advance from six to three pixels, and includes 32 matching additions. It covers all 95 printable ASCII characters. `Torneko`
measures 41 pixels; `Swap` 24; `Option` 31; `Remove` 36. No font pixels were redrawn for
this layout correction.

`assets/fonts/torneko3-english.json` freezes 95 glyphs from the original Japanese
T3 ROM, not a fan patch. Its 3–7 pixel advances and monochrome ink are unchanged;
two blank top rows align the source to T2's fourteen-row records. The asset keeps
original descriptor/bitmap bytes and their hashes. Builds/auditions need only
local assets, not the sibling ROM. The earlier
[T3 acceptance receipt](english-font-validation.json) is a historical snapshot;
[current T2 acceptance](english-menu-validation.json) supersedes it.

## Gate before further insertion

1. Record real menu variants, producers, cursor reserves, columns and byte limits.
2. Add both fonts and complete candidate labels/dynamic worst cases to the audition.
3. Resolve relevant overflows with reviewed wording or owned geometry changes.
4. Verify native rendering, selection, clipping, shading and parent restoration
   through opening, cancellation and repeated reopening on the same build.

Unknown later families stay explicit. Passing early menus does not certify the
whole game. In particular, original Japanese item-name probes do not establish
English item-name limits, and synthetic mode/state checks do not establish
natural gameplay reachability. See [the coverage limits](MENU_LAYOUTS.md#remaining-coverage).
