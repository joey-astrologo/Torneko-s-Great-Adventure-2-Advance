# Selected compact English font

This page records the original compact-font milestone. After comparison with
Torneko 3, the user preferred this font's readability. It is restored as the
build default following the [early menu resize](MENU_LAYOUTS.md). The capitals/digits and authored letters remain; the current asset narrows only
the blank word-space advance to three pixels. See [typography corrections](TYPOGRAPHY.md). Open the [side-by-side audition](../build/font-audition/index.html)
for both fonts and original/resized budgets.

The earlier English font preserves the original compact capitals and digits
and supplies matching lowercase. It covers all **95 printable ASCII characters**.
Open the [interactive preview](../build/compact-font/index.html),
[complete glyph sheet](../build/compact-font/compact-english.png), or
[native menu capture](../build/compact-font/mixed-case/menu.png).

## What was added

| Group | Change |
|---|---|
| A–Z, 0–9, space and existing punctuation | 63 original glyph records copied byte for byte, including their 6-pixel advances |
| a–z | 26 newly drawn lowercase letters |
| Backtick, braces, vertical bar and tilde | Five additional symbols beyond the original compact range |
| Backslash | One new glyph; the original raw `5C` slot contains a yen sign |

The 32 additions use the original compact font's one-pixel strokes and baseline.
Capitals and ascenders occupy rows 4–12; the lowercase body begins at row 7.
The descenders in g/j/p/q/y reach row 13, within the native fourteen stored rows.
The renderer adds its existing fifteenth background row. New lowercase advances
are 3–6 pixels: i/l use 3, f/j/t use 4, r uses 5, and the others use 6. Original
compact glyph advances stay at 6 pixels. This uses the existing VWF renderer.

[assets/fonts/compact-english.json](../assets/fonts/compact-english.json) is the
editable source: fourteen rows of `.`/`#` per glyph, explicit advance, origin,
and original record bytes/offset where applicable. The packer rejects changes
to original glyph shapes, widths or ownership, as well as incomplete coverage.
The preview shows exact glyph pixels; its annotations use a host font.

“Complete” here means basic printable ASCII: English letters, digits and ASCII
punctuation. Curly quotes, em dashes, accented letters and other Unicode symbols
are not silently substituted. The encoder rejects them until explicitly handled.

## ROM integration

The original reader remaps ASCII capitals/digits to the larger font and skips
ASCII lowercase. The English encoder therefore emits a new two-byte code for
each printable character: `F020..F07E`, corresponding to ASCII `20..7E`.
This also makes literal `@` and `~` render without entering their original
single-byte control paths. Newlines encode as `0D`; strings end with `00`.

```python
from tools.compact_font import encode, measure

encoded = encode("Start adventure")  # two bytes per printable character + NUL
pixels = measure(" Start adventure")  # 88, including the menu's leading space
```

A Thumb hook at CPU `08001A04` routes only these new codes to a separate table
appended at CPU `08800000`. Existing codes follow the original lookup, including
its alias behavior. The native renderer and text-width routine both use this
lookup. No original font bitmap, Japanese text or save data is replaced.

The build appends 3,040 font bytes and a 128-byte helper after the original 8 MiB,
and pads the cartridge to 16 MiB. The optional specimen appends its own encoded
label and updates the already-traced initial-menu pointer. The original label
bytes remain intact. `RomBuild` owns all allocations and checks original bytes,
patch overlap, resource hashes, alignment padding and unowned modifications.
Exact ranges and source-byte requirements are in [MEMORY_MAP.md](MEMORY_MAP.md).

This extension establishes its own appended resources and one label relocation.
It does not establish the rest of the game's text tables or pointer conventions.

## Build and review

The commands below now follow the active font selection. For the current build,
output paths and two-font comparison, use [FONT_AUDITION.md](FONT_AUDITION.md).
The historical measurements in this page describe this unchanged compact asset.

```bash
.venv/bin/python -m tools.build_compact_font
.venv/bin/python -m tools.verify_compact_font
.venv/bin/python -m tools.review_compact_font
open build/compact-font/index.html
open -a /Applications/mGBA.app build/compact-font/torneko-2-compact-font.gba
```

Press Start at the title screen to see “Start adventure”. The rest of the game
is Japanese. The generated ROM has its own save beside it; the supplied source
ROM and save are preserved. The generated BPS patch is checked by applying it
to the pinned original and comparing every resulting byte.

`tools.build_compact_font.build_rom(sample=None)` builds the font extension
without changing any label; the command-line build includes the review specimen.
After editing new glyph rows, rerun all three font commands. The review generator
rejects native results whose font-asset hash no longer matches.

## Validation and remaining layout work

Native mGBA 0.10.5 verification covers eight real menu specimens and all 95 glyphs:

- Normal two-byte decoding and lookup into the expanded cartridge, with no
  glyph-code register overrides during gameplay captures.
- Exact prepared bitmap pixels and final on-screen glyph pixels, including
  descenders and the last background row.
- Per-glyph cursor advances, the observed 96-pixel menu limit and the game's
  own string-width routine. The latter is tested separately by controlled calls
  which restore the complete emulator snapshot afterward.
- Seventeen controlled lookup probes covering Japanese/Latin fallbacks, alias,
  boundary codes and input masking, with callee-saved registers and SP preserved.
- Identical original/extension menu screen, EWRAM, IWRAM, battery and frame
  fingerprints when the original Japanese label is retained.

The native menu schedule boots 600 frames, holds Start for 3 and releases it for
180, capturing frame 783. All verification cartridges use disposable native
saves. The original ROM and supplied save are unchanged.

`./validate.sh` also passes all 15 tests and the existing ROM, emulator, assembly,
BPS and Ghidra acceptance checks. Reports:
[native validation](../build/compact-font/validation.json),
[build ledger](../build/compact-font/build.json), and
[retained receipt](compact-font-validation.json).

The compact font improves the line budget; it does not guarantee every English
translation fits. “Start adventure” measures 82 pixels, or 88 with the specimen's
leading space, within this menu's 96 pixels. Other windows may have different
widths, spacing adjustments or fixed-width overrides. Translation work still
needs per-window measurements, explicit wrapping and storage/pointer checks.
Other text paths and full gameplay with the expanded ROM remain unverified.
