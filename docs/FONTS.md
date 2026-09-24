# Existing Latin font in Torneko 2

This page records the original-ROM investigation. The earlier
[compact extension](COMPACT_FONT.md) added lowercase and missing ASCII symbols.
The current user-selected baseline is the [Torneko 2 compact extension](FONT_AUDITION.md),
with a [side-by-side audition](../build/font-audition/index.html) and measured
menu budgets. Original-ROM findings below remain historical source evidence.

**Confirmed on 2026-09-13:** the original Japanese ROM already contains usable
uppercase and lowercase Latin glyphs. No replacement font is needed to make an
initial mixed-case English text proof.

Open the [local font review](../build/font-research/review/index.html), the
[extracted glyph sheet](../build/font-research/review/latin-glyphs.png), or the
[native menu comparison](../build/font-research/review/native-comparison.png).
These images use original ROM pixels. Host fonts are used only for annotations
outside the specimens.

## Styles and widths

| Existing glyph group | Coverage found | Cursor advance in the tested menu |
|---|---|---|
| Compact | A–Z, digits, and symbol/punctuation slots in raw codes `20..5F` | 6 px |
| Larger serif capitals | A–Z, SJIS `8260..8279` | 9–12 px |
| Larger serif lowercase | a–z, SJIS `8281..829A` | 7–13 px |
| Larger digits | 0–9, SJIS `824F..8258` | 7 px |

These groups belong to the same lookup system and are stored as 32-byte glyph
records. They are not Torneko 3's three font variants. This investigation does
not rule out additional font resources elsewhere in the ROM.

The larger Latin shapes have serifs and variable widths. For example, `i` and
`l` advance 7 pixels, `m` advances 13, and a space advances 6 in the observed
menu. `Start` advances 47 pixels; the diagnostic label's leading space makes
its final cursor 53. Compact `START` advances 30 pixels, or 36 with that space.
These sizes motivated the later compact English extension. Torneko 3's
selected small font used 3–7-pixel ASCII advances; these findings do not imply
the same amount of English will fit Torneko 2's windows.

## Encoding matters

The native text reader does not accept ordinary mixed-case ASCII unchanged:

- ASCII capitals and digits are converted to the larger SJIS glyph codes.
- ASCII lowercase `abcde` produces no letter draws in the tested initial menu.
- Existing two-byte SJIS lowercase codes render correctly. `Start` was displayed
  using those existing Latin codes, with no font or renderer patch.
- The compact capitals exist and draw correctly, but the ordinary uppercase
  path maps capitals to the larger glyphs. The compact `START` specimen uses an
  explicit debugger register override at the glyph-call boundary. Using those
  capitals normally would require a separately designed mapping change.

The compact set's 64 slots do not contain a complete lowercase alphabet.
Slot labels in the atlas identify raw code positions; they do not guarantee
ASCII punctuation semantics. For example, `@` is consumed as a control sequence
by the tested reader. Other text paths and command bytes still require research.

An initial translation encoder can map Latin letters to their existing two-byte
codes, preserving their original glyphs. That uses two ROM bytes per letter;
longer translated strings will still need verified storage and pointer handling.
No general insertion pipeline or expansion support was established by this
original-font proof. The later compact extension verifies its own appended
resources and one relocated menu label, with a checked allocation ledger.

## Source locations and decoding

The ROM identity is pinned in `config/rom.json`. All offsets below are ROM file
offsets, with exclusive ends; add `08000000` for the primary GBA CPU address.

| Range | Purpose |
|---|---|
| `[0012B5A8,0012B66C)` | Descending code/index threshold table, including its sentinel |
| `[00180000,00180800)` | Compact glyph records |
| `[00182160,001822A0)` | Larger digit records |
| `[00182380,001826C0)` | Larger uppercase records |
| `[00182780,00182AC0)` | Larger lowercase records |

The glyph index routine at `08001A04` selects a threshold from the table and
returns `08180000 + index*32`. Each record has four metadata bytes followed by
fourteen 16-bit bitmap rows, big-endian and most-significant pixel first.
The low nibble of metadata byte zero is the drawn width. The renderer decodes
14 bitmap rows and appends one background row, then copies the resulting
15-row pixels to VRAM. Extra metadata remain uninterpreted.

The native routine at `08001A4C` prepares glyph pixels, `08001910` writes them,
and `08001BC4` advances the window cursor. `08001DA8` handles ASCII/control bytes;
`08002174` handles the observed multibyte menu characters. The initial menu's
window descriptor is at `02000000`, origin `(8,8)`, width 96 pixels, with no
fixed-width override and zero spacing adjustment. Those dimensions are specific
to this menu, not a general text budget.

These discoveries and diagnostic ownership are indexed in
[MEMORY_MAP.md](MEMORY_MAP.md). Ghidra exports and original-menu read/glyph traces
are retained under `build/font-research/`.

## Native verification

Reproduce the extraction and all font samples with:

```bash
.venv/bin/python -m tools.review_fonts
```

The verifier renders every larger A–Z, a–z and 0–9 glyph across five-character
menu samples. It checks native glyph addresses, all prepared pixels, cursor
advances and the window boundary. Four additional samples verify mixed case,
ASCII uppercase mapping, lowercase ASCII skipping and the compact override.
All **18 samples** pass, covering **62 distinct larger Latin/digit glyphs**.

Each temporary cartridge changes only the already-traced 12-byte initial-menu
label at `[00061D04,00061D10)`. Its original bytes and pointer are checked first;
all font bytes, renderer code, and the label pointer are unchanged. Per-sample
reports record original/diagnostic ROM hashes and exact before/after field
bytes. Temporary ROM files are removed when sessions close. These are diagnostic
specimens, not a distributed translation build or an approval to change other
source ranges. The user's original ROM and save remain byte-identical.

The detailed report is [review/report.json](../build/font-research/review/report.json).
A compact retained receipt is [font-validation.json](font-validation.json).
