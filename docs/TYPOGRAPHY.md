# Compact numbers and item spacing

The September 19 visual review found three issues: the attack status label said
Sword rather than Weapon; dynamic values used taller numeric fonts; item names
were compressed even when they fit. All three are corrected in the cumulative
English build. Native before/after captures: [gallery](../build/typography/index.html).

## Number source and scope

Ordinary authored English word spaces now advance three pixels rather than six,
including each side of the arrow quantity separator `x`. Letter spacing remains
unchanged. The original compact blank record is retained as provenance; only
the appended space record is narrowed. The byte-constrained Option formatter
retains its original six-pixel single-byte separators.

No replacement alphabet is needed. The selected Torneko 2 compact font already
contains matching original digits: six-pixel advances, nine-pixel digit ink
height. Authored F030–F039 used these correctly; dynamic decimal and item
formatters selected different original glyph families.

The cumulative build's checked lookup helper now aliases:

- `824F..8258`: ordinary decimal digits, including dialogue and bank balances.
- `8755..875E`: item count/enhancement digits in native 1–9,0 order.
- `875F..8764`: native compound 10–15 glyphs, composed from compact digits.
- `8740..8749`: inverse price digits; compact shapes retain inverse styling. The background
  covers each full six-pixel cell, including the trailing column, so adjacent
  green price digits form one continuous strip.
- `8196` and `8266`: bank padding asterisks and currency G.

These aliases apply to every caller of the shared glyph lookup, including
remaining Japanese text using those codes. They do not rewrite original font
records or equipment/curse/button icons. Separate graphics such as the HUD and
arrival cards are separate renderers and are not claimed here. The standalone
font research ROM keeps its original fallback behavior for comparison.

The bank amount editor retains its original eight 12-pixel selection cells.
Each six-pixel glyph is centered by the original renderer, preserving cursor
alignment. This deliberately differs from proportional balance/prose text.
Existing seven-pixel-per-digit wrapping reserves remain conservative.
Bank labels render as `Deposit:` and `Withdraw:` with no intervening space.
Their 57-pixel region ends at x69, where the numeric column begins; the original
176-pixel window is unchanged.

## Item spacing

At CPU `0800F012`, the original item row formatter calls strlen and adds controls
`1C/1D` when output exceeds 20 encoded bytes. These reduce advance by one pixel.
English uses two bytes per character, so even short English names triggered it.

A checked ROM trampoline now scans for valid F020–F07E English glyphs and keeps
normal spacing for those rows. Entirely Japanese rows retain the original
20-byte threshold. No global spacing override, new RAM or wider window is used.
The existing 64-byte row bound and 162-pixel usable inventory region still apply;
markers, counts, enhancements and prices must fit together at normal spacing.

## Verification

- Six ordinary Option routes verify Weapon, status formats, controls/help,
  Give up/Sleep prompts and toggle restoration.
- 52 item cases: four naturally carried items and 48 controlled combinations;
  full English names, uncompressed streams, glyph pixels, price separation,
  output guards, stack preservation and parent restoration checked.
- 12 bank cases verify real in-memory transfers, cancellation, empty balances,
  insufficient amounts and overflow yes/no. The amount-cancel route cycles all
  ten digits and traverses all eight selection cells. Controlled balances are
  clearly distinguished from naturally earned money. No persisted transaction
  save is claimed.
- Numeric lookup probes cover all 38 aliases, adjacent unchanged icons,
  fallback boundaries and callee-saved registers/SP.

Reports are under `build/english/{dungeon-ui,items,bank,numeric}-validation`.
A report belongs to its recorded ROM SHA; older receipts do not approve a newer
ROM. Later shop/storage and other mode layouts still need their own native checks.

The final numeric audit corrected an off-by-one mapping in the item family.
The engine's original decimal conversion tables at ROM 000648D0 and 0006B423
now independently enforce values 0–9 before any build. In particular 8754 is
an equipped/curse icon, 8755 is 1, 875D is 9 and 875E is 0. This semantic check
is separate from the bitmap and lookup checks.
