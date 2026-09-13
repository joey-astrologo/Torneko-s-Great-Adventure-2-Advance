# Torneko 2 memory map

Source: the pinned Japanese ROM in `config/rom.json`, SHA-256
`79986287eef366bba987393de8247141973d5564fa72fe2f3f6dd28684cd18aa`.
Ranges below have exclusive ends. The compact English font extension owns only
the appended resources and checked patches documented below. No general free
space, RAM reservations, or save-record allocations have been established.

| Space / range | Observation and evidence | Status |
|---|---|---|
| ROM file `[00000000,00800000)` | Entire original 8 MiB cartridge, hash pinned in `config/rom.json`. | Protected source. |
| CPU cartridge `[08000000,08800000)` | Primary mapping of the supplied image. Ghidra imports header and ROM separately. | Verified import. |
| ROM file `[00000000,000000C0)` | Header: title at A0, game code at AC, maker at B0, version at BC, checksum at BD. Branch at offset 0 targets CPU `080000C0`. | Header bytes/checksum verified. |
| CPU `[080000C0,080000F4)` | ARM startup, beginning `mov r0,#0x12`. Ghidra disassembly and native entry breakpoint. | Verified code entry; no patch ownership. |
| ROM file `[000000F4,00000104)` | Startup literals: `03007F00`, `03007FA0`, `03007FFC`, `08000355`. Last literal feeds `bx r1` at `080000EC`. | Observed literals, not RAM reservations. |
| CPU `08000354` | Thumb startup target of the literal at ROM 100. Native callback records Thumb mode; exported by the generic Ghidra scripts. | Verified entry only; export body bounds are provisional. |
| EWRAM `[02000000,02040000)` | Imported GBA working RAM; full contents compared during checkpoint replay. | Hardware mapping, game ownership unknown. |
| IWRAM `[03000000,03008000)` | Imported GBA internal RAM; full contents compared during checkpoint replay. | Hardware mapping, game ownership unknown. |
| CPU I/O `[04000000,040003FF)` | The pinned loader creates a 1,023-byte I/O block. This describes the loader output, not the full hardware register space. | Loader boundary caveat. |
| Palette `[05000000,05000400)`, VRAM `[06000000,06018000)`, OAM `[07000000,07000400)` | Imported by the GBA loader. | Hardware regions, game asset ownership unknown. |
| Battery file `[00000000,00010000)` | mGBA reports FLASH512; 64 KiB cloned/persisted/reloaded. | Physical save size verified; logical records unknown. |

Evidence: `build/toolchain-validation/mgba/report.json`, the corresponding
`mgba-supplied-save/report.json`, `ghidra-verify.log`, and
`build/captures/startup-thumb/report.json`. Startup disassembly is under
`build/disassembly/`. Reports identify the ROM used.

The debugger acceptance probe temporarily writes ARM instructions to EWRAM
`[02000000,02000008)` and test data to `[02000020,02000024)` in a disposable
session. It redirects registers, proves a native CPU read watchpoint, and
restores the complete snapshot before boot. Those addresses are test scratch
only; this is no evidence of free RAM in the running game. The memory-width
probe similarly restores the word at `02000000` before native execution.

Future discoveries must include source ROM hash, address space, exclusive range,
purpose, evidence, certainty and build/runtime context. Unidentified bytes,
padding, zero/FF runs, and relocated source text are not automatically free.

## Font discovery and diagnostic plan (2026-09-13)

The initial-menu read watchpoint at CPU `08061D05` fires at the byte reader
`08002274` and the two-byte decoder `0800217A`/`0800219C`. Native glyph calls
then reach `08001BC4`, lookup/preparation `08001A4C`, index lookup `08001A04`
and VRAM draw `08001910`. Evidence is under `build/font-research/` in
`menu-source/report.json`, `glyph-trace/report.json`, and the Ghidra exports.

| Space / exclusive range | Purpose and evidence | Status |
|---|---|---|
| ROM `[00061D04,00061D10)` | Initial label `20 82 CD 82 B6 82 DF 82 A9 82 E7 00` (space + はじめから + NUL). Direct pointer at ROM `[00141314,00141318)` contains `08061D04`. Native watchpoints establish the actual menu reader. | Protected source; only this exact 12-byte field is used by the disposable diagnostic label probes below. |
| ROM `[0012B5A8,0012B66C)` | 49 `(u16 code_start, u16 glyph_index)` pairs, including the zero sentinel; descending thresholds used by `08001A04`. | Verified lookup table. |
| ROM `[00180000,00180800)` | 64 narrow glyph records for raw codes `20..5F`, 32 bytes per record. | Extracted font source; widths 6 pixels. |
| ROM `[00182160,001822A0)` | Ten digit glyphs mapped from SJIS `824F..8258`. | Extracted font source. |
| ROM `[00182380,001826C0)` | 26 uppercase Latin glyphs, SJIS `8260..8279`. | Extracted font source. |
| ROM `[00182780,00182AC0)` | 26 lowercase Latin glyphs, SJIS `8281..829A`. | Extracted font source. |
| ROM literal `[00001A48,00001A4C)` | Font-record base `08180000`. Each record is four metadata bytes followed by fourteen big-endian 16-bit bitmap rows. Low nibble of byte zero is the width; other metadata remain uninterpreted. | Verified lookup and bitmap reader. |
| EWRAM `[02036430,020364F3)` | Existing glyph preparation buffer: at most 13×15 bytes for the Latin glyphs reviewed here. Read at lookup return to compare with decoded original font pixels. | Observed scratch use for these glyphs; not a new reservation or full buffer-capacity claim. |
| EWRAM `[020000C2,020000C3)` | Existing foreground palette-index byte read by `08001A4C`. | Observed renderer input, no change. |
| EWRAM `[02000000,02000018)` | Existing initial-menu window descriptor observed in native glyph calls; cursor at +2, fixed-width override at +6, spacing adjustment at +8, style flags at +9. | Observed scene-specific descriptor, no new reservation. |

Diagnostic scope established before use: build each temporary cartridge from the
pinned base, assert the original 12-byte label and its pointer, and replace only
that field with a fitting test string. Preserve all original font bytes and the
pointer. Record the complete source/output hashes and before/after bytes. The
temporary ROM is removed when its emulator session closes; screenshots and
reports are retained. This is a font-existence probe, not a translation build.
For the narrow uppercase specimen only, a debugger callback substitutes the
raw glyph code at the glyph-call boundary to bypass the native ASCII-to-wide
mapping. Record this override explicitly; no renderer code is patched.

All 18 diagnostic samples have now passed. The 62 larger Latin/digit glyphs
resolve to their expected original ROM records, reproduce the prepared native
pixel buffer exactly, and advance the cursor by the recorded width. Two-byte
lowercase renders; ASCII lowercase is skipped in the tested menu. Compact
`START` renders through the documented glyph-code override. Source ROM/save
hashes are unchanged. See [FONTS.md](FONTS.md) and
`build/font-research/review/report.json`; per-sample reports include every exact
diagnostic field replacement and source/output ROM hash.

## Compact English extension ownership plan (2026-09-13)

Established before insertion. `tools.rom_build.RomBuild` checks the pinned base,
source bytes, resource identities, patch overlap, and all original bytes outside
the patches. Resources append after the original 8 MiB; none of the original
font records or apparent padding is reused. The cartridge is padded to 16 MiB.

| ROM file / exclusive range | Owner and purpose | Expected source / evidence |
|---|---|---|
| `[00800000,00800BE0)` | `compact-english`: 95 printable ASCII glyphs, 32 bytes each | Newly appended; authored rows and original-glyph provenance in `assets/fonts/compact-english.json`. |
| `[00800BE0,00800C60)` | `compact-english`: Thumb lookup helper, including literals and reserved padding | Newly appended; assembled by `tools.build_compact_font`. |
| `[00001A04,00001A0C)` | `compact-english`: jump to the appended lookup helper | Must equal `00 04 01 0C 00 23 04 4A`; Ghidra export identifies the four displaced Thumb instructions. Fallback replays their effects and resumes at CPU `08001A0C`. |
| `[00800C60,00800C81)` | `compact-font-specimen`: encoded leading space + `Start adventure` + NUL | Newly appended. Diagnostic samples use the same allocator and record their actual variable end. |
| `[00141314,00141318)` | `compact-font-specimen`: optional initial-label pointer | Must equal `04 1D 06 08`; replacement points at the allocated specimen. Original label bytes at `00061D04` remain intact. |

The helper reserves two-byte glyph codes `F020..F07E`. These exceed the original
lookup maximum `987E` and originally resolve to the blank fallback; they are not
claimed as unused bytes throughout the ROM. The observed multibyte reader
`08002174` passes them to the glyph renderer. Existing code identities, the
special `9AE2` alias, and all existing fonts retain the original lookup path.
The width routine at `08001C70` also calls this lookup. No new RAM is reserved.

The build ledger reports every patch and resource with source/output hashes.
Native validation must establish appended-ROM access, fallback behavior, the
new glyphs, width measurement, and actual menu drawing before this extension is
considered validated. This is one font extension and an optional menu specimen;
other string tables, control sequences, layouts and gameplay remain research.

Validation completed: all 95 new code identities render through the native
menu reader with no glyph-code overrides. Eight specimens match the authored
rows in both the preparation buffer and final screen pixels, retain the final
background row, and match both cursor advances and the native string-width
routine. Seventeen controlled lookup calls verify boundaries, Japanese/Latin
fallbacks, the alias and 16-bit input masking while preserving r4–r11 and SP.
With the Japanese label retained, original and expanded cartridges have
identical screen, EWRAM, IWRAM, battery and frame fingerprints after the same
menu route. These are tested-path results, not a full-game compatibility claim.
Evidence: `build/compact-font/validation.json`, `build.json`, and retained
`docs/compact-font-validation.json`. BPS application reproduces the specimen
ROM byte for byte; original ROM/save hashes remain unchanged.
