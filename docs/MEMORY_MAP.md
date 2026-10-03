# Torneko 2 memory map

Source: the pinned Japanese ROM in `config/rom.json`, SHA-256
`79986287eef366bba987393de8247141973d5564fa72fe2f3f6dd28684cd18aa`.
Ranges below have exclusive ends. The font and name-entry components own only
the appended resources and checked patches documented below. No general free
space or new RAM/save allocation has been established.

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

## Opening text and compressed-bank discovery (2026-09-13)

The recorded Japanese opening reaches the first dungeon through normal button
input. `config/routes/opening.json` preserves that schedule, including redundant
inputs and waits. The native source trace is `build/opening-text/trace.json`.
All locations below describe existing resources, not new insertion ownership.

| Address space / exclusive range or entry | Finding and evidence | Status |
|---|---|---|
| CPU `080021B4` | Shared string reader: r0 window, r1 string pointer, r2 text pacing, r3 input mask. Opening menu, keyboard, story and dungeon-help calls observed. | Native reader entry verified. |
| CPU `08002298` | Wrapper passes its window/string/pacing arguments to `080021B4`. | Disassembly and opening traces. |
| CPU `08015A50` | Story-window API receives the string in r0; observed callers also supply choice/context parameters. | Native entry observed; full argument and choice semantics remain under investigation. |
| CPU `0804D6F8` | Loads related event resources from parallel tables and fixes up existing RAM headers. | Ghidra export `build/opening-research/event-loader.txt`. |
| CPU `[0805B48C,0805B490)` | BIOS type-10 LZ77 wrapper: `svc 11; bx lr`. | Disassembly and native write watchpoint. |
| ROM `[0014CD4C,0014CD68)` | Seven consecutive direct-resource pointers used by the event loader. | Table base from literal `0004D798`; individual resource roles not yet fully decoded. |
| ROM `[0014CD68,0014CD84)` | Seven consecutive compressed-resource pointers used by the event loader. | Table base from literal `0004D79C`; these resources are outside the current text-bank extraction. |
| ROM `[0014CD84,0014CDA0)` | Seven compressed event-text bank pointers. | Base from literal `0004D7A0`; index zero read at CPU `0804D71C` on the opening route. Seven streams decode structurally; this is not proof of all event resources in the game. |
| ROM `[0043FAAC,004410E3)` | Opening event-text bank, decoded size `2F64` (12,132 bytes). | Exact consumed compressed range; full decoded output equals native RAM immediately after the natural load at frame 1515. |
| ROM `[004410E4,0044453A)`, `[0044453C,00445FBB)`, `[00445FBC,00448593)`, `[00448594,0044A5F5)`, `[0044A5F8,0044F385)`, `[0044F388,00454F2B)` | Remaining six consecutive compressed bank resources, indexes 1–6. | Exact compressed ends from the bounded decoder. Per-resource lengths and hashes are in the extraction manifest; intervening padding remains protected. |
| EWRAM `[020241AC,02027110)` | Natural opening bank load destination/output. | Source pointer `0843FAAC`, destination `020241AC`, table word `0814CD84`, return `0804D726`; all decoded bytes compared before the later header fixups. |
| EWRAM `[020241AC,0202EC30)` | Maximum span required to test the seven decoded banks (43,652 bytes). | Controlled BIOS-decoder verification uses this existing destination in disposable snapshots, with guards and full restoration. This does not reserve additional RAM or prove its live availability for expansion. |
| IWRAM `[03007CFC,03007D0B)` | Name-entry display string observed as `トルネコ＊＊村`, including NUL. | Producer subsequently traced to `0801545C`; see name-editor research below. Transient stack display, not permanent name storage. |
| ROM `[000646BC,000647B3)` | Observed hiragana keyboard display string with position commands. | Native reader/byte match; key-selection storage and the alternate page need separate research. |
| ROM `[000647D4,000647F5)` | Keyboard action labels with `04` position operands. | Native reader/byte match. |
| ROM `[0006309C,000630AA)` | Shared visible yes/no label string. | Observed at the opening play-together choice; cursor/action mapping remains a separate insertion requirement. |
| ROM `[0006B0E8,0006B184)` | First-dungeon movement/combat help. | Native reader/byte match on the opening route. |

The 30 verified text spans and their original byte tokens are retained in
`translations/master.json`. Compressed-bank offsets are offsets into the decoded
resource, not physical ROM positions. Each bank record retains its compressed
ROM source. Native observations include the active bank so reuse of the same
RAM address in another bank cannot silently merge identities.

The control dispatch table is ROM `[00001E84,00002080)`: 127 four-byte handler
addresses, reached by `08001DA8` for codes `01..7F`. An earlier range export
starting at `08001E84` mechanically disassembled these table words as Thumb;
those apparent instructions are data, not verified code. Handler exports in
`build/opening-research/story-window.txt` confirm `04 xx` sets cursor x to
`floor(15*xx/16)`, while `06 xx` sets x directly. Newline `0D` is handled by the
outer reader. `@...@` sequences are retained as opaque commands until their
event semantics are established. Original command bytes must round-trip exactly.

The broad scan covers the original ROM and these seven decoded resources at
NUL boundaries, with an explicit language filter and length bound. Candidate
spans, header data and unexplored gaps are not verified strings, pointer owners
or free space. See `build/text-extraction/report.json` and `candidates.json`.

## Name-editor research (2026-09-13)

These are existing resources and observed uses, not patch ownership or permission
to reuse spare bytes. See [NAME_ENTRY.md](NAME_ENTRY.md) for the seven-letter
`Torneko` requirement and remaining English/save acceptance.

| Address space / exclusive range or entry | Finding and evidence | Status |
|---|---|---|
| CPU `0801545C` | Shared editor; opening arguments r0=4, r1=`08063D60`, r2=6, r3=11, LR=`08014BEF`. Copies a 16-byte indexed record into working RAM, converts r2 IDs to two-byte glyphs on the stack, formats and displays them; copies the record back on successful confirmation. | Native entry, four display calls and confirmation copy verified by `tools.trace_name_entry`; disassembly in `build/name-entry/editor-functions.txt`. |
| ROM `[00014BE6,00014BE8)` | `06 22`: opening caller sets r2=6, the character limit. | Native argument and normal-button boundary check agree. No patch authorized by this map entry alone. |
| CPU `08019F3C` | Selection/editing logic receives the limit in r0, writes one-byte IDs, caps the position at limit−1 and moves selection to Finish when full. Name cursor x uses slot×14. | Disassembly and native input/working-buffer observations. |
| ROM `[00063D60,00063D65)` | `%s村` plus NUL, used to format the opening name display. | Exact bytes and native caller argument verified. |
| ROM `[00141A28,00141B9A)` | Observed two-byte glyph sequence for IDs `00..B8`; `01` is the vacant-slot glyph. No Latin alphabet in this sequence. | Byte inspection and native ID conversion; trailing data remains protected. |
| ROM `[00147F00,00147FC0)` | Three 64-byte selection pages; `08019F3C` combines page×64 with selection. `FE`/`FF` invoke special actions. | Disassembly/table inspection; current normal route exercises the first page only. |
| EWRAM `[02003B46,02003B56)` | Stored 16-byte indexed-name record. Default `75 9E 65 6B 01 01 01 01 00 00 00 00 00 00 00 00`. | Native initialization by `080590D0`, editing isolation and confirmation copy observed. Battery persistence remains to be tested. |
| EWRAM `[0200CCF4,0200CD04)` | Editor's 16-byte working copy. | Actual source/destination/length observed at confirmation call `0801567C`. |
| EWRAM `[0200CCE4,0200CCE8)`, `[0200CCEC,0200CCF0)`, `[0200CCF0,0200CCF4)` | Keyboard page, selected key/action, and zero-based name position respectively. | Disassembly; selection/position checked after normal buttons. |
| EWRAM `[02000000,02000018)` during this editor | Name window descriptor; width 13 tiles, height one row, fixed advance 14. | Native descriptor at display call; this address is reused by other windows. |
| CPU `08041FD4`, `08020564` | Indexed-name consumers convert at most eight IDs and write a terminator at output+16. The latter also calls the editor with r2=6. | Disassembly; not whole-game consumer coverage. |
| EWRAM `[02003B58,02003B69)` | Separate glyph-string name field; initializer copies nine bytes for `トルネコ` including NUL. Conditional title-menu code can convert eight IDs and writes output+16. | Disassembly at `080590D0` and `08014C3A`; gameplay role/conditional four-character editor path needs native tracing. |
| Caller-supplied record offsets `[00002FE5,00002FF5)` and `[00000214,00000224)` | `08006C60` copies all 16 indexed-name bytes to both locations. `08007214` restores the former into `02003B46`. | Static record-transfer evidence only; base address, physical flash mapping and cold-load behavior are not yet established. |

Potential ID-table consumers also reference its pointer at ROM offsets `0000F584`,
`00014970`, `00014C64`, `00015634`, `00018474`, `0001FB08`, `000205E0`,
`000354BC`, `0003EFAC` and `0004202C`. This literal search is a research queue,
not proof that all references have been found or are safe to repoint together.

### English name-entry insertion ownership

The implementation uses owner `english-name-entry` in the shared `RomBuild`
ledger. Appended resources follow the font and its helper; their exact ranges,
hashes and expected original bytes are recorded by the cumulative build. No new
RAM or flash allocation is required. The accepted shared-editor maximum is
seven characters; the existing item editor retains its eight-character maximum.

- Repoint the ten ID-table literals listed above to an appended 256-entry table.
  Their consumers were inspected as indexed-name converters, including item
  displays and name-dependent comparisons. Retain IDs `00..B8`, except `01`'s
  displayed vacant-slot glyph becomes a compact underscore; append 69 ASCII
  IDs `B9..FD` for both cases, digits and seven spacing/punctuation characters.
  `FE`/`FF` remain special keyboard actions and are not character IDs.
- Repoint the two editor page-table bases at ROM `00015630`/`00018470`, action
  index arrays at `00015638`/`00018478`, grid index arrays at
  `0001563C`/`0001847C`, and input-map literal at `0001A238`. Append five pages:
  uppercase, lowercase, original symbols, hiragana and katakana. Change the
  page-cycle comparison at `0001A1CE` from 2 to 4. The original two-row rule for
  page 2 and kana action handlers remain applicable.
- Change shared-editor limits at `00014BE6`, `00014C2C` and `000205C4` to 7.
  The existing 20-byte conversion scratch holds at most 14 glyph bytes plus
  NUL; the separate saved glyph-string field's 16-byte transfer also holds it.
  For the conditional six-ID secret name, append the original six IDs plus a
  vacant marker and compare seven bytes at `00014C10`, with its literal at
  `00014C58` repointed. This preserves exact six-character matching. Clear all
  eight vacant slots at `00014C1E` before its second editor call.
- Change the shared name window x/width at `000154E0`/`000154E4` to 4/22 tiles
  (176 pixels); set VWF at `00015572` and the item editor's `000183BA`. Replace
  the fixed cursor calculation at `[00019F68,00019F72)` with a call to an
  appended helper that sums actual preceding glyph advances and window spacing,
  preserving r2 and callee-saved registers. Original cursor rendering remains.
- Repoint the shared `%s村` format pointer at `00140EF4` to an appended `%s`
  plus compact-English ` Village`. Original Japanese string bytes remain intact.
  Repoint `001416CC` (original `080603AC`, `名前: %s`) to compact `Name: `
  followed by the same `%s` operand for the conditional player-name editor.
- Hook `[000590D0,000590D8)` to an appended default initializer. It performs
  the original two bounded operations with appended source assets: a 16-byte
  indexed `Torneko` record and the 15-byte glyph-string `Torneko` including NUL.
  The initializer writes only the original destination fields; its original
  remaining instructions and literal pool are retained but bypassed.

The record routines use bounded string copies with zero fill (`0805D0D4`),
not a raw memcpy. Indexed names have no embedded zero before their eight slots,
so the existing 16-byte transfers retain seven English IDs plus the vacant
marker and fill the remaining bytes with zero. English glyph strings of seven
letters likewise fit those transfers including NUL. Physical flash and native
save/cold-load findings will be recorded with the acceptance results.

### Native gameplay route support for save validation

The first-floor layout varies with the opening's timing. Verification therefore
reads the actual map and sends ordinary directional/attack inputs to its stairs;
it does not inject coordinates, change collision flags, reveal the in-game map,
or modify the game's random state.

- CPU `08004B38` bounds x to `0..55`, y to `0..31` and returns
  `020229A8 + (x*32+y)*28`. The floor grid is column-major, 28 bytes per cell,
  EWRAM `[020229A8,0202EDA8)`. It reuses scene RAM; it is not an expansion buffer.
- Cell+`14` is a flags word. `0800A518`/`0800A490` use `4000` for ordinary
  traversable ground, with separate `2000`/`01000000` cases outside this route.
  A naturally reached first-floor stair at (49,4) has flag `20`; its native
  stairs menu confirms the interpretation. The route asserts one matching stair.
- EWRAM `[02001624,02001704)` holds 56 actor pointers used by `08026CA4`.
  Actor+`66`/`68` are signed tile x/y, +`84`/`86` HP/max HP. The observed player
  actor is `020014D0`, but route code follows the pointer rather than pinning it.
- The shared editor's frame keeps its format pointer at caller SP+`54`.
  `08019F3C` saves 28 bytes; the cursor helper saves 24 more. When its original
  LR is `080155FD`, the helper checks that format at its SP+`88` and adds the
  measured `Name: ` prefix only for the player-name format. Item-editor calls
  have another LR/frame and never enter that branch. Native cursor checks cover
  both forms and preserve LR, SP, r2 and callee-saved registers.

Disassembly: `build/name-entry/implementation/tiles.txt`, `collision.txt`,
`editor-functions.txt` in the parent research directory, and the generated
helper source in the cumulative build. These addresses support read-only route
validation; no map or actor patches are included.

### Native save records and name persistence

The acceptance route enters `Torneko`, walks to the first-floor stairs and
chooses the game's save-and-suspend option. It reaches `08015348` with the
existing record buffer at EWRAM `020096B4`. Observation at `08015354`, after
serialization and before encoding, verifies both name fields in both records.
No probe calls a save routine directly or alters its arguments on this route.

| Space / exclusive range or entry | Verified finding |
|---|---|
| Logical record `[00000214,00000224)` | Preview's 16-byte indexed-name field. |
| Logical record `[00000232,00000242)` | Preview's 16-byte player glyph-string field; seven English letters include NUL within this capacity. |
| Logical record `[00002FE5,00002FF5)` | Main indexed-name field, 16 bytes. |
| Logical record `[00002FF5,00003005)` | Main player glyph-string field, 16 bytes. |
| CPU `080076FC`, `08007778` | Encode/decode record bytes `[280,31B8)` by subtracting/adding repeating bytes `7E 23 7E 4D 7E 55`. The preview name fields precede the encoded region. Native decoded fields and independently decoded battery fields agree. |
| Battery slots `[00000000,00004000)`, `[00004000,00008000)`, `[00008000,0000C000)`, `[0000C000,00010000)` | Four rotating 16 KiB slots. `080043D8` selects the latest signature/counter; `08004480` writes and verifies four 4 KiB sectors for this save. The acceptance run observes the first two slots through save and resume. |
| Within each slot `[00003FDC,00003FE0)`, `[00003FE0,00004000)` | Counter and 32-byte identity signature checked by the native slot selector. Record offsets above are relative to the selected slot; main-field physical bytes are encoded. |
| CPU `08014FF2` | Native cold-load call to restore the main record. All four decoded name fields are checked before `08007214` restores game state. The route then resumes on floor two and moves through normal inputs. |

The native save writes whole sectors, including bytes beyond the semantic
record length. Duplicate strings in that sector tail are not additional name
fields or free space. Validation follows the native record offsets and encoding,
not a search for visible English bytes in the save.

The native battery clone equals the flushed disposable `.sav` exactly. A fresh
English emulator session reads that file and preserves both name fields through
resume and the next rotating save. A separately produced native Japanese save
also imports and resumes with its Japanese names intact. New English IDs require
the English ROM; reverse compatibility with the Japanese renderer is not claimed.

Evidence: `build/english/name-entry-validation/report.json`, captures/input
schedules underneath that directory, `build/name-entry/implementation/flash.txt`,
`save-menu.txt` and `save-codec.txt`, and
[english-name-entry-validation.json](english-name-entry-validation.json).

## Opening event text ownership (2026-09-13)

Disassembly and both normal Japanese opening branches establish the following
owners before insertion. Evidence is retained under
`build/opening-dialogue/research/`: `selector.txt`, `text-addresses.txt`,
`consumers.txt`, and `yes/trace.json` / `no/trace.json`.

| Space/range or consumer | Verified role and permitted change |
|---|---|
| Decoded bank zero `[0000,0010)` | Four words: group count 17, group-offset table 0040, entry-offset table 0084, string base 01EC. Loader fixes up the last three into RAM addresses. Preserve this header. |
| Decoded bank zero `[0010,0021)` | 17 one-byte group sizes, totalling 90 entries. Preserve counts and ordering. |
| Decoded bank zero `[0040,0084)` | 17 group-relative bases. Preserve these words. |
| Decoded bank zero `[0084,01EC)` | 90 four-byte entry offsets. Native event consumer `0804F938` and getter `080502A4` add string base + group offset + entry offset with 32-bit arithmetic. Only documented translated entries may change their offset words. |
| CPU `0804F938` / EWRAM `02010138` | Event selects group/index from bytes +1/+2 of its five-byte instruction. Byte +3 chooses ordinary dialogue or choice. Offset slot and resulting source verified for all 27 event calls in each opening branch. Script instructions remain unchanged. |
| ROM `[0014CD84,0014CD88)` | Bank-zero compressed resource pointer, originally `0843FAAC`. Owner `opening-dialogue` may repoint to an appended type-10 stream. Decoded output remains exactly 12,132 bytes; only owned entry-offset words differ. |
| EWRAM `[020241AC,02027110)` | Original decoded bank-zero allocation. No growth or new RAM allocation. English glyph strings live in appended ROM; an entry's new offset is `ROM_address - (020241AC + 01EC + group_offset)`. |
| ROM `[0014110C,00141110)` | Shared Yes/No resource pointer `0806309C`, consumed by `08015D32`. Owner `opening-dialogue` may replace this resource with compact English positioned to match the existing two cursor positions. |
| ROM `[00147238,0014723C)` | First-floor help string pointer `0806B0E8`. Consumer `0801B620`, table base literal `0801B668` = `08147234`, index 1 load at `0801B638`; native opening establishes the displayed source. Owner `opening-dialogue` may repoint this word. |
| CPU `080021B4` / `08015A50` | Story/help streams are read directly from their supplied pointer. Story windows are 28 tiles (224 pixels) by two text rows, fixed advance zero. Newline waits and clears after row two; extra newlines immediately after a clear are skipped. No whole-string copy is introduced. |
| CPU `08051664`, EWRAM byte `0201020E` | At-command callback: `@B@` invokes `0804D048(0)` then sets bit 3 and clears bit 4; `@C@` invokes `08049910(1)` then clears bit 3 and sets bit 4. Both natural branches observe flags 14→0C→14 (hex). Preserve command bytes, order and their textual positions. These are event side effects, not generic page-break commands. |
| CPU `08015E28`, EWRAM word `0201017C` | Left/Yes returns 1; Right/No returns 0. Native event saves the result at `0804F996`. Both outcomes converge on the same later scene; No reads additional source `event-bank-0.1190` instead of `1103`. |

English resources and the replacement stream share `RomBuild` allocation and
expected-source checks. All original Japanese strings, unselected table words,
scripts, other bank pointers and save structures remain owned by the base ROM.
Enumeration proves table structure; it does not prove natural reachability of
all 90 entries. New insertion/native acceptance remains to be recorded separately.

### First dungeon and resume labels

`build/first-dungeon/research/trace.json` records a native Japanese save resumed
on floor two, ordinary movement to its stairs and descent to floor three. The
same reader observes three initial-menu labels, two resume prompts, the stair
menu and both remaining first-dungeon tutorials. Owner `first-dungeon` may
repoint only these original four-byte fields to appended English resources:

| ROM pointer field (four bytes, end exclusive = start + 4) | Original source | Layout |
|---|---|---|
| `00141318` | `08061CF8`, Continue | 96-pixel initial-menu row |
| `0014131C` | `08061CEC`, High scores | 96-pixel initial-menu row |
| `00141320` | `08061CDC`, Erase Adventure Log | 96-pixel initial-menu row; display abbreviation `Erase log` |
| `001412F8` | `08061DB0`, loaded/suspend notice | 224 pixels, two rows with native paging |
| `001413B4` | `080617EC`, resume/abandon warning | 224 pixels, two rows with native paging |
| `0014723C` | `0806B080`, floor-two R/L tutorial | `0801B620`, help index 2 |
| `00147240` | `0806B03C`, floor-three A+B tutorial | `0801B620`, help index 3 |
| `000178C0` | `0806B570`, Descend/Stay/Save and suspend | 96 pixels, three rows, six-pixel left inset. Longest English label `Save & suspend` is 84 pixels, within the 90 available. |

These changes do not alter choice actions, save format, dungeon mechanics or
window sizes. The shared Yes/No resource keeps its existing `opening-dialogue`
owner. Native pointer-read observations and English acceptance are recorded with
this family's reports rather than inferred from pointer-shaped scan results.

### Playtest route observations

The first-dungeon actor pointer table contains 56 slots at EWRAM
`[02001624,02001704)`. Slot zero is the player; on the tested first-dungeon floors,
live enemy records have bit 31 at +8 set, positive HP at +84, and coordinates at
+66/+68. Read-only observations guide normal button inputs; no game RAM is
patched. Native A automatically faces adjacent enemies in these encounters.
Empty attacks advance turns and permit ordinary HP regeneration. The route now
finishes adjacent fights and recovers away from nearby enemies before continuing.
The previous movement-only route could walk away under flank/rear attacks.
Failure and normal-input combat evidence are under
`build/opening-dialogue/save-route-investigation` and `combat-probe`.

### Castle arrival and player-name substitution

The normal Japanese route in `build/castle-arrival/research/trace.json` clears
floor three and naturally reloads event bank zero before the King's first
conversation. Its source is decoded-bank range `[26C0,2914)`, group 10/index 0,
entry-offset word `[01AC,01B0)`. Owner `castle-arrival` may relocate this string
through that verified bank-zero slot; the event instruction is unchanged.

The source contains two byte-`7E` player-name substitutions. The original handler
in `08001DA8` calls `08002298` on EWRAM `02003B58` (the existing bounded player-name
record); it is read directly, without building a larger intermediate string.
The native width reader `08001C84` also measures this substitution. The name
editor's maximum is seven glyphs. Original indexed-name glyph advances are at
most 14 pixels, so a compiled `{player}` token reserves 98 pixels, covering both
English input and retained Japanese keyboard/save names. It emits the original
single byte `7E`; it is not a literal ASCII name or a new control hook.

### Town movement after the first audience

Town movement uses different records from dungeon movement. EWRAM words
`[0200FF0C,0200FF10)` and `[0200FF10,0200FF14)` are the observed town player X/Y
positions. Native function `0804B528` adjusts them from direction and step data;
the Down case adds its step at `0804B592` and stores Y at `0804B594`. It then
copies the coordinates into the active town actor's fields +38/+3C. In the
first audience fixture these copies are at `02010DF0`/`02010DF4`.

Normal left/right/up/down probes, RAM comparisons, write watchpoints and the
disassembly are retained in `build/castle-arrival/movement-research/`. The scene
camera follows the player, so screen position alone is not a movement metric.
These addresses are read-only playtest observations, not new RAM allocations.
The dungeon actor coordinates remain stale in this scene and must not be used
to assert that town controls resumed.

On the third tutorial floor, waiting with native A in a narrow passage while
enemies approach within five tiles allows them to queue for adjacent fights.
This ordinary-input route reached the castle without changing health or other
game state. It is a tested route for this dungeon, not a general combat solver.

### First castle NPC conversations

The six normal-button routes in `config/routes/castle-conversations.json` start
from a naturally reached audience-completion checkpoint. The Japanese native
reader and bank-zero table agree on the following sources. Owner
`castle-conversations` may relocate them through these four-byte entry slots,
with the same checked shared-bank reconstruction as the opening:

| Decoded bank-zero range (end exclusive) | Group/index | Slot range | Context |
|---|---|---|---|
| `[2914,2948)` | 10/1 | `[01B0,01B4)` | King's repeat request |
| `[2948,29BF)` | 11/0 | `[01B4,01B8)` | Minister, to the right of the throne |
| `[29BF,2A54)` | 12/0 | `[01B8,01BC)` | Chancellor, to the left |
| `[2A54,2AC8)` | 13/0 | `[01BC,01C0)` | Left guard's admiration for the Prince |
| `[2C86,2CBC)` | 14/0 | `[01D0,01D4)` | Right guard asks about the old man |
| `[2CBC,2D20)` | 14/1 | `[01D4,01D8)` | Right guard, Yes response |
| `[2D20,2D39)` | 14/2 | `[01D8,01DC)` | Right guard, No response |

`build/castle-conversations/research/trace.json` retains exact original bytes,
windows and input schedules. The right guard uses the existing shared Yes/No
resource; native choice returns are again 1/0. All seven new sources use ordinary
glyphs and newlines. No new command hook, RAM allocation or save field is needed.
Restoring the checked native scene between NPC routes is explicit in receipts;
this proves these interactions in this story state, not all later NPC dialogue.

### Destination menu and long home names

`build/destination-menu/research/trace.json` records the first castle exit menu,
native B cancellation (result 255) and Home selection (result 1). The latter
naturally loads event bank one and reads its first home dialogue at `[0400,0557)`.
That home dialogue is localized by the subsequent `home-return` owner below.

Disassembly at `build/arrival-research/castle-exit/inspect/menu.txt` and
`cursor.txt`, plus pointer-read observations, establish owner `destination-menu`:

| ROM range (end exclusive) | Expected original | Permitted change |
|---|---|---|
| `[0014D718,0014D71C)` | pointer `0806C524` | Repoint the travel question, source `[0006C524,0006C537)`. |
| `[0014BEA0,0014BEA4)` | pointer `0806C14C` | Repoint first destination label, source `[0006C14C,0006C154)`. Keep its native player substitution. Other destination table entries remain intact. |
| `[0004CB20,0004CB22)` | `0C 22`, `mov r2,12` | Question window width: seven tiles (56 pixels) for `Where to?` (51 pixels). |
| `[0004CB36,0004CB38)` | `0F 20`, `mov r0,15` | Destination window X: tile 10 (80 pixels). |
| `[0004CB3A,0004CB3C)` | `0C 22`, `mov r2,12` | Destination width: 19 tiles (152 pixels), retaining all six original rows. |

The home label is positioned at X=12 inside the destination window, preserving
cursor clearance, then emits `{player}'s home`. Its worst supported width is
12 + 7×14 + 42 = 152 pixels. The window ends at screen X=232, leaving room for
the border. Question and list retain their original Y=24; no RAM/save growth is
introduced. Native cursor call `0804CE0C` reads X/Y from the actual window
descriptor, so it follows the moved window rather than a separate literal.
Menu choice logic, unlock flags, destination IDs and return mapping are unchanged.

### First home return: bank one and native text styles

Owner `home-return` uses the same checked relative-offset insertion as bank zero.
ROM pointer `[0014CD88,0014CD8C)` must originally contain `E4 10 44 08`
(`084410E4`). Its type-10 resource occupies `[004410E4,0044453A)` and decodes
to exactly 29,157 bytes (SHA-256
`32b5b579e2920ba872d95840520db9154bedcfa460f2ebdc2f0e3a8e15097c19`).
The decoded header has 26 groups, group bases at `0040`, 214 entry words at
`00A8`, and strings at `0400`. Runtime storage remains the existing allocation
at `020241AC`; the decoded length, original strings, header layout and all
unselected entry words must remain unchanged. There is no new RAM/save storage.
The repacked resource and English streams use `RomBuild` appended allocations.

The first evening/morning and neighbouring NPC routes own only these entry words.
Source ranges and expected little-endian word values are checked against the
original bank and native reader evidence in `tools.trace_home_return` before
translation insertion. Table enumeration alone does not establish gameplay coverage.

| Decoded source (end exclusive) | Group/index | Slot range | Original word |
|---|---|---|---|
| `[0400,0557)` | 0/0 | `[00A8,00AC)` | `00000000` |
| `[0557,056E)` | 0/1 | `[00AC,00B0)` | `00000157` |
| `[056E,0721)` | 0/2 | `[00B0,00B4)` | `0000016E` |
| `[121E,1249)` | 0/22 | `[0100,0104)` | `00000E1E` |
| `[1249,1270)` | 1/0 | `[0104,0108)` | `00000000` |
| `[128A,12BE)` | 1/2 | `[010C,0110)` | `00000041` |
| `[12BE,130E)` | 1/3 | `[0110,0114)` | `00000075` |
| `[146E,149C)` | 1/6 | `[011C,0120)` | `00000225` |
| `[149C,151A)` | 1/7 | `[0120,0124)` | `00000253` |
| `[292E,2A64)` | 4/1 | `[01CC,01D0)` | `00000032` |
| `[3622,36D6)` | 7/0 | `[0224,0228)` | `00000000` |
| `[3790,3846)` | 7/2 | `[022C,0230)` | `0000016E` |
| `[3846,3878)` | 7/3 | `[0230,0234)` | `00000224` |
| `[388D,391F)` | 8/0 | `[0238,023C)` | `00000000` |
| `[4022,40C7)` | 11/1 | `[0264,0268)` | `00000058` |

Native text handler `08002094` saves foreground `020000C2` to `020000C3`,
then assigns `(operand & 7) + 8`. Book titles use bytes `03 06`, setting colour
14. Handler `080020AC` implements byte `05`, restoring the saved foreground.
The existing catalog token name `legacy-position` for code 3 is historical and
does not describe this observed meaning; retained lossless source tokens stay
stable. English markup `{color:6}` / `{/color}` preserves the original
control sequence. The item-sale message also uses operand 5 (colour 13);
only these two natively observed operands are insertion-ready.

Tessie's goodbye ends in code `874E`: CP932 decodes it as `⑮`, but the actual
native record `[001896C0,001896E0)` is a filled heart with a 13-pixel advance.
English `{heart}` emits that original code and reserves its actual width.
Its count/order must match the original source. The glyph is reused unchanged;
the ASCII compact-font extension does not replace this native symbol.
Disassembly is retained under `build/home-return/research-initial/color-*.txt`;
native palette and heart bitmap checks accompany the source trace.

The first return also executes the native sale routine `080515C8`. Its pointer
`[00051648,0005164C)` originally contains `F4 C8 14 08`, selecting Tessie's
sale explanation at `[0014C8F4,0014C958)`. Owner `home-return` may repoint this
verified prose source. The next pointer `[00051660,00051664)` must contain
`24 C4 06 08`, selecting template `[0006C424,0006C443)` for `08000FB8`.
The template's single `%-ld` formats the actual native sale amount; the result
is then read from existing RAM `0202F44C`. Original template bytes:
`0a144041407e82cd0305252d6c6405478ee882c993fc82ea82bd81490a0a00`.

The English sale template retains that exact directive, `@A@` callback, native
player substitution, amount colour `03 05` and restore `05`. It adds a row
break/centering command so even a seven-glyph Japanese name and a ten-digit
nonnegative signed-long amount fit. The template is 30 bytes including NUL,
one byte shorter than the original 31. With the same formatter and directive,
its output is one byte shorter for every argument; no larger RAM buffer is
claimed. Native decimal digits retain their original seven-pixel font. This
does not authorize other uses of the shared scratch buffer or change sale
values, inventory removal, currency storage or the zero-sale branch.

### Title/menu backgrounds and the first dungeon arrival card

`tools.trace_graphics_sources` records native copies, table selectors and
screenshots; `build/graphics-research/report.json` pins the reports. These are
source discoveries, **not graphics insertion ownership**.

Background loader `08004240` selects a 20-byte record at ROM `0013EC14 + 20*i`.
The record's first word points to a 512-byte stored palette followed by 38,400
uncompressed 8bpp tile bytes, representing 240×160 pixels. At `080042F0` it
calls halfword copier `08000F8C`, copying the tiles to `[06000000,06009600)`.
It synthesizes the 30×20 active tile map, with 32-column stride, at `0600B000`.
Native BG0 control is `1682`; the complete title screen reconstructed from
these tiles and the active native palette matches all 38,400 screen pixels.

| Observed scene | Record index/ROM record | Palette + tile resource (end exclusive) |
|---|---|---|
| Main title | 16 / `[0013ED54,0013ED68)` | `[0042F138,00438938)`; tiles begin `0042F338` |
| First menu background on this route | 19 / `[0013ED90,0013EDA4)` | `[00568B04,00572304)`; tiles begin `00568D04` |
| Name editor on this route | Same selected record 19 | Same byte-identical BG0 tiles/palette as the menu, under separate UI |
| First meadow walk-in background | 11 | `[0053A5CC,00543DCC)`; tiles begin `0053A7CC` |

The large title logo and small corner logo therefore belong to different
resources. The title image also contains the existing English `Push START!`.
Menu selector bytes `[0005FD98,0005FD9D)` are `0D 12 13 14 15`; the loader's
special request 13 chooses from indices 13, 18, 19, 20 and 21 and avoids the
previous choice. The candidate resources begin at `00555B04`, `0055F304`,
`00568B04`, `00572304`, and `0057BB04`. Each occupies `9800` hex bytes in the
known record format. Only record 19 is naturally observed as a menu background
in this capture; other candidates need their own native audits.

The stored palette is processed by `080035B0` into `02001064` before display.
It selects `08003434`/`080034F8` or `08003490`/`08003550` according to halfword
`03000A0E`. Native captures retain the resulting palette; direct stored values
are not a substitute for the game's calibration/fade behaviour. The menu record
loads 240 colours, leaving the final 16 for UI; the title record loads 256.

Title-audition follow-up (2026-09-30): fresh native cold boots of the Japanese
base and current English ROM `c6cf871b...f96c5` both select record 16 at frame
600. Full 240×160 pixels, 38,400 tile bytes, native palette and all 600 visible
BG0 map entries agree. The title resource is still ROM
`[0042F138,00438938)`; palette `[0042F138,0042F338)`, tiles
`[0042F338,00438938)`. Original START/A inputs select the same record 19 for
menu/name entry at frames 783/966. The five menu resources above are now decoded
as stored-palette previews; this does not expand native-selection coverage.
Evidence: `build/title-audition/reference/provenance.json` and each case's
`trace.json`; certainty: exact native observations for title and record 19,
static decoding for the other menu candidates. The English title proposal is
an offline audition only and creates no new ROM/RAM ownership or allocation.

Linked-logo follow-up (2026-09-30): all five menu candidates above are now
naturally selected by fresh cold boot followed by START at frames
604/607/600/602/601 for records 13/18/19/20/21 respectively (3 held frames plus
180 released frames). A with the same hold/wait then enters the name editor.
Evidence: `build/title-audition/backgrounds/reference.json` and five
`backgrounds/reference/<index>/trace.json` files. Exact original resource bytes,
38,400 native tile bytes and 600 visible BG0 map entries match each case;
the first 240 native palette entries persist into name entry. Every background
pixel index is below 240. No selector, ROM, RAM or register edits are used.
Certainty: observed native loads for all five listed menu/name variants, not
complete later-game logo coverage. The proposed 76×36 rectangle at (164,124)
for record 13, or (164,0) for the other four, is clear of the start menu.
The name editor naturally overlays parts of the original logo; the report
records that overlap. The audition composites modify no cartridge resources
and grant no new source ownership or free-space assumptions.

The first dungeon invokes arrival controller `08005C6C`, with dungeon ID 11 at
`02003B6C` and floor 1 at `02005674`. Compositor `08005B6C` formats floor digits
and chooses a rectangle from `0013EE58 + 8*dungeon_id`. Rectangle copier
`08005AC8` copies each tile row from the separate **4bpp** atlas based at
`0054E784`, with 28 tiles/224 pixels per row, into VRAM starting at `0600C000`.
Its tile map uses `0600B800` and palette bank 15; the card enables BG3 alone
(`DISPCNT=0800`) in the captured frame.

First-dungeon descriptor `[0013EEB0,0013EEB8)` is four little-endian signed
halfwords `(0,18,28,3)`: source X/Y and width/height in tiles. Its three native
copies are `[00552684,00552A04)`, `[00552A04,00552D84)`, and
`[00552D84,00553104)`, each `380` hex bytes. They form the 224×24 Japanese
label **ちょっと不思議の草原**. `1F` is composed separately from atlas rectangles.
The inspected atlas `[0054E784,00555B04)` is 224×264 pixels and includes other
dungeon labels and floor glyphs. Only the first label's natural selection is
claimed; the remaining descriptors and special floor cases need their own audit.

`build/arrival-research/first-dungeon/report.json` retains 600 consecutive frames
from the normal departure through the meadow walk-in, arrival card and first
tutorial; all 600 match a second native replay. The card artwork does not use
the story reader or compact English font. No title/card/atlas bytes were changed.

### Home books, shared town text and banker request (2026-09-19)

Native evidence: `build/home-books/native/trace.json` (nine ordinary-input routes),
`build/home-books/common-source/report.json` (natural load, full decode and all
300 pointer fixups), and the disassemblies in `build/home-books/research/`.
These observations establish ownership for the `home-books` batch below. Other
shared-town entries, the repaired storehouse and populated records remain separate.

| Address space / exclusive range | Meaning and insertion constraint |
|---|---|
| ROM `[00438938,0043A420)` | Shared town LZ77 resource; 16,695 decoded bytes, SHA-256 `203e93102709632d06402027ba3903ce84103b19c522c95e6c074e91400f4eff`. |
| ROM `[0004D7A8,0004D7AC)` | Owned loader pointer, original bytes `38894308`. Only this verified literal selects the shared town resource. |
| EWRAM `[020141AC,020182E3)` | Existing decoded allocation; no growth. Native call `0804D72E`, raw return `0804D732`, pointer-fixup completion `0804D746`. Guards and callee registers/SP checked. |
| Decoded shared-town `[0000,04B0)` | 300 pointer words, 204 unique source starts. Stored values use link base `801AC000`. The loader adds `81E681AC` modulo 2^32. English strings in appended ROM can use `English_CPU_address - 81E681AC` modulo 2^32 in owned words. Preserve every other decoded byte and the original decoded length. |
| Decoded shared-town slot `[00EC,00F0)` | Index 59: empty inventory when viewing; source `[2A76,2A95)`. |
| Decoded shared-town slot `[0314,0318)` | Index 197: four-row blue-book menu while the storehouse is broken; source `[3DEC,3E34)`. Consumer `0801F30C` through menu `08015E68`; 120 px wide, four rows. Keep action order, four rows and cursor inset. |
| Decoded shared-town slot `[02FC,0300)` | Index 191: empty inventory when selling; source `[4090,40AF)`. Separate physical source, same Japanese sentence. |
| Decoded shared-town slot `[0308,030C)` | Index 194: save cancellation; source `[40F4,410D)`. |
| ROM `[0001FB4C,0001FB50)` | Overwrite-template pointer, original `04831408`, source starts `00148304`. `0801FB20` allocates 128 stack bytes; formatter call `0801FB38`, return `0801FB3C`. Exactly one `%s` copies the stored village name. Text bytes, pixels and name capacity require separate checks. |
| ROM `[001412D4,001412D8)` | Save-success pointer, original `FC1F0608`, source starts `00061FFC`. Read alone for continue, or passed to the quit formatter. |
| ROM `[0014130C,00141310)` | Quit farewell pointer, original `381D0608`, source starts `00061D38`. |
| ROM `[0006B4F0,0006B4F7)` | Unchanged native quit format `%s\r\x14%s\0`. Call `080153EE`, return `080153F2`. Function `08015374` reserves 132 bytes; output starts SP+4 with capacity 128. The combined translated success/farewell must fit this buffer and its two display rows. |
| ROM `[0014BE9C,0014BEA0)`, `[0014BEA4,0014BEA8)` | Travel destinations: King's castle (`0806C154`) and square (`0806C144`). Use the already measured destination window and 12 px label inset. Preserve ordering/selection. |

The red book uses the ordinary two-row story reader. Native control `14` hex
centres the following line (`08002124`, width reader `08001C84`); three occurrences
centre its title, author and ending. Preserve those controls and keep each
centred editorial paragraph on one line. The book is opened directly; source
`event-bank-1.0724` was not observed on this route and is not owned for insertion.

Bank-one insertion adds only the following observed sources, using the existing
relative-slot relocation and shared `RomBuild` allocator. Exact original payloads,
source hashes and tokens are retained in `translations/master.json`; expected
slot words come from the pinned original decoded bank and are checked at build.

| Decoded bank-one source range | Group/index | Owned slot range |
|---|---|---|
| `[073A,0A5B)` | 0/5 | `[00BC,00C0)` |
| `[28FC,292E)` | 4/0 | `[01C8,01CC)` |
| `[449E,45FC)` | 12/0 | `[0294,0298)` |
| `[45FC,4660)` | 12/1 | `[0298,029C)` |
| `[4660,469C)` | 12/2 | `[029C,02A0)` |
| `[469C,4714)` | 12/3 | `[02A0,02A4)` |
| `[48BD,4982)` | 12/7 | `[02B0,02B4)` |

The banker No branch returns to town; Yes introduces the old man and then
the banker's alarm. A second conversation supplies the native **6F** clue.
Normal inputs then enter mansion floor one. This establishes entrance/choice
behavior, not completion of the mansion or recovery of the safe. The green-book
parent, empty scroll-name list and records menu are separately captured; their
contents and wider UI are not yet owned for insertion.


## Mansion safe recovery and bank opening (2026-09-19)

Evidence: `build/mansion/native/trace.json`, reproduced by `tools.trace_mansion`
from the fresh Japanese home-book route and `config/routes/mansion-japanese.json`.
The uninterrupted ordinary-input prefix reaches the special room on mansion 6F;
the imp is defeated, the safe recovered, and the player returns home. Four
checkpoint replays cover both family choices, plus refusal/reconsideration of
the bank request. The bank service menu is cancelled before any transaction.
No actor, map, RNG or quest-state memory is edited by this route.

The `mansion-quest` insertion owner uses existing readers, font, bank allocations
and relative-pointer mechanisms. Exact original bytes and SHA-256 identities
are retained in the native trace/catalog and checked before patching. No RAM or
save storage is added. The four direct fields below are native resource pointer
words; word searches only corroborate their uniqueness, while reader traces
establish the actual source and consumer.

| ROM source range | Owned pointer field range | Meaning |
|---|---|---|
| `[0006AFE0,0006B039)` | `[00147244,00147248)` | Anonymous 6F voice, help table index 4. |
| `[00061A08,00061AE9)` | `[00141378,0014137C)` | Imp's challenge before ordinary combat. |
| `[00061978,00061998)` | `[00141384,00141388)` | Safe acquisition; two `14` centring commands and `7E` player substitution. |
| `[0006155C,00061577)` | `[00141444,00141448)` | Completed-quest result; single line in 224 px window, initial x=12. |

Centring (`08002124` to `08002138`) measures each line independently. The compiler
preserves explicit adjacent centred lines on one two-row page, retaining each
control in source order. Name width reserves the existing seven widest Japanese
glyphs (98 px), separately from encoded byte capacity. The result row is limited
to 212 px with its native inset. These use the shared reader at `080021B4`.

| Decoded bank-one source range | Group/index | Owned slot range |
|---|---|---|
| `[0D4E,0D6B)` | 0/13 | `[00DC,00E0)` |
| `[0D6B,0D86)` | 0/14 | `[00E0,00E4)` |
| `[172E,1745)` | 1/12 | `[0134,0138)` |
| `[1745,1785)` | 1/13 | `[0138,013C)` |
| `[1785,17C1)` | 1/14 | `[013C,0140)` |
| `[17C1,1803)` | 1/15 | `[0140,0144)` |
| `[1803,18C2)` | 1/16 | `[0144,0148)` |
| `[1BDF,1CA5)` | 2/3 | `[0168,016C)` |
| `[1CA5,1D53)` | 2/4 | `[016C,0170)` |
| `[1D53,1DA3)` | 2/5 | `[0170,0174)` |
| `[1DA3,1E74)` | 2/6 | `[0174,0178)` |
| `[1E74,1E97)` | 2/7 | `[0178,017C)` |
| `[1E97,202D)` | 2/8 | `[017C,0180)` |
| `[202D,2081)` | 2/9 | `[0180,0184)` |
| `[2081,2157)` | 2/10 | `[0184,0188)` |
| `[2414,24FA)` | 3/3 | `[01A0,01A4)` |
| `[24FA,252E)` | 3/4 | `[01A4,01A8)` |
| `[252E,255E)` | 3/5 | `[01A8,01AC)` |
| `[47B9,48BD)` | 12/6 | `[02AC,02B0)` |

| Decoded shared-town source range | Index | Owned slot range |
|---|---|---|
| `[04B0,04EC)` | 80 | `[0140,0144)` |
| `[0527,0567)` | 82 | `[0148,014C)` |

Only the bank greeting and farewell are added from shared-town storage. The
transaction menu is assembled in RAM and remains a separate producer/formatting
audit; observing it does not establish insertion ownership.

Research-only navigation reads the dungeon ID at EWRAM `[02003B6C,02003B70)`,
floor at `[02005674,02005676)`, and the existing 56-by-32, 28-byte-cell map at
`020229A8`. Ground is flag `4000`; the special-room marker uses `10000000`, with
trigger `00800000`, and marker byte `85` at cell+0F. Native setup around
`08028F70` reserves actor slot one and sets `[020081CC,020081CD)` when that marker
is present. The special room is separate from ordinary 6F stairs. These are
observed engine fields, not newly available memory or patch allocations.
Dungeon command-menu B must be held long enough for its input timer (8 frames
in the retained recipe); standard 3-frame menu taps are insufficient there.

## Torneko 3 font adaptation (2026-09-19)

User-selected replacement: original Japanese Torneko 3 Latin font 0, source ROM
SHA-256 `35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02`.
No fan-patch asset is used. `tools.import_torneko3_font` reads the original
descriptor table at T3 ROM `[00C93B4C,00C97A58)` (1,345 twelve-byte records),
and the ASCII mapping at `[00CA26B4,00CA2772)`. Each selected descriptor owns a
72-byte 4bpp source bitmap; individual offsets and exact bytes are frozen in
`assets/fonts/torneko3-english.json`. The concatenated 95 descriptor/bitmap pairs
have SHA-256 `9c4a1302da0e4075cb91cc2fbe6d23843795367638326ee60b569138f8d9b5f6`.

All selected ink is monochrome and inside its 3–7 pixel advance. Conversion
adds two blank rows above the twelve source rows and repacks the same ink into
T2's fourteen-row 1bpp records. Horizontal advances and pixels are unchanged.
The active font replaces only the existing appended 3,040-byte English font
allocation at T2 ROM `[00800000,00800BE0)`; the lookup hook, F020–F07E codes,
original Japanese glyphs and save layout remain unchanged. Source shape/advance
verification rejects edits to the imported glyphs. The previous compact font
asset is retained intact for auditioning. Builds use the frozen local asset and
do not require the Torneko 3 checkout or ROM.

## Early menu geometry audit (2026-09-19)

`tools.audit_menu_layouts` observes eight original-ROM input routes from the
native mansion/home checkpoints. Evidence is retained in
`build/menu-layout-audit/native/report.json`. No new insertion ownership is
claimed by this audit. CPU hooks are window creation `08001798`, caller wrapper
`08002298`, text reader `080021B4`, reader return `08002284` and glyph draw
`08001BC4`. Window descriptors occupy 24-byte records starting at EWRAM
`02000000`; the observed `02000000`, `02000018` and `02000030` records are reused
across menus, not dedicated permanent allocations.

| Observed window | Creation r0–r3 | Return address | Text region |
|---|---|---|---|
| Dungeon commands | 1, 3, 5, 3 | `08019D79` | x=6 to 40: 34 px |
| Inventory parent | 1, 3, 21, 8 | `08018B5B` | x=6 to 168: 162 px, all fields combined |
| Inventory counter | 24, 3, 5, 1 | `08018BB9` | Separate from the item-name row |
| Inventory actions | 24, 3, 5, 4 | `08019481` | x=4 to 40: 36 px |
| Settings | 1, 3, 24, 6 | `0801A7CD` | x=6 to toggle x=71: 65 px; other rows 186 px |
| Bank transactions | 1, 3, 22, 3 | `08015EA5` | x=12 to colon x=64: 52 px for verb |

Dropped-arrow ground actions also have 36 usable pixels. Settings control
`04 4C` resolves to x=71 (`floor(15*76/16)`); the bank colon is independently
positioned at x=64. Neither bank amount capacity nor full item-name capacity
is established by these label widths. Native decimal formatting still selects
original Torneko 2 digit glyphs, independently of appended English font codes.

Descriptor +0C is a VRAM **tilemap pointer**, not a contiguous glyph bitmap.
Native BG3 control at IO `[0400000E,04000010)` is `170C`: map base `0600B800`,
character base `0600C000`, 4bpp. Parent preservation checks read the descriptor
`[02000000,02000018)`, width tile columns by twice the text-row count with a
64-byte tilemap row stride, then each referenced tile's 32 bytes. Two cancel/
reopen cycles for each of three inventory action variants preserve those exact
descriptor, map and tile-pixel hashes. OAM cursor blinking is outside this
comparison. These observations cover existing geometry only; any future window
change requires its own clipping, shading, selection and parent-panel checks.

## Restored T2 font and early menu insertion (2026-09-19)

The T2 compact asset is again the build default with approved shorter labels and original window geometry.
Its existing `[00800000,00800BE0)` allocation and lookup hook are unchanged.
The T3 asset/import proof above is retained as historical comparison evidence.
Current ownership is recorded by `tools.menu_text`, the shared allocator and
`translations/menus-review.json`. The current receipt is
`docs/english-menu-validation.json`; native scope is in `docs/MENU_LAYOUTS.md`.

Owner `early-menus` copies the 44-pointer action table ROM
`[00141904,001419B4)` to an appended allocation, changes nine selected pointers
there, and changes **only** the literal at `[00019434,00019438)` from `08141904`
to the copied table. Literals `[00019680,00019684)`, `[0001E560,0001E564)` and
`[0001E62C,0001E630)` retain the original table. Original label bytes and original
table slots are not overwritten. The per-resource source ranges/bytes/hashes
and reviewed English are frozen in the menu review JSON; appended allocation
addresses and hashes are in `build/english/build.json`.

The action producer is CPU `08019184`, returning via `080194AA`. It constructs
up to seven rows from existing action IDs at EWRAM `[0200CDD0,0200CDDE)` and masks
bit 7 for the label index; bit 7 retains disabled colouring and behavior. It
continues to use the original selection IDs/order. Selected item index/pointers
are existing fields at `0200CDB0` / `0200CC9C`. No new globals are allocated.

| ROM range (exclusive end) | Original → replacement | Owned purpose |
|---|---|---|
| `[00019474,00019476)` | `18 20` retained | Original action X: 24 tiles; resize patch removed |
| `[00019478,0001947A)` | `05 22` retained | Original action width: 5 tiles; resize patch removed |
| `[00019D72,00019D74)` | `05 22` retained | Original main width: 5 tiles; resize patch removed |
| `[0001918E,00019190)` | `A0 B0` → `D0 B0` | Action stack reservation: 0x80 → 0x140 |
| `[0001949C,0001949E)` | `20 B0` → `50 B0` | Matching action stack release |
| `[00019408,0001940A)`, `[00019442,00019444)` | `10 A8` → `40 A8` | Action temporary SP+0x40 → SP+0x100 |
| `[0001944A,0001944C)` | `10 A9` → `40 A9` | Matching concatenation temporary |
| `[00019AA2,00019AA4)` | `D0 B0` → `E0 B0` | Main stack reservation: 0x140 → 0x180 |
| `[00019E28,00019E2A)` | `50 B0` → `60 B0` | Matching main stack release |
| `[00019D08,00019D0A)`, `[00019D28,00019D2A)`, `[00019D38,00019D3A)` | `4A A8` → `54 A8` | Main temporary SP+0x128 → SP+0x150 |
| `[00019D44,00019D46)` | `4A A9` → `54 A9` | Matching main concatenation source |

The main producer is CPU `08019A98`, returning via `08019E36`. Its stat buffers
below SP+0x110 remain in place. The command stream owns stack-relative
`[SP+110,SP+150)` (64 bytes); the temporary owns `[SP+150,SP+180)` (48 bytes).
The action stream owns `[SP,SP+100)` (256 bytes), temporary `[SP+100,SP+140)`
(64 bytes). These lifetimes are stack reservations, not free persistent RAM.
Preserved registers/SP and caller-side guards are checked on native returns.

Seven main-format literals at ROM `00019CAC`, `00019CBC`, `00019D10`,
`00019D18`, `00019D34`, `00019D94`, `00019D98` (each four bytes) are checked and
repointed to appended English formats. `%c` retains the original colour argument;
row breaks and conditional mode/ground choices remain native. Source pointers
and exact template bytes are in the review JSON. Longest four-row stream: 58
bytes. Action bound: 113 bytes during concatenation, including disabled styles.

The original inventory producer at CPU `08018AF8` has a 64-byte row output
starting at SP+8 in its 0x48-byte local frame. It calls `0800EF30` with price
alignment 0x84 (132), not a general item-name width. This formatter has its own
0x14C stack frame; markers, colour, compact spacing for longer strings, quantity,
enhancement and optional prices contribute to the complete row. Item records
start at EWRAM `0200DF28` with 120-byte stride. Native inventory pages expose
20 carried slots as 8/8/4 rows; index 24 selects the ground item in this consumer.
Other slots are not granted insertion ownership by this observation.

The 168 px inventory parent is retained, with 162 usable pixels after its
6 px inset. Actions return to x=192, width 40; main commands return to width
40 at x=8. The four-pixel outer borders leave 8 px between adjacent panels.
The previous wider layout covered the parent frame and was rejected at visual
review. Current native descriptor checks enforce the separate borders; modal
close/reopen checks independently verify exact parent descriptor/map/tile-pixel
restoration, including the first opening. Existing amount/counter and selection
logic are unchanged.

Original bank owner CPU `0801DFAC` reserves 0x190 stack bytes; the formatted
string starts at SP+4 and stops before the saved field at SP+0x184, providing
384 bytes. Menu format return `0801DFF2` and consumer `08015E68` were observed.
Bank cap literal ROM `[0001E0C0,0001E0C4)` is `05F5E0FF` (99,999,999). The amount
editor at `08016154` uses the `%08d` template at ROM `0006B534`; its native
window is 14 tiles (112 px), eight original digit cells plus G. Natural and
controlled 0/1/99,999,999 display/cancel cases pass without a transaction or save
write. No bank insertion ownership is added in this batch.

## Dungeon UI and core bank services (in progress)

`tools/service_ui.py` copies original ROM `[00140D68,001417A0)` for six owned
consumers: literals `[00019B2C,00019B30)`, `[00019BEC,00019BF0)`,
`[00019C94,00019C98)` (status producer), `[0001A9F0,0001A9F4)` (controls),
`[0001AA74,0001AA78)` (give-up prompt), `[0001AAEC,0001AAF0)` (sleep prompt).
Only reviewed slots inside the copy change; other original table consumers keep
their pointers. This copies existing referenced data, not free-space ownership.
The six-option table `[00148080,00148098)` and four toggle pointers
`[00148064,00148074)` are likewise copied. Their consumer literals are
`0001A650`, `0001A698`, `0001A6C0`, `0001A6F4` (four bytes each; the last points
8 bytes into the toggle copy). All original pointers are checked before patching.
Original window geometry is retained. The option output at EWRAM `0200CD60`
is constrained to the 36-byte extent already exercised by the original map row;
no unverified adjacent bytes are claimed. Status rows keep their original
64-byte stack regions and column controls. Sources, payloads and review are in
`translations/dungeon-ui-review.json`; caller evidence is under `build/services`.

Nine further action IDs (10,12,13,14,15,17,32,33,42) were observed in the native
controlled item matrix and are localized only through the existing copied action
table. All remain within 36 px; no action IDs or dispatch behavior change.

Core bank service slots 81,83,84,85,86,88,94,95,96,97,98 in the 300-pointer
shared-town resource are owned by `bank-services`, alongside the existing six
town dialogue slots. One combined decoded resource/patch remains authoritative;
its 16,695-byte allocation and relocation mechanism do not grow. Original
source bytes remain unchanged; only these checked pointer slots redirect to
appended strings. `translations/bank-review.json` retains source bytes/hashes,
Japanese and reviewed English. CPU `0801DFAC` owns the 384-byte formatting region
previously audited above; numeric substitutions keep eight-digit reserves.
Bank gift/reward slots are not translated by this core transaction batch.

### Compact numeric aliases and English item spacing

See [TYPOGRAPHY.md](TYPOGRAPHY.md). The cumulative build opts into an appended
38-entry code/pointer table plus terminator at ROM `00800C60`, following the
existing 128-byte font hook. It owns derived numeric records immediately after
that table. Each record is independently packed from the selected compact font;
original records remain intact. Only the already-owned `00001A04..00001A0C`
lookup jump is used. Aliases cover 824F..8258, 8740..8749, 8755..8764, 8196, 8266;
all other codes preserve fallback lookup. The native bank's fixed 12-pixel cell
advance is preserved independently of the six-pixel numeric bitmap.

ROM `[0000F012,0000F01C)` is the item row's mov/strlen/cmp/bls sequence,
expected bytes `40464df0c4ff142809d9`. A ten-byte Thumb trampoline replaces that
sequence with an appended stream scan. It rejoins `0800F01C` for long Japanese
rows and `0800F030` for short or English-containing rows. It uses caller-saved
r0–r3 only and does not change SP, r4–r11, or any RAM. Every allocation and this
patch are recorded by RomBuild. Output capacities and original geometry remain
unchanged. Native source/disassembly: `build/services/item-row-formatter.txt`.

### First English item cohort ownership

The item definition table is `[00141B9C,00143054)`: 221 records of 24 bytes.
`00143054` is a blank-name pointer followed by a differently structured disguise
table at `00143058`, not more definitions. Only the copied definition table's
eight reviewed name pointers change. Name formatter `0800F244` receives the copy
through literal sites F29C, F328, F368, F3C4, F3F4, F414, F438, F470, F490, F4E4,
F580 and F5DC; all other consumers retain the original table.

The 222-pointer specific Info table begins at `00143F50` (last entry is an
invisible-item fallback), and the 14-pointer category table begins at `00143F18`.
Copied tables change seven specific entries and categories 3/6. Consumers are
17E6C/17EF0 and 17E68 respectively. The arrow formatter's 16-byte pointer table
`00140D68..00140D78` is independently copied; its +12 pointer originally targets
`080648C0`. Only consumer F4E0 receives this copy, replacing the Japanese counter
with a compact ` x ` separator. Numeric generation and colors remain native.
All original tables and text stay intact; source records and the exact consumer
lists are checked before patching. English item names fit an 80px base reserve
and 29-byte payload limit; outer formatted rows are checked against 64 bytes
and the full 162px region. Descriptions fit 216px lines and 256-byte output.

Controlled item tests use 120-byte inventory records at `0200DF28`, the native
byte-ID mapping at `020013D0`, per-type identity flags at `02003BAC + id*20`, and
actual identified flags C8000000. Earlier probes incorrectly set the inscription
bit 00400000. This correction supersedes the earlier 224-ID/289-attempt audit;
286 cases now cover the bounded 221-record table with no excluded IDs. These
are disposable RAM probes, not allocated localization storage or natural item
acquisition. Untranslated disguises and later modes remain outside sign-off.

### Repaired-storage menu and messages

Shared-town table slot indexes 178, 183, 184, 187 and 192 are now owned by
`storage-services`. Slots 183/184 alias the same Japanese acknowledgement and
share one English resource; four resources are allocated in total. Their exact
source bytes/hashes are retained in `translations/storage-review.json`. The
existing decoded town bank stays 16695 bytes with 300 linked pointers; only
these additional pointer words change before the same checked recompression.
The original decoded strings and every other byte remain intact.

The repaired blue book reads a direct ROM stream in a 224px, four-row window.
Its original column starts are x12 and x124, providing 100px per column. Native
ordinary-input checks cover populated deposits/withdrawal, R/START marking,
cancellation and a saved deposit/cold reload. The route's 20-slot warehouse and
carried bread/wand arise from normal play; no new RAM/save storage is allocated.
See `config/routes/storage-japanese.json` and `tools.trace_storage` for the
reproducible prerequisite quest and native save provenance.

## Autonomous text continuation: storage and holy flame

The shared town slots 181/182/186/188/189/190 now have explicitly reviewed
storage pot/capacity/sale resources. Slot 191 remains owned by the existing
home-books empty-inventory resource; the shared allocator correctly rejects a
second replacement of that slot. No storage record or capacity patch is made.

Native functions `0801F3E0` (deposit), `0801F83C` (stored sales), and `0801F944`
(carried sales) establish 256-byte formatted message buffers. Deposit's message
buffer is `[SP+8,SP+108)` and item-name scratch is `[SP+108,SP+148)`; sale buffers
are `[SP,SP+100)`. Formatter returns are `0801F438`, `0801F4F4`, `0801F588`,
`0801F8B2`, and `0801FA10`. Checked probes use the existing native paths,
including both pot-break choices and sale yes/no, and preserve stack guards.
Disassembly: `build/text-next/storage-deposit.txt` and
`build/text-next/storage-functions-correct.txt`.

The holy-flame acquisition pointer at ROM `[00141380,00141384)` originally holds
`08061998`. It is the adjacent quest-result entry to the earlier safe-acquisition
pointer; the normal Japanese castle quest reads that source at CPU `080021B4`.
The 28 additional bank-one sources are enumerated in `HOLY_FLAME_STARTS` in
`tools/build_dialogue.py`; only their verified relative table slots change.
Decoded bank size and all non-slot bytes remain unchanged. English native
progression acceptance is separate from source observation and translation.

The expanded item cohort retains the 80px base-name reserve and allows up to
31 encoded bytes (15 English glyphs plus terminator), supporting the full
`Lightning staff` and `Seed of agility` names without widening windows.
No RAM allocation is enlarged; each complete native row still has a 64-byte
bound and must pass name/price separation, quantity/suffix and parent checks.

## Dungeon actor names and core combat prototype

The type-10 stream at ROM `[00477700,0047CE7D)` decodes to 64,668 bytes
(SHA-256 `7e54ab711139015e4f66536ba7446140e5809579542207a714f82e6a0bcf79be`).
The loader uses literal ROM `0003A228` and writes EWRAM `020129A8`.
Its linked base is `8019C000`; the native scan adds `7FE64000`, accepts offsets
through `FFFF`, and relocates those words to EWRAM. It scans 64KiB; the decoded
payload and the trailing untouched bytes are checked against an original load.

The header at decoded `+30` selects 141 28-byte monster records at
`[989C,A808)`. Their first words are name pointers, followed by attributes which
must remain unchanged. Repacking the same-size stream with appended-ROM name
pointers bypasses the native linked-pointer relocation by its existing range
check. Owner `actor-names` may replace only those name words and the loader
literal. `tools.verify_monster_resource` compares both complete native loads,
all 141 names, unchanged attributes and the relocation-scan tail.

Raw ROM `[00144C38,00144E6C)` contains 141 parallel actor-name pointers, followed
by zero. **Index 0 and 131 differ:** raw `何者か`/`にせ神父`, dungeon
`トルネコ`/`幻覚`. Raw result/history consumers (`0001CBBC`, `00056FEC`) remain
outside this insertion until their individual layouts are accepted.

The native actor getter `08009ACC` handles player/unknown/disguise conditions
before reading the appropriate definition name. Its level format pointer is at
ROM `00009C08`, originally `0806B3D0` (`%s%d`). Appended `%s Lv%d` improves English
readability. Its existing EWRAM scratch is `[02008D08,02008D48)`; the next live
field starts at `02008D48`. Names plus even an int32 textual suffix fit 64 bytes.
Native signed16 level extremes and guard bytes are checked separately.

Core combat format pointers are owned individually at shared table `00140D68`
plus offsets `19C,1A0,1A4,1A8,1B4,1B8,1BC,1C0,1C4`. Original bytes, Japanese
source hashes and exact substitution sequences are pinned in `combat-review.json`.
The native attack/defeat format buffer starts at caller `SP+1C` and has 256 bytes
before name scratch at `SP+11C`. Incoming damage is stored at caller `SP+26C`.

The prototype queue adapter owns only `[0001588C,00015894)`. It reproduces the
original eight-byte prologue/branch for ordinary callers. Return addresses
`0800C9CF`/`0800C9F7` identify incoming prefix/damage queue calls: append damage to
the first owned buffer and suppress its duplicate second queue call. Original
formatting, damage animation and combat logic still execute. Other owned calls
`0800CEFB`, `0800D487`, `0800D4D1` permit removing authored soft breaks only if the
actual native glyph advances total at most 216 pixels. Unsupported byte forms
retain breaks. The helper uses 36 bytes of temporary stack plus native call
frames; no persistent RAM/save storage is added.

The combat reader is `080022D8`, not the story reader `080021B4`. Glyph entry
`08001BC4` precedes its own scroll check at `08001BDA..08001BEC`; a row coordinate
of 2 at entry is not itself clipping. Validate final coordinates and pixels at
`08001C14`, after native scrolling. This distinction matters when a one-line
attack is followed by a two-line defeat/EXP message.
# Bank reward name lookup and player-name reserve (2026-09-19 continuation)

ROM literal `[0x1E380,0x1E384)` originally holds `0x08141B9C`, the item
definition table. Function `0x0801DFAC` uses it only for raw gift-name lookup at
`0x0801E2FA..0x0801E308`; point it to the checked copied item definitions so gifts
use the same reviewed names. Gift IDs, bonus values and counts remain in their
original tables: thresholds `[0x148284,0x1482AC)`, counts beginning `0x1482B0`,
three item-ID slots per tier beginning `0x1482BB`, and bonuses at `0x1482DC`.
These tables are evidence, not free space. Exact consumer evidence is in
`build/text-next/bank-rewards.txt`.

The bank function's text buffer is `[SP+4,SP+0x184)`, 384 bytes. Its gift path
concatenates up to three formatted slot-91 strings into this buffer. A gift
uses a raw definition name, not the decorated inventory row. Preserve the native
player command and one `%s`; bound the complete concatenation, including all
terminators/page separators. Native gift counter is byte `0x02002C16`; balance
is word `0x02002C1C`. Capacity probes modify disposable RAM only.

The player-name reserve is **98px**, seven original Japanese glyphs at 14px,
as already established by `dialogue_layout.PLAYER_WIDTH` and the name-editor
checks. An item-description compiler incorrectly duplicated this as 84px; the
widest Japanese name exposed that error in Surefoot staff's Info text. Item and
bank compilers now import the shared reserve. The shorter wrap passes all three
native name cases; no name-entry restriction or font compression was added.

## Unidentified item appearances and assignment

Original ROM `[00143058,00143EE0)` contains 155 records of 24 bytes: 154
appearance names, followed by the explicit End Mark record. Their names are
independent of the 221 identified item definitions. Category counts are 30 staves,
29 rings, 37 scrolls, 15 pots, 34 herbs and nine breads. The adjacent range
`[00143EE0,00143F18)` contains fourteen category-label pointers used with custom
item names. `tools.extract_item_aliases` pins their source bytes and identities;
these sources are now included in the inventory, without claiming insertion.

Static Ghidra evidence: `build/text-next/alias-assignment.txt`, native Thumb
function `08009E68`. Its literal at ROM `00009FD8` points to `08143058`.
The assignment loop checks a **signed halfword at record +8**, stopping before
record 154 where it is one; all preceding records have zero. Thus the End Mark
name is excluded from this assignment loop. The code shuffles appearance IDs
within categories and stores them at +4 in existing 20-byte per-definition
records starting at EWRAM `02003BAC`. Category 0 has 38 definitions but only 37
appearance names; do not assume the extra definition can use an appearance or
index the marker. The prefilled unassigned value is 999. Native reachability of
special definitions still needs investigation.

The ordinary unidentified name formatter has original table-pointer literals
at ROM `0000F628`, `0000F64C`, and `0000F684`. No alias pointers or assignment
logic have been patched yet. Future display-only relocation must preserve all
non-name fields and leave assignment semantics intact.

The inscription path also needs separate work. At `0800F310` it strips six
**bytes** from an identified scroll name, corresponding to the Japanese suffix;
that is not a valid English suffix operation. Its special ID 153 path uses the
spell table, and custom-name formatting uses the category labels above. Passing
ordinary identified-item tests does not establish safe inscription or rename
support.

## Conditional item Info and invisible scroll

`build/text-next/item-info-description.txt` disassembles the native Info selector
at `08017D88`. Ogre shield (ID 38) substitutes description index 1 (no specific
text) when item word bit `0x20` is clear; the original definition's +4 word is
`0x20`. Tests now separately exercise the controlled bit-present state instead
of assuming every synthetic item record must expose the special description.

Hocus Pocus scroll (ID 135) calls visibility function `0801211C`; if false, Info
uses description index 221 (original Japanese: an invisible item). The copied
222-pointer description table now includes a reviewed English replacement for
that owned slot. In the name formatter, `0800F3A8` calls the same predicate;
ROM pointer literal `0000F3D4` -> `08143054` -> `08065628` selects **seven blank
Japanese space glyphs**. This is intentional invisibility, not untranslated text
or truncation. Preserve it. The separate visible test sets only the supported
visibility bit `0x100000` in the disposable player's actor word +8. Static
predicate evidence is `build/text-next/item-visibility.txt`; it also checks
Shadow ring (ID 107), existing dungeon flags and a dungeon-index threshold.

## Shared system/combat text inventory

`tools.extract_shared_text` enumerates the 654 original text pointers in ROM
`[00140D68,001417A0)`, the same span already copied for isolated dungeon UI
consumers. Every source is decoded with a byte-exact round trip. The next word
is zero and subsequent data is numeric. Sources include combat, status effects,
item actions, naming screens, results, menus, fragments and format strings;
table adjacency does not imply a common width or buffer. `build/shared-text`
records pointers and sources, and `tools.text_inventory` deduplicates overlaps
with existing item, menu/UI and native-master reviews. New insertion still
requires individual consumer and substitution audits.

### Additional miss formatter and player-initial investigations

The attack resolver at CPU `0800BCBC` formats shared table entry `+208` into
its existing stack message region `[SP+1C, SP+11C)` (256 bytes). The two
formatter returns are `0800C049` and `0800C5B7`; their subsequent queue returns
are `0800C051` and `0800C5BF`. The isolated `{actor} misses!` prototype passes
149 native formatter/display cases, all one line, maximum 201/216 pixels.
The enemy route is reached through ordinary battle; the player route uses a
controlled miss-probability argument at an ordinarily reached attack entry.
Evidence: `build/text-next/miss-consumers.txt`, `attack-resolution.txt`, and
`build/combat-miss-prototype/report.json`. This prototype is not yet inserted
in the cumulative accepted ROM.

Reader control `7F` draws the first two-byte glyph from player RAM `02003B58`:
CPU `08002158` loads the bytes and calls the glyph renderer. Width measurement
at `08001D78` performs the same lookup, so centered lines include the initial.
Control `7E` instead reads the whole name. Evidence: Ghidra
`build/text-next/reader-control-dispatch.txt`, `player-initial-reader.txt`, and
`build/player-initial-prototype/report.json` (four native cases: required
Torneko, widest English, widest Japanese, one-letter English). This probe
changes an existing untranslated bank-one text span only in disposable RAM
after an ordinary village approach; it allocates no RAM and writes no save.
It proves rendering and centering, not missing-King scene progression.

The item-111 unidentified regression also exposed repeated pre-instruction
reader-entry breakpoint observations after an IRQ. Both glyph and layout
observers now accept a repeated entry only before any glyph, with identical
registers (including SP/LR), payload and window. Actual nested calls remain
separate. Evidence: `build/services/item111-diagnostic.json` and the passing
five-case `item111-regression.log`; cumulative checks were restarted.

### Write scrolls omit the native Info action

The native action builder at CPU `08019208..08019224` substitutes action 33
(Write) for action 40 (Info) on item IDs 124 and 151. Evidence:
`build/menu-resize/producers.txt`, the full 221-definition native action sweep,
and `build/services/write-scroll-regression.log` (22 passing cases, including
all nine states for both IDs). Unidentified items have already substituted
Name (41), so they do not acquire Write through this branch. Disabled action
flags remain native. The item validator now checks this explicit distinction;
it does not claim these two descriptions were rendered through the inventory
Info route. Their other description consumers remain to be investigated.


## Player status-message formatter ownership

`build/shared-text/item-use/report.json` records fourteen controlled inventory
replacements followed by the native Drink action. The source save and fixture
remain unchanged; these are item-effect probes, not natural acquisition.
`build/text-next/item-status-functions.txt` disassembles complete native Thumb
functions `0800B6E0`, `0800B764` and `08015848`.

The first two reserve exactly 256 stack bytes for the hallucination/blindness
message. Shared table offsets E4/E8 are formatted at `0800B748`/`0800B7C4`, using
the name returned by `08009ACC(0)` (the player). Their queue return addresses are
`0800B759` and `0800B7D1`. The blindness function also has a separate source at
shared offset 4A0. These are proven consumers, not an exhaustive shared-pointer
cross-reference audit.

Helper `08015848` reserves 256 stack bytes and always obtains the player name
with actor getter argument zero. It formats at `0801585C` and queues at
`08015864`; caller-provided r1 is preserved as queue flags. Probes naturally
through the controlled item actions observe shared 178 (maximum HP), 194
(fullness cannot increase), and 528 (berserk) through this helper. No status
message insertion or width acceptance is claimed by these traces.

The 7F control is now supported by the production dialogue compiler and glyph
expectation walker. Four native cases were repeated without monkeypatching the
expectation walker (`build/services/player-initial-integration.log`). The compiler
reserves 14px, requires the exact source-control order and emits the original
single byte. Existing @A event timing is retained, not synthesized or reordered.

### Bakery native consumer and isolated English prototype

Complete Ghidra function `0801E394` owns a 256-byte formatting buffer at
`[SP+4, SP+0x104)` after its 0x104-byte local allocation. Town table
`020141AC` slots 100–104, 106 and 107 supply greeting, four-row menu, farewell,
purchase confirmation, another-purchase confirmation, insufficient gold and
full inventory. Slot105 is not read by this function and stays unmodified.
The greeting also has a separate slot212; that consumer stays unmodified.

ROM literal `0001E448` points to signed-halfword item IDs 203/206/207 at
`081482FE`. Prices are 100/300/400G in the corresponding 24-byte definition
records. Literal `0001E44C` supplies both the raw item-name pointer and price
word at record+0x0C. The isolated prototype redirects this one owned literal
to the existing checked English definition copy; all non-name words remain
original. Formatter `08000FB8` returns at `0801E41E`, then native Yes/No
`0801D0D8` controls the purchase. Delivery uses `08041E9C`, followed by exact
price subtraction. Full capacity reads the last 120-byte inventory slot at
`0200DF28+0x8E8`; no new RAM storage is introduced.

The native bread menu is 176px wide with four rows. English item names start
at x12 and prices at x128; the original menu/cursor geometry remains. Dialogue
has two 224px rows with the established 216px text budget. The formatted
confirmation reserves 80px/30 bytes for the item and three native price digits;
its full encoded result must fit 256 bytes.

`tools.research_bakery` and `tools.verify_bakery_prototype` explicitly redirect
a normally reached bank invocation into the bakery with PC=0801E394/r1=0.
The original r0 town table, caller and return are preserved. This is a controlled
service probe, not evidence of ordinary bakery unlocking. Thirteen prototype
cases validate purchases of all breads, cancellation/decline, repeated purchase,
insufficient and exact gold, full inventory, and three player-name extremes.
Checks cover glyph pixels, native widths, formatting guards/ABI, delivered item
IDs, exact gold changes, service return and unchanged battery.

Evidence: `build/text-next/bakery.txt`, `build/services/bakery-native/report.json`,
`build/bakery-prototype/report.json` and `build/bakery-prototype/build.json`.
The earlier `tools.research_shop` route reached Ed's warehouse-repair dialogue,
not a bakery transaction; its name was misleading. Neither that route nor the
new controlled tests establishes ordinary bakery availability.

### Player-only status message prototype

`0800B6E0` (hallucination) and `0800B764` (blindness/refusal) each own a
256-byte buffer `[SP, SP+0x100)` and obtain the player name through
`08009ACC(0)`. Their private shared-table literals at ROM `0000B760`,
`0000B7D8` and `0000B7A8` can be redirected to a checked table copy for these
consumers alone. Prototype offsets E4/E8/4A0 replace only hallucination,
blindness and failed-blindness wording; other original shared consumers remain
unchanged. Original bytes and source SHA are pinned by `tools.player_status_text`.

Formatter returns are CPU `0800B74C`, `0800B7C8` and `0800B7A0`. Queue returns
are `0800B758` and `0800B7D0`. Nine native Drink/effect cases pass exact format,
256-byte guard, ABI, queue, glyph bitmap and cursor checks. Maximum expanded
widths are 205px (hallucination), 155px (blindness) and 105px (refusal), all
single lines within 216px. No combat meaning or font width is removed.

Cases replace one carried item with herb 176/173 and set its identification
bit, supply three supported player-name extremes, and exercise the original
Drink action. Refusal cases additionally set the player actor's byte +B2 to 1
at `0800B764`, following its observed native condition; this is explicitly
controlled branch coverage, not a naturally earned resistance claim. The
status byte's complete gameplay meaning remains outside this text probe.
Screenshots stop after the actual queue renders, before subsequent turns clear
it. `build/player-status-prototype/report.json` records all overrides and its
separate ROM hash; the cumulative accepted build is unchanged.

### Event-text getter entry and special format consumers

Complete disassembly identifies the callable getter as **08050270**.
Previously cited **080502A4** is its final pointer-summing instruction, not the
function entry. Arguments are group/index in r0/r1. It adds the relocated
string base, group offset and selected entry offset, preserving r4–r7/SP.
`0804F8F4` is the event dialogue handler (pointer summation at 0804F938);
script byte +3 selects ordinary dialogue, Yes/No or a custom handler. The
ordinary and Yes/No branches feed the source directly to `08015A34`.

Nine direct BL sites to 08050270 were found in the original code interval
`[08000000,0805FE00)`: 0804FA7A, 0805020A, 08050BF4, 08050C18, 08051366,
080513B4, 08051466, 08051490 and 08051568. Complete containing functions are
recorded in `build/text-next/event-special-consumers-exact.txt`; this scan is
not proof that indirect calls cannot exist.

Special formatting uses EWRAM **0202F44C**, not the ordinary stack reader:
`080501DC` formats group7 index5/6/7/8 with an 8-bit value; `08050BC4`
formats an argument string generated into `[0202F4CD,0202F4ED)`; `08050C14`
formats a selection from ROM pointer table 0814D354. The output lies 0x81 bytes
before that 32-byte argument region. Do not infer that an English string fitting
216px is safe for this shared temporary storage. The medal consumer `0805132C`
explicitly clears **128 bytes** at 0202F44C before its formatted messages;
it formats group14 index7 and conditional index3/4/10/11, with direct-reader
messages at other group14 indices. Buffer boundaries, argument meaning/range
and reuse across these consumers need their own native cases before insertion.

`tools.research_event_relocation` now checks **1,046 native getter cases**
across all seven loaded banks. The full original loader `0804D6F8(bank_index)`
executes in a disposable session; all four native header fixups, original
decoded sizes and `0200FF38 == 020241AC` are verified. Then 876 selected
RAM offset words are redirected to the appended prose-preflight strings.
Every getter resolves the exact expected address and bytes without changing
the bank, preserved registers/SP or battery. ROM event tables stay unchanged.
This establishes the existing relocation arithmetic for the remaining banks,
not ordinary story coverage or special formatting-buffer safety. Evidence is
`build/event-relocation-probe/report.json`; the attached ROM is the separate
prose-rendering candidate.

### English event bindings and floor-progress buffer proof

The subsequent insertion prototype changes **875 owned ROM offset words**
across the seven banks. The native loader and all **1,046 getter cases** pass
with these ROM bindings already present; the verifier makes no RAM offset-word
replacement in this mode. All other decoded bytes and decoded sizes remain
original. `tools.event_prose_text` checks exact Japanese bytes, source hashes,
original slot values and the shared allocation ledger. The first candidate
(`25b0126584bebcd680194c801bab7bc58c956cceb622cd59a7859479db3b294a`)
also passes **1,079 rendering cases / 183,604 glyph checks**. Evidence lives in
`build/event-prose-insertion/`; its reports are regenerated for later editorial
changes. These are controlled rendering/getter checks, not ordinary progression
through all 875 scenes. The cumulative accepted build is reported separately.

Floor-progress function **080501DC** always formats its selected source,
including the floor-27 branch whose text has no `%d`. Therefore source
`event-bank-5.2747` is excluded from the ordinary prose insertion alongside
the three numeric branches. Its English payload is 266 bytes including NUL;
window fit alone cannot authorize the old shared temporary destination.

`tools.floor_progress_text` gives this specific function an owned **288-byte**
stack region `[SP+8, SP+296)` after its enlarged allocation. `[SP, SP+8)`
remains the original outgoing-argument area; saved registers are above the
new region. Checked ROM patches are `[000501DE,000501E0)` (`82b0`→`cab0`),
`[00050210,00050212)` (`114c`→`02ac`) and `[0005024E,00050250)`
(`02b0`→`4ab0`). No new persistent RAM or save storage is claimed. The four
group-7 slots, indices 5–8, retain their source identities and use the same
checked bank relocation as ordinary prose.

The isolated candidate SHA is
`c210e4cd522c533919c8d018572ee3271ede331af30e408d770742b586f8bddc`.
`build/floor-progress-prototype/report.json` records **27 passing cases**:
floors 0/9/10/19/20/26/27/28/255 with three player-name extremes. The probe
redirects an ordinarily reached bank call, supplies bank-five data and the
floor byte explicitly, then restores the prior bank before returning. It
checks the actual selector, formatter argument, exact output, region guards,
pixels/pages, native return ABI, items/gold and unchanged battery. This proves
the bounded consumer in the recorded call context; ordinary final-quest
reachability and other consumers of 0202F44C remain separate work.

Further tracing of **0805132C** identifies a second static source passed to
the formatter: bank-six group14 index3, `event-bank-6.465b`. Its English is
143 bytes including NUL. Along with formatted indices 4/7/10/11/12/13, it
requires explicit ownership of the medal consumer's output region. It is now
excluded from ordinary event insertion, reducing that candidate to **874**
sources. The 875-source rendering/getter evidence above remains historical;
it did not test this consumer's temporary buffer. Medal total is a signed
halfword at `020102A8`, clamped to 999 by the observed consumer, with reward
steps of 20 and a terminal 999 target. This is consumer evidence, not ownership
of new save storage or a complete medal service validation.

### Private well-level acknowledgement prototype

Native **08050C14** reads signed-halfword `02005674`, subtracts one and selects
from ten pointers at ROM `[0014D354,0014D37C)`. Their exact original labels
are レベル1 through レベル10; source strings occupy their individually pinned
ranges around ROM 0006C380–0006C3F6. The two known callers choose bank-five
group14/index18 or bank-six group8/index8. After formatting and displaying, it
sets bit 04 of byte `0201020E`. These fields retain their original layout.

`tools.well_level_text` copies the ten labels privately, binds only those two
acknowledgement sources, and replaces `[00050C14,00050C1C)` with a checked
far jump to a function reproducing the native getter/selector/display/flag
sequence. The helper owns `[SP,SP+256)` below its saved r4/LR and restores SP
and all callee-preserved registers. Original level table and other consumers
are untouched. Maximum English label width is 42px; complete formatted text
must fit the separate 256-byte bound.

Candidate SHA `ba06c7665dec1552ca7b1cd2d371b26e5846d5e8e9fafbd1b3c43ba90e8b3912`
passes 40 calls in `build/well-level-prototype/report.json`: both source banks,
levels 1–10, completion bit clear/set. The probe redirects a native bank entry,
supplies the selected bank/group/index and changes the level/flag only upon
that entry, so those overrides cannot prevent reaching the service. Exact
formatter bytes, guard, pixels/paging, caller ABI and bitwise flag result pass;
`[0202F44C,0202F4ED)` remains unchanged, as do items, gold and battery. Supplied
event-bank bytes are restored before returning to the original caller. This
does not claim the level-selection menu is English or validate ordinary well
access. Actual input schedules and original arguments accompany every case.

### Village-name prose formatter prototype

Native **08050BC4(group,index)** clears `[0202F4CD,0202F4ED)`, calls
**08041FD4** to generate a name there, and formats into **0202F44C**, only
0x81 bytes earlier. Its known sources are bank-five group23/index1 and
group29/index14, plus bank-six group28/index14. Their English payloads need
up to 392 bytes after substitution, so retaining those adjacent shared
destinations would risk overwriting the argument during formatting.

08041FD4 reads indexed name bytes starting at **02003B46**, using the glyph
table referenced at ROM 0004202C (already redirected by English name entry).
It emits up to eight two-byte glyphs and forces NUL at output+16; byte value
01 terminates early. The current player editor's seven-character limit does
not reduce the producer's underlying eight-glyph bound: reserve 112px and
16 encoded bytes for this field. No stored-name or save layout is changed.

`tools.village_prose_text` checks and redirects `[00050BC4,00050BCC)` to a
helper reproducing the original name generator, getter and display calls.
Its 480-byte frame assigns output `[SP,SP+448)` and argument
`[SP+448,SP+480)`, beneath the original r4–r7/LR save. It clears all 32
argument bytes before calling the native producer and preserves the original
callee ABI. Three original event slots are changed through checked bank
repacking; other decoded bytes and bank sizes remain original.

Candidate SHA `666aedfcaec84b0836502399a012f01c83133701d37d6691db3f71ee3ec1ef94`
passes twelve calls in `build/village-prose-prototype/report.json`: all three
sources with Torneko, eight widest English glyphs, eight widest Japanese
glyphs and the empty-name branch. Eight-character probes intentionally exceed
the editor limit. Tests check the exact native-generated name, formatted bytes,
argument/saved-register guards, stack bounds, pixels/paging, original shared
temporary bytes, items/gold and battery. Bank data is restored before the
original bank caller resumes. These are controlled consumer tests, not ordinary
access to the burned-village dialogue or newspaper scenes.

### Medal formatter and reward-message prototype

`tools.medal_text` adapts **0805132C** with a 480-byte stack message region.
The entry at `[0005132C,00051334)` jumps to a helper that reproduces the
original low/high-register saves, allocates 480 bytes and resumes at 08051336.
The exit at `[0005157C,00051584)` releases the region and reproduces all
original register restores. Three output-address instructions at 0005133E,
00051444 and 0005153E now select SP instead of the shared EWRAM temporary.
The original 128-byte clears stay within the larger owned region. The original
selector, inventory operations, threshold arithmetic and flag calls are kept.

Nine bank-six group14 sources are bound to checked English: formatted indices
3/4/7/10/11/12/13 and reward messages 8/9. Static index3 still requires this
buffer; the longest formatted result (index4) needs 468 bytes including NUL.
The three-digit numeric reserve follows the observed 0–999 total/threshold
range. Reward source commands, including @A and player/centering controls,
retain exact order and are exercised by native reward calls.

Native flags DB and FD use the original bit table `[020101AC,020101CC)`;
DB distinguishes the conversation state, while FD alternates the next reward.
The observed reward IDs are 22 (Metal king sword) and 43 (Metal king shield).
The function counts/removes carried item 215 (Mini medal), advances the total
at 020102A8, clamps it to 999 and changes FD only when awarding a reward.
The prototype claims no new persistent RAM and does not alter these save fields.

`build/medal-prototype/report.json` records **33 passing cases** on SHA
`22dbb5115bf3d440ac482eeeef7695c12a4bf3086a7a6041e0d6b2746863efc4`.
Initial/repeated explanations, both gifts, twenty carried medals, 999 clamp and
terminal states use three player-name extremes. Tests verify exact formatted
bytes, stack guards, all preserved registers, paging/pixels, medal removal,
actual gift IDs, total/flag results, gold and battery. The native selector does
not choose index4 in the observed configurations; its separate cases explicitly
override index3→4 at 08051568 and record that intervention. This is proof of
the bounded display consumer, not evidence that this source is naturally used.
All inputs, original state and overrides are recorded; ordinary postgame
reachability remains outside the accepted gameplay routes.

### English unidentified-name prototype

`tools.item_alias_text` copies all 155 alias records, replaces only the first
word of records 0–153 with appended English pointers, and redirects the three
audited formatter literals at `[0000F628,0000F62C)`, `[0000F64C,0000F650)`
and `[0000F684,0000F688)`. The original `[00143058,00143EE0)` table, assignment
literal at `[00009FD8,00009FDC)`, every non-name field, record order and complete
End Mark record remain byte-identical. No assignment or save logic is changed.
The 154 names are unique within the English display catalog and stay within
80px and 31 encoded bytes including NUL. Nineteen use documented compact forms.

The isolated prototype SHA is
`5b8b06fd9ac6d5ed76397deff7731ebb9e7308feb7e5d2ebc72eb1904a8210ae`.
It adds these appearances to the early-text baseline, separately from the current
story candidate. `build/item-alias-prototype/report.json` contains 166 passing
cases: every appearance, plus the widest priced and identified case per category.
The probe sets a representative carried item and the existing per-definition
appearance halfword at `02003BAC + 20*item_id + 4`, and explicitly sets/clears
identification bit 40000000 in that definition's flags. Inscription bit 00400000
is never set. Cases record the original and controlled records separately.

Native formatters, 64-byte row guards, bitmap/width checks, normal English
spacing, numeric cells, identification reveal and two action-panel reopen/
restore cycles per case all pass; the battery stays unchanged. The six
representative categories exercise the pot, staff and general appearance-name
branches. Randomized ordinary discoveries, custom naming, inscriptions and
special item definitions are not claimed by these controlled cases. The native
gallery is `build/item-alias-prototype/index.html`.

### Private player-effect message consumers

`tools.player_effect_text` owns only thirteen four-byte ROM literals (exclusive
ranges are each listed start through start+4): B48C, B4B0, B4F8, B53C, B588,
B5CC, B614, B65C, B6AC, B6C4, B6DC, B728 and B820. Original values must point
to the original shared-message table; a private copy changes only source slots
200, 7A8, 7DC, 490, 7A0, 498, 918, 8F4, E0, 110, 118, 7AC and 3DC respectively.
Original shared pointers and every other slot/consumer remain unchanged. Existing
hallucination/blindness literals are owned separately by `player_status_text`.

Full Ghidra disassembly in `build/text-next/player-effect-consumers.txt` proves
entries 0800B450, B4B4, B540, B5D0, B664 and B7DC; the B6E0 routine is recorded
in `item-status-functions.txt`. B634 and B688 are interior instructions, not
callable entries. Player lookup is either direct 08009ACC(0), or the fully
inspected wrapper `[08015848,08015870)` which calls that lookup and formats into
its existing 256-byte stack buffer `[SP,SP+256)`. B450/B6E0/B7DC likewise own
256-byte local output buffers. Source 7A0 is immutable direct queue text and
has no formatter buffer. No stack frame, persistent RAM or save storage changes.

`verify_player_effect_prototype` uses a disposable native 6F checkpoint and Drink
call stack. It explicitly redirects the effect entry from 0800B6E0, controls gear
words at `[020081D4,020081DC)` where needed, and records helper-result overrides
at 0800B468 or 0800B67C for the slowing/confusion outcomes. Confusion refusal
slots 110 and 118 alias the same Japanese source but are independently exercised.
All thirteen reads with three name extremes pass: exact output, buffer guards,
formatter/queue/consumer ABI, native one-line pixels and unchanged battery.
The widest item-recognition sentence is exactly 216px with the maximum Japanese
name; dancing is 208px. Sources' Japanese fit-next/newline presentation becomes
one measured line, without dropping semantic content. This establishes private
consumer rendering, not ordinary effect acquisition or gameplay equivalence.
Candidate SHA: `baafdc54fbfbc802a8da8e749b09c6d4dbcc05ee3e63d312b53be861ea5b8e36`.
Evidence: `build/player-effect-prototype/report.json` and its native provenance,
screenshots and input schedules. Cumulative insertion remains pending.

The remaining Japanese Drink announcement led to an additional ROM table at
`[001419B8,001419F0)`, fourteen category-indexed pointer slots referencing five
formats at 000649B0, 000649C4, 000649D8, 000649EC and 00064A00. A direct ROM
reference to the table occurs at `[000258D0,000258D4)`. These are discovered
sources/consumer leads, not yet accepted insertion ownership or free space.

### Private item-use announcement prototype

Full disassembly of `[080257F8,080259A4)` in
`build/text-next/item-use-message-functions.txt` establishes the native owner.
The fourteen category slots in `[001419B8,001419F0)` alias five source formats.
`tools.item_use_text` copies this table and redirects only literal
`[000258D0,000258D4)`. All original table words remain unchanged. The native
function uses a 320-byte frame: `[SP,SP+256)` for the formatted announcement and
`[SP+256,SP+320)` for the item argument. The player argument comes from
08009ACC(0); 0800EEF0 generates the complete coloured item name.

The private queue-call patch owns `[0002585A,00025864)`, including the original
MOV r0,1 after the call. This site is halfword-aligned, so its ten-byte indirect
jump uses an aligned pointer at 00025860. The helper reproduces r0=SP/r1=1,
saves 36 bytes temporarily, and measures actual native glyph advances. It removes
the authored break only when the entire message fits 216px. Colour opcode03
and its parameter and reset05 have zero width and are preserved when copying;
unknown controls retain the fallback. After the unchanged native queue returns,
it restores the original MOV r0,1 and continues at 08025864. Every fallback line
is statically bounded using player98px and verified item-row162px; maximum output
is 95 bytes including NUL, within the existing 256-byte output. No persistent RAM
or save allocation is introduced.

Native prototype SHA
`f00c615e9a61fd0251f3cbb5c4e76cc9ea6f44d2a08cec0232607bb391b8ee74`
passes 60 cases: five formats, three player names and four item fields (native
Misleader herb, synthetic162px, synthetic63bytes, another valid colour operand).
Forty messages join to one line; twenty retain both complete lines. Tests check
exact output, the entire adjacent64-byte item buffer, original continuation r0,
callee-saved registers/SP, queue ownership, glyph pixels/cursors and battery.
The r1=1 queue path may clear the old window before copying; its saved LR at
SP+12 identifies this owner when live LR has changed. Evidence is in
`build/item-use-prototype/report.json` and its native provenance/input schedules.

An early isolated attempt used an eight-byte jump at the halfword-aligned site;
native validation rejected it before any cumulative insertion. A second probe
exposed colour controls that prevented otherwise-safe joining. The corrected
aligned trampoline and colour-aware helper above pass the complete suite.
No ordinary non-Drink action, custom name, inscription or special definition is
claimed by the category/field probes. Cumulative integration remains pending.

### Story A-command announcement prototype

The native wrapper `[080503F8,08050438)` passes callback pointer 08051665 (literal
at `[00050444,00050448)`) to 08015A34. Full callback disassembly
`[08051664,080516B6)` proves that `@A@` only invokes 08058BC0 with arguments
010F and 10. Gift allocation and dungeon-unlock flags do not occur in A; those
belong to surrounding event logic. B/C still perform the documented scene/flag
transitions and are not admitted by this prototype's compiler.

`tools.story_command_text` appends fifteen reviewed streams and repoints their
exact offset slots in banks0/2/3/4/5/6. Only a single @A@ is permitted per source;
printf fields and other at-commands are rejected. The two medal reward sources
are already owned by the medal consumer and are excluded. All decoded bank
sizes, original strings, nonselected slots and scripts remain byte-identical.
No new RAM or stack buffer is introduced: the existing direct reader consumes
appended ROM strings. Slots and packed-bank pointers are recorded in
`build/story-command-prototype/build.json` with expected-original checks.

Prototype SHA
`62b15a9cd81aa06a863890a2d383d8683fb5e5b53ab9468db2157aade5a86313`
passes all seven native ROM bank loads and 1,046 getter targets without any RAM
offset substitution. Forty-five controlled calls (fifteen sources, three names)
redirect an ordinarily reached bank invocation to the native 080503F8 wrapper.
Every A callback occurs after exactly the expected preceding English/player
glyphs and requests exactly the original sound/parameter once. Callback and
wrapper callee-saved registers/SP, native pixels/colours/centering/paging, inventory,
gold, quest/event flags and battery remain correct. The 13,104 glyph checks and
all input schedules/captures are in `build/story-command-prototype/report.json`.
Gallery: `build/story-command-prototype/index.html`.

This supersedes the earlier uncertainty about A's display-side effect for these
fifteen streams. It does not claim naturally earned gifts, dungeon unlocks or
ordinary later-story progression; those surrounding native scripts are unchanged.
Cumulative insertion is pending while the preceding build is frozen for regression.

### Additional player-condition prototype

`build/text-next/player-recovery-functions.txt` fully disassembles the sleep
routine0800B374, wakefulness0800B3C4, immobility0800B3F8 and poison0800B240.
The latter takes an actor pointer but all displayed names and strength storage
use the native player. `tools.player_condition_text` redirects only four-byte
literal ranges beginning B3A0, B3C0, B3F4, B434, B264, B280, B2EC and B36C
(exclusive end = start+4). B434 serves two source slots; the private table changes
only slots11C/F0/4A8/1F0/88C/204/2FC/298/DC. Original shared-table data and all
other pointers remain unchanged. Native 256-byte stack buffers are sufficient;
no code/frame or persistent-storage patch is introduced.

Poison's strength field is the signed halfword at player actor+76. For positive
strength, severity<=1 subtracts one; greater severity subtracts three and clamps
to zero. The message receives the original-minus-result amount, hence1..3.
The numeric format reserves one six-pixel native compact digit. Immunity paths
read floor result101, actor flag40000000 or gear bit0200 and preserve strength.
Wakefulness sets actor+A4 to99. Immobility always prints1F0; actor+B2 nonzero
adds the immediate-recovery88C message, while zero invokes the native status setter.
These are bounded observations, not claims about ordinary availability.

Prototype SHA
`6457d95c3084e7d6dbf4c3a83cad6bb6cefe47dcbeafd986da355bcc8d1dc4a4`
passes 45 controlled native cases/48 single-line messages and1,143 glyph checks.
Three player names, strength1/2/3/32767, severity1/2/3, three poison protections,
both sleep branches, wakefulness and both immobility branches are covered.
Native strength results and wakefulness timer are checked at consumer return;
formatted values, exact buffers/guards, preserved registers/SP, queue pixels and
battery also pass. Inputs/dispatch/helper-result/state overrides are explicit in
`build/player-condition-prototype/report.json`; the gallery is its `index.html`.
This independent candidate includes the earlier private effect/use/appearance
extensions on the early-text baseline, but omits the story candidate. Cumulative
insertion remains pending while the 1,848-resource regression is frozen.

### Native conditional break: compact-font boundary proof

The conditional-break handler at CPU ROM080020E2, within08001DA8, advances the
stream by two bytes and calls residual-width helper08001C84 at the third byte.
The outer reader then skips that third byte without drawing it. With stream
`0E 0A 49`, hidden ASCII I maps to native glyph8268 and contributes9px. At
080020F4, r0 is224 (the native dialogue-window width) and r1 is current x plus
remaining rendered width plus9. Thus actual totals<=215 join;216+ wrap. The
verified216px text region remains respected. The Japanese hidden N marker has
an11px advance and would impose a different threshold; it must not be assumed
interchangeable. This finding is for one break and the audited control vocabulary.

`tools.probe_native_soft_break` appends eleven specimens through RomBuild and
changes a native item-use printf argument only in disposable emulator sessions.
No production source or code is replaced. SHA
`a289d0a0ef30da957a52c1549001ccd37664adb4ae673e5b8120b4623e8255e0`
passes totals210/213/214/215/216/217/224/225, two native Japanese-prefix cases at
215/216, and a valid coloured suffix at215. The recorded native fit registers,
exact queued control bytes, glyph sequence/pixels/cursors, first suffix position,
256-byte guard, queue ABI and battery all pass. Evidence and original-to-controlled
argument/item records: `build/native-soft-break/report.json` and native provenance.
All actual draws stay within216px. No arbitrary control stream, custom inscription,
or multiple-break pagination is accepted from these probes.

### Equipment/removal/drop private text prototype

`build/text-next/item-action-consumers.txt` fully disassembles CPU ROM routines
Equip `[080246FC,08024908)`, Remove `[08024918,080249D6)` and Drop
`[08024E70,08024F7E)`. Their native outputs are192 bytes, not256. Equip's frame
is0x150: outgoing arguments `[SP,SP+10)`, message `[SP+10,SP+D0)`, and two64-byte
item fields `[SP+D0,SP+110)`/`[SP+110,SP+150)`. Remove's0x140 frame has the message
`[SP,SP+C0)` followed by two64-byte fields. Drop's0x100 frame has that same message
and one64-byte field. No frame/code change or new RAM/save allocation is needed.

`tools.inventory_action_text` copies the original654-pointer table and changes
only slots078/07C/080/084/088/094/0A8/0AC/A14. Only original ROM four-byte literals
starting2471C/24774/247B8/24880/24994/249D8/24EB8/24EE8/24F60/24F80 are redirected
(exclusive end=start+4). Literal24880 serves both successful equipment and its
subsequent curse announcement. SlotA14 is selected by offset literal24F84 when
ground allocation fails: its mysterious-force explanation differs from A8's
location refusal. Remove's separate ground fragment090 and literal24930 remain
unchanged pending contextual evidence. All other shared consumers remain original.

Nine reviewed sources fit their fixed/fallback216px lines and native192-byte
outputs; each item argument reserves63 content bytes/162px. Maximum expansion
is133 bytes including NUL. Four sources use the separately proven native
`0E 0A 49` conditional break; source088 fits exactly216px without one, while
source094 fits213px. No font compression, window change or assembly helper is used.

Prototype SHA
`071cd8052b4fc226e02d8ff41c61e54d029a4b3991aa51ebc21873887f1e7e80`
passes44 controlled native-menu cases: equipment, newly discovered curse,
previously equipped curse blocking replacement, invalid category, ground
restriction, removal/refusal, drop/refusal, unavailable floor and mysterious
force. Four field cases per route cover native text,162px width,63-byte length
and valid colour controls. There are48 messages,32 one-line and16 two-line,
with1,875 glyph/pixel checks. The original192-byte guard and separate name fields,
formatter/queue/consumer registers/SP, equipment/removal flags, inventory counts,
dropped floor item identity and battery pass. Force failure skips the allocation
call entirely in the controlled session, avoiding an artificial duplicate item.
The game patch itself changes only the owned literals and appended resources.

Evidence, controlled originals/overrides and actual input schedules:
`build/inventory-action-prototype/report.json`; screenshots/index.html beside it.
Private-table/code preservation also passes `tests.test_inventory_action_text`.
Ordinary acquisition, arbitrary item state, custom names/inscriptions, other
shared consumers and the original ground-removal fragment remain unaccepted.
This prototype is separate from the frozen1,848-resource cumulative regression.

### Central pickup private text prototype

CPU ROM routine `[08024AD8,08024E6C)` uses a 0x100-byte frame: message
`[SP,SP+C0)` and item name `[SP+C0,SP+100)`. Private table reads use original ROM
four-byte literals beginning 24B40, 24B88, 24C0C, 24CE8, 24D24, 24D38, 24DE4 and 24AC0
(exclusive ends = starts + 4). Their only translated slots are 150, 1EC, 37C,
09C, 0A0 and 098. The original table and surrounding code stay unchanged. The automatic-walk
wrapper `[080249DC,08024AD8)` has a separate 256-byte output and reads slot37C
through owned literal24AC0. Its name field is `[SP+100,SP+140)`; its 0x148-byte
frame also reserves eight outgoing bytes at `[SP+140,SP+148)`. No frame changes
are required.

Source09C has distinct gold, arrow-merge and ordinary-item formatting calls.
Gold uses definition212 (category4; definition213 is explicitly excluded from the
gold path) and adds the signed item halfword at+4 to player actor+60, with the
native gold cap. Arrow merging uses category8, matches native definition IDs,
and updates the carried quantity via0800E054. Full inventory branches on r1:
zero queues098 directly; nonzero formats0A0 with both refusal and standing text.
Actor flag01000000 selects150. Floor item flag10000000 selects1EC, except native
ID220 selects37C. This is control-flow evidence, not a claim that the special
item's definition/name is fully localized.

`tools.pickup_text` adds six reviewed streams through the shared private-action
compiler. Existing 192-byte outputs and 64-byte fields remain unchanged; the
largest formatted reserve is151 bytes including NUL. Native conditional breaks
preserve full wording at the verified width boundary. The full-inventory standing
message keeps both clauses on two bounded lines.

Prototype SHA
`f57a4cfd25aa757fb2b74023890d13385069e60ae6697663a5cece2a50ed5c3a`
passes 36 cases: nine paths with native,162px,63-byte and coloured item fields.
All 1,307 glyph checks pass; 26 messages occupy one line and 10 occupy two. Ordinary
Drop inputs establish a real floor-item allocation, then Floor/Take inputs reach
the native pickup consumer. Explicit controlled fields select gold123, arrow5
merging into10, full20-slot inventory, player/floor flags and the special220
branch (the latter overrides only the selector result, not the actual item ID).
The resulting inventory counts, gold totals, merged15 arrows, refusal inventory
preservation, buffers, separate item fields, registers/SP and battery all pass.
Evidence and original-to-controlled bytes/input schedules are in
`build/pickup-prototype/report.json`; its gallery is `index.html` beside it.
Arbitrary gold cap/arrow limits, ordinary acquisition, custom names, inscriptions,
ordinary automatic walking and other shared consumers remain separately scoped.
The wrapper is exercised by controlled dispatch from the Take call stack. Its
status bytes at actor+BF/+AA/+9A/+9C are explicitly cleared, last-position words
`[02005664,0200566C)` set to -1/-1 and option byte0200567D set to1. This proves
the existing standing-only display branch; it does not claim an ordinary route
that enables that option. Native formatter/queue/wrapper ABI and inventory
preservation pass for all four field cases.

### Floor/Swap private text prototype

CPU ROM consumer `[08025648,080257EC)` preserves a 0x1B8-byte frame: a temporary
120-byte item record `[SP,SP+78)`, message `[SP+78,SP+138)` (192 bytes), floor name
`[SP+138,SP+178)` and inventory name `[SP+178,SP+1B8)` (64 bytes each). The first
inventory slot at0200DF28 is tested as a signed flags word; nonnegative means no
carried item and selects8F0. Actor flag01000000 selects154. The floor record's
10000000 flag selects1EC; failure of carried-item removal0800FF4C selects080.
Successful swap selects0C4 with the floor argument first and inventory argument
second. The routine then copies the actual120-byte item records, removes the
carried equipped flag00800000, and refreshes the floor item. No argument reorder,
new RAM, frame change or helper patch is needed for English.

`tools.swap_text` owns only four-byte original ROM literals beginning25664,
256C0,256F8,25728 and257EC (exclusive ends = starts+4), pointing to a private copy
of the654-entry shared table. Its five changed slots are8F0/154/1EC/080/0C4.
Unrelated shared reads and the original table remain unchanged. The confirmation
is “Swapped {floor} for {item}.” in the already established Floor/Swap context;
that context identifies the ground item, and source argument roles are retained.
The native conditional break yields at most two lines of207/189px at the widest
fields. Its maximum encoded output is158 bytes including NUL, within192 bytes.
Curse and stuck-item explanations retain their complete reasons.

Prototype SHA
`17d9a58b5cfda3d9588f730ddff9d03e75d5cc6f0eed643dd9c24d03d99ea830`
passes20 cases: success, empty inventory, inability, stuck floor item and cursed
carried equipment, each with native,162px,63-byte and coloured fields. Thirteen
messages fit one line; seven use two. All742 glyph checks pass. Native Drop and
Floor/Swap selection inputs establish the two actual items; recorded state/type
changes select refusal branches. Empty inventory is explicitly cleared at
consumer entry after selection, so this is not an ordinary empty-menu route.
The successful native case is203px; maximum-width fields render207/189px.

Checks preserve both64-byte name fields around the192-byte output, formatter/
queue/consumer registers and SP, native glyph pixels, and battery. Inventory
identity counts and the resulting floor item prove the correct exchange; refusal
cases preserve both item sides. Evidence and original-to-controlled records/input
schedules: `build/swap-prototype/report.json`. The `index.html` gallery includes
selection/result screenshots and actual widths/bytes for every case. This is a
separate prototype, excluded from the frozen1,887-resource cumulative regression.

### Private container transfers and generic kind names (prototype)

Native CPU ROM Put consumer `[08025108,0802528C)` has a0x164-byte frame:
message `[SP+4,SP+C4)` (192 bytes), two64-byte names `[SP+C4,SP+144)`
and32-byte selected-index storage `[SP+144,SP+164)`. Take consumer
`[08025474,08025588)` has a0xE4-byte frame: message `[SP+4,SP+C4)` and
indices `[SP+C4,SP+E4)`. Helpers `[0802528C,08025474)` and
`[08025588,08025648)` have0x140-byte frames: message `[SP,SP+C0)` and
names `[SP+C0,SP+140)`. All remain unchanged. Native item-name wrapper
0800EEF0 passes0x84 to0800EF30 as optional price-column alignment; it is
**not** a132px name bound. Price output and equipment/curse/ability prefixes
are disabled at this call. The prototype retains the conservative162px and
63-content-byte bounds for each name; arbitrary custom names remain open.

`tools.container_text` owns only four-byte ROM literals at25220,25258,25288,
252D8,2530C,25334,2536C,253C0,25460,25524,25558,25584,255E8,25644
(exclusive ends=start+4). These redirect to a private shared table changing
A24/A28/B0/B8/150/1EC/80/A2C/A30/BC/C0. Single Put success B4 and floor-prefix38 are also redirected through the
private table literal25178. The prefix becomes “Floor: ”; the confirmation keeps
its native floor-prefix, item, pot order: “{floor}{item} put into {pot}.”
Maximum formatted output is
166 bytes including NUL in the192-byte native region. One conditional break
preserves full wording and both argument roles. Partial summaries keep total
first and successful count second; single withdrawal keeps pot first, item second.

The two generic kind pointers occupy ROM `[001483D0,001483D8)`: index0 points
to0006B9A4 (`宝石箱`, jewel box), index1 to0006B9A0 (`壺`, pot). Both sources
are copied with a private8-byte table. Only literals250F8/25104 redirect to it.
CPU ROM helper080250E0 selects index0 for itemID167, index1 otherwise. Static
aligned Thumb BL scanning identifies its four calls at2520E,25228,25512,2552C;
no raw080250E1 pointer was found. Those are the audited bulk transfer consumers.
This documents ownership of those reads, not free space in the original table.

Container records have120 bytes, with seven12-byte contents at offsets24..108
and signed capacity byte+4. There are20 carried slots. Native selector08016BA0
and iterator08016BCC are controlled to exercise multiple selections: Put uses
carried indices1..19 and floor index99; Take uses contained indices0..6.
The child-item menu's native action IDs are26/16/7/40; **16** is Take out,
whereas18 is floor pickup. Generic kind selection is independently controlled
and does not establish ordinary Magic jewel box mechanics.

Prototype ROM SHA
`33922d757cc5094565e45c9b0264a1e66bbe7c1c48cefc45df5182872c66a7c1`
passes54 cases,2,333 glyph checks,34 one-line and20 two-line messages. All four
bulk summary formats remain one line, including two-digit totals and “jewel box”.
Native Drop establishes a floor allocation; ordinary Put in or View/Take inputs
reach the transfer consumers. Recorded controlled inventory/contents/state,
selector and formatter fields exercise successful carried/floor single insertions and single withdrawals, bulk and
partial transfers, full inventory and refusal paths. Checks prove192-byte output
bounds, both64-byte fields, formatter/queue/consumer ABI, pixels, conserved item
identities/counts, unchanged refused floor items and unchanged battery. Forced
Put failure skips the mutating08032ED0 call before returning failure.
Evidence/input schedules: `build/container-prototype/report.json`; screenshot
and actual-width gallery: `build/container-prototype/index.html`. These15 resources
are separate from the frozen1,887-resource candidate. Ordinary bulk selection,
custom names, special containers and other consumers remain open. Successful floor
insertion additionally checks removal of the real floor allocation and conservation
of carried plus contained plus floor item identities. The longest single insertion
is197/212px; it retains the floor designation without shrinking the font.

### Action-table boundary correction and contained-item producer prototype

The complete original action-pointer table is ROM `[00141904,001419B8)`:
**45 slots**,40 nonempty labels, one empty slot0 and NULL slots36..39. The early
private table deliberately copied only `[00141904,001419B4)` (IDs0..43); this is
not the complete original boundary. ID44 at1419B4 points to000648F8 (`すてる`,
discard), immediately before the category-use table beginning1419B8. Native
reads in CPU ROM0801E522/0801E576 use original literals1E560/1E62C and select
index44 (offsetB0), proving the extra entry. Complete-table SHA:
`aabf92a3a3c2560abae5368f545fe8a038d85ca8048e143fa49f2e6fb215546e`.
`tools.extract_action_labels` enumerates all45 and explicitly classifies holes.
ID44 and its consumers remain pending; translating the private first44 slots
does not translate this label or establish complete action-menu coverage.

`translations/additional-actions-review.json` reviews21 additional IDs in the
first44-slot copy. Together with the existing18 this covers all39 nonempty IDs
in that owned subset, including contained-item Take16/22, alternate Throw26,
Name41, Skills34/43 and Spells35. All fit the selected compact font's36px region;
the longest existing Remove remains36px. Prototype SHA
`139d07ca20ecbf914afce18e736bd548183845a3fdcd088f74a264613c14c4bf`
passes12 grouped enabled/disabled cases and1,248 glyph checks in the original
main item-action producer. Each case opens/cancels three times, moves selection,
checks disabled confirmation, and preserves parent tile pixels, inventory,
battery, producer registers/SP and guards. Availability is explicitly synthetic;
enabled synthetic actions are not executed. Evidence/gallery:
`build/additional-actions-prototype/{report.json,index.html}`.

The contained-item action producer is independently CPU ROM
`[080194C0,080196F6)`. It loads the original action table through ROM literal
`[00019680,00019684)`, so the earlier19434-only patch did not affect pot contents.
The native producer originally has a128-byte frame with64-byte output and64-byte
scratch. `tools.child_action_text` reserves320 bytes: output `[SP,SP+100)` (256),
scratch `[SP+100,SP+140)` (64), preserving the original saved-register area.
Checked halfword patches (ROM exclusive ends=start+2):194C8 `A0 B0→D0 B0`,
19652/1968E `10 A8→40 A8`,19696 `10 A9→40 A9`,196E8 `20 B0→50 B0`.
Only19680 redirects to the already owned reviewed table. Original geometry at
196B2/196B6/196C2 stays x192,width40,inset4; the8px outer-border gap is retained.
No RAM/save allocation or original shared-table mutation is introduced.

Contained-item prototype SHA
`bb7f94f7b672778c905c7a3acdabe1da4e8103a55ba47a4d36f1658d3893cfb3`
passes12 grouped enabled/disabled cases and1,524 glyph checks. A controlled known
Storage pot with a real contained Oak club reaches View by ordinary menu inputs,
then the contained action IDs are explicitly overridden to cover all39 reviewed
labels. Three open/cancel cycles preserve the parent and item data; native
formatting, glyph pixels,256/64-byte bounds and producer ABI pass. Separate
consumer return196F4 and materialization196B2 are checked. Evidence/gallery:
`build/child-actions-prototype/{report.json,index.html}`. Both menu prototypes
remain separate from the frozen1,887-resource candidate. Ordinary availability,
custom Name entry, separate discard menus and later-mode behavior remain open.

### Private town inventory actions and discard confirmations

CPU ROM `[0801E490,0801E75C)` owns the town inventory loop. Its 268-byte frame
contains a 256-byte output at `[SP+4,SP+104)` and action IDs at `[SP+104,SP+10C)`;
these sizes stay unchanged. The complete function uses its r9 table base only for
index59 (empty inventory) and108/109 (ordinary/filled-pot discard warnings).
`tools.town_item_text` allocates a sparse private110-slot ROM table with exactly
those three pointers. A checked eight-byte entry patch at ROM
`[0001E490,0001E498)` replaces original `F0 B5 4F 46 46 46 C0 B4` with an aligned
Thumb trampoline. The appended helper reproduces the original pushes and high
register moves, supplies the private table in r0, then returns to0801E498 for the
unchanged local-frame allocation and `mov r9,r0`. The original town RAM table,
other consumers, saved-register area and return stack remain unchanged.

The action labels use a separate full45-slot copy of ROM `[00141904,001419B8)`.
Only IDs40/42/44 become Info/View/Trash; only four-byte literals1E560/1E62C point
to this copy. Their menu formatters return at0801E53A (three labels for pots) and
0801E588 (two for other items), writing SP+4. Window creation0801E59C keeps
x192,width40,inset6: **34 usable pixels**, with an8px outer-border gap. Trash is
29px; Discard would be38px and is rejected. The three direct messages measure
155/106/187px within the216px dialogue budget. No geometry or font changes.

Choosing Trash reaches the native Yes/No consumer. A filled pot selects109 if
any of its seven contained records is active; the confirmation explicitly warns
about losing its contents. Yes clears the selected item's active flags before
native inventory refresh08010228; No returns without changing the record.
View and Info retain their native action IDs and handlers.

Standalone ROM SHA
`a1b28234a695e3729ec1a410f43e006e006600356f8478ac3bcdb31aa826d9e5`
passes10 cases and427 native glyph checks: empty inventory, repeated cancellation,
Info, ordinary-item discard No/Yes, empty-pot No/Yes, filled-pot No/Yes and View.
A normal bank invocation is explicitly redirected to0801E490 with its existing
town argument/caller; item records and identification are controlled. The native
menu selections and confirmation inputs then execute normally. Checks cover all
three messages and labels, output guards, full entry/return registers and SP,
original geometry, parent restoration, exact cancellation/remaining inventory,
selected-item removal, and unchanged gold/battery. The filled-pot deletion check
concerns native record ownership, not erasure of inactive historical bytes.
Evidence and schedules: `build/town-actions-prototype/report.json`; gallery:
`build/town-actions-prototype/index.html`. Ordinary access to the town inventory
menu and other consumers remain separately scoped. These six resources, the
additional action labels, contained-item producer, Swap and container messages
are now integrated in the1,934-resource candidate; full acceptance is pending.

### Common player-name message formatter: private source mapping

CPU ROM `[08015848,08015870)` owns a 256-byte output frame. The wrapper always
obtains player getter(0), formats its input source with that player name, then
queues the result with the original caller's flags. `tools.player_message_text`
owns only the eight-byte entry patch `[00015848,00015850)`; expected bytes are
`30 B5 C0 B0 04 1C 0D 1C`. Its appended Thumb helper reproduces the original
saved registers/local frame and substitutes only33 exact original ROM pointers
from a private source-to-English map. It resumes at08015850. Unknown original,
already-English and RAM pointers pass through unchanged. No original shared
pointer table, other consumer or RAM/save allocation changes.

Each reviewed source retains its original zero/one player argument. The existing
player field permits14 content bytes/98px; the largest formatted result is112
bytes within256. Fixed messages fit216px; the established conditional break
retains complete meaning when maximum names require a second line. Source-call
BL bytes and their target are checked against the pinned base, while ordinary
reachability of every listed effect remains separate.

Standalone SHA-256
`cd155dac0667135fdd6bd22305695da9fb6abb8d0d8f20cd6dad2d88f08294c3`
passes216 controlled native cases:33 sources with three names and queue flags0/1,
plus unmapped English/Japanese/existing-player-RAM fallbacks for the same six
combinations. A native Life herb Drink reaches the wrapper before recorded
source/flag overrides. Exact routing, output guards, queue flags, whole-wrapper
ABI, caller guard, all5,562 glyphs, player field and battery preservation pass.
There are190 one-line and26 two-line results, including fallback cases. Source214
provides the plain Japanese fallback; a previous sourceC8 probe exposed an
unsupported ASCII-space path in the test observer and is not claimed as covered.
Evidence: `build/player-messages-prototype/report.json` and its native gallery.
This33-resource prototype remains separate from the1,934-resource candidate.

### Blacksmith service: isolated table and native exchanges

CPU ROM `[0801D110,0801D544)` receives the shared town table in r0 and a
presentation mode in r1. It retains these in r6/r7. The existing528-byte local
frame has message storage `[SP,SP+200)` (512 bytes), two payment indices at
`[SP+200,SP+208)` and iterator temporaries throughSP+210. The saved32-byte register
area is above that frame. Direct and question wrappers0801D0A0/0801D0D8 pass text
straight to08015A34 with distinct question flags; plain prose does not use the
512-byte formatter output.

The standalone blacksmith prototype owns only `[0001D110,0001D118)`, expecting
`F0 B5 57 46 4E 46 45 46`. Its appended helper reproduces those pushes/high-register
moves, substitutes a private300-pointer ROM table and resumes0801D118. Original
shared town data and all other consumers remain unchanged. Unselected private
slots still point to the original source bytes within the resident town RAM
resource. Selected slots are0,3..26,60..67,69..78:43 sources, comprising35 plain
streams and eight formats. Sources1/2/68 are not read by this function and remain
separate. Neither relocation nor a language review establishes that they are free
space or safe for another caller.

Native formatter returns are0801D180/1D1A6 (initial payment offer),1D1FA/1D220
(payment lookup),1D3D8/1D3FA (next payment),1D434 (milestone count) and1D520
(ordinary count). The unchanged512-byte output is guarded. Base item arguments
reserve80px/30 content bytes; player display uses the established98px reserve.
The job counter at RAM `[02002C1A,02002C1C)` is a signed halfword but normal
progression runs0..120;0801D40A compares119 before incrementing. The compiler
reserves three digits/21px. A deliberately corrupt negative-counter probe did
not match the native formatter and is excluded, rather than broadening the
supported state claim. The longest reviewed format expands to464 bytes.

Requested payment IDs occupy existing RAM `[02002C14,02002C16)`; zero in the
first byte triggers native requirement selection. Controlled exchange tests set
IDs2/3 and three known items1/2/3, then use ordinary buttons. The native service
consumes the two payment items, strengthens item1 by its native1-or3 bonus,
selects the next requirements and updates the counter. No new RAM/save space is
claimed or changed by the text patch. Static tip selection divides the counter
by10 and caps the resulting tip index at22.

Standalone SHA-256
`6acc7d5348aba4b4340034ce16111de15b913b80336c53b8824d12bfd09af20d`
passes57 rendering/formatter cases and6,711 glyph checks, including widest player
names, widest/longest base item arguments and counts0/120. Whole-consumer return
registers, SP/caller guards and battery pass. Transaction evidence and all input
schedules are in `build/blacksmith-prototype/transactions.json`; screenshots and
source text are in its `index.html`. These are controlled service invocations,
not proof of ordinary unlocking/acquisition. The43 resources remain a separate
prototype, excluded from the1,934-resource cumulative build.

### Gaibara synthesis and the shared item-selector heading

CPU ROM `[0801D544,0801D824)` is the synthesis consumer. Its576-byte local frame
contains outgoing arguments `[SP,SP+8)`, two120-byte item copies `[SP+8,SP+F8)`,
message storage `[SP+F8,SP+1F8)` (256 bytes), a full item-name field
`[SP+1F8,SP+238)` (64 bytes) and two saved selection values throughSP+240.
The original32-byte saved-register area follows. r5 retains its town table, r6
its presentation mode, and SP+238 its caller-supplied joke selector.

`tools.gaibara_text` owns only entry bytes `[0001D544,0001D54C)`, expecting
`F0 B5 57 46 4E 46 45 46`. An appended helper reproduces the original prologue,
sets a private300-pointer table and resumes0801D54C. Thirty-four selected slots
are30..34,36,39..54,110..119,198,199; all other slots retain original town-RAM
source pointers. The original shared town table and source bytes remain intact.
The three formatted sources52/113/114 use the existing256-byte output and
reserve162px/63 content bytes for the complete native item name. Price52 keeps
its original paired `03 05`/`05` colour controls around `%d`; a conservative
positive32-bit reserve allows ten digits/70px. Formatter returns at0801D660,
0801D6B0 and0801D758 are checked. No new RAM/save space or stack growth.

The root selector at0801D596 reads source112 directly. The Japanese native
window is x8,width72,three rows, with two original six-pixel structural spaces
per row reserving12px for the cursor. Its60px text budget fits Synthesise55px,
Explain36px and Leave30px. English retains that padding and exact geometry.
Five native menu cases check all three choices, first-use greeting/flag at
RAM02002C17, empty inventory and three complete Explain/reopen cycles. No
menu/column resizing is introduced.

Native synthesis replay exposed a remaining shared heading: source ROM
`[000648AC,000648B3)`, Japaneseどれを, shared table byte offset14. The only table
read in item selector0801DD5C for that heading loads literal0001DDE4 at0801DDBE,
then slot14. `tools.selection_prompt_text` redirects only that four-byte literal
to a private24-byte sparse table with the selected pointer. Its original table,
other readers and source bytes remain unchanged. “Which?” is33px within the
original40px/one-row window atx8; the168px inventory stays atx64, preserving the
8px gap between outer borders. This is structural cursor/window spacing, not a
change to the three-pixel English word-space rule.

Standalone ROM SHA-256
`21b1499a02dca6c6aa9275bb3c8b66460a5eda8bbe227c474afd6232e8214ddf`
contains34 synthesis sources and one selector heading. It passes39 prose/format
cases (4,898 glyph checks), five menu cases (1,620),25 actual synthesis cases
(14,320) and three selector cases (288). The actual transactions use controlled
service entry, two known weapons+3/+4, gold and joke selector0..12, followed by
ordinary buttons. Output retains base ID1 with+7, consumes both inputs and
subtracts the displayed native fee. Both answers to each joke preserve its
reveal and normal price confirmation. The selector cases validate cancellation,
second-item selection and three SELECT/Info cycles with exact restoration of
both heading and inventory tilemap/tile pixels. ABI, byte guards and battery
preservation pass. Explicit field/state/register overrides and input schedules
are recorded in `build/gaibara-prototype/`; its `index.html` is the native gallery.

Ordinary unlocking, other synthesis categories, sources35/37/38/55 and unrelated
readers remain separate; unobserved fragments are not automatically discarded.
These35 resources remain a prototype outside the frozen2,010-resource cumulative
regression. Static observations are in `build/text-next/town-service-functions.txt`
and `item-selection-function.txt`; Japanese menu geometry is recorded in
`build/gaibara-research/report.json`.

### Remi service prototype and saved-village warning

Evidence: `build/text-next/town-service-functions.txt`,
`service-number-picker.txt`, `picker-width-setter.txt`,
`village-control-producer.txt`, `save-block-read.txt`,
`build/remi-research/roots.json` and `build/remi-prototype/*.json`.
This is a separate prototype, not part of the accepted2,010-resource archive.

CPU ROM `[0801E75C,0801F064)` is Remi's service consumer. The dispatcher at
0804FFF8 invokes it with r0=town table, r1=presentation mode,
r2=RAM0200FEF4 output record, r3=availability profile and a fifth stack argument.
The400-byte local frame has outgoing arguments `[SP,SP+14)`, formatted text
`[SP+14,SP+114)` (256 bytes), a complete item-name field
`[SP+114,SP+154)` (64 bytes), five available IDs `[SP+154,SP+159)`,
a25-byte profile copy `[SP+15C,SP+175)` and locals throughSP+190.
The original32-byte saved-register area follows; the fifth argument is SP+1B0.
These are existing regions, not new RAM allocation claims.

`tools.remi_text` owns entry ROM `[0001E75C,0001E764)`, expecting
`F0 B5 57 46 4E 46 45 46`. Its appended helper reproduces the original
prologue and substitutes a private300-pointer town table. The entry branch
uses r0, whose original table value is replaced, and the helper branches using
already-saved r4. **r3 must remain intact** because it is the availability
profile, unlike the earlier blacksmith/synthesis consumers. Sixty selected
slots are58,124..176 except133/141,200..205,208,213. The two excluded slots
are not read by this function. All unselected pointers retain original town-RAM
values. Source208 is copied to the existing256-byte buffer; its English148-byte
stream is checked separately at compile time. Ordinary unlocking remains open.

ROM `[0006B8F6,0006B90F)` contains five5-byte profiles:201/204;
201/204;201/204/202;201/204/202/203;201/204/202/203/205, padded with zeros.
The native signed-halfword field at `*(u32*)02001624+88` suppresses204 when
**greater than1**. Ten controlled profile/gate probes confirm the branch and
original root at x8,y24,width112,one to five rows. Two six-pixel ASCII spaces
reserve12px for the cursor, leaving100px. English labels measure66/89/36/42/82px.
The vocation field at `*(u32*)02001624+90` is one byte; native change/decline
transactions establish values0Merchant/1Warrior/2Mage. Its three menus preserve
72px/three rows with12px padding and60px text budgets; Merchant45px is widest.
All18 choice/confirmation/cancel cases preserve inventory/gold/battery and ABI.

Shared number picker CPU `[08016410,08016660)` creates the existing88px panel
at x144,y88. Its176-byte frame contains formatted output `[SP,SP+80)` (128 bytes)
and a two-cell numeric argument atSP+80. The original call at08016454 sets a
fixed12px advance through080018C0. English “Level ” plus two digits would not
fit under that rule. Only ROM `[00016454,0001645C)` is redirected, expecting
`0C 21 EB F7 33 FA 12 49`. An appended helper checks the picker format at
originalSP+A4 against the three exact private Remi template pointers. Matches
use proportional advance0; every other pointer retains12. It reproduces the
original setter call and displaced literal load02002C10 before resuming0801645C.
No geometry, argument layout or new RAM changes. Twenty-one English number
cases and three original-template fallback cases pass; number changes, return
values,128-byte guards and ABI are checked. Original fallback positions remain
multiples of12. Other shared-picker callers are not translated by this patch.

Native text control1F calls0801FAAC. It clears `[0200CEE8,0200CEFC)` (20 bytes),
reads a64-byte save block through08004438 at logical offset200, then decodes
up to eight indexed name bytes from localSP+14 through the name glyph table.
It returns0200CEE8 on success or null on read failure. This is the **saved
village name**, distinct from live player-name storage; the logical save offset
is not a claim about a fixed physical SRAM address. No save data is patched.
Remi213 retains1F followed by “ Village” and explicitly warns about overwriting
the village save before entering the dungeon. Layout reserves112px for eight
widest native glyphs, while the256-byte formatter stores only the1F byte.
Paired price colour controls are preserved; the maximum formatted warning is
201 bytes after the final wording revision. Six probes check the real saved header and controlled native
save-reader results for Torneko, eight English/Japanese glyphs, empty and
failure. The producer, nested glyphs, pixels/paging, declined question and
unchanged battery pass. A real warp/overwrite transaction is not yet claimed.

Initial standalone ROM SHA-256
`2d4844de9eeab0711042ce8e437b464fcaab00194ea25c3f171651e1329a2cfb`
passes73 prose/format cases,10 roots,21 English number selectors,3 original
selector fallbacks,18 vocation cases and6 saved-village cases (131 total).
The13 dungeon-name arguments still come from the original shared table at
ROM00140D68 plus slots174..180hex; their longest Japanese name fits the
conservative168px reserve. Their English binding, warp-selection menu, actual
Iron safe/staff/level transactions and ordinary service availability remain
separate work. The private selector heading included here has its own prior
synthesis proof; Remi staff selection still needs its actual route checked.


### Remi warp names and completed transaction probes (2026-09-24)

This supersedes the outstanding transaction/name work in the initial Remi
prototype section above. The previous170-case prototype SHA was
`324abc7c72db56ef2b49c3da4238dda66ea815d4949f083facf4dd6244d83781`.
A final warning-only revision is now undergoing cumulative regression on
`6c150efdece6cabe9c6f5ba433f4b308d83f4f5081d71bcc5be764ac4b9f0e2e`.
Evidence: `tools/remi_warp_text.py`, `build/text-next/remi-warp-selector.txt`,
`build/remi-prototype/{safe,charges,levels,warp-menu,warp-payment}.json`,
and the source-pinned cases/input schedules under those report directories.

The native warp selector is CPU ROM `[0801F064,0801F2D8)`.
Visited-depth data occupies existing RAM `[02005646,02005660)`:13 signed
halfwords. Controlled depth50 fixtures establish selection/order, not ordinary
progression unlocks. It excludes IDs7/11/12, restricts9 to Warrior and10 to
Mage, and suppresses6 when the service's fifth argument is nonzero.
The selector swaps the order of1/2 and3/4. First and second pages preserve
x8,y24,width128 and5/4 rows respectively, with a6px text inset and122px budget.
Six availability profiles survive three right/left cycles each with exact
panel restoration; all ten reachable IDs and the empty case are checked.

The original654-pointer table occupies ROM `[00140D68,001417A0)`.
`tools.remi_warp_text` appends an owned private copy and replaces only
slots174hex+ID for0..6,8,9,10. The two owned literal patches are ROM
`[0001EFB8,0001EFBC)` (Remi destination formatting) and
`[0001F234,0001F238)` (warp selector); both expect little-endian08140D68.
The shared original table and other consumers remain unchanged.
Names use documented PS1 fallback evidence, with provenance in
`translations/remi-warp-names-review.json`; those secondary name lists are
not claimed as primary bilingual captures. Cemetery Dungeon is widest90px.

Native Iron safe ID217 costs2000G (price ROM00143000); six cases include
exact funds, refusal, insufficient funds, full inventory and already owned.
Six staff cases establish5000G per charge, +5 and98-to99, selection/number
cancellation and insufficient funds. Controlled known-item fixtures do not
set inscription bit00400000. Five level cases verify native hero+88 halfword,
level2/5 fees and no-change refusal paths. It is the level field, not a generic
availability flag; values greater than1 suppress the root's Level up option.

Five warp-payment cases cover Magic Dungeon6 and Ordeal Mansion8, accepted
and declined offers plus insufficient funds. Native service output at existing
RAM `[0200FEF4,0200FEF7)` becomes bytes1,dungeon,floor on paid acceptance;
the flag stays0 on cancellation. Wallet deduction is1000G per selected floor.
Proof stops at CPU0801F062 before dispatcher processing. Subsequent dungeon
transition and actual saved-village overwrite/cold reload are explicitly unproved.
Battery and inventory remain unchanged within the controlled consumer probes.

Source213's final layout reserves112px for eight widest saved-name glyphs;
“the {village} Village save.” is200px, and the256-byte formatted stream's
maximum is201 bytes. Its1F expansion remains native. The revised standalone
SHA d21e78fa34beb2ee0e570443bfbbea8d9cc06f9b3e9b61ac9d72a2048e015f7c
passes all six saved-name variants and73 prose/format cases. Existing storage
and buffers are reused; none of these observations grants new allocation rights.


### Mayor village-renaming prototype (2026-09-24)

Evidence: `build/text-next/town-service-functions.txt`,
`build/name-entry/editor-functions.txt`, `build/name-entry/input.txt`,
`build/mayor-prototype/{report,editor,persistence,preview}.json` and its
source-pinned screenshots/input schedules. Prototype SHA `2c193162b58451954496b6da8dbd21c5926243001b420adc8740810b04f25be7`.
It remains separate from both accepted2,010 and the running2,115 candidate.

CPU ROM `[08020564,0802068C)` owns village renaming. Existing frame allocation
is276bytes: output `[SP,SP+100)` (256bytes) and newly decoded village-name
field `[SP+100,SP+114)` (20bytes), followed by32 saved-register bytes.
The function reads town slots99/206/207/209/210/211. `tools.mayor_text` appends
six reviewed streams and a private300-pointer table; unselected pointers retain
original town-RAM sources. Entry ROM `[00020564,0002056C)` expects
`F0 B5 57 46 4E 46 45 46`; its helper reproduces that prologue, substitutes r0
and resumes0802056C. r1 presentation mode is preserved; r3 is not an input.
No frame size or original shared table changes are made.

Slots206/210 each take one native `%s`, decoded from existing indexed village
RAM `[02003B46,02003B56)` into the20-byte local field. The decoder retains its
eight-cell limit and explicitly terminates offset16; layout reserves112px and
16 content bytes for legacy eight-wide-Japanese names. Maximum formatted English
is173/232bytes respectively, within256. The native calls are0802063E and
08020670, with return sites08020642 and08020674. Complete named villages stay
with the “Village” suffix in the outcome. New editor entry remains limited to
seven characters by the already-owned name-entry patch atROM000205C4.

Twelve controlled rendering cases cover four plain passages and both formats
with Torneko/eight-W/eight-wide-Japanese/empty names. Five native-button cases
cover greeting No, B on an empty editor, Torneko, seven-W and rejecting a name
then entering Newtown. **Back moves the name cursor; cancellation uses B when
empty.** Confirmation copies the existing16-byte indexed field; surrounding
bytes, separate player name, inventory/gold, caller registers/stack and battery
are preserved. No direct writes to persistent fields occur in these tests.

Three further cases walk normally from the controlled service location to the
house book, invoke the native save, cold-load in a fresh emulator and move.
Torneko, seven-W and the revised Newtown village names persist; the distinct
player name remains unchanged. Input schedules and disposable save hashes are
recorded. These prove persistence after the controlled service entry; ordinary
mayor unlocking/location traversal and every legacy-save scenario remain separate.
Existing regions are observations, not permission to allocate new RAM/save data.


### Well difficulty picker prototype (2026-09-24)

Evidence: `build/text-next/well-picker.txt`, `well-progress-getter.txt`,
`service-number-picker.txt`, `build/well-picker-prototype/{report,preview}.json`.
Prototype SHA841aec68f162b1d95018168560a90df22590859f253219204a2b0b5409b162db
passes20 cases. This is separate from the running2,115-resource build.

CPU ROM `[08051290,080512F4)` contains the well picker and literal pool.
The caller sets existing RAM word0201017C to1, reads a progress byte through
08041C80 (from existing RAM0200161E), clips it to10, and calls shared
08016410 with minimum1, exclusive maximumprogress+1 and initialprogress.
Cancellation clears0201017C; confirmation stores the chosen signed halfword at
existing RAM `[02005674,02005676)`. No new RAM/save fields are introduced.
Ordinary well unlocking and subsequent dungeon entry remain unverified here.

`tools.well_picker_text` owns only two ROM literals:
`[000512DC,000512E0)` originally0806C3F8 (question, source
`[0006C3F8,0006C415)`), and `[000512E0,000512E4)` originally0806C418
(level template, source`[0006C418,0006C423)`). Sources are byte/hash pinned by
`translations/well-picker-review.json`; original streams stay unchanged.
The new question “Which level would you like?” measures132px in216px.
“Level {number}” reuses the identical existing private Remi129 stream,
so the already-owned exact-pointer conditional helper selects proportional
advance. No second hook or change to unrelated picker formats is required.

Original picker geometry remains x144,y88,width88,row1. The two-cell field is
native; its existing128-byte output needs at most17bytes and44px under the
conservative digit reserve. The shared picker retains its own native input,
arrow and restoration handling. Five controlled getter returns1/2/9/10/255
exercise Cancel, initial value, repeated decrement to minimum and repeated
increment to maximum (255 clips to10). Full consumer register/stack guards,
formatted bytes/glyph pixels, native output flag/level and unchanged
inventory/gold/battery pass. Entry is a redirected normal bank invocation;
getter return/initial level overrides and snapshot-key release are recorded.
This tests specified valid menu ranges and the cap, not all progression states.


### Native hunger-warning consumer prototype (2026-09-24)

Evidence: `build/text-next/player-turn-hunger.txt` and
`build/hunger-prototype/{report,preview}.json`. Prototype SHA`7418292ff709c777237807b7ba1a16706fbfc98f913592cee075afc99020917d`
passes seven controlled-state/ordinary-input cases; this is not in2,115 yet.

CPU08008F4C is the large native per-turn handler. The hunger branch reads
existing player-pointer RAM02001624; player+54 stores fixed-point fullness
(256units per displayed point). It chooses shared slots23C/240hex when
crossing below20/10 respectively: original constants atROM00090E4/00090E8
are13FF/09FFhex. Existing RAM word02003B9C tracks consecutive starvation turns;
zero fullness increments it, with counts1/2/3 selecting slots244/248/24Chex.
Positive fullness resets the counter. With its native action flag set, this
branch reduces the existing signed HP halfword at player+84 by1 when starving.

Only ROM literal `[00009148,0000914C)` is patched by `tools.hunger_text`;
it expects08140D68 and feeds the warning lookup at080090FA. The queue call
is08009104, returning08009108. Its private654-pointer table replaces only
these five entries; the original shared table and unrelated per-turn literals
remain unchanged. All five English streams fit one216px line at normal spacing,
with maximum197px and77 encoded bytes. No formatter or new writable buffer is
introduced; these are direct ROM streams passed through the existing queue.

Seven cases control fullness/counter and existing HP/maxHP100, then use an
ordinary attack input, without PC or text-pointer overrides. They hit both
thresholds, the first three starvation warnings, a value above the first
threshold and the later quiet starvation turn. Native fullness decrement12
is observed and checked for this fixture; it is not claimed as the universal
rate (the handler includes equipment/status modifiers before subtraction).
Each starving action loses1HP. Queue text, one-line glyph pixels, cursor,
preserved queue registers/stack, inventory/gold and unchanged battery pass.
The checker records actual modifier/decrement values and all field overrides.
Other turn effects, starvation death/revival and ordinary long-play hunger
progression are not inferred from these bounded tests.


### Status-trap direct-text consumers (2026-09-24)

Evidence: `build/text-next/trap-message-consumers.txt`,
`status-trap-effects.txt`, `hallucination-timer.txt`, and
`build/status-traps-prototype/{report,preview}.json`. Prototype SHA
`901c2e4eabe8c5d2b26094b547de51697078bdbcb40563be3e2ec5ecd5975df0`
passes18 controlled-handler cases and1,101 glyph checks; not yet in2,115.

CPU `[08027A10,08027A8C)`, `[08027A8C,08027B08)` and
`[08027B08,08027B84)` contain sleep, hallucination and spinning-plate handlers
and their literals. Native r0 is the actor pointer; nonzero r1 selects failed
activation. They queue shared slot2F4, then2EC on failure or308/314/310 on
activation, followed by their original status dispatch. ROM literal ranges
`[00027A48,00027A4C)`, `[00027AC4,00027AC8)`,
`[00027B38,00027B3C)` and `[00027B80,00027B84)` each expect08140D68.
`tools.status_trap_text` owns these four replacements and a private654-pointer
copy replacing only those five slots. Existing original shared tables remain
unchanged. Direct English streams use at most164px/65bytes; no new writable
buffer is allocated. Sleep's player wrapper and status acknowledgements retain
their separately owned mappings and original256-byte outputs.

Controlled cases redirect the native per-turn call into each handler with
activation/refusal arguments, three player-name bounds and cleared resistance
fields. All writes and input schedules are recorded. Complete queue chains,
one-line glyph pixels, formatter guards, caller/queue registers and stack,
unchanged HP/items/gold/battery pass. Return instructions are08027A86,08027B02
and08027B7E. Existing actor bytes at offsets95/96/97 contain confusion,
hallucination and sleep timers; AF4C sets player hallucination to50 if zero.
Sleep/confusion activation produces positive timers; refusal leaves each zero.
Resistance fields include actor+08 bit20000000, +A4/+B2 and existing gear flags
at RAM020081D4; clearing these is test setup, not a game patch or new RAM claim.
Ordinary trap discovery/placement, special resistance and other trap handlers
remain unverified.


### Warp-trap consumer prototype (2026-09-24)

CPU handler `[08027680,080276F0)` uses ROM literal `[000276B8,000276BC)`
with original value08140D68. `tools.warp_trap_text` owns only this literal,
a private654-pointer copy and two direct streams for slots2F0/2EC (warp
announcement / failed activation). Original table and other handlers remain
unchanged. No new RAM or save storage is introduced.

Evidence: `build/text-next/trap-message-consumers.txt` and
`build/warp-trap-prototype/{report,preview}.json`, prototype SHA
`8529f2932404e1531b7af1c1b7b7cf1387c843266d159560fbab48035c57c3a1`.
Six controlled native-entry/activation/name cases pass162 glyph checks.
The handler queues2F0 with flag1; nonzero r1 queues2EC with flag0 and returns.
With r1 zero it calls08012220 with actor pointer r0 and mode0, then0802871C
with the original coordinates. Existing actor+66/+68 halfwords change from
(46,20) to(31,6) in this fixture; all failure cases preserve(46,20). These are
observed coordinates, not universal destinations. Queue/caller registers and
stack, HP/items/gold/battery are preserved. Caller return is080276EC.
Ordinary trap placement/discovery and other terrain/teleport constraints are
unverified. These two consumer bindings remain outside the2,133 candidate.


### Equipment-removal trap prototype (2026-09-24)

CPU `[08027B84,08027CE0)` includes the native handler and literals.
`tools.unequip_trap_text` owns only ROM literals `[00027BDC,00027BE0)`,
`[00027CA8,00027CAC)` and `[00027CDC,00027CE0)`, each expecting08140D68,
plus a private654-pointer copy replacing slots2F4/2EC/318/438. Direct streams
use at most146px; no new RAM/save storage or formatter is introduced.

Evidence: `build/text-next/trap-message-consumers.txt` and
`build/unequip-trap-prototype/{report,preview}.json`, prototype SHA
`9338c6f2362c6d9ae7cd2dcd5bd09d05cbf1ef879a51a1f1fbbecd0778d5c680`.
Four cases pass205 glyph checks. Native inventory records remain120bytes at
RAM0200DF28; present bit80000000 and equipped bit00800000 select removal.
The native mask atROM00027C60 isFF7FFFFF. In the activated fixture, native
slot2/item30 loses only its equipped bit, and0800BA70 recomputes equipment.
Failed activation and the no-equipment branch preserve all inventory bytes.
The latter shows slot438. Original return is08027CDA.

Protection reads bit4 atRAM020081D8 (base literal020081D4 plus4). A protected
case records an override immediately before CPU08027BA6, then executes the
native branch and failed-activation message. Setting this flag earlier was
insufficient because preceding native turn logic refreshes gear flags. This
is a controlled protection test, not ordinary equipment acquisition. Caller
and queue registers/stack, HP/gold/battery and exact expected inventory pass.
Ordinary trap discovery and protection acquisition remain separate. The four
bindings are outside the2,133 candidate and current source-review inventory.


### Mud-trap consumer prototype (2026-09-24)

CPU `[08027DCC,08027EC4)` owns the handler and literals.
`tools.mud_trap_text` replaces ROM literals `[00027E04,00027E08)`,
`[00027EA4,00027EA8)` and `[00027EC0,00027EC4)`, each expecting08140D68,
with a private654-pointer table replacing only slots2F4/2EC/320/324/328.
All five streams are plain direct notices, at most146px, with no new RAM/save
allocation or formatter. Original shared sources and other consumers remain.

Evidence: `build/text-next/trap-message-consumers.txt`,
`mud-item-updates.txt`, and `build/mud-trap-prototype/{report,preview}.json`.
Prototype SHA`91a40d7846ccd015b22132eff8c4e6ec3f59533d0c8dcba25886d1258abc6295`
passes ten native cases/510 glyph checks. Controlled entry/activation and
first-slot IDs203..210 exercise all eight bread types, plus failure/no-bread.
Native comparisons select IDs203/204/206/207/208/210;205(Rotten bread) and
209(Golden bread) are unchanged. Affected records become205 through08004B08;
0800F8AC sets identification bit08000000 in the record and40000000 in the
existing205 type record at02003BAC+205*20. All other inventory bytes remain
identical. Failure skips mud/effects; harmless activation shows328.
Queue/caller registers/stack, complete one-line messages, HP/gold/battery pass.
Return is08027EBE. Ordinary trap discovery, acquisition and other inventory
arrangements remain separate. Five bindings remain outside2,133/inventory.


### Poison-arrow and falling-rock trap prototypes (2026-09-24)

CPU `[080276F0,080277E8)` and `[080277E8,08027990)` hold these handlers
and their literals. `tools.damage_trap_text` owns ROM literals
`[00027734,00027738)`, `[000277E4,000277E8)` and `[00027828,0002782C)`,
each expecting08140D68. Its private654-pointer copy replaces only
2F4/2EC/2F8/30C. Original shared tables and status/damage helpers remain
unchanged. No new RAM/save storage is introduced.

Evidence: `build/text-next/trap-message-consumers.txt`,
`native-trap-damage.txt`, `damage-traps/report.json` (queue discovery), and
`build/damage-traps-prototype/{report,preview}.json`. Prototype SHA
`b06b754c568aa70af4c1f4b1fc2e4b54d229632a0cd17384f4db6a64cf7f740a`
passes12 native cases/714 glyph checks: both handlers, activation/refusal and
three player-name bounds. Native arrow dispatch calls0800B240(actor,1,1),
reducing existing current-strength halfword actor+76 from8 to7 in this
unprotected fixture. Both active handlers call08011DA4(5,cause,0,1),
reducing HP at actor+84 from29 to24; failure preserves both fields.

Existing native damage consumer at CPU08011DA4 uses256-byte output
`[SP,SP+100)` plus28 saved bytes. Its existing combat slot1C4 formatter call
returns08011E06 and queue returns08011E0E. Poison's separately owned
condition slotDCh formats at0800B356 and queues at0800B35E in its original
256-byte output. Tests check exact native name/value arguments, formatted
streams/guards and complete notice/strength/damage chains; all fit one line.
Whole trap returns080277D8/0802797A preserve caller registers/stack.
Items/gold/battery remain intact. Ordinary discovery, resistance and
death/revival branches remain separate. Four bindings are outside2,133.


### Acid/rust follow-up discovery, not inserted (2026-09-24)

Evidence: `build/text-next/acid-trap/report.json`,
`trap-message-consumers.txt`, `rust-equipment.txt` and
`rust-item-formatters.txt`. A controlled call to CPU08027990 produces the
switch notice, acid notice(slot300), then a still-Japanese rust-resistance
format around the already-English Leather shield+1. HP/current strength remain
29/8. This is discovery only, not an English acid-trap acceptance.

Acid's table literal is ROM `[000279C8,000279CC)` (08140D68). The handler
calls08010EE4 with mode1 and returns08027A08. The selector uses native
equipped-item getters; mode1 chooses shield,2 sword,3 evaluates both.
Shield rust consumer at08010F98 has320 bytes of locals:64-byte item field
`[SP,SP+40)` and256-byte output `[SP+40,SP+140)`, plus12 saved bytes.
Its item-name call0800EEF0 returns08010FE4, formatter returns08010FF6, and
formatted queue returns08011014. Source slot43C is one native%s item field,
including the native colour controls; future English must preserve them and
check widest item substitutions and buffer capacity.

Native shield IDs30/33 have the named no-rust branch; other protection uses
slot304. Shield/sword degradation uses slots280/284 and stops reducing an enhancement
already at signed byte-99 in record+4. Ring ID90 selects slot27C. Empty branches use8E4/8E8,
and mode3 without either item uses288. Identified original shared-table
literals are ROM offsets10F68,10FAC,10FFC,11018,11038,1106C,11080,110A8,
110C8,110F8 (each four bytes, expected08140D68); these are audited reference
leads, not allocated patch ownership. The original table, consumers and all
these source bytes remain unchanged. Native resistance/acquisition, degraded
item outcomes and full menu/name budgets still need their own insertion tests.


### Acid/rust English prototype (2026-09-24; supersedes discovery-only status)

`tools.rust_text` now gives explicit ownership to the eleven four-byte literal
references listed above, plus a private654-pointer copy and eleven source
bindings. It reuses `add_reviewed_actions` for source/printf validation,64-byte
item limits and the existing conditional break. That compiler's conservative
192-byte limit is retained as a compile budget; the actual named shield
formatter output remains256 bytes at `[SP+40,SP+140)`. No stack or window
change is introduced. Named text needs at most99 formatted bytes, with
worst-case fallback lines184/58px; ordinary Leather shield+3 uses one164px line.

Prototype SHA`81ba695a5c365e5d5d0342cd43aa37ad600e2684cd99b1d7666e4996a6fad4e3`
passes19 native cases/582 glyph checks in `build/rust-prototype/report.json`.
Cases cover acid activation/failure, native shield and weapon degradation,
no equipment in all three selector modes, Leather/Silver shield protection,
controlled protection/ring getter returns, enhancement already at-99 and three
64-byte item-field stress forms. The maximum-width field uses two lines;
The full64-byte item-field case reaches the99-byte formatted bound and stays
on one179px line; the coloured field also remains one line. Exact item/format bytes,
colour glyphs, guards, caller/queue state, HP/gold/battery pass.

Item-definition record properties at ROM00141B9C+id*24+4 must be retained in
controlled equipped records. The original Leather shield carries property3;
Silver shield carries1, while the checked Bronze shield and weapon1 carry0.
Native0800A24C tests mask00000001 in the item flags for rust protection, then existing
gear flag100hex. Merely changing an item ID in a blank record does not recreate
its native material protection. Test records use these original definition
properties plusC8800000 present/known/equipped bits, never inscription00400000.
They use enhancement+3 (distinct from the original research fixture's+1).

Ring/protection tests explicitly override getter return values at their owned
read sites; ordinary protection acquisition and other inventories/modes remain
separate. These eleven bindings are still outside the2,133 candidate/inventory.
Source/Japanese, English, bounds and native screenshots are in the rust gallery.

### Remaining trap consumer discovery (2026-09-24)

Evidence: `build/text-next/trap-message-consumers.txt`,
`trap-summon-spawner.txt`, and `remaining-traps/{report.json,*/*.png}`.
The eight discovery cases use ROM SHA
`f00ffbad98c02fd29e0151e77db9dbb200d3ce242769d4d8c14284a2372d6a4a`
with the recorded isolated 6F fixture, ordinary attack input and explicit
handler-entry/activation overrides. They are discovery, not accepted English
insertion, normal trap discovery or complete outcome coverage.

- CPU `[08027CE0,08027DCC)` is the summoning handler. ROM literals
  `[00027D18,00027D1C)` and `[00027DC8,00027DCC)` both contain `08140D68`.
  Slots `2F4/2EC/31C/3D4` are switch, activation refusal, summon and no-monsters
  messages. Native `080131BC` receives count4 and player coordinates; in the
  observed active case, the live actor count rises from8 to12. Refusal preserves
  the count. Return is `08027DC6`. Its seven stack arguments include a final
  mode selected by `080069B8`: that getter checks existing RAM dungeon ID
  `02003B6C`, floor `02005674` and flags at `0200160C`. The alternate condition
  is dungeon6/floor27 with flag40 clear; no ordinary arrival there is claimed.
  Spawner count0 is tested at `08013288` and reaches its native zero-result
  branch. It is a possible controlled no-spawn probe, not natural exhaustion.
- CPU `[080283D4,0802848C)` is the pitfall handler. Its shared-table literal
  `[00028434,00028438)` reaches `334/328`. Successful dispatch sets the existing
  halfword `[020037C4,020037C6)` to1 and calls `08006BF8`. The caller subsequently
  queues slot338 through the interior table pointer `081410A0` at ROM
  `[00005468,0000546C)`, read at `08005388`. This is a separate consumer:
  translating the trap's first literal alone would miss its damage message.
  CPU `08005398..080053B2` subtracts5HP after that message and clamps at0.
  Our discovery stop caught the message before damage: HP29 at trap return
  does **not** prove no damage or a completed floor transition.
- CPU `[0802848C,08028518)` is the mine handler. Literal
  `[000284C4,000284C8)` reaches `2F4/2EC/33C`; native explosion call `08012F3C`
  has r3=11. The observed active fixture loses14HP (29 to15) and queues the
  existing English damage format. Death/revival paths remain separate.
- CPU `[08028518,0802866C)` contains the iron-ball handler and its literal pool.
  Shared-table literal `[0002855C,00028560)` reaches `2F4/2EC/340`.
  Native projectile/effect call `08013714` receives r2=5/r3=12 in this fixture;
  HP29 becomes24. Refusal preservesHP. Return is `0802864A`.

All listed storage is existing native state; none is newly allocated or free.
The ordinary triggering turn can move monsters before the per-turn injection
point. Any future summon verifier must compare live actors at actual handler
entry and return, separately retaining the earlier fixture state.


### Summoning-trap English prototype (2026-09-24)

`tools.summon_trap_text` owns the two summoning literals above, each expecting
`08140D68`, and a private 654-entry table for slots2F4/2EC/31C/3D4. Static English
fits216px; no new RAM or native buffer size is required. Prototype SHA
`951382e2599eeac5a7995dc1fdfeb63f91e4db42b9973cd8b5cb36e87a6d9480` passes four complete native cases:
activation, refusal, alternate spawn mode and zero requested monsters.
Both active modes add four monsters using the original spawner; the alternate
mode is selected by an explicit return-value override at08027D40. The no-monster
message uses the native spawner with r0 controlled from4 to0 at080131BC,
then checks its actual zero result at08027DAC. It is not a natural exhaustion
or terrain-rejection test. Existing live actors are compared at actual handler
entry and return, since the ordinary triggering turn moves actors beforehand.
All messages render on one line, with caller/queue ABI and stack guards,
HP/items/gold/battery preserved. Evidence:
`build/summon-trap-prototype/{report,preview}.json` and its gallery.
These four bindings are outside the current2,159 cumulative regression and
source-review inventory. Ordinary trap discovery/progression remain unclaimed.


### Mine and iron-ball English prototype (2026-09-24)

`tools.blast_trap_text` owns the two literals at284C4/2855C described above,
expecting08140D68, and a private654-slot table for2F4/2EC/33C/340. The four
reviewed notices fit one216px line and use the unchanged direct queue reader.
Prototype SHA `eb98b01f503b8cc0bd230bb9be3a1d5c1f1f185556890ff171ce03ec9444f3f4`
passes12 native handler/name/activation cases. The mine dispatches12F3C and
then11DA4, losing14HP from29; the iron ball dispatches13714 then11DA4, losing5HP.
Existing combat slot1C4 supplies the complete numeric acknowledgement in its
original256-byte output. Refusal preservesHP; strength/items/gold/battery,
queue/caller ABI and guards pass. Caller return addresses are28514/2864A.
Evidence: `build/blast-traps-prototype/{report,preview}.json` and its gallery.
Controlled entry/names and healthy fixture outcomes do not establish ordinary
trap discovery, resistance or death/revival. These four bindings remain outside
2,159 cumulative acceptance and the source-review inventory.


### Pitfall English prototype (2026-09-24)

`tools.pitfall_text` owns ROM `[00028434,00028438)` (expected08140D68)
and `[00005468,0000546C)` (expected081410A0). Its private654-pointer table
replaces slots334/328/338 only; the second literal points to private-table+338,
retaining the original interior-pointer lookup. Original shared data remains
unchanged. All three reviewed English messages fit216px on one line.
Prototype SHA `da504a8b5594ac1730fc89c5cc857cd9329121c991bd8ccd73da233d1351b68d`
passes four cases: active, refused, protected and special-floor.
Protection controls the existing flag1000 at its actual read080283FC; the
special-floor case controls the getter return at080283F4. The successful case
continues beyond trap return to the damage message's queue return08005392,
then verifies HP29 to24 at080053B2. It does not stop at the earlier unchangedHP
snapshot. All direct-reader glyphs, caller/queue ABI, stack guards and preserved
items/gold/battery pass. Evidence: `build/pitfall-prototype/{report,preview}.json`.
No new native RAM/frame is introduced. Final next-floor arrival, ordinary
trap discovery/protection acquisition and death/revival remain separately scoped.
These three bindings remain outside the2,159 cumulative regression and source
inventory, alongside the separate summoning and mine/iron-ball prototypes.

### Trap caller and second-person wording audit (2026-09-24)

`build/text-next/trap-caller-references.json` scans original Thumb BL operands
in ROM `[00000000,0005FE00)` and pointer bytes across the base. The two direct
call sites per handler are confirmed by `trap-dispatchers.txt`; raw matches
alone are not treated as ownership or exhaustive runtime coverage.
CPU08026E0C loads the player pointer through literal ROM `[00026ED8,00026EDC)`;
CPU08027410 does the same through `[00027468,0002746C)`. Both literals equal
`02001624`, and both dispatch the loaded player actor to the trap handlers.
This supports the existing player-directed “you/your” notices in these two
callers. Neither caller substitutes an arbitrary monster actor.
The second dispatcher reads the trap kind from the current player's map cell+0A;
its kind0..17 switch is bounded explicitly. This is static caller evidence,
not a claim of ordinary traversal of every trap or proof that no further
indirect/external entry can exist.

### Bear-trap consumer lead (2026-09-24)

`build/text-next/bear-trap-consumer.txt` traces CPU `[080275B8,08027680)`.
ROM `[000275F4,000275F8)` holds08140D68. Slots2DC/2E8 are the trap notice
and successful dodge; the active branch also reads slot978 using offset978
at ROM `[00027674,00027678)`. That additional format says that `{actor}` let
go in shock, and uses the original native fit control0E074E. A translation
must cover this branch as well as the first notice.

The handler has a256-byte output atSP and24 saved bytes. It visits actor
pointer slots1..55 from existing RAM `[02001624,02001704)`. Live actors whose
flags word+8 includes40 are passed to08012050 and0800BA70, then named through
08009ACC and formatted at08027644 (return08027648). The message queue returns
at08027650. After the loop, the player+ A3 byte is set to6 and existing RAM
byte `[02003B8F,02003B90)` is cleared. Caller return is08027670.
These are static disassembly findings. Maximum actor-name expansion, the
shock/release branch, immobilization duration/recovery messages and ordinary
trap discovery remain unvalidated; no English insertion is claimed here.

## Closed static-notice mapping at the owned dialogue queue

The 2,255-resource candidate extends the existing combat-owned queue hook at
CPU `[0801588C,08015894)` / ROM `[0001588C,00015894)` (expected original bytes
`70B5061C00291CD0`). The patch retains the same owner and single allocator claim;
there is no second overlapping entry patch. The helper adds a closed mapping
for85 exact original string pointers from `queue-notices-review.json`, covering87
shared-table slots with identical-source aliases deduplicated. It changes only
saved r0 when a pointer matches, then resumes the previously owned combat
handling and original queue. Other arguments, saved registers and the original
queue-flag branch remain intact. Stack overhead is still the existing36 bytes;
no new persistent RAM/save storage is claimed.

Each message and the85-row `(original pointer, translated pointer)` table are
appended via `RomBuild` under `queue-notices`; exact exclusive allocation ranges
and original source ranges/hashes are in the build ledger and review catalog.
Original shared pointers/strings are preserved. Only complete unformatted
notices without native position/colour/substitution controls are eligible;
output is at most216px and256 bytes including NUL. Menu readers, formatted RAM
copies and other shared consumers are not translated by this mapping.

`build/english/queue-notice-validation/report.json` records176 passing native
cases:85 mappings times two queue flags, plus unmapped Japanese, already-English
and RAM fallbacks times two flags. The debugger redirects a naturally reached
turn callback to the queue with explicitly recorded arguments; the destination
instruction executes without another entry breakpoint, so the check records
that controlled entry separately. Subsequent mapping/output/glyph/return events
are native. Exact one-line bytes, glyph pixels, cursor bounds, caller stack/ABI,
gameplay state during queue execution and save preservation pass. This establishes
the owned reader and bounded mapping; ordinary occurrence and other readers of
these sources remain separate coverage claims.

## Bear-trap named release prototype

CPU `[080275B8,08027680)` retains its native256-byte output plus24-byte saved
frame. ROM `[000275F4,000275F8)` changes only its owned table literal from
`08140D68` to a `RomBuild` private table; slots2DC/2E8/978 receive three appended
English strings. Original shared strings/table remain unchanged. Source hashes
and exact private allocation ranges are in `build/bear-trap-prototype/build.json`.
The978 format keeps `%s` and uses verified conditional control `0E0A49`, with
up to63 bytes in the existing64-byte actor-name scratch and256 output bytes.
The conservative31-wide-letter field uses lines189/85px; the same-byte-count
narrow field remains one181px line.

Native helper CPU `[08012050,080120B4)` clears the holding actor's bit40 and
player byte `+A3` when actor byte `+91` is6/player timer99 or7/player timer98.
The trap then sets the player's byte `+A3` to6. This proves the stored value,
not the number of ordinary turns until recovery. Its release animation uses
CPU `[0800BA70,0800BB1C)` without replacing gameplay logic. ROM field addresses
and CPU disassembly are in `build/text-next/bear-release-functions.txt`.

RAM byte `[02003B8F,02003B90)` is also cleared by the native queue at CPU15930
(watchpoint reports pipelined PC15934), including the evasion branch. It is not
an exclusively trap-owned persistent flag. The active handler separately clears
it at2765E (watchpoint PC27662). Controlled initial value4 and all writes are
recorded, including the explicitly configured debugger write itself.

`build/bear-trap-prototype/report.json` passes seven cases on prototype ROM
`1a7bf352adae1fdcb5faa67ca263f7e39bdaf85bc7bcebb5e530492dfbabede8`:
activation/evasion, native release for both configured grab types, maximum-width,
maximum-byte-count and coloured name fields. The name getter can return a ROM
pointer; stress cases explicitly use the already established64-byte RAM scratch
`[02008D08,02008D48)` and override only that getter result. Ordinary native names
are retained in the two grab-type cases. Queue bytes/pixels, formatter guards,
caller ABI, cleared holding flags, player timer, HP/items/gold/save all pass.
The prototype is separate from the2,255 cumulative build and its inventory.
Ordinary trap/grab acquisition and later recovery turns remain unclaimed.

## Stumbling-trap notice and item-loss prototype

CPU `[08027EC4,080283D4)` retains its original0xEBC-byte local frame and32-byte
saved-register frame. Four ROM literals, `[00027F48,00027F4C)`,
`[00027F88,00027F8C)`, `[00027FB0,00027FB4)` and `[000283B4,000283B8)`,
are checked against `08140D68` then redirected to one `RomBuild` private table.
Only slots32C/330/328/1D0 receive English strings. Original shared table/string
bytes, item dropping and pot-breaking code are preserved. The actual loss
formatter uses `[sp+0xCD8,sp+0xDD8)` for256 output bytes and the existing item
field atsp+0xDD8 (verified64-byte bound). Source identity and exclusive appended
ranges are in `build/stumble-trap-prototype/build.json`.

Native item placement CPU `[08013F20,08013FD4)` returns0 before allocation if
the destination is occupied or the128-record floor-item pool is exhausted.
The prototype selects the latter branch by recording an r6 override to128 at
CPU13F66, before any item is allocated. It does not turn successful placement
into a reported failure after creating a floor item. Ordinary successful dropping
uses native allocation; the floor record's identity/amount matches the carried
record and inventory loses exactly that item. Failed placement also removes the
carried item and creates no floor record, matching the complete loss warning.

Nine cases pass on prototype ROM
`d10969c32ac1e9cd5e4b062a50359f163cbb1d620228ba5aca4593de6cbd850a`:
empty inventory, evasion, configured protection, actual held Surefoot staff,
successful floor drop, controlled allocation exhaustion, and three width/byte/
colour field cases. The normal loss warning uses201px on one line; widest and
maximum-byte fields use189/153px and96/153px fallback lines. Coloured fields use
one178px line. Queue pixels, formatter/caller ABI, guard bytes, HP/gold/save and
native item-loss/drop counts pass. The ordinary loss wording is “hit the ground
and was ruined,” preserving the T2 ground-impact and unusable-item meaning.
Reports, actual schedules and captures are under `build/stumble-trap-prototype/`;
`tools.review_stumble_trap` rebuilds its gallery. Ordinary trap/terrain discovery,
full inventory arrangements and pot-breaking/contents remain separate.

## Exact-copy static notice prototype

The separately assembled queue entry helper compares an unmatched input against
the closed85-source Japanese notice map through the terminating NUL. Exact RAM
copies redirect to the same appended English strings; near matches and unrelated
strings remain unchanged. No caller buffer or persistent RAM is written, and
the original36-byte helper save frame is retained. Default compilation still
uses the previously verified pointer-only lookup pending cumulative integration.
`build/copied-notices-prototype/validation/report.json` passes348 cases on ROM
`aead1c0e7572ba0339ce4c2e102223a07637f3d32acc146ec8e6c08c4784f2d2`:176
existing direct/fallback cases,170 native player-wrapper RAM copies and two
suffixed Japanese near matches. Exact queue bytes, native glyphs, caller-buffer
preservation,256-byte wrapper guards and ABI pass. This expands consumer
coverage of existing translations without adding unique reviewed sources.

## Monster curse prototype

CPU `[0802B918,0802BA38)` retains its256-byte formatter frame. Checked ROM
literals `[0002B968,0002B96C)` and `[0002BA1C,0002BA20)` originally contain
`08140D68`; the private table owns only slots274/270. Source strings and shared
table are preserved. Native curse priority is equipped shield, weapon, ring,
then the first eligible carried item. Exactly one item's04000000 flag changes;
carried-item wording is therefore “An item was cursed!” Native Curseproof ring
lookup checks ID93. Protection/ability return overrides are explicitly recorded.
Thirteen cases pass in `build/curse-prototype/report.json` on ROM
`d7cd341f0c05c0acc8160d897a33d725fd08fab1c2a7ac982c7d0d61b6f3892d`: equipment
priority, carried items, empty/already-cursed inventory, ring/protection/ability
and maximum-width/byte/coloured actor fields. The original64-byte actor scratch
`[02008D08,02008D48)` is reused only in recorded controlled field probes. Native
pixels, formatter bounds, caller ABI, unrelated inventory bytes and HP/gold/save
pass. Ordinary monster AI and other curse consumers remain separate.

## Strength/max-HP and level drain prototypes

CPU `[0802BACC,0802BC4C)` owns the strength/max-HP drain handler, retaining its
256-byte local and24-byte saved-register frames. ROM table literals
`[0002BB44,0002BB48)` and `[0002BC40,0002BC44)` are checked against08140D68
and redirected to a private table changing only258/94C/A18. Native strength
loss updates maximum strength atplayer+78, clamps to1 and clamps current
strength atplayer+76; the numeric message receives the actual decrease. The HP
branch only reduces maximum HP atplayer+86 when it exceeds19, subtracts five
times the argument, clamps to2 and clamps current HP atplayer+84. Existing
player-wrapper results2FC/2BC remain mapped by their owned reader. Random branch
and resistance results are explicitly controlled; actual stat changes execute
natively. Nineteen cases pass on prototype
`d311ae71e9945a0aff088a3cb0679dc9a5d756fbbd1067ef5e7dba5d9e8a5aa9`, including
minimum/clamp/current-low cases and actor/player field boundaries. Normal
messages are one line; widest actor/player cases use conditional wrapping.

CPU `[0802BC4C,0802BCEC)` retains its256-byte local and8-byte saved frame.
ROM literals `[0002BC8C,0002BC90)`, `[0002BCC0,0002BCC4)` and
`[0002BCE8,0002BCEC)` are checked against08140D68 and redirected to a private
table changing904/EC/C8. Player level is the native signed halfword at+88;
transformation state is byte+BF. Native BB1C performs the configured one/two-level
loss and clamps at1; transformed, minimum-level and resistance branches preserve
level. Eighteen cases pass all three player-name bounds, original output guards,
ABI, native single-line pixels and unchanged items/gold/save. The longest
unchanged-level message is212px including the widest Japanese player name.
Reports, schedules, captures and allocation/source hashes are retained under
`build/drain-prototype/` and `build/level-drain-prototype/`. These are controlled
handler tests; ordinary AI, transformations and resistance acquisition are
separate. Neither prototype is yet part of the2,255 cumulative build.

## Gold theft and expanded exact-copy notices

CPU `[0802BCEC,0802BE5C)` retains0x144 local bytes and24 saved-register bytes.
The output is `[sp+4,sp+104)` (256 bytes), with the amount field at
`[sp+104,sp+144)` (64 bytes) and the third printf argument atsp. Checked ROM
table literals `[0002BD38,0002BD3C)`, `[0002BD84,0002BD88)` and
`[0002BE58,0002BE5C)` originally contain08140D68. The private table changes
2B0/2B4/710/714, retaining native thief/victim/amount argument order.
Native code adds four random rolls, caps the stolen amount at99,999,999 and
transfers only available player gold; actor+60 stores the exact amount lost
from player+60. Original immunity/transformation branches transfer none.
Fifteen cases pass on ROM
`85969c4f9cb11c05db97eba5456fee58a484d2325d89c74834c3306c1afdc28c`, including
empty/insufficient/max gold, recorded roll/protection/ability controls, actor
width/byte/colour fields, all player-name bounds and combined widest-player
plus maximum actor fields. Native transfer is conserved; original64/256-byte
guards, ABI, HP/items/save and native queue pixels pass. Ordinary messages
including eight-digit amounts are one line; longest combined fields wrap.
Reports and capture hashes are under `build/steal-gold-prototype/`. Ordinary AI
and later recovery of stolen gold remain separate.

A second isolated queue prototype extends the reviewed map from85 to123 unique
static source pointers, with source aliases retained. All500 direct/copied/flag/
fallback cases pass on ROM
`f8e14f63eefa1da14be99ce6dafdaf5b22ec8aaae1404f3529e52d1625e1a570`. Its
source catalog is `translations/queue-notices-next-review.json`; native evidence
and gallery are under `build/next-notices-prototype/validation/`. Every notice
fits216px on one line. Other text readers remain unchanged; this is queue
coverage, not proof that all uses of a shared source have been translated.

## Visible queue capture and monster-condition prototypes

A direct turn-callback invocation can render message tiles while the message
window is hidden. The generic static-notice probe now opens it through a native
Life herb Drink action, then substitutes only the queue/player-wrapper source
and flag. Native context `[02000000,02000014)` identifies the8,120 screen origin
and two text rows. Actual final-frame pixel comparison establishes16px row pitch
(the13/14/15px alternatives disagree). Later native scroll events shift earlier
glyph positions upward; the checker accounts for that and rejects any authored
glyph that has scrolled off-screen. Two visible lines are the static-notice limit.
Earlier2,255 static queue artifacts prove native glyph preparation and ABI, but
their generic screenshots can be blank and are not visual-display acceptance.

CPU `[0802C14C,0802C1F0)`, `[0802CE0C,0802CE88)` and
`[0802CE88,0802CEC0)` retain their original256-byte formatter frames. Checked
ROM table literals `[0002C1EC,0002C1F0)`, `[0002CE84,0002CE88)` and
`[0002CEBC,0002CEC0)` redirect only these consumers to a private table changing
slots2C4/418/490. Source/shared table bytes remain unchanged.
Player fullness at+54 uses8 fractional bits. Native code subtracts the ROM value20
from08144B06, shifted by8, clamps at0, then helper58C20 displays the ceiling.
Spell sealing preserves an existing player+9E byte or writes20 from08144B38.
Kaclang helperAFE4 preserves actor+9B or writes15 from08144B3A and executes the
original grab-release/status-refresh helpers. These stored values are not yet
claims about ordinary turn durations.
`build/monster-conditions-prototype/report.json` passes27 cases on ROM
`10a7fcb74cddf7faaf19416407142c8769ffa36bc2e882b663fb7e78a54f0c11`: actual
fullness loss/rounding/limits, protected/resistant states, all player-name bounds,
fresh/existing seal and Kaclang states, actor width/byte/colour fields, original
buffer guards, ABI and unchanged HP/items/gold/save. Original resistance/helper
returns are controlled explicitly in the schedules; ordinary AI/acquisition and
status recovery remain separate.

### Results/history raw actor consumers (controlled research, 2026-09-24)

Disassembly `build/text-next/raw-actor-consumers.txt`, `history-menu.txt` and
`history-dispatch.txt` establishes raw ROM pointer table `[00144C38,00144E6C)`
(141 entries, then a zero). Its two aligned literal consumers are results
`001CBBC` and history `00056FEC`. The existing reviewed raw labels differ from
compressed dungeon actors at IDs0 (Someone) and131 (False priest).
Results CPU0801CA84 owns a256-byte format output `[sp+8,sp+108)` inside its
408-byte local frame; history CPU08056E04 owns128 bytes `[sp+4,sp+84)` inside
its148-byte local frame. Shared-table literals ROM001CBA4/00056FE4 read slot654
for `%sにたおされた`; private copied tables can replace only that slot without
changing other readers. Expected pointers are08140D68 (shared) and08144C38(raw).

Controlled native panels on the2,312 ROM are captured in
`build/text-next/{result,history}-panel-original/`. Results uses original
224px window at(8,24), actor line x12,row2:212px remaining. History's body is
224px at(8,72), actor line x0,row1. These are measured native contexts, not
ordinary defeat/progression evidence. Input schedules, overrides, ROM identity
and actual format arguments accompany both panels. The complete proposed
English line's worst reviewed actor name is182px, below both limits.

RAM `[020037CC,020037D0)` supplies results reason/attacker signed halfwords;
reason21 selects monster defeat. History reads28-byte records at02004EFC;
record+17 is reason, +1A attacker, and index lives at02011BDC. This establishes
reader fields only, not save-file ownership. No additional RAM is allocated.
The history caller08058C10 passes02002C44 through08056BC0 to08056E04; that
existing context's bit100 controls mode. The controlled history probe preserves
this parameter and substitutes one observed record in disposable emulation.
History ID0 bypasses the raw table and instead dereferences0815460C, whose
word points to the fixed トルネコ atROM `[0006EB2C,0006EB35)`. It must retain
Torneko, separately from results ID0/Someone. Future insertion owns only its
literal00057008 through a private pointer word; the shared original is preserved.

The follow-up results/history cause prototype copies the same shared table and
replaces only slots `[00000658,000006C8)` except the monster slot000006AC,
plus cause-wrapper000006D4. These are offsets within the table, not ROM addresses.
Native reason IDs0..27 except21 select the27 complete reviewed cause fragments;
results formatter call0801CBDC and history08057022 consume them through their
original256/128-byte outputs. No claims are made about unexplained reason28+
values or their source markers. The longest complete line, “Fell after triggering
a poison-arrow trap.”, is208px within results212px/history224px budgets.
`build/results-causes-prototype/validation/report.json` has336 passing cases,
including54 cause cases with final screenshot pixels, buffer tails/guards and
caller ABI checked. Original window positions/sizes and battery are unchanged.

### Result headings, locations and statistics (isolated prototype)

The optional result UI copy additionally owns four-byte ROM literals001CD3C,
001CDC4,001CE30,001CE8C and001CF5C (exclusive end=start+4); each originally
points to08140D68. They stay within CPU0801CA84's audited result consumer.
22 table resources cover13 destination labels and650/6E0/6E4/6CC/930/934/938/
93C/940: locations, direction, None, score/rank, EXP/strength and trip heading.
The existing reviewed Remi destination wording is reused, including Banker's
Mansion and Cemetery Dungeon. This replaces obsolete source-language column
position commands in the two statistic lines with measured English spacing;
score yellow/restore controls remain intact. No window geometry changes.

`build/results-ui-prototype/ui-validation/report.json` passes42 controlled cases:
all13 dungeon IDs with native result reasons21/32/33 and three numeric/rank
bounds. Rank's64-byte stack output `[sp+150,sp+190)` is separate from the
256-byte main output `[sp+8,sp+108)`. Header has224px; inset body212px.
All observed format bytes, untouched tails/guards, caller registers/SP, score
colour and actual final-screen glyph pixels pass. The invalid negative-input probe uses-32768/-2147483648, whose low bytes
are zero. Native decimal formatting lacks signed-negative support: it skips
the digit loop and emits low-byte+ASCII0, hence0 for these two inputs only.
This is preserved behavior, not a general clamp or legitimate negative values. Authored width/byte reserves remain conservative.
Other result equipment/exit text and ordinary record persistence are separate.

The25-resource equipment follow-up is isolated in
`build/results-ui-equipment-prototype/`. Its642 cases include all75 reviewed
weapon/shield/ring names in eight native formatter states: identified,
unidentified,cursed,maximum enhancement,priced,priced maximum,priced cursed
maximum andability-present. It preserves the native equipment getters and
substitutes an explicit inventory record/known-name flag. Original64-byte item
fields, complete names/markings/enhancements,256-byte result outputs, ABI and
all captured glyph pixels/colours pass. Native price cells begin at relative
x174 and advance6px throughx204, ending210 in the224px panel. Label/name ink
stops before this column in every case; inverse cell background/spacing is
preserved. Body inset6 leaves a204px price-inclusive occupied span. Unpriced
conservative bounds are Weapon207px, Shield201px, Ring192px; full row budgets
include the204px price span for each. Custom names/inscriptions and natural
record persistence remain outside this controlled cohort.

Result glyph tiles use palette bank15, identified by their actual tilemap
entries, not palette bank0. Final screenshots are compared against the final
bank15 palette (after native fade), including score yellow, item red/white and
inverse price green. The initial renderer palette may still be black during
fade and is not evidence of the displayed colour.

### High-score record writer and remaining literal labels

CPU080066E4's disassembly in `build/text-next/history-record-writers.txt`
confirms50 records of28 bytes in RAM `[02004EFC,02005474)`. Fields are score+00,
gold+04, EXP+08, frame count+0C, maxHP+10 (u16 stored, s16 displayed), adventure
count+12 (from02003B44), floor+14, dungeon+16, result reason+17, maxstrength+18,
level+19, attacker/exit-method discriminator+1A and vocation+1B. The latter
strength/level values are truncated to one byte by the original writer.
These supersede speculative “level/maxHP” readings of offsets10/12: the writer
and Japanese labels establish maxHP/adventure count. No save-file offsets are
inferred. Score is clamped to99,999,999; this does not bound every other stored
field. Time formatting divides frames by216000 for hours and3600 modulo60 for
minutes. Native negative decimal conversion lacks a sign path; prior invalid
low-byte-zero probes are not general clamp semantics.

`tools.history_text` owns only four-byte ROM literals56E80/56F5C/56F68/56F6C/
56F70/56FE0/571B8/571BC/571C4 (ends=start+4), all inside CPU08056E04.
Their expected original pointers/source bytes are pinned in
`translations/history-review.json`. English keeps the144px empty-message
window,56px High score heading,224px summary with72/108/44px columns, and224px
five-row body. The native128-byte output `[sp+4,sp+84)` and record data remain
unchanged. Labels remain white and values cyan; score/rank/floor, EXP/gold,
trip count and hour/minute meanings and argument order are preserved.

The combined prototype `build/history-ui-prototype/` adds these nine resources
to the33 result UI resources. All54 history cases pass original buffers/guards,
ABI, byte/glyph/colour checks and actual final-screen pixels. They include
all13 dungeon locations, completion/escape/wind/priest/give-up reasons, all
three escape-method discriminators, maximum stored display fields, hour/minute
boundary, rank50, no records and native DOWN/UP navigation. Controlled records
and index overrides are recorded; ordinary score saving/loading remains separate.
Additional private history-table literals570A4/571B4 use the same owned result
copy for exit outcomes; original shared source tables are not modified.

### Records parent menu and password notice

`tools.history_menu_text` owns ROM literals `[00056CA0,00056CA4)` and
`[00056D54,00056D58)` inside CPU08056BC0, with exact original pointer/source
bytes checked. Both original64px menus retain58px text budgets and2/3 rows.
Flag40000000 at existing RAM02002C48 selects the Password option. Child entries
are08056E04 Scores,0805734C Records and0805791C Password. Parent return is
08056DFC bx r1. Nine controlled native cases verify full glyph pixels, cursor
wrap, child dispatch, cancellation and repeated reopening with preserved
selection, caller guards/ABI and battery. Separate folder
`history-menu-validation` avoids the existing early-menu report namespace.

Password header and full notice own only ROM `[00057A44,00057A48)` and
`[00057A48,00057A4C)`. Original sources are `[0006E4E8,0006E4F3)` and
`[00154610,001547B9)`; the latter contains the complete16-line historical
promotion. The English notice hasfive editorial pages in the original224px,
four-row window; line widths are at most216px. Header is64px with58px reserve;
code window remains128px. Native page waits are CPU080023A0; caption completion
is08057A24 and final return08057A8E. Allfive pages are required evidence.

Nine-kana generated password data is retained, not translated. Literal57A3C
points to the original centered nine-%s format,57A40 to alphabet08154494.
The format uses permutation0,5,1,6,2,7,3,8,4 of native generator08057A94's output.
Native local32-byte output `[sp+1C,sp+3C)` emits20bytes including center andNUL;
unchanged tail/seed guard and caller ABI are checked. The existing context
02002C44 has trip field+0C and level/depth byte+0E; flag+04 and existing frame
counter02002C30 contribute to the code. Controlled boundary inputs are recorded;
no new RAM/save allocation or ordinary unlock/promotion claim is made.
`build/password-prototype/password-validation/` passesfour cases and a complete
hash-pinned gallery, including A/B closing and unchanged battery.

### Adventure-record row/rank prototype ownership

CPU0805734C creates224px windows withtwo summary rows andsix achievement rows.
It owns128-byte output `[sp,sp+80)` followed by the256-byte status array in its
384-byte local frame. Native RIGHT/LEFT select eight six-row pages; each row is
one line. CPU08057674 selects48 formats from original ROM table
`[00154520,001545E0)`. All19 aligned table references are private literals in
that formatter:57754/57770/57788/577A0/577B8/577D0/577EC/57804/57814/57824/
57834/57844/57854/57864/57884/57894/578A4/578BC/578D8, ends=start+4.
The11-rank pointer table `[001545E0,0015460C)` has owned literals57450/574FC.
Original table bytes remain unchanged; private copies use checked RomBuild
allocations. Header/time/unknown-row literals5744C/574F8/57500/575D0 and trip
unit literal57758 are separately owned four-byte patches.

The firsteight statistics receive the native right-aligned field produced by
CPU08057628 at existing RAM02011BE0. Its06 pixel-X control is224 minus measured
field width. No RAM capacity is inferred or expanded. The 回 suffix is expressed
by the English Adventures label, leaving an empty private suffix; native output
only shrinks. Gold's original G maps to native8266, already covered by the
selected compact numeric alias. Each label retains at least6px separation from
the widest10-digit/G field. Other rows and complete rank/header formats are
checked against224px and128bytes. Hidden/grey/white state flags and all record
values remain native; controlled record scenarios are separate from ordinary
achievement acquisition and persistence.

### Actual walking pickup validation (September26)

On candidate ROM `bb45e403ac90272571d925f204af3535fa3187b61807bcf7c34371bde8eebb61`,
ordinary Drop then directional step-away/return reaches CPU080249DC from
080324C6, then CPU08024AD8 from08024ACC. These are observed native calls,
without PC/register redirects. The ordinary item case has no controlled state
changes. Gold123,5 arrows merging into10,and full20-slot inventory cases change
only the recorded existing floor/inventory fields. All five cases pass exact
formatter bytes,192/256-byte message guards,separate64-byte item fields,
native dispatch and final visible coloured glyph pixels. Inventory/gold/arrow
outcomes and unchanged battery are checked.

The standing case sets existing transient byte `[0200567D,0200567E)` to1 at
the actual walk callback. Movement refreshes this field, so setting it before
movement is insufficient. This is explicitly a controlled branch test, not
proof of the normal button/option that enables standing. Other four cases use
the unmodified walk callback. No ROM changes or new memory ownership follow
from this verifier. Evidence: `build/english/walking-pickup-validation/report.json`
and its hash-pinned gallery; original source and input schedules are retained.

### Dungeon priest private prototype ownership

CPU ROM root `[0801AAFC,0801AE18)` dispatches four services at0801AE18,
0801AF20,0801B0D4 and0801B1F0. Their original256-byte formatting outputs are
`[SP+4,SP+104)` within0x104-byte local frames; root has0x9C local bytes,
including its original120-byte bread temporary. No stack,RAM or save expansion
is made. The native menu reader08015E68 reads its ROM stream directly.

Owned four-byte shared-table literals start at original ROM offsets1AB8C,
1AC30,1ADBC,1AE08,1AE94,1AF90,1B154,1B278,2467C,246B0,246F0; each exclusive
end is start+4. `tools.priest_text` gives these consumers a checked private
copy of `[00140D68,001417A0)`. It changes only25 reviewed slots listed in
`translations/priest-review.json`; all other copied pointers retain original
values. Root companion literal1AB3C remains original pending its separate audit.

Native menu creation is(1,3,23,4),screen x8/y24,width184,four rows. Label
start12 and price start128 leave108 usable label pixels plus8px separation.
The English uses explicit X controls instead of Japanese space/tab counts;
all labels fit the original geometry. The unchanged signed-halfword costs in
ROM `[00144B24,00144B2C)` are return50,healing300,poison500,curse1200.
The following halfword `[00144B2C,00144B2E)` is the40% random gift threshold.

Observed native transactions clear cursed flag04000000 only on occupied,
equipped inventory records (80000000 and00800000),restore current strength
at actor+76 to maximum+78,and restore HP or add2 max HP when already full.
Ordinary player max HP is capped at500 by0800DE88; a separate equipped item
can alter that cap and is not claimed by the cap500 probe. Return charges50G
then invokes08036CAC with reason35. Per-service flags prevent a second paid
blessing in the same conversation. No changes to these mechanics are patched.

Prototype35 paged/name/numeric-bound cases and17 native menu/transaction cases
pass. Every captured glyph and its colour is checked on the final screen,
along with original geometry,cursor wrap,menu reopening,formatter tails/guards,
caller registers/SP,payments and recorded outcomes. Transaction tests explicitly
set an existing dungeon actor to priest and prepare existing inventory/player
fields; they force the independent gift RNG result to99 when reached. They
do not claim a natural priest encounter,random gift acquisition or a completed
surface transition. Both gifts' texts are covered by paged preflight.
Evidence: `build/priest-prototype/{priest,priest-service}-validation/report.json`.

### Throw consumer and monster announcements (September 26)

The native Throw handler occupies CPU ROM `[080259FC,080263EE)`. Its 0x234-byte
local frame contains the unchanged output `[SP+10,SP+110)` (256 bytes), item
copy `[SP+110,SP+188)` (120 bytes) and name field `[SP+188,SP+1C8)` (64 bytes).
The region beginning at SP+1C8 is other native state, not an additional name
buffer. Actor-name arguments come from the native name helper, which can return
an immutable ROM name or its existing 64-byte scratch at 02008D08.

`tools.projectile_text` owns six four-byte ROM literals: 25A58,25A90,25B10,
260E0,263F0 point to the shared-table base; 25FEC points inside it at +1D4.
Each exclusive end is start+4. Their private copy changes only slots 80,1C8,
1D4,1EC,2D0. The original table `[00140D68,001417A0)` and source code remain
unchanged. Item/actor bounds are respectively 162/186 pixels and 64 bytes;
formatted output is at most 142 bytes. Conditional joining uses the existing
215-pixel limit; complete fallback lines fit 216 pixels.

Twenty prototype cases pass final pixels/colours, field preservation, output
tails/guards and full caller ABI. Native Throw of a controlled equipped/cursed
item reaches the refusal branch. The other messages use explicit formatter
arguments there and do not establish natural hit/landing branches. Ordinary
Big bread Throw in the recorded fixture lands silently; visibility-dependent
announcement conditions remain separate. Evidence:
`build/projectile-prototype/projectile-validation/report.json` and
`build/text-next/throw-consumer.txt`.

Monster special-action announcements are selected in CPU ROM
`[0802A998,0802AB82)`, with unchanged output `[SP,SP+100)` (256 bytes).
The signed halfword at +20 in each original 28-byte monster definition is a
shared-table index. All 141 definitions yield 45 nonzero actor selectors and
24 distinct source slots. The compiler rechecks this exact selector set from
the original compressed resource `[00477700,0047CE7D)` before insertion.
Only literal `[0002AA54,0002AA58)` is redirected to the private table; the
resource, ability code and other table consumers are untouched by this module.

Native formatter call/return are 0802A9EC/0802A9F0; queue call is 0802A9F4.
All 45 selectors plus 72 maximum-width/maximum-byte/colour cases pass. Tests
dispatch an existing actor into the native function after opening a message
window, then explicitly skip the ability body at 0802A9F8 to the 0802AB76
epilogue. They establish selection, formatting, visible rendering and caller
preservation, not natural encounters or ability outcomes. Maximum fields are
placed in the helper's existing scratch; ordinary immutable ROM names are
never overwritten. Evidence:
`build/monster-announcement-prototype/monster-announcement-validation/report.json`.

### Baker companion floor conversations

Within the priest root `[0801AAFC,0801AE18)`, actor byte +91 equal to 86 hex
selects the baker branch. Literal `[0001AB3C,0001AB40)` is owned solely by this
branch; it is separate from the priest service literals. Native signed dungeon
floor `[02005674,02005676)` plus constant 1DF selects a shared-table index,
so floors 1 through 6 select slots 780,784,788,78C,790,794. The compiler checks
the existing floor pointer/constant at ROM `[0001AB40,0001AB48)`.

The private table changes only these six direct-ROM dialogue pointers. Other
floor values retain their original pointer cells; their reachability is not
assumed. Native reader 08015A18 is called from 0801AB82, with its original
224-pixel window and 216-pixel prose budget. No formatting buffer is enlarged.
Six controlled actor/floor cases use the unchanged selector, with no source
pointer substitution, and check every page's final glyph pixels/colours,
caller ABI/guard and unchanged inventory/gold/battery. Natural recruitment and
quest progression remain separate. Evidence:
`build/companion-prototype/companion-validation/report.json`.

### Recovery and warp formatter follow-up

`tools.recovery_text` privately replaces slots 120,124,210 for four owned
four-byte literals, ROM starts 13E30,13EB0,40E30,122EC (exclusive ends +4).
General recovery `[08013D90,08013EAE)` has 0x108 local bytes, with output
`[SP,SP+100)` followed by two saved native pointers. Skill recovery
`[08040DB8,08040E30)` and warp `[08012220,080122EA)` each retain their original
0x100-byte output. Shared table, code, scalar HP updates and all other literals
remain unchanged. Actor fields are bounded at 186 pixels/64 bytes. Integer
reserves conservatively allow 11 glyphs, although the native decimal formatter
does not support signed negative output; valid HP amounts are nonnegative.

Nineteen prototype cases cover every caller, real HP/max-HP arithmetic and
explicit zero/2147483647 formatter substitutions, name bounds, colour, output
guards and full caller preservation. The controlled skill context skips only
sprite animation helper 0803F354 (return 08040DD0); its initialization is absent
from this Drink-based harness. Warp skips movement/animation after its genuine
message return at 08012268 to the native 080122E2 epilogue. These exclusions
are in the report and input/override schedules; natural skill activation and
teleport destinations are not claimed. Evidence:
`build/recovery-prototype/recovery-validation/report.json`.

### Controls help modes and wounded-soldier objects

Option/Controls selector table is original ROM `[0006B736,0006B776)`: four
groups of eight signed-halfword shared-text indices. CPU0801A794 chooses group
0/1/2 from the existing player vocation byte +90, or group3 when its town-mode
argument is nonzero. Its existing private UI table literal1A9F0 covers all four
groups. Seven additional reviewed bindings complete warrior/mage/town help,
including the separate town Run slot9A4. The unchanged help window is224px,
eight rows, x8/y24. Every row fits216px; no formatting output expands.
All four controlled mode cases pass native selection/order, every final glyph
pixel, twice closing/reopening and caller/battery preservation. Ordinary class
unlocking and town-mode entry remain separate.

The A-action dispatcher `[08023C14,080243BC)` scans56 existing 68-byte world
object records at EWRAM `[0200D048,0200DF28)`. Type word+00 equal to2 and tile
bytes+3E/+3F matching the facing tile select soldier dialogue. Unsigned byte+40
is added to200 hex and multiplied by4, yielding slots800 through818 for the
seven reviewed selectors0..6. Only shared-table literal `[00024378,0002437C)`
is redirected. Other selectors remain original, with reachability unclaimed.
The paged reader is called at08024370 and the full dispatcher returns at
080243BA. No new world-object, stack, RAM or save storage is allocated.

Nine native A-input cases temporarily set the first existing object record at
08023E2C, then restore all its original bytes at0802434E, immediately after the
selector load. No PC/register/source-pointer redirect is used. Seven passages
and three player-name variants for the addressed-name passage pass all pages,
final glyph pixels/colours, full caller guard/ABI and unchanged inventory/gold/
battery. Natural wounded-soldier placement and quest progression remain separate.
Evidence: `build/soldier-prototype/soldier-validation/report.json`.

### Spell definitions, Info and selection menus

Original ROM `[00146DF4,001470D0)` contains 61 spell records of 12 bytes.
The corresponding 61 description pointers occupy `[001470D0,001471C4)`.
Name pointer is +0, signed HP cost +4, target kind +6 and menu order +8.
Both enumeration loops at CPU080222BA and CPU080222EC stop after index60;
order99 records are skipped by these loops. This is a bounded menu exclusion,
not proof that those names or descriptions are unused in every consumer.
`tools.extract_spells` checks the loop bounds and all source bytes. This family
adds 121 distinct sources to the inventory, including one shared description.

Item Info owner `[08017A4C,08017EEE)` checks item ID153 at08017B06 and calls
CPU08022828 with the item's signed byte+4 as spell ID. Consequently this item
shows spell Info, not its ordinary item-description pointer. Controlled item
checks must use a valid spell ID0..60; quantity99 is not valid for this field.
The item table still has exactly221 definitions. Its 15 special/reserved rows
are not being classified as naturally obtainable or unused.

Spell Info `[08022828,080228CA)` uses a 0x104-byte local frame, with its256-byte
header output at `[SP+4,SP+104)`. Four-byte literals at ROM228CC,228D0,228D8
(exclusive ends +4) select the shared header/target table, spell definitions
and description table respectively. Only these literals are redirected by
`tools.spell_text`; all scalar costs/target IDs and source tables are preserved.
Header arguments remain name, signed cost, target. Native costs are nonnegative.
Original Info window is x8/y32,224px wide and six rows; header row0 and body
row1 use216px. Descriptions use at most four body rows, including a98px reserve
for the seven-character player substitution. Evidence:
`build/text-next/{item-info-owner,spell-description,spell-menus}.txt` and
`build/spell-info-prototype/spell-info-validation/report.json`.

All61 Info selectors plus three explicit player-name variants pass:64 cases,
with two ordinary Info openings per case. Tests set an existing item153 record
and then use normal inventory buttons, without PC/register dispatch overrides.
Native source selection, exact costs/targets, complete glyph sequences, final
coloured pixels,256-byte header guards, caller preservation and unchanged
battery pass. Casting, acquisition and other text consumers remain separate.

Selection root `[08022280,080224D6)` uses existing learned bytes at EWRAM
`[02004D80,02004DBD)` and equipped spell byte `[02004E7A,02004E7B)`.
The list producer `[080224D8,0802267E)` keeps its64-byte output at
`[SP+8,SP+48)` and eight-byte marker scratch at `[SP+48,SP+50)`, in the
original0x6C-byte local frame. Its order lookup searches up to128 entries,
although there are only61 spell definitions. The menu prototype therefore
copies the exact original read window `[00146DF4,001473F4)` and replaces only
name pointers in records0..60. The copied tail is not reclassified as spell
records or free space. Private literals225C8/22600 own this lookup.

The spell list uses its original168px window; marker plus text reserve is156px.
Its action menu `[08022690,080227E0)` has256-byte output and original40px,
three-row geometry with34px labels after its native six-pixel inset. Private shared-table literals225D8,
226DC,22760 and interior literal2261C (base+74C) cover target/marker,
Cast/Set/Unset/Info and Not learned. Native row-format literals225E0,
22604,22620 receive equivalent colour/argument controls with compact brackets
and a three-pixel English word space. Menu validation is ongoing; the Info
checks above do not sign off these separate menu consumers.

### Special spellbook invalid unidentified state

Definition153 at ROM `[001429F4,00142A0C)` retains category0 and alias sentinel
999 at record+10. The controlled native RAM type record at EWRAM
`[020047A0,020047B4)` has that999 in its+4 alias field (verify address arithmetic
from02003BAC+153*20; no new storage is allocated). Clearing its known-name flag
forces the generic unidentified reader0800F650..0800F670 to index999 in a
155-record appearance table. This is an invalid synthetic input, not a supported
appearance; it is excluded explicitly from required item row cases. Eight other
row states and all61 spell Info IDs remain required. Evidence:
`build/text-next/spellbook-unknown-trace/trace.json`, source disassembly
`build/text-next/item-formatter.txt`, and source sentinel checks in verify_items.

### Item theft and waiting (isolated candidate)

Native item theft is CPU ROM `[0802BE5C,0802C146)`. Its local150hex frame owns
output `[SP+4,SP+104)` (256bytes), item field `[SP+104,SP+144)` (64bytes), and
locals through SP+150. Only original shared-base literals at ROM2BEA4,2BED4,
2C0EC,2C110,2C148 are redirected to a private copy, changing slots2AC,2B0,
2B8,710,718. Its inventory scan is exactly20 carried120-byte records;
its stolen-item store is16 records, bounded by the original loops. The exact
stolen-store address is pinned by original literal2C0E0 in the verifier. Native
record copy, ownership at actor+50, carried-item removal and refusal outcomes
are checked; the production code and item identities stay original.

The same2AC waiting source has another owned reader in
`[0802A72C,0802A996)`, with local118hex and256-byte output `[SP+8,SP+108)`.
Only literal ROM2A824 is redirected. Visibility/state inputs are controlled for
its four native cases; post-queue native actor cleanup and caller return run.

Twenty-five isolated cases pass under `build/item-theft-prototype/`: theft
success/empty/store-full, resistance/ability/transformation refusals, waiting,
maximum width/byte/colour fields and seven-character player names. Sprite
animations and the successful thief's post-transfer teleport are explicitly
skipped because they close/redraw the message in this controlled context.
Ordinary messages join to one line. Two native conditional controls can yield
three lines for maximum synthetic fields; the native two-row log then scrolls.
Every glyph bitmap is checked while drawn; final-frame pixels cover only the
remaining visible rows, and scrolled glyph counts are recorded. This is not
proof of ordinary AI encounters, teleport destination or recovery of stolen
items. The full compiler/consumer patches remain outside the2,854 root build.

### Skill records and isolated Info/menu readers (2026-09-26)

ROM `[001457EC,001469EC)` contains128 skill records of36bytes, and ROM
`[00146BF4,00146DF4)` contains128 description pointers. Original128-ID loops
at CPU08021A0A/08021A42/08021A7A/08021AB2 corroborate the count. Each record's
name pointer is+0, Hunger cost byte+23, display order+25 and kind+26. The100
menu-eligible records exclude orderF0; that exclusion does not prove unusedness.
`tools/extract_skills.py` pins definitions, descriptions and consumer evidence.

Info CPU `[0802172C,080218E2)` owns an original0x150-byte local frame:
`[SP+4,SP+104)` is256-byte formatted output, `[SP+104,SP+144)` is64-byte
equipment-name scratch, `[SP+144,SP+14C)` is the four-kind index map, and
`[SP+14C,SP+150)` is the footer visibility argument. Kind3 maps to Status.
Its224px/six-row window has a zero-inset header, then a native6px inset for
body/footer (080217B6). The right-margin endpoint remains216px, so body/footer
text has210px, three body rows, and footer row4. These constraints are verified
by native glyph positions and final pixels, not dialogue-window assumptions.

The footer reads48 equipment definitions and the existing assignment bytes
EWRAM `[02004CF0,02004D80)` (48×3). Its no-assignment branch distinguishes IDs
at most76 or115 (weapon) from others (shield). The multiple-assignment branch
originally copies9bytes of Japanese at CPU0802182E. The isolated Info patch
replaces exactly `[0002182E,00021836)` with a Thumb call to the original
strcpy CPU0805CF54 and two NOPs, retaining64-byte scratch and ABI. Complete
English copying is checked at entry/return and through final pixels. Empty
assignment bytes make reserved skill0 match all slots; this original behavior
is reported explicitly rather than declaring the record unreachable.

`tools/skill_text.py` allocates private definition, description, shared-UI and
48-record equipment copies through RomBuild. Only name pointers change in
copied definition records; all cost, ordering and gameplay bytes are preserved.
Info redirects literals2184C/21854/21850/21888/2185C and literal labels21864/
218E4. Original tables and other readers remain untouched. The skill-menu
prototype reuses the owned names and changes only literals in warrior reader
CPU08020F9C, equipment preview0802144C, selection08021974 and row producer
08021C90; their exact sites are declared in `tools/skill_menu_text.py`.

Learned-skill bytes are EWRAM `[02004DFA,02004E7A)`; the following byte is the
independent equipped-spell selector. Controlled menus change only the existing
learned/assignment fields and retain these original bounds. Selection's row
producer has64-byte output `[SP+4,SP+44)` and marker scratch `[SP+44,SP+4C)`
inside its0x74-byte local frame. Equipment preview has256-byte output
`[SP+8,SP+108)` within its0x114-byte frame. Confirmation has256-byte output
`[SP+24,SP+124)` within the0x13C-byte warrior-menu frame. No new RAM/save storage
or original-ROM free-space claim follows from this work.

Evidence: isolated `build/skill-info-prototype/skill-info-validation/report.json`
passes131 cases, every128 ID plus single/multiple/hidden footer states, twice
opened and closed. This is controlled native-rendering coverage; ordinary skill
acquisition, all menu transitions and combat outcomes remain separate. Menu
prototype validation is ongoing. The item-theft stolen-record area is existing
EWRAM `[0200E888,0200F008)` (16×120bytes), selected by original literal2C0E0;
its native transfer/removal checks allocate no additional storage.


## Remaining dungeon effect readers (2026-09-26)

The private `dungeon-leaves` table owns only the sixteen original ROM literals
listed in `tools/dungeon_leaf_text.py`; their original four bytes must point to
ROM00140D68. Thirteen shared source slots are translated in this private copy.
All other slots retain original pointers, including the existing independently
translated queue notices C8,144,1FC,D4. Original shared strings/table and other
callers remain owned by their original readers. Each new resource uses RomBuild
allocation and overlap checks. No original padding or source text is free space.

CPU `[08037D80,08038434)` is the staff effect dispatcher. Its original local
frame0x44 has a64-byte output at `[SP+4,SP+44)`. The full linear disassembly
`build/text-next/staff-effect-frame.txt` contains only SP+0 for an outgoing fifth
argument and SP+4 for the message, besides allocation/release. There are no
incoming stack-argument loads. Checked patches at ROM00037D86/00038428 enlarge
the frame to0x104 and the output to `[SP+4,SP+104)` (256bytes), preserving
existing offsets and all dispatch code. Original bytes91B0/11B0 become C1B0/41B0.
This is stack-local storage, not a new EWRAM/save allocation.

The other readers retain their existing256-byte outputs: upgrade/uncurse
CPU08035074 at SP+4; transformation080352CC, charge/capacity08035370, healing
pot08035B50, full recovery080356E8, speed0803431C/08037760 and defence08037B80
at SP+0. CPU08036EFC uses `[SP+8,SP+108)` for Kaclang and
`[SP+108,SP+208)` for the flame announcement in its0x208 frame. Kaclang guards
in0800BCBC,0800CD38 and0800D694 use `[SP+1C,SP+11C)`. These exclusive ranges
are relative to each function's allocated SP. Item scratch stays separate.

Evidence: `build/dungeon-leaves-prototype/dungeon-leaves-validation/report.json`
and gallery,72 controlled cases across18 caller/branch variants. Checks cover
original format selection, expanded bytes, adjacent guards, field preservation,
native line breaks, colours, visible pixels, caller ABI and battery preservation.
Upgrade amounts, curse removal, transformation, charges/capacity, HP recovery
and defence state are checked directly. All four Kaclang text callers are
exercised. Flame's subsequent damage body is explicitly skipped after native
announcement rendering to retain its pixels; damage outcomes are not claimed.
RNG branch choices, actor activity/Kaclang flags and attack visibility are
recorded controlled inputs. These probes are separate from ordinary encounters.


## Item bonus effects and maximum fullness (2026-09-26 prototypes)

CPU `[080334E0,08033664)` selects an unused effect from seven existing bytes
in EWRAM `[020081E6,020081ED)`. The original RNG result0..6 starts its native
search. Selection sets one byte and changes existing actor flags at+8
(40000000 strength protection,20000000 sleep protection,10000000 hunger
protection,08000000 quiet movement,04000000 identification), or restores HP
at+84 from+86, or increases current/max strength at+76/+78. Source F4/F8/FC/100/
104 joins the existing108/10C mapping only at player wrapper CPU08015848. Its
original256-byte output and player-name bound apply; other shared readers
remain independent. The shared branch call is CPU08033632 (six outcomes),
with identification using08033652. Byte evidence is in
`build/text-next/bonus-effect-dispatch.txt` and the prototype ledgers.

When all seven effect bytes are set, original source8EC is formatted in the
function's existing `[SP,SP+100)` output. Its item-name argument uses a raw
24-byte definition record. `tools/floor_buff_text.py` owns ROM00033548 and
00033550 only, copies the shared table and all221 definitions privately, and
changes only copied name pointers. Original gameplay bytes and the original
item table remain intact. It reports no special effect without denying the
ordinary fullness restoration that runs before the selection. The exact
item dispatch is CPU08032D98; no guessed English item identity is required.

Maximum-fullness source D0 has three owned readers in CPU0803316C,08033908
and08033998, each with `[SP,SP+100)` output. Literals ROM000331F8,00033994 and
00033A10 are redirected by `tools/fullness_text.py`; other shared slots remain
unchanged. Actor+54/+58 are current/max fullness in256ths. Original cap is
200*256; the ordinary food increase reports D0 only below200, while the other
increase path can report200. Decrease clamps to0. Native decimal output is
nonnegative; it does not implement signed negative numbers. Extra formatter
probes cover0 and2147483647 without changing bounded native state.

Evidence:25 native bonus-effect cases and246 common-wrapper cases in
`build/floor-buffs-prototype/`, plus12 fullness cases in
`build/food-effects-prototype/fullness-validation/`. These checks cover exact
selection, full caller/buffer/name/battery preservation, actual HP/strength/
fullness/flag changes and final pixels. Controlled RNG/name/state inputs are
recorded. Ordinary item acquisition and floor-transition expiration remain
separate. Unit checks preserve every scalar in the copied item definitions.


## Additional actor status readers (2026-09-26 prototype)

`tools/status_effect_text.py` owns thirteen original shared-table literals in
nine native routines: sleep08039054/08039860/0803C6FC, confusion080390EC/
080398C0, fake-priest disguise08039700, maximum HP0803947C, level0803953C,
and strength/speed08039158. Each retains `[SP,SP+100)`256-byte output. Nine
source slots are copied privately; all other copied slots and original shared
resources remain unchanged. Exact literal/source pairs are declared in the
module and checked against original bytes. No new RAM/save storage is used.

Controlled native state evidence: actor+97 holds sleep turns6..10 for a
non-player target; existing+ A4 protection prevents sleep. Confusion uses+95
(10..12 turns). Disguise sets+A9 to20 and+BE to0. HP increase adds5 to+86,
leaving current+84 unchanged; actor maximum is900 from0800DE88. Level+88
subtracts1 unless already at1. Strength+76 changes10 to7 in08039158; its
speed-only path uses actor+92 and native0800B120 halves it, setting+8 bit20
when speed becomes0. These findings describe the probed actors/branches.

Evidence:56 cases in `build/status-effects-prototype/status-effect-validation/`
exercise every changed literal, both sleep outcomes through three callers,
both confusion callers, disguise, HP, both level branches, strength and speed.
All actual helpers run, with input overrides recorded. They verify formatter
bytes/guards/ABI, maximum fields, native conditional wrapping, colours, final
pixels and complete caller/battery preservation. The skill sleep helper returns
through r1; the others use r0. Natural encounters and other shared callers
remain separate. Repeated IRQ-resume notifications at glyph preparation are
deduplicated only when their glyph pointer, registers and colour match exactly.

### Spell messages and inscribed spellbooks (September 26)

ROM offsets below are file offsets; CPU addresses add `08000000`.
`spell_message_text.py` privately copies shared table `[140D68,1417A0)` and
redirects only literals `41070`, `411E0`, `3EF3C`, `41B8C`. The five owned
slots are `920` (unlearned), `860` (cast), `86C` (insufficient HP), `848`
(learned), `91C` (forgotten). Spell definition literals `41074`, `411E4`,
`3EF38`, `41B94` reuse the independently owned 61-record copy; all eight
non-pointer bytes of every original 12-byte record remain unchanged.
Original definitions `[146DF4,1470D0)` and all unowned shared slots are intact.

CPU cast `[08040FD0,08041A42)` has a `264`-byte local frame and 256-byte
output `[SP+8,SP+108)`. Learn `[0803EDF8,0803EF2A)` has a `1FC`-byte local
frame with output `[SP,SP+100)`; forget `[08041A58,08041B76)` has the same
local-frame size with output `[SP+4,SP+104)`. No frame changes were required.
Existing EWRAM `[02004D80,02004DBD)` contains 61 learned-spell flags;
`[02004DBD,02004DFA)` receives the matching learned-history flags. Evidence:
original loops and native state changes, not a claim of new storage ownership.
The forgetting routine excludes spell IDs 0, 1 and 22 and checks existing
EWRAM byte `0200883A`; this is not newly allocated storage.

`verify_spell_messages.py` passes 384 native cases: 60 cast, 60 unavailable,
59 insufficient-HP, 49 learnable selectors with three player names, and 58
forgetting selectors. Learning retains control `7E`, forgetting retains `14`.
The full spell names fit; learning uses a conditional break for wide Japanese
player names. Native casts are stopped after HP payment and before individual
spell targeting/effects, explicitly recorded in each case. Learned/history
bytes, actual HP changes, formatter/queue/panel output, 256-byte guards,
caller ABI, native glyphs/final pixels and unchanged battery are checked.
These are controlled routines, not ordinary spell acquisition/progression.

Item153's inscription branch `[0800F2BE,0800F2E4)` now redirects only ROM
literals `F2E8`, `F2EC`, `F2F4` to an owned format, private shared slot `84C`
and the owned spell definitions. It uses a valid signed amount-byte selector
0..60 with inscription bit `00400000`. The separate ordinary-known tests
continue to leave that bit clear. Original non-spell inscription suffix
operation at `F310` is unchanged and remains an open reader.

The category display is `Sp.` (Spell), followed by a three-pixel space and
the full spell name. `Spell: Lightning Storm` failed the actual priced-row
64-byte guard with 67 bytes; `Sp. Lightning Storm` uses 61 bytes in the
same row, with a conservative compiler bound of 63 bytes. Maximum base width
is 97px. Original 168px inventory geometry, 162px usable row, six-digit
price region, normal glyph spacing and action-panel border gap remain intact.
The dedicated test distinguishes inverse-price glyphs from the green spell
name even though they share a foreground colour. It checks all 61 normal and
priced selectors plus longest-name maximum-price and marker stress cases,
full row buffers, name/price separation, final pixels and repeated cancellation.
Other custom names, writing/acquisition and non-spell inscriptions remain open.

### Identification, transformation and decoy readers

`tools.discovery_message_text` copies `[00140D68,001417A0)` privately,
replacing only slots `074`, `1AC`, `230`, `35C`, `7E0`, `95C`, `9C8`.
Owned file-offset literals: `32ECC`, `33BE4`, `40C24`, `33B7C`, `399F4`,
`2C368`, `2A01C`, `2D98C`, `2D9B8`. All original tables, code and unrelated
copied entries remain unchanged; RomBuild checks expected pointer bytes and
shared allocation overlap. No buffer enlargement or new RAM/save allocation.

Native CPU routines and exclusive bounds: identification after item use
`[08032E4C,08032ECC)`, identify-scroll `[08033B10,08033BE2)`, identify-spell
`[08040B7C,08040C24)`, actor transformation `[08039928,080399EA)`, monster
revelation `[08029EB8,0802A01C)`, grabbing `[0802C258,0802C368)`, actor-turn/
decoy timer `[0802D5C8,0802DE7E)`. Ghidra evidence is in
`build/text-next/{identify-leaves,actor-next-leaves,monster-status-names}.txt`.

The first two identification routines have 180hex local frames: old/new item
names `[SP,SP+40)` and `[SP+40,SP+80)`, output `[SP+80,SP+180)`.
The spell reader instead has output `[SP,SP+100)` and old/new names in
`[SP+100,SP+140)` / `[SP+140,SP+180)`. Transformation's140hex frame uses
output `[SP,SP+100)` and original actor name `[SP+100,SP+140)`; the new
name comes from getter09ACC, whose existing scratch is
`[02008D08,02008D48)` (level1 can return an immutable ROM name directly).
Revelation's104hex frame uses `[SP,SP+100)` output. Grabbing's11Chex frame
reserves outgoing arguments `[SP,SP+1C)` then256-byte output. The108hex
actor-turn frame uses256-byte output then two local pointers.

Ten native branches × four field cases pass. Grabbing checks both species
branches, hero+A3 values98/99 and its actor pointer at+C0. Revelation clears
the selected existing species-definition byte+13hex; transformation actually
changes species1→2. Item readers actually set identification flags, and both
decoy branches decrement+A9 to zero and restore the original actor pointer.
Decoy sprite movement is explicitly skipped; other original timer and state
updates run. Selection/RNG overrides and input schedules are recorded.

`Oh!` preserves the source surprise cue while allowing ordinary item discovery
(old alias plus full identified name) to fit one line. The existing two-control
conditional-break path retains full identities at maximum widths; three
synthetic lines can scroll the two-row log. Every glyph is checked during draw,
while final screenshot checks cover remaining visible rows and report the
scrolled glyph count. No ordinary three-line combat claim is made.
The original known-monster branch at29EF8 formats slot910 and jumps directly
to the epilogue without queuing it. That separate source remains untranslated
pending a disposition or a separately bounded consumer; no queue was added.

Final prototype/current3,187 SHA:
`b88c2e4b7d8a2e5a32fabc7ddfca9faaf0ffd3632d552ef8d171416494d6b928`.
All40 cases were transferred only after confirming the integrated ROM is byte
identical to the tested candidate. Prior3,180 spell checks and137-context font
acceptance retain their own hashes; cumulative acceptance is still3,144.

### Staff draining, pulling and waving (September 26)

Audited native CPU readers `[0802F9C4,0802FAB6)`,
`[0803181C,0803191C)` and `[080263F8,080267DE)` use private copies of
shared slots478/470 and3D8/228, respectively. ROM literals2FAB8,31924,
264E8 alone move to the corresponding owned tables. Source disassembly:
`build/text-next/save-and-monster-readers.txt` and `other-item-readers.txt`.
The pull reader's sole SP+0 output grows64→256bytes at ROM
`[31824,31826)`/`[3190E,31910)`; original halfwordsB090/B010 becomeB0C0/B040.
Its complete body has no additional stack locals or incoming stack arguments.
Staff drain retains its original194hex frame: outgoing third field pointer at
SP+0,20 candidate pointers atSP+4..54,256-byte outputSP+54..154 and64-byte
item nameSP+154..194. Actor getter scratch is the existing
EWRAM`[02008D08,02008D48)`; player field remains the existing16-byte name,
14content bytes /98px maximum. No new RAM storage is claimed.

Native checks cover8 cases per family. The staff charge actually decrements,
and pulling updates the player to the original facing-derived destination.
Staff waving retains frame164hex, outputSP+8..108 and nameSP+108..148.
Zero-charge completion runs normally; the announcement case explicitly skips
projectile targeting/effects at264AE→267BA and executes the original charge
update. Ordinary AI encounters and projectile effect outcomes remain separate.
Three-field formatting uses the real fifth argument atSP+0; maximum player
probes never overwrite64bytes into the16-byte name. Glyphs, visible pixels,
conditional wrapping/scrolling, fields, guards, ABI and disposable battery pass.
`build/english/staff-use-validation` is bound to the3,191 development ROM;
monster-interaction evidence from3,189 remains separately hash-bound.

### Non-spell inscription labels (September 26)

CPU`[0800F2F8,0800F328)` previously copied a name then removed six bytes,
matching the Japanese suffix. The selected English names do not share that
suffix length. ROM`[0000F310,0000F312)` changes3806→4600 (SUB r0,6→MOV r0,r0),
keeping the full explicitly compiled effect. The original64-byte field at
SP+4..44 and native44hex local frame stay unchanged.

Private ROM literalsF328/F32C/F330 point to a dedicated221×24-byte definition
copy, the coloured `{kind}: {effect}` format, and a shared-table copy changing
only slot448 (`Blank`). Every original definition's bytes4..24 remain identical;
37 category0 non-spell name pointers use reviewed effects. English category
suffixes ` scroll`, ` scr.` or ` sc.` are removed editorially in the catalog,
not by unchecked runtime subtraction. Special names retain their full labels.
Item153 continues through its separate, previously audited spell branch.
`add_items(reserve_inscription=True)` leavesF328 for this explicit owner, while
ordinary name consumers retain their complete English names. No shared original
text is changed. Owned allocations and all four patches useRomBuild.

All77 native row cases pass on the3,230 development ROM:37 selectors in
normal/priced states and the widest row with six-digit price, equipped marker
and cursed marker. These are explicit controlled inscription states, including
special/reserved category members; ordinary writing eligibility remains separate.
Native field/row guards, exact effect lookup, original windows, final glyph and
inverse-price pixels, two action cancellations/reopenings, caller ABI and
unchanged battery are checked. Maximum base101px in the conservative110px name
region; conservative complete byte bound63/64. Evidence:
`build/english/scroll-item-validation/report.json` and its gallery. This
supersedes the earlier open non-spell suffix operation. Custom names remain open.

### Native scroll/spell writing (September 26)

The complete CPU reader `[08026A30,08026B86)` has an original100hex local
frame, used solely as a256-byte output. Six private shared-table literals
ROM26A64/26ABC/26ADC/26B04/26B50/26B88 supply slots440/444/6E8/854/858/85C.
ROM26AC4 and26B58 reuse the owned item/spell definition copies; all gameplay
fields remain unchanged. Static evidence: `build/text-next/other-item-readers.txt`.

The selected item getter atF6E0 determines the existing item; the command's
byte+6 supplies the writing selector. Blank scroll124 changes to its selected
item ID only when that definition's existing20-byte history record has bit
00400000. Spellbook151 requires the ever-learned byte at
EWRAM`[02004DBD,02004DFA)` indexed by selector-10, then becomes153 with that
spell ID in amount byte+4. These are distinct history conditions, both retained
in English. Attempt bit01000000 and successful inscription bit00400000 keep
native semantics. Invalid name selectors leave the item identity intact.

All102 native checks pass on the3,236 development ROM:37 category0 non-spell
selectors,61 spell selectors and four actual refusal branches. Special/reserved
states are explicitly controlled; this is not a claim that text entry permits
every target. The original getter, identity/flags/amount mutations, full named
messages,256-byte output, native static-copy source and guards, direct-ROM
sources, caller ABI, glyph pixels and unchanged battery are checked. The generic
leaf verifier now accepts explicit native-selector cohorts and audited static
copy/direct-ROM queues, in addition to its earlier format/field checks. Earlier
leaf families are rerun after that verifier extension. English successes use
complete owned ROM names, with measured bounds taken from those exact catalogs.

### Item loss, pot results and direct player notices (September 26)

Private slot1E0 (complete item loss) redirects ROM literalsC468,14338,28864,
3E260,3E81C,3EA80. Slots1D8/34C (pot break/explosion) redirect3891C/38D08.
All eight are source-checked shared-table pointer patches; no original code or
other shared entry changes. Ghidra: `attack-resolution.txt`,
`lost-item-readers.txt`, `other-item-readers.txt` under `build/text-next/`.
Audited native256-byte outputs and separate64-byte name fields, relative toSP:

| CPU function | Local frame | Output | Name |
|---|---:|---:|---:|
| 080287E8 | 140 | 000..100 | 100..140 |
| 0800BCBC | 2A8 | 11C..21C | 21C..25C |
| 08014150 | 140 | 000..100 | 100..140 |
| 0803D894 | 408 | 078..178 | 178..1B8 |
| 0803E278 | 268 | 108..208 | 208..248 |
| 0803E93C | 14C | 000..100 | 100..140 |
| 08038834, both messages | 670 | 01C..11C | 11C..15C |

Numbers in this table are hexadecimal exclusive ranges. The warrior output
pointer is stored atSP+3F0; it points toSP+78, not SP+280. The pot item pointer
is stored atSP+644. All32 native field/colour cases fit one line, including
maximum162px item fields. The skill-item routine runs its assigned-skill gate
and actual item clear at28846. Its subsequent10228 cleanup can compact another
item into the vacated slot; the verifier therefore observes removal at28848.
The other cases deliberately execute original prologue/name/formatter/queue/
epilogue blocks while skipping gameplay conditions and outcomes. The separate
skill name-cache copy to0200FD58 is explicitly skipped; its ownership/capacity
is not established by this test and remains a research lead. This is bounded
rendering/insertion evidence, not full combat/skill/pot acceptance.

The no-staff and full-recovery consumers retain native player control7E:
ROM2FA40 redirects slot47C; ROM3CBD0 redirects9C0. They stream immutable English
ROM directly through1588C, introducing no RAM output. Six native cases cover
Torneko, widest seven-letter English and widest seven-character Japanese names,
empty-inventory preservation, HP/strength restoration and the nine original
status-byte clears. Complete native name expansion, conditional wrapping,
coloured glyph pixels, full caller ABI and unchanged battery pass. Evidence for
both families is regenerated against the3,241 development ROM in
`build/english/item-loss-validation` and `player-notices-validation`.


### Player strengthening notices (native random-effect branches0/1)

Verified ROM `[0x356E8,0x35B50)` owns a `0x108`-byte frame and preserves
R4–R8. Its RNG branches0/1 converge at CPU `0x08035B2C`, load shared slots
`0x368/0x36C` and call the player-only wrapper at `0x08035B30`. The existing
wrapper's exact source-pointer mapping now contains40 entries. No original
shared table, caller frame or gameplay code is changed. Player substitution
uses the existing16-byte name record (14 content bytes,98px bound), and the
wrapper's existing256-byte output. New English segments fit216px; ordinary
Torneko fits one line, while maximum names use the existing conditional break.

Evidence: `build/text-next/item-full-recovery.txt`,
`build/text-next/strengthen-branches.txt`; 12 controlled native handler cases
verify all eligible inventory increments, unchanged unsupported records,
weapon/shield/staff saturation at99, pot saturation at7, both strength fields
at96 and HP against the native `0x0800DE88` result. All three supported name
extremes and ordinary/capped states pass full output, pixel, stack/caller ABI
and battery checks. The full258-case wrapper cohort also passes. The probe
controls the original valid RNG result; natural selection is not claimed.
Generated evidence is pinned to its ROM hash; no new RAM/save storage owned.


### Kerplunk and grabbed movement messages

Original shared slot0x480 has three independently audited readers: ROM
`[0xCD38,0xD694)`, `[0xD694,0xDB84)` and `[0x2FBA4,0x2FCC6)`.
Only literals D1A8/D9DC/2FCC8 redirect to the owned dungeon-leaf copy.
The respective original local frames are0x268/0x160/0x120 bytes, with the
256-byte text output atSP+0x1C. The native actor getter supplies the name.
Evidence: `build/text-next/kerplunk-consumers.txt`; all three callers and
four field extremes pass. Controlled message entry/epilogue skips explicitly
exclude revival, death, damage and map changes from gameplay acceptance.

Grabbed movement reader ROM `[0x2291C,0x22ED2)` owns0x104 local bytes,
with text output `[SP,SP+0x100)`. Exact literal22CD4 reads slot0x360; the
earlier CFG-provenance lead22EBC was imprecise and is not patched. The
existing player-record pointer at+C0 selects the captor. All four name/colour
cases retain the original prologue, name getter, formatter, queue and epilogue;
movement dispatch and grab animation are explicitly skipped in the probe.
Evidence: `build/text-next/grab-reader.txt`. Original shared sources untouched.

### Skill acquisition and attack announcements

ROM `[0x3BE18,0x3BF5E)` owns0x108 local bytes; output
`[SP+4,SP+0x104)` and incoming saved parameter atSP+0x104. The native
acquisition loop scans128 bytes in EWRAM `[02004E7B,02004EFB)`, clears a
pending flag and sets the corresponding existing learned flag in
`[02004DFA,02004E7A)`. These are existing records, not new storage.
Parameter0 suppresses the optional celebration animation; the two actual
panels still execute. The first uses shared slot754 and an indexed skill
name; the second selects7E8/7EC/7F0 from unchanged definition flags.
Only original literals3BF64/3BF70 redirect those message lookups;3BF74
reuses the already-owned128×36-byte skill definition copy, with all non-name
mechanic bytes preserved. The first panel keeps its original two explicit
rows and trailing09 tab: CPU `[080020D6,080020E2)` advances x to the next
32px boundary. Evidence: `build/text-next/control09.txt`, `grab-reader.txt`.

Attack owner ROM `[0x3D894,0x3E254)` owns0x408 local bytes. The two
announcement regions are `[SP+0x80,SP+0x180)` and `[SP+0x2A0,SP+0x3A0)`.
Message literals3DB18/3DC04/3DF9C use slots774/764 (with original literal
addends preserved); name literals3DB20/3DC08/3DFA0 reuse the same definition
copy. Both battle cries, including the finishing-move emphasis, fit one line
with every full skill name (maximum99px). No frame/window changes.
Evidence: `build/text-next/lost-item-readers.txt`; all512 selectors through
four native message blocks pass field/output/stack guards, ABI and pixels.
Those render probes explicitly exclude skill selection and battle outcomes.
All384 skill-acquisition selector/player-name cases execute native flag changes
and both panels, with source routing,09 tab, pixels, ABI and battery checks.
Reports/galleries are hash-bound; natural skill eligibility remains separate.


### Battle totals, damage absorption and Cop Out

The six shared source slots7D0/898/954/958/82C/830 have private ownership
only through original literals C95C/BEBC/33DCC/417DC. They share no changed
source table or original string bytes. Cop Out uses the established skill name
forうけながし. Slots954/958 preserve the distinction between monsters alone
and monsters plus priests;82C preserves total EXP;830 keeps player control7E.

ROM owner `[0xBCBC,0xCC96)` has0x2A8 local bytes; absorption formats into
`[SP+0x1C,SP+0x11C)`, while Cop Out queues immutable ROM directly.
Area-effect owner `[0x33BE8,0x33DC6)` has0x108 local bytes and output
`[SP+4,SP+0x104)`. Spell owner `[0x40FD0,0x41A42)` has0x264 local bytes,
summary output `[SP+0x138,SP+0x238)`, saved old level atSP+0x238 and EXP
atSP+0x23C. Counts select shared954/958 from the original priest-inclusion
flag; XP and level use separate original argument blocks. No frame/code
changes or new RAM/save allocation. Bounds retain186px actor,98px player and
66px decimal reserves. Most messages remain one line; conditional wrapping
is available only where the complete maximum exceeds216px.

Evidence: `build/text-next/numeric-battle-reader.txt`, `spell-summary-reader.txt`
and valid code ranges `[08041730,080417C4)` / `[08041A2C,08041A42)` in
`spell-summary-block.txt` (its first12 bytes begin inside a data pool and are
not code evidence).37 native message preflights cover nine numeric readers
and the direct-ROM announcement, zero/max positive signed32-bit values,
longest names, colours, guards, full caller ABI, final pixels and battery.
They preserve original prologues/epilogues but explicitly skip gameplay
calculations. The generic verifier treats `%d` as a value, never a RAM pointer.


### Staged dungeon-shop panels and save notices

The dungeon shop handler ROM `[0x243C0,0x2461C)` has0x204 local bytes.
Price output is `[SP+4,SP+0x104)`; SP+0 is the existing outgoing fifth
argument. Shared slots41C/424/464 are respectively the item purchase offer,
payment confirmation and half-price counteroffer. Slots420/428 retain reviewed
thank-you and insufficient-gold wording for this independent modal consumer.
Only literals24480/24544/24588/245D4/2461C redirect in the isolated prototype.
Every original instruction and choice flag is retained.16 message-block cases
cover prices17/0/999999/2147483647, original Yes/No options, numeric colour
03/05, exact bytes, final pixels and full stack/caller/modal ABI. The probes
explicitly skip commerce effects; no natural transaction acceptance is claimed.
Evidence: `build/text-next/dungeon-shop-readers.txt`, the staged compiler/review
and `build/dungeon-shop-prototype/dungeon-shop-validation/`. Slot468 and its
caller are still outside this ownership.

Save notices are immutable-ROM sources: slot5C4 via literal14E20 in owner
ROM `[0x14780,0x14E5A)`, and598 via15058 in `[0x14F04,0x151A6)`. Original
frames are0x148 and4 local bytes, with no formatted English output in RAM.
The actual common modal reader15A50 creates a28-tile-wide, two-row window.
The four-line improper-suspension notice therefore retains the native wait
between two pages; it does not create a four-row window. Both source branches
pass original-prologue/epilogue, source, modal/caller ABI and all visible
pixels, without changing gold/battery. Corruption/suspension detection and the
subsequent inventory/gold reset are explicitly skipped in these preflights.
Evidence: `save-and-monster-readers.txt`, `modal-body.txt`, and the isolated
`build/save-notices-prototype/save-notices-validation/` gallery/report.
The staged resources are not part of the frozen3257 cumulative run.

### Staged reference-list consumers

ROM `[0x20760,0x208CC)` is the reference category selector. Its 12-byte local
frame contains up to three existing action indices; labels come from shared
slots9B0/9B4/9B8 through literal207F0. Original window geometry is `(1,3,8,n)`:
64px with a6px cursor inset, leaving58px. "Blank list", "Skill list" and
"Spell list" fit. The source script call at50A38 remains separately audited;
the rendering probe invokes the complete function from a clean native menu
context, not from an inventory panel with incompatible active clipping.

The original row renderers are ROM `[0x20A18,0x20ADA)` (27 scrolls),
`[0x20C40,0x20D16)` (100 menu-ordered skills) and `[0x20E88,0x20F52)`
(50 menu-ordered spells). Each owns a64-byte local output. Their row window
is168px with6px inset /162px text, created by1D00C. The separate40px page
indicator remains atx192, preserving an8px outer-border gap. Its16-byte
output is formatted by1CFBC with unchanged `%2d/%2d`.

Literal20A84 reuses the English221-record item copy;20AFC/20CC8 reuse the
128-record skill copy;20D48/20F08 reuse the61-record spell copy. Only name
pointers differ from the original records. The scroll selector is the original
27-byte table at ROM `[0x148343,0x14835E)`; the history bit00400000 is in
its20-byte definition-state records at EWRAM02003BAC, not in an inventory
item's flags. Skill availability reads `[02004DFA,02004E7A)`; spell history
reads `[02004DBD,02004DFA)`. The latter is distinct from currently learned
spells. These are existing state fields; this work claims no new RAM.

The isolated private text table also owns "Can't write" at9BC via20A80,
and "Not learned" at74C via20D18/20F54. Existing `%s`, grey `%s`, and
colour `%c%s` formats retain their controls. No geometry or frame changes.
All nine staged cases pass: masks1/3/7, all177 names in eligible/locked
cohorts, every page and short final page, cursor wrapping, refusal and twice
opening/cancelling, exact bytes, full caller/formatter ABI, pixels and battery.
Source/ownership evidence: `build/text-next/writing-picker-functions.txt`,
`writing-picker-readers.txt`, `list-menu-parents.txt`, and
`build/reference-lists-prototype/reference-lists-validation/`. This remains
outside the frozen3257 cumulative run until integration.

### Staged priest expiry notice and title save-preview text

Priest slot4E0 is read through ROM14144 in the complete original function
ROM `[0x140AC,0x1413E)`. The handler has16 local bytes, decrements its existing
signed16-bit timer (address loaded at14140), and on expiry scans56 actor
pointers. Active actor flags at+8 lose bit2; the message queues once via14104,
then native12F3C map effects run. Two complete controlled calls, targeting the
player or an existing monster, verify the actual timer/flag changes, original
map calls, queue, full caller ABI, pixels and battery. The isolated private
pointer table contains only the English priest notice; all mechanics remain
original. Evidence: `common-message-helpers.txt` and
`build/priest-warning-prototype/priest-warning-validation/`.

Title owner ROM `[0x14780,0x14E5A)` formats its save preview into
`[SP+0x14,SP+0x114)` (256 bytes). The indexed village-name decode is the
adjacent17-byte `[SP+0x114,SP+0x125)` field, supporting all eight stored
indices; the current input editor's lower limit is separate. Original labels
use slots5C8 (ordinary dungeon), A0C (Well level),5CC (town/completion) and944
(completion). Private literals14978/149B8/14A18/14B28 bind20 preview resources:
three formats, completion,13 dungeon names and three town location names.
The copied table retains the already-owned Name/Village editor substitutions.

Town names are selected by ROM `[0x52B18,0x52B3A)`, through literals52B2C and
52B38 and the three-pointer table `[0x14E6DC,0x14E6E8)`. Selectors0/1/2 are
inside the player's home, outside the old mansion and inside the magic shop;
values above2 retain the original third-label fallback. New exact sources are
ROM `[0x6CF1C,0x6CF26)`, `[0x6CF0C,0x6CF19)` and `[0x6CF00,0x6CF0B)`.
The home label retains native7E rather than baking in the player's name.

Preview window creation remains `(1,13,28,3)`:224px and three rows. The
existing castle sprite occupies the bottom-left of row3. English row3 therefore
uses native control04/14 to reserve20px, leaving196px through the conservative
216px right boundary. This is text positioning; the sprite, background and
window are unchanged. The widest ordinary dungeon line is194px after the
inset; the Well branch's measured label is18px. Every displayed field remains
present, including current/max HP, floor versus Well level and run count.

All56 staged preview cases pass: two unmodified cold save/resume routes plus
18 selector states × three name/numeric profiles. Controls exercise all13
dungeon labels, town0/1/2/fallback3 and completed-game summary, native eight-ID
name decoding, seven-character player substitution, and32767 signed16-bit
positive field bounds. Guard checks cover the following name/local fields,
formatter/caller ABI (caller return only on the two real resume routes), all
three visible rows and exact pixels. Controlled profiles stop at the preview.
Natural later-game progression and artwork remain excluded. Evidence:
`save-and-monster-readers.txt`, `save-preview-location-reader.txt`, and
`build/save-preview-prototype/save-preview-validation/`. These staged builds
remain outside the frozen3257 cumulative run.

### Staged separate town command root

ROM `[0x2068C,0x20760)` supplies the two-command Items/Option root called
at4BF8A with existing context020141AC. Shared slot994 has its own literal206B8.
Its original32px width leaves only26px after the6px cursor; "Items" needs28px
and "Option"31px. The staged width immediate at ROM `[0x2069A,0x2069C)`
changes `0422` to `0522`, giving40px/34px without altering position or height.
The new text reserves6px with two selected-font spaces. No frame grows.

The owner closes this root at20724 before either child: Items at20732 calls
1E490, while Option at20750 calls1A780. Four staged cases verify cancellation,
empty/populated Items, Option, both original selection indices, cursor wrap,
twice opening/closing each child, actual root descriptor closure, restoration,
full caller ABI, final pixels and unchanged inventory/gold/battery. Controlled
native bank invocation supplies the same context; ordinary4BF78 entry remains
separate. Evidence: `writing-picker-readers.txt`,
`reference-list-native-caller.txt`, and
`build/town-root-prototype/town-root-validation/`. The change is not included
in the frozen3257 cumulative run.

Ordinary town-menu follow-up (2026-09-30): on release ROM SHA256
`7716f8c51c452499a1bb651acd24ccd20d3833531188fa66f0732cf3bb8307c8`,
pressing B inside the home/shop at the saved book and outside the bank reaches
CPU `0x0804BF8A` and root `0x0802068C` without register, RAM or PC overrides.
Both observed menus contain only Items/Option in the existing 40px, two-row
window at x8/y24; no location-name banner is drawn. The indoor case also closes
and reopens with B. Reader traces record just the English root stream for each
opening. Evidence: `build/town-menu-location-check/{inside,outside}/report.json`
and `menu.png`; the outside fixture's ordinary input route is in
`build/town-menu-location-check/native/provenance.json`. Reports retain build,
save and input provenance. This confirms ordinary entry in these two saved-game
locations, not every town state, child menu or separate save-preview label.

Custom-item editor research: ROM `[0x18284,0x1851C)` explicitly passes a limit
of8 at18432 to19F3C, displays eight indexed glyphs in its17-byte local field,
and copies10 working bytes to definition-state+9 before setting+8. General
unidentified custom-name display F244 decodes at most eight IDs into its
existing64-byte scratch atSP+4; category labels load viaF58C/F59C/F5B8.
Original forms are category:name and category:name[count]. This establishes
the actual8-character limit, not safe layout in every priced item state.
The original maximum-Japanese-name layout requirement was superseded by the
2026-10-02 user clarification: custom item-name layout acceptance uses English
names, labels, counts and prices; Japanese-name width does not block insertion.
See `TEXT_OPEN_QUESTIONS.md` for current scope. Reader/storage evidence:
`build/text-next/custom-name-editor.txt` and `writing-picker-readers.txt`.

## Integrated save/reference/town consumers (3,291)

The six staged families documented above are now compiled by
`tools.build_english`: dungeon_shop, save_notices, reference_lists,
priest_warning, save_preview and town_root. All34 resources share RomBuild's
allocation/overlap checks. Root ROM SHA `5e33e4556bcca4deae9759aff4574744b1977e997f8906a464c42ef97de7cd91`.
All89 cases pass on this combined ROM; receipts are pinned in
`build/text-next/saved-text-accept-3291.json`, galleries under
`build/english/*-validation/`, and118 unit tests pass. The43 additional font
contexts verify each actual menu/save region, including cursor/sprite/name
reserves. Full cumulative acceptance remains at the archived3,257 milestone.

The128 original skill records select only sword/shield acquisition followups:
85 have neither bare-hand bit nor shield mask;43 have both, and the nonzero
shield mask overrides the bare-hand bit atCPU0803BF00..0803BF0A. The acceptance
check now derives the exact expected explanation per record. This does not
claim native selection of the retained bare-hand message.

## English inscription input prototype (not yet in root build)

`build/writing-input-prototype/`, ROM `a862c329503a5817c50f7379cbe4e0cbd0743223cd66580e915d1d0e61379736`,
adds106 English input names/aliases for the27 original Blank-scroll targets
and50 original spell targets. Original Japanese lookup rows remain byte-exact
in private copies. Source tables are ROM `[001442C8,00144480)` (54rows and
sentinel) and `[00144480,001447A8)` (100rows and sentinel). New English names
reuse reviewed canonical effect/spell names and displayed scroll names; case
folding applies only toF0-prefixed English glyphs. No native eligibility set or
return ID changes. Spell matching still returns ID+10.

Original matchers CPU `[08035458,080354D4)` and `[0803EF48,0803EFC4)` expand
their stack decoding buffers from20 to36bytes and limit to15glyphs/31bytes.
Literals354B8/3EFA8 select private lookup copies. Owned8-byte code sequences
354A4/3EF94 replace only candidate comparison; original target loops remain.
All584 English title/lower/upper/mixed-case, original kana and refusal probes
pass with input guards and complete callee-saved ABI.

Item editor CPU `[08018284,0801851C)` expands its local frame20→36bytes,
using `[SP,SP+31)` for up to15glyphs plusNUL and `[SP+32,SP+36)` for the input
limit. Special item124/151 receives15; ordinary custom names retain8 and
unchanged definition-state10-byte writes. Special input initialization copies
15vacant IDs plusNUL through a new private literal182D8; ordinary copying stays
10bytes. Existing owned EWRAM `[0200CCF4,0200CD04)` remains16bytes. Previous
display copy starts0200CD08 and retains the existing16-byte maximum strcpy.
No new RAM/save storage is used. The special name panel alone becomes
(1,1,28,1),224px; ordinary custom-name panel remains(7,1,15,1),120px.
The shared keyboard stays(1,5,28,7); no adjacent windows overlap.

Owned helper entry patches: ROM182E8 (limit/displaced initialization),18344
(special-only geometry),183A4 (bounded conversion/terminator),18432 (limit
argument),1A2BA (B-delete),354A4/3EF94 (candidate comparison). The shared
B-delete keeps the original8-slot clearing and NULs at8/9 except when its
already-passed limit is15, where it clears through14 and writesNUL at15.
Native kana modifier helpers1A370/1A448/1A520 already honor the input limit.
The unaligned1A2BA trampoline requires a PC-relative literal displacement4;
the first prototype's incorrect displacement was caught by the Back test and
corrected before any main-build integration.

Nine actual Write/Name button cases now pass: complete15-character spell,
long canonical scroll names, a displayed abbreviated scroll name, mixed case,
unknown text, empty B cancellation, ordinary8-character naming and15widest
selectable Japanese glyphs. Full-name Back/replacement, cursor/glyph/final
pixels, editor/lookup ABI, ordinary10-byte custom-name storage, resulting
item/spell identities/inscription flags and battery preservation are checked.
Controlled setup changes item/history/vocation only; editing and matching use
normal buttons. The existing shared-player/village input regression also
passes all69 English characters and its original copy/cursor/guard checks.
This does not settle Japanese category labels in custom-named inventory rows.

## Staged fused-ability loss and talk refusal

Fused ability pointer table ROM `[0x144848,0x1448E8)` has40 pointers, two
kinds of20 bits. Its owned reader literal is `[0x112C4,0x112C8)`. Original
CPU080110FC uses a0x148-byte frame: output `[SP,SP+0x100)`, item-name
scratch `[SP+0x100,SP+0x140)`, kind/result at+140/+144. Message slot3AC
loads through literal112C0. The prototype copies the original shared table
and ability pointer table into distinct RomBuild allocations. Original tables,
frame and selection/removal logic stay intact. Native wrapper112D0 supplies
sword20/FFFFF or shield16/FFFF masks. Tests control an equipped ordinary
weapon/shield, one extra bit and the RNG result0, then execute the full
original scan/removal/flag logic. Four upper shield table labels remain
copied/reviewed without ordinary reachability claims. Sources and byte checks:
`build/text-next/fused_loss_text.py`, `fused-loss-review.json`,
`fused-loss-callers.txt`, `save-and-monster-readers.txt`.

Talk refusal shared slot950 is loaded through the dedicated pointer literal
ROM `[0x23DA8,0x23DAC)`, already pointing at the individual original table
slot. Both native blocks23D4E and23DDE obtain actor0 with09ACC and format
into `[SP+8,SP+0x108)` in the23C14 owner's0x140-byte frame. Formatter
returns23D68/23DF8; modal15A18 returns24374; owner epilogue returns243BA.
The staged patch redirects only that pointer literal to one allocated pointer
and English payload.12 controlled cases enter the original action prologue
and jump after literal initialization to each block. The original getter,
formatter, modal and epilogue execute; full field/output/ABI guards, visible
pixels, inventory/gold and battery checks pass. NPC/gating conditions are
excluded. Source and disassembly: `build/text-next/cannot_talk_text.py`,
`cannot-talk-review.json`, `common-message-helpers.txt`.

## Staged trap-step and two-choice stairs menus

Original17854 calls17768 with shared slot18 and two choices, then writes
command byte+1=20 only for selection0. Literal `[0x1786C,0x17870)` can point
to a private shared-table copy with only18 changed. Helper17768 creates
(8,9,14,1):112px width,6px initial cursor inset. Original04,38 control
positions the second label at52px (legacy coordinate scaling), unchanged
by English insertion. Stairs1787C selects its two-choice variant for mode12
or a successful native059F0 gate. Literal `[0x178F8,0x178FC)` directly
points to source ROM6B590. It creates(8,7,12,2):96px width,90px after
cursor. Original three-choice prompt at178C0 remains independently owned.
Six probes invoke full functions using the ordinary A command pointer, with
recorded dispatch/mode controls. Native command results, ABI, original
geometry, both cursor choices and repeated reopening pass. Subsequent
trap/floor execution is explicitly suppressed after the result is checked.
Evidence: `build/text-next/step-stairs-menu-functions.txt`,
`choice-menu-function.txt`, and `build/step-stairs-prototype/`.

## Staged pot View labels and native inert controls

Original renderer CPU08018CE8..080190DC reserves0xDC bytes. Its row output
is `[SP+8,SP+0x48)` (64bytes), temporary item `[SP+0x48,SP+0xC0)`
(120bytes), original pot pointer at+C0 and signed capacity at+C4. The
168px pot window begins at(8,24); a six-pixel cursor inset precedes ordinary
rows. Recovery/Monster pots157/158 use concealed labels directly via18DE0;
Thief pot161 copies slot20 through18FB8 into the64-byte row field, returning
18FB0. Empty paths use slot24 via18F74/190E0. Four private literal ranges
are `[18DE0,18DE4)`, `[18F74,18F78)`, `[18FB8,18FBC)`, `[190E0,190E4)`.
The two English labels remain in an allocated shared-table copy; no original
frame, selector or item contents change.

Source empty-label controls07/08 are **inert**, not centering commands in
this GBA reader. CPU08001DA8 indexes the table atROM1E84 using(code-1)*4;
entries `[1E9C,1EA4)` for07/08 both point to08002168, the unchanged return.
The compiler asserts those exact original pointers and retains both bytes.
The native centering control is14, separately visible in the dispatch code.
Eleven controlled pot/capacity states enter View through ordinary inventory
buttons. Three complete opens per case, final pixels, original geometry,
full renderer/copy ABI/guards and inventory/gold/battery preservation pass.
All9 copied Thief-pot labels retain the64-byte output guard. Captures were
visually inspected. Evidence: `build/text-next/pot-view-owner.txt`,
`reader-control-dispatch.txt`, `noop-controls.json`, and
`build/pot-view-prototype/pot-view-validation/`.

### Compound numeric aliases

The existing compact-numeric-aliases allocation after ROM00800C60 now owns
46 entries, including876C–8770 for16–20 and8771–8773 for(1)–(3). Its size
is computed by the shared allocator; no new original font/RAM/save ownership.
Original sequences `[000644C8,000644F3)` (blank plus1–20 andNUL) and
`[00060770,00060779)` (blank plus three counts andNUL) supply checked semantic
oracles.874F is the original blank and is not aliased;875E is0 and is skipped
by the ordinal sequence. Inspection of raw glyphs additionally confirms shared
6C is equipment/curse icons and1CC is four question marks. Evidence:
`build/text-next/symbol-rows/`, `build/compound-numbers-prototype/`. The latter
passes two controlled visible rows and72 native lookup/ABI probes; natural
consumer routing is excluded. Parenthesized glyphs preserve all ink, with13px
advance. No user font asset or normal letter spacing changes.

### Legacy record menu and travel-confirmation text (staged)

CPU `[08050AA8,08050BC4)` owns the2/3-row record-menu labels, including the
third Trade items option and its empty-storehouse modal. Original source table
ROM `[0014D340,0014D354)` holds Records/Scores twice, then Trade items. A
private20-byte copy is read by literals50AC4/50B1C;50B7C privately owns the
requirement string. Original72px menu at(8,24),6px cursor inset,2/3 rows.

CPU `[080524F4,08052790)` owns two travel-confirmation variants. Private
one-pointer copies replace literals5256C (Meadow),52574/5271C (Yes/No),
5263C (overwrite) and52714 (Travel?). Original source pointers are14D70C,
14D710,14D714 and14BCE4. Original windows: Meadow/overwrite224×32 at(8,120);
choices80×16 at(152,88), or Travel?80×16 at(32,72) and choices at(128,72).
The two choice labels begin6px/38px; cursor stride stays32px.

Original1F invokes CPU1FAAC, reads64 bytes of save header at save offset200
into its64-byte stack local, and decodes up to8 indexed bytes atlocal+14.
Its existing20-byte output is EWRAM `[0200CEE8,0200CEFC)`; no new RAM/save
ownership. The source lookup literal1FB08 already follows the shared English
name table. Keep1F and centering14 in the overwrite warning and reserve112px
for eight14px saved-name glyphs, yielding189px first line and142px second.

Evidence: `build/text-next/book-meadow-functions.txt`, `saved-village-getter.txt`,
`reader-control-dispatch.txt`, `build/book-travel-prototype/book-travel-validation/`.
All16 controlled complete-owner cases pass native cursor/selection/return,
two cancellation/reopening cycles, final pixels, ABI/guards, unchanged items
and battery; three saved-name profiles use recorded overrides after the real
header read. Ordinary bank input is redirected at the full callee boundary.
No claim of ordinary script access/unlocking, actual trading, travel or saving.
The eight resources remain outside3,443 until the current cumulative run finishes.

### Fused-equipment Info descriptions (staged)

ROM `[001447A8,00144848)` is the40-pointer sword/shield description table;
the adjacent `[00144848,001448E8)` contains the separately owned loss-message
ability names. CPU `[08017A4C,08017EEE)` selects descriptions when item bit
00200000 is set and at least one low20 property bit is present. A private
40-pointer copy replaces only literal ROM00017CA4. For sword property16 with
property4 also present, literal00017CC8 selects shared offset9FC instead;
a private shared-table copy changes only that slot. All original tables stay
intact. No new original-ROM, RAM or save ownership.

The original208-hex-byte frame supplies256-byte header and body buffers at
SP+8/SP+108. Original window:224px by7 rows at(8,24). The body starts at
row3, or row4 above12 properties. English uses at most3 rows and216px per
line, including at most256 encoded bytes with the optional0305 highlight.
EWRAM0200CDC4 holds the original selected property. CPU189FC cycles it with
Left/Right;18914 draws property badges as sprites through02B28. Their Japanese
marks are graphic assets, kept for the explicitly deferred graphics pass.

Evidence: `build/text-next/ability-info-owner.txt`, `ability-selection.txt`,
`build/ability-info-prototype/ability-info-validation/`. All45 controlled item
cases pass ordinary inventory Info, selection, closing and two reopens, body
copy guards, full caller ABI, exact body pixels and unchanged items/gold/save.
All40 table slots, the special alternate, both20-property layouts and both
cyan masks are exercised. Placeholder and impossible combinations are stress
cases; natural synthesis/acquisition is not established by these probes.

### Dungeon cutscene text outside the event catalog (staged)

ROM `[001471D4,00147234)` is a96-byte table: a leading empty source, five
baker-grave sources, ten forest-relic/old-man sources and eight flame-relic/King
sources. A private copy owns21 reviewed strings and replaces literals0001BE10,
0001C198,0001C278 and0001C530. The leading entry and two stored farewell slots
atrelative40/80 remain unchanged: no reader of those farewells is established
by these functions. Original table/source bytes remain intact.

CPU owners `[0801BC24,0801BE10)`, `[0801BFBC,0801C278)` and
`[0801C2E8,0801C530)` select direct ROM strings for15A18. The forest identity
question at1C164 uses native choice mode1: Yes returns1 and selects source12,
No/B returns0 and selects13, then both select14. Relic-acquisition lines pass
through `[0801C958,0801CA3C)` before15A18. These readers retain original frames
and224px two-row windows; English uses216px,98px name and14px initial reserves.

The reader resets foreground at page clears. Grave/voice inscriptions require
0306 at each new page, followed by14 centering per translated row. Preserve the
original number of yellow colour commands, with verified per-page placement;
moving them all to the beginning fails native colour checks. No new RAM/save
storage or source ownership beyond these literal replacements/private resources.

Evidence: `build/text-next/dungeon-story-functions.txt`, `relic-message-owner.txt`,
`build/dungeon-story-prototype/dungeon-story-validation/`. All33 cases pass
original source selection, complete pages/pixels, player/initial bounds,
Yes/No/B branches, relic-helper handoff and helper/modal/caller ABI. Controlled
entry skips scene staging, movement and quest effects. Inventory is held stable
only across the text block; the ordinary Drink trigger consumes its test herb
before entry. Gold/battery remain unchanged. This is not native story-progression
or relic-acquisition acceptance.

### Empty-inventory scroll-reading refusal

CPU `[080175B4,0801775C)` checks actions12/29 for scroll IDs117/128/132/133.
If EWRAM0200DF28 has no live first item (nonnegative flags), it queues the
direct source ROM `[0006B550,0006B56D)` through1588C at17634 and changes the
command byte at+1 to1. Literal ROM00017648 privately owns this source;
the English allocation changes only that literal. One216px line, no formatter
or new buffer/frame/RAM/save ownership.

Evidence: `build/text-next/empty-read-function.txt` and
`build/empty-read-prototype/empty-read-validation/`. Four controlled known scroll
IDs, native Drop followed by empty carried inventory and ordinary Floor/Read
inputs reach the complete original check without PC/register redirects.
Native command cancellation, queue/caller ABI, final pixels, intact floor scroll,
empty inventory, gold and battery all pass. Natural scroll acquisition is separate.

### Dungeon-entry restrictions (prepared prototype)

ROM `[0014C8E4,0014C8F4)` contains four restriction pointers: maximum items,
store/discard, sell/discard and level1. Private table/strings replace only
literal ROM0004BD04 (base),0004BD30 (base+4) and0005222C (base+12).
The original strings/table remain intact; new allocation uses `RomBuild`.
CPU `[0804BCC0,0804BD2A)` clears and formats the original128-byte scratch,
EWRAM `[0202F44C,0202F4CC)`. Its item limit comes from signed16-bit getter41D00;
zero uses52DB0(flagF2) to select storage versus sale. CPU
`[08052044,08052304)` invokes the item gate and checks hero+88 for level1
when destination7 is selected. Original15A34 windows remain224px/two rows;
English uses216px and at most124/128bytes. No new RAM/save allocation.

Evidence: `build/text-next/travel-gates-functions.txt` and
`build/travel-gate-prototype/travel-gate-validation/`. Eleven cases cover
limits1/5/32767 and both store/sell branches in both original placements,
plus the level gate. Complete128-byte clear/format, guards, native modal
pixels and helper/modal/caller ABI pass. Controlled item-limit/getter/flag
results and message-block entry are recorded; actual travel, menu unlocking
and inventory-capacity rules are excluded. The Drink trigger consumes its
herb before the block; inventory is stable within it, and gold/battery remain
unchanged. This prototype is not yet part of the3,514-resource candidate.

### Timed ending dialogue (prepared prototype; credits artwork separate)

ROM `[00153F20,001541D8)` contains58 twelve-byte descriptors: text pointer,
32-bit flags and32-bit timer. Five groups begin at153F20,153FF8,154094,
1540C4 and154130. A private copy replaces57 nonempty sources while preserving
all flags/timers and empty sentinel index43 (`0806DADC,00000300,60`). Only
literal ROM00055920,000559B8,00055A3C,00055AD8 and00055B7C changes; original
source/table bytes stay intact. Setup functions557C8,55934,559CC,55A50 and
55AEC store those pointers in original EWRAM `[02011BB4,02011BB8)`.
No new RAM/save/source ownership.

Dispatcher CPU `[08054F44,08055098)` reads each descriptor and calls15A50
with callback0805509D and typewriter1. Flags low byte chooses original224px
by2-row windows at(8,8) or(8,120); high byte governs group continuation.
Timer loads original EWRAM `[0200C87C,0200C880)`. Global02003B30=1 makes native
page/modal waits count down. Callback `[0805509C,080550C4)` maps `@W<byte>@`
to60×operand frames and `@w<byte>@` to10×operand; reader1DA8 executes each
wait through59184. Mode commands1330/1331 set the original byte0200C880,
controlling the prompt marker. All commands retain source order/operands,
including player7E and initial7F. The scoped compiler wraps216px rows using
98px player/14px initial reserves; flags, timers and window geometry stay
unchanged. All timer1 pages retain their native terminal timed waits.

Evidence: `build/text-next/ending-functions.txt`, `ending-dispatch.txt`,
`ending-renderer.txt`, `ending-callback.txt`, `ending-pagewait.txt` and
`build/ending-prototype/ending-validation/`. All85 cases pass native setup
literal loads/stores, complete setup/dispatcher frames, source selection,
automatic pages without advancing input, exact W/w elapsed frame counts,
mode outcomes, final pixels and full modal/caller ABI. Controlled selectors,
auto state and message-block jumps are recorded; actor staging, movement,
fades, natural ending progression and credits are excluded. Inventory is
stable after the Drink trigger consumes its herb; gold/battery unchanged.
This prototype remains outside the3,514-resource candidate until integration.

### Dungeon destination picker (prepared prototype)

CPU `[08052304,080524F0)` owns the seven-label table ROM
`[0014D71C,0014D738)` through literal00052420 and direct centered heading
ROM0014D42C through literal000523B8. A private seven-pointer copy and heading
change only those literals. Original160px heading at(40,24) and144px five-row
list at(48,56) remain intact. Six cursor pixels leave138px per label; the
heading uses152px. Strings are read directly, without a new RAM/format buffer.

Original progression byte EWRAM020101F0 and flag getter52DB0 select one of
eight availability rows in ROM `[0014D3E3,0014D423)`. Label indices2/3 and
returned selection positions1/2 have explicit native swaps; preserve both.
The original rows do not emit stored label1 (Mysterious Meadow), so its
rendering uses a recorded selector override rather than claiming reachability.
Original cursor/result byte020101A1 and row count020101A0 remain unextended.

Evidence: `build/text-next/travel-gates-functions.txt` and
`build/dungeon-travel-prototype/dungeon-travel-validation/`. All25 cases pass:
eight availability rows, five locked fallbacks, the BA/BB alternate, ten
positive selections and the stored meadow label. Full original owner, cursor
wrapping, two cancel/reopen cycles, both window closures, final pixels and
caller ABI/guards execute. Availability/progression results are explicit
controls; natural unlocking and actual travel remain unverified. Inventory,
gold and battery are unchanged. Eight prepared text resources remain outside
3,514 until the next integration.

### Soldier/adventurer tutorial topics and prose (prepared prototype)

Original27-entry outer label/intro pointer tables occupy ROM
`[0014CF50,0014CFBC)` and `[0014CFBC,0014D028)`. The prepared tutorial-help
owner copies both and changes only configurations0,3,18,19,24,25, with private
inner tables and29 translated sources. All21 other configurations retain their
original pointers. Source descriptor triples `[0014CEFC,0014CF4D)` and
16-byte menu geometries starting0014D52C remain unchanged. Literal ROM0004F9F0,
0004FA1C,0005103C,00051088 select the label copy;0004F9F4,0004FA20,00051040,
0005108C select the intro/prose copy. No new RAM/save or source-byte ownership.

CPU `[0804F8F4,0804FA5A)` dispatches menu configuration through original
`[08050DD0,08050EE4)` or two-page `[08050FB8,080511C0)`. Renderer
`[08050EE4,08050FAE)` uses a224px one-row heading at(8,24) and the original
list at(8,56): selected widths144/160px, three to six rows,6px cursor reserve.
The soldier paged family18 selects adjacent19 with Right/Left. All13 direct
explanations use15A18's224px/two-row modal, compiled at216px with native waits.
Other tutorial configurations may instead use two-byte bank/group references;
those are not text and are preserved by this owner.

Evidence: `build/text-next/tutorial-readers.txt`, `tutorial-menus.txt`,
`tutorial-accessors.txt`, `tutorial-sources.json` and
`build/tutorial-help-prototype/tutorial-help-validation/`. Six cases exercise
all owned topics and complete prose, both soldier pages, cursor wrap, B and
Cancel selection, two cancel/reopen cycles, original table loads and full
script-reader/modal/caller frames. Exact pixels, ABI/guards and unchanged
inventory/gold/battery pass. Native bank entry is redirected before event-bank
setup, and script advancement is excluded. Natural NPC/story access and the
other21 menu configurations remain separate; no whole-tutorial sign-off.

### Expanded tutorial menus and bank explanations (prepared after 3,612)

The staged compiler in `build/text-next/tutorial_all_text.py` expands the private
outer/inner copies described above to all27 configurations and104 unique text
sources (75 beyond the first29). Original ROM descriptor triples
`[0014CEFC,0014CF4D)`, outer tables `[0014CF50,0014D028)` and all original inner
tables remain unchanged. Only the eight previously owned outer-table literals
change. Every inner slot is checked against original bytes; nontext selector
slots are retained exactly. Mode1 explanation entries are two-byte event-bank
selectors, not strings; translating bytes merely because they decode would
corrupt the binding.

The three two-column cursor arrays are ROM `[0014E3BC,0014E3FC)` (herbs,
left/right x0/84), `[0014E4D0,0014E518)` (equipment, x5/120), and
`[0014E54C,0014E58C)` (staves/pots, x0/96). Original04 text-column commands are
not the cursor positions. In the unchanged224px list, English starts at x6/90
for herbs, x11/128 for equipment, x6/102 for staves, and x6/113 for pots. These
insets preserve the entire cursor reserve. The equipment left/right budgets
are109/96px. Other single-column windows retain their original geometry.

Native evidence on prototype ROM
`a5a421a08119fc50697272597e44299b6a43f17b18da176c6c744568bf74cf68`:
`build/tutorial-all-prototype/` contains27 render/cursor cases, six direct-prose
cases,20 bank-backed cases and four explicitly selected alternate-header cases.
All pass exact source/glyph/pixel, original geometry, repeated cancellation and
caller-ABI checks. The bank cases execute full original loader `0804D6F8`, verify
actual decoded bytes/fixups in EWRAM `[020241AC,020241AC+decoded_size)`, then
execute original `0804FA68` selection/getter/modal paths. The original fixture
bank is restored through the same loader before returning. No bank offsets are
replaced in RAM. Bank/config selection and alternate intro-pointer+4 are
explicit controlled overrides; natural NPC reachability is not established.
Correct binding cohorts: config4/5 bank2; config6/10/13 bank3; config11 bank4;
config7/12/16 banks5 and6; config15/17/20/21/22/26 bank6; config23 banks5 and6.

Original configurations1/2 contain mode0 entries pointing at selector bytes;
8/9/14 contain inconsistent labels/cancel positions and mappings. Their original
behavior/data is preserved, with only rendering/cursor/cancellation established.
They are not declared unused or fixed, and remain explicit selection/reachability
gaps. Alternate headings in configurations6/17/20/21 receive separate controlled
render proofs; normal selection of those headings is also unproved. Evidence:
`build/text-next/tutorial-bank-dialogue.txt`, `tutorial-accessors.txt`,
`verify-tutorial-bank.py`, `verify-tutorial-alternate.py`, and the four prototype
report/gallery folders. The compiler and review remain staged until cumulative
integration; this is not a new whole-game or whole-tutorial acceptance claim.

### Link-trade UI and failure messages (prepared prototype)

The link compiler owns only six direct string literals and one private five-pointer
copy. Original ROM error table `[001547BC,001547D0)` is copied and literal
`00057C50` redirected. Its bounded indices0..4 select source offsets6EBB0,
6EB94,6EB74,6EB58,6EB38. Original error wrapper6EBD0 is read at57C4C;
selected-item confirmation6EBF4 at57DB8; cable readiness6EC10 at57DC4;
repeat-trade6EC60 at57DC8; Trade/Info6ECAC at57FE4; item instruction6ECB8 at58094.
(All offsets in this paragraph are ROM offsets.) These11 sources receive private
English; no source ranges or unrelated pointer consumers are overwritten.

Owner `08057C1C..08057C4C` formats an error plus cable advice in128 stack bytes.
Owner `08057C54..08057DAE` has a200-byte local frame: selected-item scratch
`[SP+8,SP+48)` is64 bytes, confirmation `[SP+48,SP+C8)` is128 bytes. Native
messages retain224px/two rows and216px safe lines; the item field reserves162px.
Owner `08057E08..08058082` retains168px storage list at(8,24),40px/two-row action
window at(192,56),6px action cursor reserve and8px outer border gap. Trade sets
one byte in existing EWRAM selection flags `[0200CDE8,0200CEE2)`; page/row/index
are shorts at0200CEE2/CEE4/CEE6. Existing stored records are250×12 bytes at
`[0200F008,0200FBC0)`, with count at02002C2A. These are original storage uses,
not permission to allocate new save/RAM fields.

Prototype `build/link-prototype/`, ROM
`18ebb4ca375e5c3813768c611b514e68d9ee2a25bd605bd10a57c6da5ac4e46b`,
passes21 message/choice/maximum-field cases and three picker cases. Native
formatters, buffer guards, Yes/No/B returns, original menu geometry, two list
pages, Info, Trade selection flag, repeated cancellation/reopening, exact parent
restoration and text pixels pass. Storage inputs and entry/message blocks are
explicitly controlled; link transfer, natural access and post-error storage sort
remain excluded. Item identities, gold and battery are unchanged. Evidence:
`build/text-next/save-link-functions.txt`, `link-display-functions.txt` and
`build/link-prototype/{link-message,link-picker}-validation/`.

### Pre-ending save-cancellation notice (prepared prototype)

ROM source `[0006CF38,0006CF55)` is selected by direct literal00054F1C in owner
`08054DA4..08054EEE`. Only that literal is patched to private English. Native
message block `08054E04..08054E40` passes the original source/flags/placement
argument to15A34, waits for a second input after that modal returns, then closes
the window. The observed original window is224px/two rows at(8,120); the private
English is one line within216px. No new RAM/save storage is used.

Prototype `build/ending-notice-prototype/`, ROM
`9b734797c235823797c29df2272761e432a76bc5f3fc95e1c7d0d106664831b9`,
passes A and B secondary-wait cases, exact text pixels and modal/caller ABI.
Full owner frame and original display/waits/window closure execute; save work,
scene setup and subsequent ending are explicitly skipped in disposable probes.
Inventory/gold/battery remain unchanged. This is display evidence, not validation
of an actual save failure or natural ending progression. Sources:
`build/text-next/save-link-functions.txt` and
`build/ending-notice-prototype/ending-notice-validation/`.

### Tutorial pickup tips and queued control09 (2026-09-27)

Verified original pickup owner `[ROM 0x24AD8,0x24E70)` copies a120-byte floor
item into an available inventory slot, removes the floor object and formats
its ordinary pickup message into192 bytes with a separate64-byte item field.
Only after successful insertion, the load at08024DAE/DB0 tests EWRAM
`[0x02003B6C,0x02003B70)` for11. Original item identity dispatch then selects:

| IDs | ROM literal | Original text range (exclusive end in catalog) |
| --- | --- | --- |
|203,204|0x24E10|0x1474C4|
|1,3|0x24E18|0x147264|
|30,31|0x24E20|0x1472BC|
|51|0x24E28|0x14743C|
|118|0x24E30|0x1473F8|
|169|0x24E38|0x147314|
|188|0x24E40|0x14734C|
|190|0x24E6C|0x1473D8|

These eight literal words alone are patch-owned. Source strings and item/mode
selection instructions remain intact. New text uses the existing RomBuild
expansion allocator; no new RAM is allocated. Exact original sources, exclusive
ends and hashes are recorded in the pickup-help catalog. Ordinary pickup
formats and tutorial NPC explanations are different resource families.

`080158FC..0801591C` appends into the existing1024-byte queue with bounded native
copies and a forced terminator. Compile-time bounds include the preceding
192-byte pickup output and suffix reserve. The original queued renderer
`[ROM0x22D8,0x239E)` treats09 specially:08002316..1C writes1 to its native flag,
and0800236C..70 detects09 in lookahead. It does **not** pass09 to01DA8's32-pixel
tab handler. Original09 markers and initial newline behavior are preserved;
actual rendered line starts are0 and the English limit is216px. The general
codec name `tab` must not be used to infer queued-message indentation.

Evidence: `build/text-next/pickup-help-carpenter.txt`, `queue-controls.txt`,
`native-queue.txt`, and `build/pickup-help-prototype/pickup-help-validation/`.
Prototype ROM024921446259671e9a2827a2d6501062a004af453eebb4b060613c9197d6d597
passes13 cases: all11 selectors, mode-off and unrelated-item negatives.
Ordinary Drop plus directional step-away/return invokes real walking pickup;
controlled floor identities and the mode load are explicit. Mode is restored
immediately after the original load, before any other owner reads it. Complete
English glyph/pixel checks, original09 flag writes, message and item guards,
queue/full-owner ABI, inventory increment, unchanged gold and battery pass.
The fixture's real mode is0; these do not establish natural tutorial progression.

### Warehouse repair service's direct dialogue (2026-09-27)

The complete original carpenter owner `[ROM0x502BC,0x503F2)` and message helper
`[ROM0x503F8,0x50438)` select nine direct prose sources, independently of the
translated warehouse-opening event bank. Literal words502D8,502F0,50334,
5035C,50360,5036C,503C0,503E0 and503F4 are the sole new patch sites.
`build/text-next/carpenter-review.json` pins the exact source ranges/hashes in
`[ROM0x14D058,0x14D33D)`; original text bytes are preserved. English ROM resources
use RomBuild; no RAM is allocated. The capacity template at14D14A uses the
original128-byte shared scratch `[EWRAM0202F44C,0202F4CC)`, with a checked32-byte
following guard. Its English `%d` preserves the value without Japanese field
padding; byte/width bounds cover255 from the native unsigned-byte load.

Native flag helpers52DB0/511C0/511E0 use `[EWRAM020101AC,020101CC)` for256bits;
this owner reads flags0x25,0x27,0x26, in that priority. Relevant byte is020101B0.
The capacity byte at`[02010208,02010209)` is mirrored into the halfword
`[02002C2A,02002C2C)`. Completion adds10; reaching180 instead writes250 and
sets flag0x27. Other completed increments clear0x26. Accepting the proposal
requires funds>999, calls41F64(-1000), then sets0x25. That gold helper clamps
the actor's native `[actor+0x60,actor+0x64)` to0..99,999,999; the signed-maximum
probe correctly preserves that clamp. These are observed existing fields, not
new storage ownership or authorization to repurpose them.

Evidence: `pickup-help-carpenter.txt`, `carpenter-readers.txt`,
`carpenter-gold.txt`, and `build/carpenter-prototype/carpenter-validation/`.
Prototype5f88e2095f2cdf2fb44ffbb72607c8ec432106b335cbdf69a8e70dcecd8b7079
passes28 full-owner cases. A controlled bank-call entry and explicit flags,
capacity, funds and original layout-helper return values reach all nine sources
and both modal positions. Entire original function executes after entry:
Yes/No/B choices, all pages, payment/refusal, construction/completion flags and
capacity outcomes pass, with exact visible glyph pixels, buffer guards and
helper/modal/caller ABI. Inventory, stored item records and battery are unchanged.
The255-capacity and signed-maximum funds probes are synthetic bounds. Natural
carpenter access, work-completion triggers and save persistence remain separate.

### Fixed-block house-fire scene (staged September27)

ROM offsets`[0x150470,0x152F70)` contain43 original256-byte records;
indices10,11,20 start with NUL, and the other40 are complete dialogue sources.
`08052DD8..08052E28` reads start index/count, calculates`base+(index<<8)`
and runs the original modal`08015A34`, incrementing the index until count is
zero. The literal is ROM`[0x52E34,0x52E38)` and shift instruction is
`[0x52DF4,0x52DF6)`(`28 02`, Thumb`lsl r0,r5,#8`). The original16-byte modal
descriptor is`[0x6CF28,0x6CF38)` and is copied to the original24-byte stack
frame; no text is copied into a new RAM buffer. Evidence:
`build/text-next/remaining-special-owners.txt` and`fixed-prose-caller.txt`.
The scene caller starts`08052E38`; its statically observed text batches end
at index42. Record29 has an isolated native-reader check but no proven natural
call in that scene. Empty records and unused padding are not free space.

`build/text-next/fire_scene_text.py` appends a private43×512-byte ROM block
through`RomBuild`, checks every original source, redirects only the literal
and changes the owned shift to`68 02`(`lsl r0,r5,#9`). The largest English
record is389 bytes. Original source records/padding, loop, modal descriptor,
scene staging and progression are preserved. The selected font and216px budget
are unchanged. Staged ROM
`58792daa6d117a68376db613952eac95327df7239b4e3a3873bbb2dad7e72d13`
passes56 full-dispatcher cases:40 records, maximum English/Japanese player
names, nine consecutive native batches and zero count; full pages, pixels,
modal/owner ABI and caller guard checked. Controlled bank entry/index/count is
recorded; this is not natural fire-scene progression. Inventory/gold/save are
unchanged. Evidence:`build/fire-scene-prototype/fire-scene-validation/`.

A second43-record byte-identical block at ROM`[0x1552E0,0x157DE0)` has no
absolute pointer to its base in the supplied ROM. It remains an unassigned
consumer lead; absence of that pointer does not establish unused status.
The source-only NUL scan reconciliation is
`build/text-next/unaccounted-scan-3707.json`; decoder hits are not automatically
text or free space. Japanese strings at`0x5FDE8/0x5FDF4` and
`0x6B4A8/0x6B4C0/0x6B4E4` also occur in save-header copying/comparisons
(`08014F2A..08014F44`, `08014F64..08014F70`), so they must not be blanket
translated merely because a string scan sees Japanese.

### Travel confirmations omitted from direct-pointer inventory (staged)

ROM`[0x14C7EC,0x14C809)` is the dungeon-entry question;
`[0x14C809,0x14C84A)` is the centred saved-village overwrite warning.
The latter contains two native14 centring controls and one1F saved-name
substitution. Six owned literal words are`[0x4BB2C,0x4BB34)`,
`[0x4CA24,0x4CA2C)` and`[0x522CC,0x522D4)`. The respective original
owners are`0804B8AC`, `0804C980` and`08052044`; each selects one of the
literal pair based on the original item-limit result and calls`08015A34`
with Yes/No enabled. Evidence:`build/text-next/travel-confirm-owner.txt`,
`travel-confirm-second.txt`, `travel-gates-functions.txt`.

The staged compiler`build/text-next/travel_confirm_text.py` owns only those
six literal words and appended English resources. Original prompts, source
controls, selection sense and all route/save code remain intact. Saved names
still use the existing20-byte EWRAM`[0x0200CEE8,0x0200CEFC)` scratch;
its following16-byte guard is checked. Eight Japanese glyphs reserve112px
inside the original216px safe region. No new RAM/save allocation.
Prototype ROM`1b58a1108776d04e39258086709efa46f9a87be1df72521ee333963b7d8b02db`
passes105 cases: three original owner/modal blocks, both applicable display
placements, Yes/No/B, real saved-name read plus required/widest English,
widest Japanese, empty and read-failure names. Complete glyphs, centring,
final pixels, name-scratch guard and reader/modal/caller ABI are checked.
The controlled setup and skips around each message block are recorded;
actual dungeon entry, save overwrite and progression are excluded.
Evidence:`build/travel-confirm-prototype/travel-confirm-validation/`.

### Older town/dungeon destination tables (September 29)

Original ROM `[0x14BE98,0x14BECC)` contains 13 destination pointers. Indices
1–3 are already owned by the initial castle/home/square insertion. The remaining
ten slots contain nine unique Japanese strings (Cancel is shared). The new
`tools/town_routes_text.py` copies the table, verifies and reuses those three
owned English pointers, and inserts the nine reviewed labels into the copy.
Only ROM literals `[0x4CC64,0x4CC68)`, `[0x4CD9C,0x4CDA0)` and
`[0x4CDAC,0x4CDB0)` point to this private copy, at offsets 4, 0 and 36.
Other readers, original source strings, availability masks and geometry remain
untouched. `RomBuild` checks every original word and allocation overlap.

CPU `[0x0804CB10,0x0804CC50)` selects the town list using the 48 bytes at
ROM `[0x14BE33,0x14BE63)`: map byte EWRAM `0x0200FED8`, clamped to 7,
and a count of five original flag-reader results. CPU
`[0x0804CC70,0x0804CD9C)` uses four bytes `[0x14BE8A,0x14BE8E)` and
three flag-reader results for the dungeon list. Their original result-ID tables
are `[0x14BE74,0x14BE84)` and `[0x14BE8E,0x14BE96)`. The common cursor
helper `[0x0804CDB8,0x0804CE58)` resets cursor byte `0x020101A1`, polls
native town input and returns the sentinel row on B. The private English lists
retain the 12px cursor reserve, 140/76px label regions and existing 8px gaps.
The dungeon heading uses a conservative 96px region in its 104px window.

All 67 prototype cases pass on ROM
`843bb7c784b266042163d338a0fa03a106d5bf634f653742a66981e13bd8c9a3`:
all 48/4 availability cells, ten destination selections, two explicit Cancel
mask probes, clamped map state and widest English/Japanese player names. Each
case checks three openings, cursor wrapping, actual returned IDs, cancellation,
resumed town movement, exact pixels and caller stack/register guards. Positive
selection IDs are checked before suppressing travel in these controlled probes.
Natural unlocks and travel outcomes remain separate. A long-held DOWN input
originally moved the cursor after opening; the corrected test releases each
short directional pulse and checks the initial cursor before navigation.
Evidence: `build/text-next/town-destination-menu.txt`,
`town-destination-owners.txt`, `town-route-cursor.txt` and
`build/town-routes-prototype/town-routes-validation/`.

### Guard refusal for the current form (September 29)

ROM `[0x14C84A,0x14C88B)` is a two-line refusal with native colour command
`03 04` and restore `05`. The original map-transition owner
`[0x0804B8AC,0x0804BC3E)` compares the three bytes at EWRAM
`[0x02010204,0x02010207)` against ASCII `M.A` at CPU
`[0x0804B984,0x0804B998)`. On a match, literal
`[0x4B9AC,0x4B9B0)` supplies the refusal to helper
`[0x0804BC40,0x0804BC70)` and native modal `0x08015A34`.
The new owned literal points to the appended English stream; original bytes,
form predicate, layout and control sequence are preserved. Operand 4 selects
foreground palette index 12, as checked by the native reader.

Ten prototype cases pass on ROM
`a7a05791570d2ced3b6182cc9705e7071f772afc721f71199bd582a4bd1adf28`:
matching form with A/B dismissal in both native layouts, plus each individual
byte mismatch. Full original owner frame/epilogue, predicate branches, glyphs,
colour/pixels and stack/register guards pass. Controlled setup bypasses map
movement; mismatches skip subsequent travel. Temporary form bytes are restored,
and items/gold/battery remain unchanged. This does not establish natural
transformation access. Evidence: `build/text-next/travel-form-gate.txt`,
`travel-gate-modal.txt`, and `build/form-refusal-prototype/form-refusal-validation/`.

### Empty name-cell initializer (September 29)

Original ROM `[0x648E8,0x648F1)` contains eight `01` bytes and a NUL.
Shared table slot `+0x004` supplies it to native copies at CPU
`[0x08009E84,0x08009E8E)`, `[0x080182C4,0x080182CE)` and
`[0x08058DF8,0x08058E02)`. The first and third walk 221 item records at
20-byte strides and initialize the name-cell field at record `+9`; the second
copies it into the name editor. These are encoded empty cells, not Japanese
prose or eight authored text styles. Source disposition is retained nonlinguistic;
all original bytes remain untouched. Evidence:
`build/text-next/name-cell-initializers.txt` and
`translations/source-dispositions-review.json`. This makes no unused-code claim.

### Event-script references and Japanese placeholders (September 29)

Original ROM `[0x14CD4C,0x14CD68)` holds seven pointers to uncompressed
script banks. Their starts are `0x43CD5C`, `0x43D474`, `0x43E2DC`, `0x43E868`,
`0x43EC7C`, `0x43F1C0`, `0x43F710`; the final exclusive bound is `0x43FAAC`.
Each starts with a u32 count and that many u32 offsets relative to the following
payload. Counts are 15/33/18/15/15/20/17. Each script root has a four-byte
trigger header before instructions. All 133 physical script spans decode using
the original operand-length table, ROM `[0x14CEBC,0x14CEE0)`. There are 207
physical dialogue instructions. All 27 actual opening calls in each of the
original Yes/No traces match their script address, group, index and text ID.
No currently unresolved single-character source is referenced in this family.
This is bounded static and opening-route evidence, not all-scene reachability.

The other seven pointers, ROM `[0x14CD68,0x14CD84)`, select compressed NPC
resources beginning at `0x43A420`, `0x43A6A0`, `0x43ADE0`, `0x43B298`,
`0x43B7B0`, `0x43BC3C`, `0x43C3FC`. Native loader `0804D6F8` decompresses
these to EWRAM `0x020129AC` and fixes five header-relative pointers in
`[0x020129AC,0x020129C0)`. They address 32 map-relative offsets, 32 pairs of
u16 first-actor/count, a u32 script-offset table, script bytes, and eight-byte
actor records. The actor record's byte4 becomes native actor byte`0x25` through
`0804DA94`; it is a selector, not necessarily the actor's ordinal.

Native talk selector `0804B33C` reads map byte `0x0200FED8`, actor records at
`0x02010A78 + 0x40 * actor`, and resource pointer `0x02010144`. Unless the map
offset is `FFFFFFFF` or selector is `FF`, it writes EWRAM script PC
`[0x02010138,0x0201013C)` as:
`script_base + map_relative + offsets[first_actor - 1 + selector]`.
These are original storage/reads; this research allocates no new RAM.

Interpreter `0804EA80`, specifically `0804EF40..0804EF7E`, consumes an opcode
before calling the handler in ROM `[0x14CE30,0x14CEBC)`. Opcode8 has five
operand bytes: actor, group, index, mode, extra. Mode0 displays normal text;
mode1 displays Yes/No; mode2 dispatches a custom menu and ignores its nominal
text entry. Opcode6 (`0804F888`) branches by a signed byte relative to the
opcode on the selected flag result. Opcode16 (`0804FE28`) branches by an
unsigned byte relative to the opcode on a choice result. Opcode21 terminates;
opcode20 waits for pending work before advancing. Physical bytes after an END
are not automatically reachable dialogue or free space.

The decoded NPC root audit finds 22/63/69/74/67/79/85 roots. A conservative
branch traversal finds only two of the 36 unresolved single-character sources:

- Bank3 group23/index0, `event-bank-3.3ec2`, source `サ`: map11 selectors1/2
  start at decoded offsets `0x720`/`0x739`, directly with a Yes/No dialogue.
- Bank4 group6/index1, `event-bank-4.0d25`, source `な`: map5 selector1 starts
  at decoded `0x516`; original flag`82` selects repeat dialogue at `0x528`.
  With that flag clear, the existing full boy prose is selected at `0x51B`.
  Native flag bits begin at EWRAM `0x020101AC`; flag82 uses byte`0x020101BC`,
  bit2.

The other three physically referenced stubs (bank2 group25/indices1–3) occur
after an unconditional END at decoded `0x5AE`; the audited root at `0x5AB`
does not reach them. This alone does not establish unused status across other
consumers. Bank2 also has an original selector targeting decoded `0x5E2`, past
the declared script bound `0x5E0`, and another root at `0x5DF` falls outside
that bound after a zero byte. Both remain explicit unresolved source anomalies;
no read beyond the declared range is accepted as script evidence.

Six controlled checks on candidate ROM
`a7a05791570d2ced3b6182cc9705e7071f772afc721f71199bd582a4bd1adf28`
execute the full native loader, NPC selector, flag branch (bank4) and dialogue
handler. They confirm original `な` and `サ` actually render through those
selected branches; bank4 flag-clear prose and bank3 A/B also pass. Inputs,
RAM/register controls, source bytes, source windows and screenshots are saved
under `build/event-stub-research/`. Caller ABI/guard, inventory, gold and battery
are preserved. NPC/map activation is controlled; ordinary story reachability
and subsequent script consequences are not established. No placeholder English
has been inserted pending the user's wording decision.

Research scripts/reports: `build/text-next/audit-script-text-refs.py`,
`script-text-refs.json`, `audit-npc-text-refs.py`, `npc-text-refs.json`,
`audit-npc-control-flow.py`, `npc-control-flow.json`, `probe-event-stubs.py`.
Disassembly: `event-loader.txt`, `actor-event-selector.txt`,
`actor-event-roots.txt`, `event-branch-owners.txt`,
`event-branch-owners-small.txt`, `event-opcode-handlers.txt` and
`event-consumers-full.txt`. No stub is classified unused by this partial audit. The reusable equivalents are
`tools.research_event_script_refs`, `tools.research_npc_script_refs`,
`tools.research_npc_control_flow` and `tools.research_event_menu_refs`; their
reports are under `build/event-script-audit/`. Reproduction order is in
`EXPLORATION.md`.

The nine direct Thumb calls to getter `08050270` in original code
`[08000000,0805E000)` are at `0804FA7A`, `0805020A`, `08050BF4`, `08050C18`,
`08051366`, `080513B4`, `08051466`, `08051490`, `08051568`. Original literal
references to event-bank global `0200FF38` are loader `4D7C0`, script reader
`4F96C`, and getter `502B8`. Getter wrappers `08050BC4`/`08050C14` receive
fixed pairs `(23,1)`, `(29,14)`, `(28,14)`, `(14,18)` or `(8,8)` from owned
opcode33 dispatch blocks `080509B4`, `080509BE`, `080509C2`, `080509CC`.
The well reader `080501DC` selects group7 indices5–8; medals `0805132C`
select group14. None of these valid pairs names a currently unresolved stub.
This bounded scan is not a proof against dynamically constructed references.
Evidence: `event-getter-owners.txt`, `event-helper-dispatch-blocks.txt` and
`event-generic-parents.txt` in `build/text-next/`.

The tutorial wrapper `0804FA68` receives pairs from `08050E82`. Cross-referencing
original mode2 NPC instructions gives 31 bank/configuration combinations.
`build/text-next/event-menu-references.json` retains two mismatched combinations:
config12 in bank4 (map11 roots `0x6B6`/`0x6CA`) and config14 in bank5 (map4 root
`0x3A4`). The former asks for pot explanations using group2 indices2/5–10, while
that bank's group2 contains Maggy's single conversation. The latter contains
out-of-group Gon selectors and a non-selector final pointer. Original native
address arithmetic can consequently reach unrelated prose or the middle of a
string. This is an explicit consumer/reachability gap, not authorization to
reinterpret those bytes as coherent source dialogue. Config12 is correctly
bound in the separately tested banks5/6. No ordinary access to either mismatched
combination has been established, and this audit does not change their data.

### Appearance-table end marker and empty assignment (September 29)

The last 24-byte record of ROM `[0x143058,0x143EE0)` is
`[0x143EC8,0x143EE0)`, alias154. Its name pointer is `08065638`, source
`[0x65638,0x65645)` (`エンドマーク`, "End marker"). The signed halfword at
record+8 is1; preceding154 records have0. Original assignment owner
`08009E68` checks that halfword before adding an alias to its category pool
(`08009EBA..08009EBE` and `08009EDA..08009EDE`), so the sentinel is not
assigned as an appearance. Its name has only the sentinel record's absolute
pointer in the original ROM. The original and private English copies preserve
the complete sentinel record; `tests/test_item_alias_text.py` checks this.

The original unassigned pool value is999, from literal `08009FDC`, not `FFFF`.
Three complete native initializer calls on candidate3768 inspect all221 output
records in existing EWRAM `[0x02003BAC,0x02004CF0)`: alias halfword is at+4,
20-byte stride. No assignment equals154; each populated appearance category
uses its own pool or999 (one unassigned record per call). Source assignment
code/table and native RNG execute unchanged. The controlled calls intentionally
reset disposable item-identification/name/assignment RAM, preserve caller ABI/SP
and battery, and do not prove safety for corrupt or externally edited saves.
Evidence: `build/text-next/probe-alias-sentinel.py`,
`build/text-next/alias-sentinel/report.json`, `alias-assignment.txt` and
`name-cell-initializers.txt`. Classification as internal sentinel metadata is
separate from player-facing translation; the source must remain intact.

### Floor-Remove fragment (prepared prototype)

Original Remove owner `08024918` reads command byte3 and branches when it is
above49. Literal ROM `[0x24930,0x24934)` loads shared table `08140D68`, then
slot90; source is ROM `[0x643EC,0x643FD)` (`足元のアイテムに`). Native
`0802492A` queues that source alone in mode1, then returns through
`080249CE..080249D6`. There is no formatter or concatenated completion in
this branch. The Japanese is itself an incomplete phrase.

The staged compiler redirects only that literal to an owned private table and
appends "To the item at your feet", preserving the fragment without inventing
a refusal reason. Prototype ROM
`22839aa308c88ec1e149c49151c6321fe811c79518423c47f197d811688e6521`
passes two real action-menu Remove invocations with controlled compared values
50/255. Exact queue bytes, one-line216px budget, native glyph pixels, queue/
owner ABI and unchanged equipped status pass. Ordinary availability of Remove
for those floor indices is not claimed. Sources and all other action branches
stay intact; no new RAM or save allocation. Evidence:
`build/ground-remove-prototype/ground-remove-validation/` and staged
`ground_remove_text.py`, `ground-remove-review.json`, `verify-ground-remove.py`
in `build/text-next/`. This resource is not yet included in the root candidate.

### Already-known monster identity format (September 29)

Original CPU owner `[08029EB8,0802A01C)` has two branches. If the selected
species definition's byte19 is zero, it loads shared slot910 via literal
`[00029F00,00029F04)`, calls the ordinary actor-name getter08009ACC and formatter
08000FB8 at29EF4, then returns through2A00C without calling the message queue.
The source `[0006059C,000605B6)` is the identity statement `このモンスターは\r%sである`.
The other branch uses its separately owned slot7E0/literal2A01C and does display
an already-localized revelation message. This establishes the first branch's
formatting behavior, not a new on-screen message or ordinary encounter route.

`tools/monster_identity_text.py` prepares a private654-pointer copy,
translates only slot910 as `This monster is\n{actor}.`, and redirects only
literal29F00 with expected-source and shared-allocation checks. Original tables,
source bytes and frame size remain intact. The256-byte output is `[SP,SP+100)`
at formatter entry; the native actor-name scratch has64bytes. The first prototype
is `838f42fa1a126ebff1959a1f4a0f618859aa377101c87581617d82148beada70`.
`tools/verify_monster_identity.py` exercises the full original owner,
verifies exact formatted bytes and unchanged tail/caller/ABI/field guards, and
checks that no queue/modal/glyph call occurs and actor/player/items/battery stay
unchanged. All141 species at level1, the widest name at signed16-bit level32767, and three
synthetic name-field cases pass (145 total). The level is the signed halfword at
actor+88, read by09BBE/09BF2; native numeric aliases are verified through the
original level formatter. The earlier exploratory byte+44 level assumption was
corrected before integration. The40 existing discovery/revelation checks also
pass. This source is now integrated in3,770; evidence lives in
`build/english/monster-identity-validation/report.json`.

### Town table reader leads and reused EWRAM (September 29)

The original town-pointer interval is EWRAM `[020141AC,0201465C)` (300words).
A literal-load scan of original Thumb space `[08000000,0805E000)` finds nine
base loads:4BF88,50044,5007A,500CE,50124,50170,501A4,501BA and50A36. The native
service dispatch table at ROM `[00050024,00050044)` gives eight exact branch
entries:50044,50054,5008C,50118,50140,501A4,501B4,501BA. Their town-table
consumers include1D110/1D544/1E75C/1DFAC/1F2D8/1E394/20564;4BF78 passes the
table to2068C and50A36 to20760. The original1F2D8 selector passes that same
table on to storage/item subconsumers; it does not establish ownership of every
unused town slot. Correct listings are in
`build/text-next/town-dispatch-verified-roots.txt`; the earlier exploratory
`town-table-dispatch.txt` includes misidentified literal words as entries and
must not be used as function-boundary evidence.

Four additional literal loads fall inside the *address range*:53DEE→020143E8,
55EC6→02014268,55EE0→02014328 and55FCE→02014568. Full owners53B34 and55B90
pass these as 48-byte-record destinations to079C8, rather than dereferencing
town text pointers. Their listings are `build/text-next/town-range-aliases.txt`.
This is evidence of EWRAM reuse by another phase, not evidence that town text
slots239 or others are read there. No source is classified as unused from this
bounded literal scan, and no RAM region is declared free.

### GBA credit bitmap and complete identified arrival family (2026-09-29)

Addresses below are ROM file offsets unless prefixed by a CPU address. This is
source discovery and an offline audition, not insertion ownership or a free-space
claim. Sources and native artifacts are pinned to the configured Japanese ROM.

| Address space / exclusive range | Discovery and evidence | Certainty |
|---|---|---|
| ROM `[00585304,0058B269)` | BIOS type-10 compressed GBA scrolling credits, selected by the literal at `[000555DC,000555E0)` | Native decoder output and source reader verified. Padding after the consumed stream is not claimed. |
| Decoded stream `[00000000,000136BA)` | 79,546 bytes: 32-byte palette, u16 cell count at32, 7,800 one-byte occupancy cells at34, 2,241 4bpp tiles at7,834 | Fully decoded; exact length, occupied-cell count and native output checked. |
| EWRAM `[020129A8,02026062)` | Original credits decoder destination; the original ending uses this existing RAM | Observed for the isolated credits renderer only; no allocation for larger replacements or other scenes established. |
| CPU Thumb `[080554FC,080556AA)` | Credit renderer: decompression via `0805B48C` (BIOS SWI11), sparse rows copied into a wrapping 511-slot tile ring | Source loads, uploaded tile bytes, full routine return and caller ABI checked. |
| VRAM `[0600B800,0600C000)` / `[0600C000,06010000)` | 32×32 BG3 tile map and 4bpp character region; zero reserved, uploaded slots1..511 | Native copies verified. Raw final tile-map contents alone do not establish an entire scrolling sequence. |
| Palette RAM `[050001E0,05000200)` | Credits/arrival bank15; pixel index0 remains transparent and uses the display backdrop | Native credit comparisons use an explicitly controlled black backdrop. |
| ROM `[0054E764,0054E784)` / `[0054E784,00555B04)` | Arrival stored palette and224×264 atlas | All selected location/floor rectangles checked against native calls. |
| ROM `[0013EE00,0013EE58)` | Eleven8-byte signed-halfword rectangles: digits0..9 andF | Verified ordinary1/2/3-digit floor composition. |
| ROM `[0013EE58,0013EEC0)` | Thirteen8-byte location rectangles, selectors0..12 | All13 controlled selectors verified at floor1; only11/floor1 follows the original natural fixture fields. |
| ROM `[0013EEC0,0013EEC8)` | Separate8-byte `レベル` (Level) prefix descriptor; not a fourteenth location | `08005B6C` selects it for Well ID12. Floors1 and10 show it;11 suppresses the entire card. |

Credit script order is established by ending root`08054DA4`: five story scenes,
then original preparation at`08054EA2`, call`080554FC` at`08054EC8`, then final
artwork through`0805532C`. The credit bitmap is240×2080, with67 visible English
lines. The older English ASCII block beginning`0006DF04` and descriptor block
`[001541D8,00154428)` do not supply this bitmap renderer. No blanket unused-source
disposition is made for those older tables.

The controlled credit probe begins at a fresh-title wait and executes original
ending setup while bypassing its save and five story scenes. It substitutes the
native VBlank wait for surrounding scene-update calls and records BG3-only,
blank-map/tile-zero, backdrop and blend overrides. This is necessary isolation:
entering without that setup leaves unrelated scene/window work active and does
not provide a valid credits screenshot. All2,241 unique tile sources match;121
exact full-screen comparisons cover all67 visible lines. Eight captured
blank/lead-in/fade frames are excluded. It verifies decoded text-layer rendering,
not an unmodified ending playthrough or initial/final transition fidelity. Reads
of write-only I/O scroll/blend registers are bus diagnostics and must not be
interpreted as reliable register state.

Arrival names occupy24px-high rectangles of64..224px, centred in the240px screen
at y32. Ordinary floors use a right-aligned three-character `%3d` field at tile
columns16/18/20 andF at22, y80. Well uses the Level prefix at tile8 and the last
two number columns; its controller omits every rectangle when floor>10. The
original fade stops at step1. The18 native cases compare38,400 pixels each using
an explicit observed stored-to-visible palette mapping, not a new theoretical
fade model. No town arrival family is established by this atlas.

Evidence: `build/graphics-audition/research/{arrival-functions,ending-root,credits-player,credits-decompress}.txt`,
`build/credits/{manifest.json,research/report.json}`, and
`build/arrival-cards/{manifest.json,native/report.json}`. Reproduce with the
commands in`docs/GRAPHICS_AUDITION.md`. The root English ROM/BPS bytes are unchanged.

### Shiren reference graphics and credits preservation (2026-09-30)

These Shiren addresses are **external source-file offsets and SNES source
labels**, not Torneko 2 ROM/RAM ranges or free space. The nominated checkout is
`../Shiren/shiren-revamp-fixes`; it is read-only in this workflow.

| Source space / exclusive range | Evidence | Certainty |
|---|---|---|
| Shiren `gfx/fonts/area_title_font.2bpp` file `[0000,9000)` | 36,864-byte SNES 2bpp asset included at source label `AreaTitleFont` / `$DB7000` | Source declaration and file size verified. This is the file envelope, not a claim that every byte is a separate glyph. |
| SNES source `Data_db6000`, 194 two-byte entries, logical `[$DB6000,$DB6184)` | `data/demos/demos.asm`; each selected word minus `$7000` gives an offset in the bitmap file | All referenced 144-byte chunks bounded; per-title exclusive file spans and hashes recorded in `build/arrival-cards/shiren/shiren-source.json`. |
| SNES source `[UNREACH_C5CDCE,UNREACH_C5CEFA)` / `[$C5CDCE,$C5CEFA)` | 30 ten-byte area-title records in `code/bank_05.asm`; first byte is original start column, next nine select chunks/spacing | 28 labelled title strips decoded; two spacing-only records excluded. Each chunk is 24×24 pixels (3×3 tiles). Not a Shiren emulator verification. |

The configured crops recover 43 exact bitmap characters. A new period uses the
dot from the recovered `i`; spacing is newly assigned. The resulting subset
is a local audition resource, with no GBA/SNES patch, new allocation or native
Shiren-font execution claim. See `docs/SHIREN_ARRIVAL_FONT.md` for missing
characters and every current T2 name's measured budget. The separately loaded
Shiren Kointai floor numbers have not been imported into this Latin subset.

The user approved preserving the original English GBA credits unchanged.
Acceptance compares the existing development ROM's `[00585304,0058B269)`
compressed credit bytes with the Japanese base and checks that the viewer's
approved-original mode preserves the source pixels. No replacement allocation
is needed for these already-English credits.

### Approved Shiren arrival insertion (2026-09-30)

The user approved inserting all 13 current arrival names and Level, including
widening Ordeal Mansion. `tools.arrival_art` owns two appended resources and
six original data literals through `RomBuild`; it changes no instructions,
RAM/save allocation, palette, number artwork or credits. The exact build is
`c6cf871bcb20060b91ca226d203bdf78713d89aa8cb1643170286e0b011f96c5`.

| Address space / exclusive range | Ownership / evidence | Certainty |
|---|---|---|
| Expanded ROM `[008F8A80,00909100)` | Private 67,200-byte 4bpp atlas, 224×600px. First 33 tile rows copy original `[0054E784,00555B04)` exactly; 42 new rows hold 13 names and Level. | Shared append allocator, expected resource hash, decoded bounds and native uploads verified. No original gaps reused. |
| Expanded ROM `[00909100,009091C8)` | Private 25×8-byte descriptor table. First 11 entries retain original digits/F; entries11–23 select new name rows33–71; entry24 selects Level at row72. | Original descriptor bytes preserved; every native selection and source span verified. |
| ROM `[0005B68,0005B6C)` | Atlas literal in CPU Thumb copier `08005AC8`; expected original pointer `0854E784`, new `088F8A80` | Owned redirect; retained original atlas prefix also preserves original rectangle coordinates. |
| ROM `[0005BFC,0005C00)` | Well Level descriptor literal; expected `0813EEC0`, new table+`C0` | Native Well1/10 rendered;11 suppresses all copying. |
| ROM `[0005C00,0005C04)` and `[0005C5C,0005C60)` | ASCII-biased digit-table bases; expected `0813EC80`, new table−`180` | Original `ASCII_digit*8` addressing retained; every digit and 1/2/3-digit fields verified. |
| ROM `[0005C60,0005C64)` | F descriptor literal; expected `0813EE50`, new table+`50` | Original F pixels and placement retained. |
| ROM `[0005C64,0005C68)` | Name descriptor base; expected `0813EE58`, new table+`58` | All 13 native selectors verified. |
| VRAM `[0600C020,0600CDA0)` at largest tested composition | 108 uploaded tiles after reserved tile0, inside original character region `[0600C000,06010000)` | Full96KiB VRAM before/after comparison matches only expected tiles/map writes. No new VRAM reservation. |

Ordeal Mansion's private descriptor is `(x=0,y=57,w=17,h=3)` tiles. The
controller places that136×24px rectangle at screen `(48,32)`. Its130px advance
is centred at x55 with every ink pixel inside the copied rectangle; no glyph
rescaling or extra text row. Other name widths remain unchanged. Native
compositor `08005B6C` still uses its original16-byte stack scratch and the
existing tile counter at EWRAM `[020015A4,020015A6)`.

Bounded direct Thumb-BL scan of original CPU space `[08000000,0805E000)` finds
the five copier calls at5BBE/5BDC/5C1E/5C30/5C4E, the compositor call at5CF6,
and controller call at4D62. Aligned original-ROM word references to the atlas
base are5B68 and5D80;5D80 remains unchanged and supplies the original blank
tile. Original Level/digit/F/name base references occur at the five recorded
descriptor literals above (the digit base has two references). This bounded
scan is supporting evidence, not a general proof about computed references.

The30 native cases compare1,152,000 visible pixels, exact native tile-map and
atlas uploads, compositor/controller preserved registers and stack guards,
original fade/hold/return, and unchanged battery bytes. One current-ROM fresh
opening route uses no overrides, renders Mysterious Meadow1F, finishes all
three English tutorial pages and moves normally. Other selectors/floors use
only temporary fields at`02003B6C`/`02005674`, restored before the original
caller resumes. Natural late-game entrance/unlock routes remain untested.

Evidence: `build/arrival-cards/inserted/{report,acceptance}.json` and its native
gallery; input/state hashes are retained in `inserted/fixture/`. The accepted
delta preserves all earlier text allocations/patches and every unrelated byte
of the archived3,770-resource ROM. Source ROM/save and original GBA credits are
unchanged. Reproduction and limitations: `docs/ARRIVAL_INSERTION.md`.

### Approved title and five floating corner logos (2026-09-30)

The user approved all six images for insertion. `tools.title_art` owns six
private resources and six descriptor pointer redirects through `RomBuild`.
The resulting ROM is
`bd61d3f6f2db7af8119ecc6ee757f7560808d55ddec192c670368523a2708ab3`.
Ranges below are exclusive; ROM offsets become CPU addresses by adding
`08000000`. Each resource is `9800` bytes: `200` palette bytes, then `9600`
tiled 8bpp bytes. All original graphics remain intact.

| Address space / exclusive range | Ownership / evidence | Certainty |
|---|---|---|
| Expanded ROM `[009091C8,009129C8)` | Private title record 16 resource | Appended after the arrival descriptors; hash-checked packing and native upload verified. |
| Expanded ROM `[009129C8,0091C1C8)` | Private family record 13 resource | Same allocator and native checks. |
| Expanded ROM `[0091C1C8,009259C8)` | Private monsters/slime record 18 resource | Same allocator and native checks. |
| Expanded ROM `[009259C8,0092F1C8)` | Private monster collage record 19 resource | Same allocator and native checks. |
| Expanded ROM `[0092F1C8,009389C8)` | Private chest record 20 resource | Same allocator and native checks. |
| Expanded ROM `[009389C8,009421C8)` | Private village record 21 resource | Same allocator and native checks. |
| ROM `[0013ED54,0013ED58)` | Record 16 pointer: expected `0842F138`, redirected to `089091C8` | All 20 original descriptor bytes checked; only the pointer changes. |
| ROM `[0013ED18,0013ED1C)` | Record 13 pointer: expected `08555B04`, redirected to `089129C8` | All 20 descriptor bytes checked. |
| ROM `[0013ED7C,0013ED80)` | Record 18 pointer: expected `0855F304`, redirected to `0891C1C8` | All 20 descriptor bytes checked. |
| ROM `[0013ED90,0013ED94)` | Record 19 pointer: expected `08568B04`, redirected to `089259C8` | All 20 descriptor bytes checked. |
| ROM `[0013EDA4,0013EDA8)` | Record 20 pointer: expected `08572304`, redirected to `0892F1C8` | All 20 descriptor bytes checked. |
| ROM `[0013EDB8,0013EDBC)` | Record 21 pointer: expected `0857BB04`, redirected to `089389C8` | All 20 descriptor bytes checked. |
| Original ROM `[0042F138,00438938)` | Original title resource | Retained byte for byte; not free space. |
| Original ROM `[00555B04,00585304)` | Five contiguous original menu resources | Retained byte for byte; individual starts above, each `9800` bytes. |
| VRAM `[06000000,06009600)` | Existing 600 background tiles | Native loader `08004240` uploads the entire new resource's pixel portion. No new reservation. |
| VRAM `[0600B000,0600B500)` | Existing 32-column BG0 map, first 20 rows | 30 visible columns per row checked against native synthesized tile IDs 0–599. The two unused columns per row are not claimed as new capacity. |
| BG palette `[05000000,05000200)` | Existing title palette | All 256 entries checked after native calibration. |
| BG palette `[05000000,050001E0)` | Existing menu image palette | 240 entries checked; UI tail `[050001E0,05000200)` is preserved. |
| IWRAM `[03000A0E,03000A10)` | Native colour/monochrome selector | Observed read by palette loader; nonzero selects monochrome functions. No patch or ownership claim. |
| IWRAM `[03000C38,03000C3C)` | Signed first calibration-row selector | Native title uses −2; menus use −1 from original descriptor fields. Controlled function probes restore the full snapshot. |
| IWRAM `[03000C3C,03000C40)` | Second calibration-row selector | Native title/menu observation is 4. Controlled probes cover 0–4; no RAM allocation. |
| ROM `[0005FB98,0005FCF8)` | Eleven 32-byte first-stage channel lookup rows | Colour function `08003434` clamps selector to −5…5 and indexes relative to `0005FC38`. Monochrome variant `08003490` averages RGB first. |
| ROM `[0005FCF8,0005FD98)` | Five 32-byte second-stage rows covered by probes | Functions `080034F8` / `08003550`; monochrome variant averages RGB first. Machine clamp allows 0–7, but rows 5–7 are not established as valid display settings by this work. |

The background table is at ROM `0013EC14`, with 20-byte records. An aligned
word scan finds each of the six original resource base pointers only at its
record. This is bounded supporting evidence, not proof about computed/interior
references; retaining every original resource avoids overwriting such consumers.
Loader palette call `080042D6` and tile-copy call `080042F0` are observed natively;
loader return is `08004370`. Instructions and all other descriptor fields remain
unchanged, including the 256/240 palette counts and −2/−1 calibration selectors.

Packing locks every source palette index used outside title rows `[0,136)` or
the corner rectangles `[164,124,240,160)` (family) / `[164,0,240,36)` (others).
The corresponding source palette entries are unchanged. Native baseline
comparisons check all unedited screen pixels, UI VRAM `[06009600,06018000)`,
OAM `[07000000,07000400)` and the menu palette tail through opening, cancellation
and reopening. No RAM/save layout or graphics-engine code changes are made.

Evidence: `build/title-insertion/research/palette-and-loader.txt`,
`assets/title-screen/packed/manifest.json`, and
`build/title-insertion/{native-report,acceptance,repack}.json`. Five ordinary
fresh-save background selections and one copied supplied-save route cover 36
stable snapshots, with 50 startup-transition frames each. The 640 native
colour-function probes cover the two used gamma selectors, five levels and
colour/monochrome paths; these are explicitly controlled calls. Natural
late-game routes and additional logo discovery remain open. Reproduction and
full scope: `docs/TITLE_INSERTION.md`.

### Dungeon-menu location banner reader correction (2026-09-30)

The user's screenshot exposed a missed consumer: the main menu still read all
13 Japanese names from the original shared table. Results/history already had
reviewed English. Earlier command/status checks excluded this field and did
not prove a wholly English screen. `docs/LOCATION_BANNER.md` records the gap,
correction and stronger native checks.

| Address space / exclusive range | Ownership / evidence | Certainty |
|---|---|---|
| ROM `[00019E44,00019E48)` | `dungeon-location-banner` owns one literal redirect: expected `08140D68`, replacement `088C626C` | Shared allocator checks source bytes and overlap. Only this four-byte field changes; all other ROM bytes and allocation records match the archived pre-fix build. |
| Expanded ROM `[008C626C,008C6CA4)` | Existing `result-shared-table`, owned by `results`; banner reuses offsets `[5D0,604)` | No new allocation. All 13 pointers and corresponding existing `results-ui` English payloads checked before reuse. |
| CPU `[08019E10,08019E28)` | Banner selection in main-menu producer `08019A98`: reads table literal, loads dungeon selector, adds `174`, scales by four, loads string, calls `08002298` at `08019E24` | Original Ghidra disassembly and actual native reader source/window observed. Bounded Thumb literal-load scan over original ROM `[0,5E000)` finds this literal referenced only at `19E10`; not a proof about arbitrary computed references. |
| EWRAM `[02003B6C,02003B70)` | Existing dungeon selector read via literal at ROM `19E48` | Natural Meadow value 11. Other banner names tested by changing r1 only at `08019E16`, after this load; the RAM dungeon ID remains unchanged. No new RAM ownership. |
| EWRAM `[02000030,02000048)` on the fresh root menu | Existing banner window descriptor | Native descriptor gives screen x64/y32, width168, initial x0, one row, proportional advance and zero extra spacing. This transient window is not new storage. |

The English strings are read directly from ROM with no new stack formatter.
Their maximum stored length is37 bytes including NUL; maximum advance is98px
(More Magic Dungeon), below168px. Main outer border x52 and banner outer border
x60 retain the8px gap. No name shortening, geometry edits or glyph changes.

`build/location-banner/research/main-menu-owner.txt` and `menu-trace.json`
retain static/native evidence. The39-case verifier covers13 names × three
command modes, opening/cancelling/reopening three times each. All five reader
fields and every drawn glyph are checked, including unknown/Japanese rejection.
The pre-fix ROM is rejected by the new check. Meadow/normal mode is an ordinary
fresh route; other IDs and the existing actor mode byte at `actor+90` are
controlled display probes, with save and real dungeon identity preserved.
No later class/dungeon unlock route is claimed.

Current ROM `7716f8c51c452499a1bb651acd24ccd20d3833531188fa66f0732cf3bb8307c8`;
previous ROM/ledger are archived in `build/location-banner/pre-fix/`. Evidence:
`build/location-banner/{report,acceptance}.json`. Resource counts remain3770
text and20 graphics; fixing this reader does not add new reviewed sources.

## Dungeon screen audit: gold separator (2026-09-30)

Ordinary mansion-floor-six walking reaches an existing 321-gold pile at (8,6).
On ROM `7716f8c51c452499a1bb651acd24ccd20d3833531188fa66f0732cf3bb8307c8`,
the actual message is `Picked up 321Gold.`. The amount/name formatter preserves
the Japanese no-space concatenation. This is an English spacing defect, not
evidence of Japanese pickup text on that route.

CPU `[0800F43C,0800F444)` loads its format from ROM `[0000F444,0000F448)`,
loads the signed item halfword at record+4, and branches to `0800F4CA`.
The shared tail `[0800F4CA,0800F4E0)` loads the reviewed item name and calls
formatter `08000FB8`, returning at `0800F4DE`. Original literal bytes are
`58 b4 06 08`; source ROM `[0006B458,0006B461)` is
`03 25 63 25 64 25 73 05 00` (colour, signed amount, name, colour reset).
Evidence: `build/coverage-audit/gold-branch.txt`, `gold-name-reader.txt`,
and the unfiltered native formatter/queue trace and gold screenshot under
`build/coverage-audit/dungeon/natural-gold-arrows-combat/`.

`tools.gold_spacing` owns only that four-byte literal and one appended private
format, adding the selected font's three-pixel word space between amount/name.
The original shared template remains untouched. Append after all existing
resources to preserve their addresses. The signed-halfword bound (six printable
characters), existing 30-byte/80px name reserve and outer markers fit the
64-byte item output and 162px row; no new RAM/save storage or window change.
Validation now passes on ROM
`c93c573ae1d0d4c643a580c04c8b385bd3d1b5381913763aca2abab078c22ea4`:
ordinary 321 gold and controlled 32767 gold pickups, 22 item cases and five
walking-pickup regressions. Existing allocations and all unrelated ROM bytes
match the previous build exactly (`build/coverage-audit/gold-delta.json`).
The original malformed message is rejected by the new scenario check.
Current evidence and limits: [DUNGEON_SCREEN_AUDIT.md](DUNGEON_SCREEN_AUDIT.md).

The screen audit observes queue entry at CPU `0801588C` and the post-hook
payload at `080158CE` (r6). The former may still be a Japanese static pointer
which the existing queue hook remaps before display. In the native Eat case,
`お腹が いっぱいになった` at entry becomes `You're full!` before glyph output.
Actual saved player-name bytes at EWRAM `[02003B58,02003B68)` are compared to
the exact prefix of the displayed use-message; the old earned save's Japanese
name is not an untranslated English-format defect. No new storage is claimed.

## Floor command and status refusal modals (2026-10-02)

The user-reported first-floor Floor notice was reproduced through ordinary
B, Down, A after the recorded fresh opening. Original static source ROM
`[0006481C,00064831)` is selected by shared slot030. The reviewed English
queue notice already existed, but this reader bypasses the queue hook.

The root owner begins at CPU08016C78. Its empty-floor branch at
CPU `[08016FA6,08016FB0)` loads the shared table from ROM
`[00016FB0,00016FB4)`, loads slot030 and calls CPU08017068. The modal owner
CPU `[08017068,080170C6)` creates `(8,9,21,1)` at screen `(64,72)` with168px
of one-line text, reads its immutable-ROM argument through08002298, waits for
input and closes the panel. It holds the source pointer in r4; there is no
formatted output buffer or new RAM requirement.

The sibling refusal selector CPU `[080170D4,08017150)` uses the table literal
ROM `[00017154,00017158)`. Selectors0/1/2 represent item/floor, trap and stairs
eligibility. Its complete source set is slots0C8 (fallback),3E4 (transformed),
408 (frightened),3C8 (dancing). Native predicates08019E4C/08019E74/08019EA8
read existing hero bytes+BF/+9C/+9A with different combinations. Status priority
and all gameplay predicates remain unchanged. These are existing actor-relative
fields, not new RAM/save ownership.

`tools.floor_notice_text` owns both four-byte literals, each with expected
original bytes `68 0d 14 08`. It copies the original table prefix ROM
`[00140D68,00141174)` and changes only the five audited slots. Four reuse owned
queue-notice English resources. The transformed refusal receives the reviewed
context variant “Can't do that while transformed.” (162px), because the
queue's full-subject wording measures183px. Other widths are113/139/162/166px.
No geometry, original strings, code instructions or save format are changed.

On the recorded build, appended ROM `[009421D4,00942215)` owns the65-byte
variant, and `[00942218,00942624)` owns the1036-byte private table. Alignment
bytes are tracked byRomBuild. Allocations occur after the previous last
resource; every prior allocation and unrelated ROM byte is unchanged.
Evidence: `build/floor-menu/{floor-conditions,floor-range,floor-owners}.txt`,
`delta.json`, `native/report.json`, `negative-control/report.json`,
`acceptance.json` and the screenshot gallery. All ranges here are exclusive.

The unfiltered audit passes13 cases on ROM
`dd21b782b9a0bfa98722e664036cc29825afb466f3994c442d8059b08c8e0c89`:
three ordinary routes (empty first-floor tile, native Drop then Floor, native
walk then Stairs), and ten explicit mode/tile/status probes. Each opens and
cancels three times;30 modal returns preserve caller registers/stack guards.
It checks all7,808 observed glyph draws, one-line bounds, unchanged inspected
tile/inventory/battery and restoration of the parent panels and underlying BG3
tiles independently of animated sprites. The original blank marker874F in the
first glyph of a one-row ground-item window has a narrowly scoped audit
exception matching its native `(8,24)` origin,6px inset and168px width.

The same13-case audit rejects the previousc93c573a… ROM's ten modal cases for
Japanese output; item/trap/stairs selection branches pass on both ROMs. The
fallback slot0C8 is source-checked but not reached in these successful routes.
Further39 root-menu cases, six Step/Stairs choice cases and135 unit tests pass.
Source ROM/save hashes are preserved. Native class unlocking, trap effects,
status expiry and full-game coverage are separate. See [Floor menu](FLOOR_MENU.md).

Exploratory observation outside that accepted matrix: queue caller CPU080096F9
passed generated IWRAM text at03007A40 containing an English player name followed
by Japanese fear/dance-expiry text after one-turn controlled status values
elapsed. This occurred while the initial harness accidentally cancelled an
automatic stairs prompt instead of opening the root menu. It establishes a
separate observed display gap, not its original-source ownership, buffer extent,
ordinary acquisition route or insertion. No storage claim follows from that
scratch pointer. Dedicated retained reproduction remains in
[Text investigations](TEXT_OPEN_QUESTIONS.md#remaining-gameplay-evidence).
This historical observation is the fear/dancing subset of the seven-message
repair recorded below. It is resolved in ROMaa12a37b…; it is not an additional
unfixed expiry reader.

## Modal caller audit and status expiry follow-up (2026-10-02)

The subsequent static audit finds four Thumb BL sites targeting08017068 across
the source and compiled ROMs:08016F28/08016F56/08016FAA/08017224. Ghidra confirms
the first three in owner08016C78 and the fourth in owner080171E0. The fourth
loads the table literal ROM `[00017238,0001723C)` and slot034, whose original
text lies in ROM `[00064800,00064819)`. It was missed by the preceding Floor
fix. Its literal now uses the existing floor-notice private table, whose slot034
reuses “You have no items.” from the owned queue-notice allocation. Expected
original literal bytes remain `68 0d 14 08`. Only this literal and the private
table pointer cell ROM `[0094224C,00942250)` differ fromdd21b782…; all other
bytes and allocation addresses remain identical. No new RAM/save ownership.

`tools.audit_reader_routes` fails for any unaccounted direct modal call pattern
or unbound selector, without filtering reviewed sources out of the result.
It also retains623 provisional shared-table literal-load candidates across
original ROM `[00000000,0005E000)`. Those candidates include unresolved code/data
and queue-remapping questions and are explicitly not a bug count. Previous
exploratory scripts retained broader JSON leads but printed only sources marked
untranslated; that source-level filter could hide missed readers of reviewed text.

The native turn handler CPU `[08008F4C,08009832)` includes the separate expiry
loop. ROM `[00009748,0000974C)` still selects the original shared table.
CPU096D8 loads a selector from the stack list,096DE loads its text pointer,
096E2 gets the player's name,096EC calls formatter08000FB8, and096F4 queues
the generated text. The output starts atSP+50; the next scratch region starts
atSP+150, giving an apparent256-byte region requiring formal bounds for insertion.
This generated buffer bypasses the player-message wrapper used by other
consumers. Static notices can still be translated by the queue's copied-text hook.

The disassembled selector construction drives20 automated timer probes through
native turn entry, with a single controlled actor timer set to1. Seven rendered
outputs are Japanese: slots17C/180/184/188/3C0/3E0/8FC for actor bytes
95/96/97/98/9A/9C/AB. All seven include a player-name substitution. Thirteen
other timer branches display English. Transformation uses a separate direct
queue call at08008FAC (return08008FB1); its earlier25C scratch selector is cleared
before the common loop and is not a reached loop case in these probes.
Two immobilization timers and two speed timers share their respective messages.

Evidence: `build/reader-audit/{menu-siblings,status-expiry-owner}.txt`,
`routes.json`, `routes-before.json`, `inventory-delta.json`,
`native/report.json`, `negative-control/report.json`, `status-expiry/report.json`.
Fourteen menu cases pass, including ordinary consumption of the opening bread
then empty Items, while the preceding ROM fails that extra case for Japanese.
At this pre-repair stage the seven expiry failures remained unresolved. Sources, inputs, controlled writes,
actual queue/glyph observations and battery preservation are retained; normal
status acquisition and whole-game completeness are not inferred.
Pre-expiry-repair ROM: `eb04b1a6c4c74e448f8f3fab0f538b0f92f3f2eea3c9a95e115cfa74a8f1a2ea`.

## Computed status-expiry reader repair (2026-10-02)

The seven failures above are now repaired by `tools.status_expiry_text` and
`translations/status-expiry-review.json`. CPU `[08008F4C,08009832)` retains its
instructions and timer semantics. The sole new original-ROM patch owns literal
`[00009748,0000974C)`: expected `68 0d 14 08`, replacement `cc 26 94 08` in this
build. Load080096C6 now supplies the private654-pointer table at CPU089426CC.
Only slots17C/180/184/188/3C0/3E0/8FC change; all647 sibling entries and the
original shared table ROM `[00140D68,001417A0)` are preserved.

`RomBuild` owns these appended ROM resources with exclusive ranges:

| ROM file range | Ownership |
| --- | --- |
| `[00942624,00942650)` | Confusion format, with a conditional break after the possessive name. |
| `[00942650,00942684)` | Hallucination format, with a conditional break after the name. |
| `[00942684,00942699)` | Newly reviewed sleep-recovery format. |
| `[0094269C,009426C9)` | Newly reviewed fear-recovery format. |
| `[009426CC,00943104)` | Private copy of the654-pointer shared table. |

The intervening3-byte alignments are explicit FF padding in the allocation
ledger. Three formats reuse existing owned English payloads: blindness008B1B78,
dancing008B1838 and item recognition008B1BFC. Existing allocation addresses and
payloads are unchanged. Original source records are hash-checked against the
review catalog; no source gaps or original padding are claimed as free space.

The handler allocates0x3A0 stack bytes (literal ROM000090CC=`60 fc ff ff`).
Instruction080096C4 sets output to SP+50, and08009786 uses the next scratch at
SP+150. Thus the verified expiry output is the256-byte stack-relative interval
`[SP+50,SP+150)` in IWRAM, not new permanent storage. Native checks assert that
destination, exact expansion,16-byte adjacent guard and formatter/queue/handler
register/SP preservation. No RAM/save allocation or stack-size change is made.

Getter CPU `[08009ACC,08009C02)` with argument0 returns the saved player glyph
string at EWRAM `[02003B58,02003B68)` when actor+BF is zero. While transformed it
instead uses the signed identity halfword at EWRAM `[02003BAA,02003BAC)` and the
loaded monster definition's base-name pointer. Both branches are disassembled
and natively observed. Maximum saved name:98px/14 content bytes. Maximum current
monster base name:114px/44 content bytes, Crack-billed platypunk. Budgets use the
larger field; the largest complete encoded expiry output is100 bytes including
NUL, and conditional line segments are bounded by216px. No leveled-name suffix
is used by this getter's player/transformation branch.

All44 controlled native cases pass, covering20 recovered timer branches,
maximum English/Japanese saved names, seven widest-transformation cases and
three simultaneous-seven-expiry cases. The checks see49 exact repaired-message
queues/1,358 exact glyph draws and1,609 unfiltered glyph draws; the old ROM fails
exactly seven baseline cases for Japanese, with all20 routes reached. Source
ROM/save and fixture batteries are unchanged. Normal status acquisition and
other readers remain separate coverage questions.

Evidence: `build/status-expiry/{player-getter.txt,routes.json,routes-before.json,
acceptance.json,native/report.json,negative-control/report.json}` and
`build/reader-audit/status-expiry-owner.txt`. Current ROM:
`aa12a37b76e49d44f8a336642d334fa8324d92c2d98457200482742ea5b46723`.

## Broader caller-coverage audit (2026-10-02)

`tools.audit_text_callers` scans CPU `[08000000,0805E000)` for direct Thumb call
patterns to08000FB8/08015848/0801588C/08017068/08002298/080021B4. It retains
1,025 patterns, constant-flow candidates for650 sites and375 unresolved call
arguments. It follows both original and compiled literal/table reads without
filtering by source review status. This is provisional code/data and branch
analysis, not a reachability proof. Computed indices, indirect calls, other
readers and763 budget-limited seed traversals remain explicitly unresolved.

The42 native follow-ups confirm23 additional untranslated call sites using18
source sentences already inserted elsewhere. There are41 Japanese scenarios
and one English control, not41 distinct defects. No ROM patches, new RAM or
save ownership are introduced by this audit. The source ROM/save and disposable
fixture batteries are hash-checked unchanged. See
[caller coverage audit](CALLER_COVERAGE_AUDIT.md) for all confirmed calls and34 remaining static leads.

Five failures use ordinary menu buttons after recorded item/status setup:

| Address space / exclusive range | Discovery and evidence |
| --- | --- |
| CPU `[080175B4,0801775C)` | Dungeon item-target selector. Call `[0801768A,0801768E)` reads original slot014 via ROM literal `[000176D0,000176D4)`. Peep scroll Read reaches the Japanese heading with normal buttons. The translated town/synthesis selector owns a different literal,0001DDE4. |
| CPU `[08017A4C,08017EEE)` | Item Info. Actor+AB is read at08017A76..08017A80; a nonzero recognition-block timer selects source8F8 through call `[08017A9C,08017AA0)`, before the ordinary item-description branch. Native setup writes only that existing actor byte, then uses Info. |
| CPU `[08032708,08032E04)` | Eating/consumption dispatcher. Item206 selects08033238;208 selects08033428. Native inventory records use existing120-byte slots beginning EWRAM0200DF28, known type flags at02003BAC+20*ID, and no inscription bit. |
| CPU `[08033238,080332C6)` | Giant bread handler. Call `[080332AE,080332B2)` formats original source0D0 with the actual new maximum fullness, then queues at080332BA. Normal Eat shows105 in Japanese after English consumption/fullness notices. |
| CPU `[08033428,080334E0)` | Putrid bread handler. Call `[080334B8,080334BC)` formats original source0DC with player name and strength loss. Normal Eat reproduces the Japanese result. |
| CPU `[08033A14,08033AAE)` | Strength-seed helper. Normal Drink reaches call `[08033A5C,08033A60)`, using original source108 despite the player-message wrapper's English version of that source. |

CPU `[08037D80,08038434)` is an item-impact dispatcher. Ghidra confirms
selectors171/175/181 reaching08039420/080390B4/080395B0, respectively. Their
separate actor-target probes run actual native handlers and message code with
controlled entry/arguments; ordinary impact/AI routes are not claimed by those
probes. The blindness recovery in08039420 is distinct from the repaired timer
loop at080096EC. Both readers use source188, but have different table literals.

The nearest-PUSH discovery heuristic misidentified original literal08017648
(`50 b5 06 08`, a text pointer) as a function prologue. The full owner080175B4
and native selector trace resolve it. This is concrete evidence that candidate
disassembly starts cannot alone establish executable ownership or free space.

Evidence: `build/caller-audit/{static.json,static-negative-control.json,
followup-owners.txt,dispatchers.txt,native/report.json,summary.json,index.html}`.
The Ghidra disassembly and actual caller/source/glyph observations are retained
together. Four caller-tracer unit checks pass. The old Floor/empty-Items ROM is
flagged by the static negative control; the current bindings classify as
English. Current ROM remainsaa12a37b…; the23 new findings are an open repair
backlog, and no whole-game remaining-defect count is established.

### Continued caller audit, 2026-10-02: branches, modal wrappers and uncatalogued literals

This is research on unchanged ROM SHA
`aa12a37b76e49d44f8a336642d334fa8324d92c2d98457200482742ea5b46723`.
It grants no new insertion, padding, RAM or save ownership. The preceding
23-site audit is the first pass; the continuation confirms54 caller sites,
with31 additions. Full per-caller source/output evidence is in
`build/caller-audit/summary.json`; review/insertion totals are unchanged.

**Reader discovery (GBA CPU addresses).** Ghidra `extra-readers.txt` and
`modal-reader.txt` establish `08015A18` and `08015A34` preserving the source in
r0 when calling `08015A50`. That owner holds it in r7 and forwards it as r1 to
window reader `08002298` at `08015ADA`. The source is independent of the
Floor-modal family `08017068`. `0805CF54` copies a terminated byte string from
r1 to r0; a Japanese source passed here alone is not proof of Japanese output.
Three controlled level-one cases (`08033410`, `08033864`, `08035AFC`) execute
that copy and subsequently draw English through existing queue remapping.
The identification copy at `08033B9C` remains a separate unconfirmed lead.

**Marked Storage-pot menu.** Owner entry `08017F04`, disassembled in
`container-owners.txt`, draws original source CPU `[0806B5B0,0806B5B5)` using
literal `[08018024,08018028)` and call `08018002`. It reads the existing marked
selection count from `08016BA0`; input dispatcher `08016B30` tests key mask300
(L/R) and updates marks through `08016B1C`. The original menu is40px wide,
one row at(192,24), with the existing style/cursor behavior. Normal View(42),
R, Down, R, A after controlled two-item contents draws Japanese Take. This
source has the same bytes as reviewed action source08064940 but is a separate
literal/binding outside the catalog pointer list. No geometry or text changes
were made. The contents records use the previously established item record's
seven12-byte slots beginning at+18hex; no extra storage is allocated.

**Trap discovery.** In attack/action owner `08023C14`, instruction region
`[080241B6,080241FE)` checks the adjacent map cell's halfword+0A againstFFFF
and bit8000. It sets8000 for a newly discovered trap, checks `0801211C`, and
passes shared-table slotA10 to choice-modal wrapper `08015A18` at080241FA.
Normal A with a controlled adjacent selector0 and facing2 draws Japanese
“Found a trap!”; the source is already reviewed elsewhere. This is not the
standing-trap Floor menu. Existing direction table CPU `[08140B18,08140B58)`
contains eight signed(x,y) pairs; selector2=(1,0), verified before the controlled
floor-item scenario. Map associations/flags use the existing28-byte cells from
`tools.name_entry_playtest.MAP`, not newly allocated RAM.

**Effect branch controls.** `remaining-owners.txt` and `branch-helpers.txt`
record the actual handler arguments and preconditions. Actor flags at relative
`[+08,+0C)` include40000000 for the tested strength-loss resistance; current
strength is the signed halfword `[+76,+78)`, level `[+88,+8A)`, blindness timer
byte+98, wakefulness byte+A4 and Kaclang byte+9B. `0800ADCC` tests+A4 for the
sleep-resisted branch. Handler08033A14 has separate full-strength and
partial-recovery formatter sites33A5C/33A9A. Item recovery sites33802/348D2 are
separate from the repaired timer reader. The Rotten-bread switch starts at
080332C8 and selects random outcomes0..5; continuation probes select0,2,5
and the resistance variant at080332DC, after the native RNG has executed and
before its comparison. H. Pocus handler080356E8 similarly selects allowed
outcome4 at080356F8 for level loss. These are explicit controlled random
branches, not natural item-outcome claims.

**Summons and item capacity.** The native summoner080131BC scans neighboring
walkable cells; clearing4000 in their existing map flags makes it fail normally.
No summoner return value is replaced. Native allocator08013F20 scans the128
120-byte floor-item records at EWRAM `[0202EDA8,020329A8)` for a clear80000000
occupancy bit. Occupying those bits at controlled handler entry exercises
allocation failure in landing/spill/scatter functions. The probe records every
write; it does not claim those synthetic records came from ordinary gameplay.
Eight-argument handler08038644 uses the existing caller stack; the diagnostic
supplies additional argument words at entry and restores the original words
at its verified return before normal execution continues. ABI checks cover
saved r4-r11 and SP. This is not authorization to reuse any stack/RAM interval
in the translation build.

**False lead removed.** Options help owner0801A794 reads four rows of eight
halfword selectors from CPU `[0806B736,0806B776)`, indexed by supported modes
0..3. None selects the cursed notice08064410. The first scanner ignored known
CMP outcomes and allowed the loop to run past its eight entries, generating
that spurious candidate at0801A9B0. The refined tracer invalidates APSR facts
after unknown flag writers/calls and prunes only comparisons with known
outcomes. A checked selector enumeration and seven focused tracer tests retain
this distinction between static leads and reachable branches.

**Additional static leads.** `static-wrappers.json` covers1,171 direct patterns
to ten consumers, with759 sites having argument candidates and412 unresolved.
It retains20 unconfirmed Japanese-argument sites, one unresolved copied refusal
and794 budget-limited traversals. Six additional uncatalogued Japanese modal
source pointers and link success source0806ED58 are recorded as leads, not
newly reviewed/inserted text. The existing source-level catalog is not expanded
merely by a candidate decode. `exchange-success-block.txt` disassembles CPU
`[08058610,0805867A)`: the success tail formats source0806ED58 at0805866E,
using source literal `[08058698,0805869C)`, then passes the stack result to
08057BDC. It has no insertion or native two-device transfer acceptance here.

The original five remaining leads are0801CD00/080570F0 (result/history default
selectors) and0802AF54/0802B0FC/0802CD7E (projectile/landing branches).
`projectile-branches.txt` and the retained trials document the attempted
branches. Two complete handler returns did not reach the expected landing
callers and are recorded as incomplete, with no language conclusion. The
Silver-arrow condition selects item80; the inspected first-floor definition
snapshot has no species selecting80. This does not prove the branch unused in
all definition states.

Current evidence includes79 scenarios:73 Japanese, four English controls and
two incomplete routes, representing54 distinct confirmed callers rather than
73 defects. Eight routes use normal buttons after explicit setup; other cases
control native entry, arguments/state and sometimes RNG outcomes. Source
pointers and text readers are never replaced. All batteries and original ROM/
save hashes remain unchanged. Some handler-only output clears within a frame;
queue/reader-linked glyph traces establish those messages, not blank captures.
The gallery has inspected visible panels for the newly demonstrated Storage-pot,
trap-discovery and invisible-item scenarios. Historical first-pass evidence is
retained as `first-pass-summary.json` and `first-pass-index.html`.

## Confirmed missed caller bindings (2026-10-02)

The 54 native-confirmed routes in `translations/caller-repairs-review.json`
own only the 52 enumerated four-byte ROM literals, each `[literal_offset,
literal_offset+4)`, and appended resources allocated by `RomBuild`. The catalog
pins each original literal and the 28-byte instruction context ending after
the consumer call. Ghidra owners are retained under `build/caller-audit/` in
`remaining-owners.txt`, `followup-owners.txt`, `container-owners.txt`,
`dispatchers.txt`, and `modal-owners.txt`. Native caller/destination/glyph
correlation is in `summary.json`, with original inputs and state controls.

Each private table copies ROM `[00140D68,001417A0)` and changes only the slots
used by that literal's confirmed routes. Identical per-literal slot sets may
share a copy. All other sibling slots remain byte-identical to the original.
Relative-table literals `0002C5E4`, `00033E44`, and `00039048` originally point
to `08140E88`, `08140F58`, and `08140F38` respectively; preserve these offsets.
Direct literal `[00018024,00018028)` selects the separate marked-pot Take
source `[0006B5B0,0006B5B5)`, identical in content to the approved Take action.
Its original window is 40 px, with a 36 px text region; selector Which? uses
its original 40 px heading. Other repaired messages use the original 216 px
line budget. No window geometry changes.

Formatted destinations retain their disassembled 256-byte scratch buffers.
Most start at SP, with offsets +4, +8, or +1C in larger frames; the scatter
handler uses its existing r10 scratch destination. Native acceptance must
check destination bytes, a 16-byte guard at destination+256, preserved
formatter registers/SP, and all visible glyphs. Actor/item substitutions
are bounded to 63 bytes, with 186/162 px widths; signed decimal formatting
is budgeted for 11 characters. Conditional breaks preserve one-line output
when the complete substitutions fit. This introduces no new RAM/save
ownership and leaves the original shared table and source strings unchanged.

Exact literal ROM offsets:

`0000CC98, 000176D0, 00017AE8, 00018024, 000242D4, 000258E0, 00026758, 000286A0, 000286EC, 0002C300, 0002C5E4, 0002C66C, 0002C700, 0002C768, 00033290, 00033338, 00033384, 000333C0, 00033404, 0003347C, 00033810, 00033858, 00033A68, 00033AB0, 00033E44, 000348F0, 00035AF0, 00035C3C, 00035DBC, 00036C34, 0003788C, 000378B8, 00038610, 0003876C, 000387C4, 00038D08, 00039048, 000390E8, 00039154, 0003923C, 00039350, 00039464, 00039538, 00039604, 00039664, 000396C8, 00039CAC, 00039DB0, 00039FD8, 0003A01C, 0003E31C, 00040D78`.

Follow-up ownership: ROM literal `[00038D08,00038D0C)` is shared with
the existing item-loss family; its replacement inherits that family's full
private table before adding slot 1D0. Slot 34C and all prior English siblings
are preserved. Its patch is deferred to the shared caller-repair builder,
avoiding overlapping patch ownership.

Recognition-blocked item naming: CPU `0800EF30` tests actor byte +AB and
selects shared slot 1CC through literal `[0000EF70,0000EF74)`, copying it
at `0800EF64` to SP+8. Source and replacement both contain nine bytes
including NUL. The four wide question marks become four compact question
marks, without changing meaning. This private table owns only slot 1CC;
Ghidra evidence is `build/caller-repair/item-placeholder-owners.txt`. The
ordinary Info route records this caller and its displayed item row. No new
item-name capacity is assumed.

Verified cumulative allocation envelope for caller repairs: ROM offsets
`[00943104,0095ACD0)`, CPU cartridge `[08943104,0895ACD0)`,
with exact resource ranges and alignment padding owned only by the shared
allocator ledger. The build adds 49 allocations, including 37 private
tables; reused payloads remain in their original allocations. All 3,965
prior allocations are byte-identical, and the 159 changed original-ROM bytes
are contained in the 53 enumerated literal words. Evidence:
`build/caller-repair/repro.json` and `receipt.json`; ROM `c19475eee8cd5c77601a634654b036301d779a59b3bb0adf7cc092b585fc4b7a`.


## Caller continuation ownership (2026-10-02)

The twenty remaining static leads execute original message blocks in complete
native frames in `tools.audit_remaining_callers`; baseline evidence is in
`build/caller-continuation/baseline` and `baseline-more` (ROM c19475ee...).
The adjacent Stone's murmur acquisition at CPU0801C640 passes source in r1 to
0801C958, which forwards it to modal08015A18 at0801CA1A. Its source was also
Japanese. The copied refusal at08033B9C is already translated by byte matching
at the queue; retain that source/consumer and use it as an English control.

All ranges below are file offsets, end exclusive. No original string range,
padding, new RAM or save storage is claimed. `translations/remaining-callers-review.json`
pins source bytes and32-byte call contexts. Appended resources use RomBuild.
Private shared copies cover[140D68,1417A0); their only changed slots are834,
A04/A08,644,388,C8,1C8 or1D4 for the individual literals. Literal056C8,014BAC,
01B494,027318,02AFB8,02B11C and02CDB0 select these private tables. Result/history
literals01CD3C/0571B4 inherit the entire existing `results.shared_table`, changing
only slotC8; their earlier patch owner explicitly delegates those two words.
The first source table[147234,147248) has translated tutorial/Imp siblings:
copy current build bytes and change only slot0 for01B5C4. The cutscene table
[147248,14725C) changes slots0,4,8,C for01C668, preserving unread farewell slot10.
The melody table[14725C,147264) changes both slots for01BA90.
Direct pointer words04AC08,04BA64,04BA74 and058698 bind the locked notice,
strong-monster warning, overwrite prompt and trade-completion format.
Projectile definition words02AFBC/02B120 select the existing complete English
`item-definitions` copy (221 records,24 bytes each), preserving effects/IDs.

Native frame ownership: arrow output SP+10..SP+110 is256 bytes; disarmed-item
name SP+10..SP+50 is64 bytes and output SP+50..SP+150 is256 bytes. Link completion
output SP+8..SP+88 is128 bytes; item field SP+88..SP+C8 is64 bytes. Native formatter
checks observe original source selection and output guards. Story/modal streams
read directly from ROM; two rows,224px native/216px authored budget. Saved-village
control1F uses the existing20-byte name scratch0200CEE8..0200CEFC and eight cells
(max112px); it is not a player-name alias. Family callback0801B674 invokes
08006BB0 and returns0100000A for@w@ or01000014 for@W@; retain all37 commands in
order, the original callback pointer and10/20-frame pacing semantics.

Controlled probes skip pre/post-dialog world effects (including deletion, link
transfer and saving). Result/history default0x32 is exercised deliberately;
its ordinary reachability is not asserted. This is caller/rendering evidence,
not natural late-game progression acceptance.

Forwarder follow-up: CPU08057B54 takes text in r0, preserves it in r5,
and forwards to08002298 at08057B84; 08057BDC takes r0 and forwards to
08015A34 at08057C08. Adding those consumers exposed link-status direct
literals[058220,058224) and[05868C,058690), selecting ROM06ECF0 and06ED24.
Both are centered two-row warnings and read directly from ROM. These two
words are additionally owned by `remaining-callers`; the original full
link-owner frame/message blocks execute in disposable native probes, while
the actual transfer and save are skipped.

Blacksmith raw-name producers: original CPU literals0801D188,0801D1B8,
0801D200,0801D284,0801D3E0 and0801D444 (each four bytes) contain08141B9C,
the original221-record item-definition table. Six native formatter calls
0801D17C,0801D1A2,0801D1F6,0801D21C,0801D3D4 and0801D3F6 read record+0
names, bypassing the translated naming helper. Own these six literal words
only and bind them to the existing English item-definitions allocation.
The table's numeric fields are unchanged. Original512-byte stack output
[SP,SP+200) remains unchanged; no new RAM or save allocation. Ghidra evidence:
`build/caller-continuation/item-field-owners.txt`; six Japanese baseline cases:
`build/caller-continuation/item-baseline/report.json`. Recipe IDs are controlled
inputs; source/field producers and complete original frames execute unchanged.
The Remi literal0801ECE0 is a non-name control: its constant offset1464 is
record217*24+0C, the Iron safe price. Its native offer is already English.

Continuation allocation envelope: file offsets[0095ACD0,00960EBC), CPU cartridge
[0895ACD0,08960EBC),21 allocations with exact resource/padding ownership only
in the shared ledger. Final ROM81f8b1aa13f6d67d0d9d83ebe4abaef276887e30d46b60442bffe4082e5275d6
preserves all4,014 earlier allocations. Exactly78 original-ROM bytes change
inside26 checked four-byte literals. The80-load definition consumer inventory
is pinned in `config/item-definition-consumers.json`;27 loads use owned English
copies (two skill loads use their existing48-record subset),53 use only numeric
record fields. No interior definition-table literal provides an extra name
consumer in Thumb[08000000,0805E000). Receipt: `build/caller-continuation/receipt.json`.


## English custom item-name categories and formats (2026-10-02)

Addresses below are ROM file offsets unless prefixed with a CPU address.
Owner `custom-items`, implemented by `tools/custom_item_text.py`, copies the
original 14-pointer category table `[00143EE0,00143F18)` into a private appended
allocation. All original table bytes and strings remain intact. The native
owner is CPU `0800F244`; its indexed name decoder still accepts eight glyph
indices and writes through its existing 64-byte scratch. No new RAM/save storage
is allocated, and name indices, colour state, category/name/count order and
menu geometry are preserved.

| Original literal interval (exclusive) | Required original word | Replacement role |
| --- | --- | --- |
| `[0000F58C,0000F590)` | `08143EE0` | Private 14-category table |
| `[0000F59C,0000F5A0)` | `08143EE0` | Private 14-category table |
| `[0000F5B8,0000F5BC)` | `08143EE0` | Private 14-category table |
| `[0000F588,0000F58C)` | `0806B484` | Counted category/name format |
| `[0000F598,0000F59C)` | `0806B438` | Plain category/name format |
| `[0000F5B4,0000F5B8)` | `0806B438` | Plain category/name format |

For ROM `2c88892deb78aa2bd000d8326c1e89d110cf82c34bf3fc51ab72ae8f09be1e65`,
the 14 English strings occupy separate checked allocations within
`[00960EBC,00960F6D)`; intervening alignment bytes are allocator padding, not
additional free space. The private table is `[00960F70,00960FA8)`, counted format
`[00960FA8,00960FB8)`, and plain format `[00960FB8,00960FC2)`. These offsets are
build-specific; the shared `RomBuild` ledger is authoritative. Seventeen
allocations add 16 text resources. All earlier allocations are preserved, and
only the six listed original literal words change from the preceding build.

Thirty native cases cover six nameable categories with English custom names in
inventory and storage, prices, counts, equipped/cursed markers, repeated action
opens/cancels and actual storage deposit/withdrawal under controlled setup.
Exact native bytes, 64-byte guards, ABI, glyphs, numeric cells and unchanged name
and battery bytes pass. Storage item rows have 168px windows; its 100px columns
are command labels. Eight widest English letters occupy one line with ink edges
88–105px and the tested price column at 121px. Japanese custom-name width is not
an acceptance requirement. See `docs/LOCALIZATION_CLOSURE.md` and
`build/localization-closure/candidate/custom-items-validation/report.json`.

### Caller and event follow-on research

`tools.audit_source_readers` models paired original/compiled RAM images only for
the verified town relocation at EWRAM `[020141AC,0201465C)` and its following
resource data. This does not grant RAM ownership or apply to unrelated phases
that reuse the same addresses. Synthetic stack addresses near `10000000` are
analysis tags, not GBA memory discoveries or allocated buffers. Four checked
service entry helpers substitute private tables. Observed dispatcher arguments
are propagated into other native service owners. The initial pass left 54 shared
and 10 town sources without a resolved reader. Manual follow-up found the wind
selector below; the final bounded scan leaves 53 shared and 10 town sources.
None are declared unused or safe to overwrite.

The deeper service pass raises its per-path bound to 4,096 instructions. Its four
verified private entry contexts finish without path/budget cutoffs; the bank
and other loops still report cutoffs. Of 529 original unresolved direct-call
arguments, 102 now bind checked English resources, 307 have producer candidates,
five are buffer leads followed manually, and 115 retain unresolved data flow.
These classifications do not assert native reachability or English contents for
unknown buffers. Evidence: `build/localization-closure/source-readers-deep.json`.

Storage selector CPU `0801F2D8` receives the town table in r0 from the literal
at ROM `[0005019C,000501A0)` and retains it in r4. Its switch at CPU `0801F35C`
uses ROM `[0001F364,0001F384)`, eight branch pointers whose full bytes are checked
against both ROMs. The branches pass the table in r1 to seven action owners,
and in r0 to `0801E490`. `tools.audit_storage_readers` follows these actual
argument transfers: 19 contexts, 17 table-read candidates, no read of the ten
unresolved town sources; three contexts exhaust their step budget. This is
bounded static evidence, not an assertion that every menu option is available.

The five automatic buffer leads have identifiable producers. CPU `08016294`
reads the amount editor's SP+`1C` buffer, written as eight two-byte glyphs in
`[08016250,08016280)` and appended at `08016284`. Literal ROM
`[000162B8,000162BC)` selects the original numeric table at ROM `00147EB8`;
the 11 entries are the existing `8196` padding marker and `824F`..`8258` digits.
Its only two direct callers, `0801E046` and `0801E0F6`, are bank paths. CPU
`08019490`/`080196DC` consume buffers assembled through the existing concatenator
`0805CE24` at `0801944E`/`0801969A`, after main/child action formatting.
CPU `08019DD4` consumes SP+`10`, written at `08019B0E` from private UI-table
slot `50`. CPU `08019E08` consumes SP+`110`, written by the vocation root format
at `08019CB6`/`08019CC6`, followed by ground/Option concatenation at
`08019D48`/`08019D50`. These are existing buffers and code, not new storage
ownership. Disassembly, native verification families and limits are linked in
`docs/LOCALIZATION_CLOSURE.md`.

The original event dispatcher table is ROM `[0014CE30,0014CEBC)`; opcode `n`
uses word `n-1`. Six controlled follow-on cases in `tools.research_event_stubs`
execute the original bank loader, NPC selector and flag/dialogue/choice/actor
handlers. The host performs opcode dispatch and skips WAIT before END; this is
not a full native story route. Both bank-3 map-11 NPC selectors choose the same
single-character prompt; Yes reaches source `.3ef9` and No `.3ec5`. Bank-4 map-5
selector 1 reads flag `82`: clear displays `.0c68` and sets the flag, set displays
`.0d25` and ends. No handler supplies missing text. See `EVENT_STUB_AUDIT.md` for
the source-faithful evidence and the subsequently approved editorial repairs.

On 2026-10-02 the user approved insertion of those two repairs. The owned decoded
event-table words are bank 3 `[00000214,00000218)` (group 23/index 0, original
relative `00000000`) and bank 4 `[00000104,00000108)` (group 6/index 1, original
relative `000000BD`). Original source intervals are bank 3 `[00003EC2,00003EC5)`
(`83 54 00`) and bank 4 `[00000D25,00000D28)` (`82 C8 00`). `add_prose` verifies
these source hashes and original slot values before allocating either stream;
the shared bank assembly verifies all non-slot bytes and original decoded sizes.

In the 3,813-resource ROM, the new English streams occupy ROM-file ranges
`[00850844,008508AE)` and `[008508B0,00850936)` (CPU addresses add `08000000`).
Both allocations belong to `event-prose` in the `RomBuild` ledger. No source
padding is reused and no RAM/save range is allocated. The original flag-`82`
byte remains EWRAM `[020101BC,020101BD)`, mask `04`; the first boy conversation
sets it and the repeat preserves it. This describes existing state, not new
storage ownership.

Eight native branch cases verify the original bank/NPC selectors, Yes/No/B
outcomes, flag byte, full reads, glyph bitmaps, visible repair pixels, original
224px/two-row windows and handler guards. Host dispatch and skipped WAIT remain
explicit controls; ordinary story access is unproven. All 1,046 native event
getters pass. `build/event-stub-repair/delta.json` accounts for every prior
allocation/patch after exact pointer relocation, with only these two new bindings;
scripts and all other decoded bytes are preserved. See `EVENT_STUB_AUDIT.md`
for exact English, user approval and editorial provenance.

### Computed final wind warning — confirmed missed reader

Manual follow-up of unresolved CPU call `080051F0` identifies a computed
shared-table selector. ROM `[0013EDF0,0013EDFA)` is the five-entry u16 table
`0000,0000,0114,0115,0116` (hex); native stage EWRAM `[02003B38,02003B3C)` indexes it. The
previous stage is EWRAM `[02003B34,02003B38)`. These are existing wind state,
not new allocations. For stage4, shared slot `458` supplies source ROM
`[00062C10,00062C24)` (`%sは風にさらわれた!`) to the player wrapper `08015848`.
Its existing formatter uses the 256-byte stack output, then the queue. Because
the resulting string contains a player name, the static copied-notice adapter
does not translate it. Stages2/3 use already-mapped static notices.

Controlled native probes set only the current/previous wind stage at CPU
`08005150`, then execute the original animation, selector, player formatter and
queue through ordinary A input. On the 3,801-resource ROM, stages2/3 have zero
unclassified glyphs; stage4 draws nine Japanese text glyphs outside the saved
player name. Evidence: `build/localization-closure/wind-baseline/` and
`dynamic-owner-followup.txt`. This supersedes the earlier no-resolved-reader
finding for this source; the automatic scan missed the computed index.

Insertion owner `wind` owns only ROM literal `[00005220,00005224)`,
expected word `08140D68`. A private copy of original shared table
`[00140D68,001417A0)` changes only slot458 to an appended English format.
All original table/string bytes, sibling entries, native logic, frame sizes
and save layout remain unchanged. “The wind swept {player} away!” measures
207px including the 98px saved-name bound; maximum output is 57 bytes in the
existing 256-byte buffer. `RomBuild` assigns format `[00960FC4,00960FF1)` and
private table `[00960FF4,00961A2C)` in the 3,811-resource ROM. Six native cases
pass stages2/3, stage4 with four name profiles, exact formatter/queue glyphs,
guards/ABI and original expulsion outcome. Report: `build/english/wind-validation/report.json`.

### Town overview labels — computed reader follow-up (2026-10-02)

Confirmed original ROM `[0014D4CC,0014D52C)` has twelve eight-byte descriptors:
four window bytes (x/y/width/rows in tiles) followed by a text pointer. Slots
0,5,8 are null; nine labels use native centring byte14. Reader CPU08051F86
selects a descriptor with the byte reached through literal08051FB4, then invokes
02298. ROM `[00051FB0,00051FB4)` is the single aligned reference to this table.
The source table and strings remain owned original data, not free space.

The activation chain is 4E7C0's native state1 switch, conditional on02010210=2,
then callback51B98, callback51C70 and callback51E4C. A disposable native probe
sets the existing transition bits in EWRAM `[0201020C,02010210)` and the current
selector/refresh state; it executes the complete native setup and selector with
no PC/register/source substitutions. It renders Japanese “Square” on the preceding
3,802-resource English ROM. This proves the controlled path, not ordinary access to this overview.
Evidence: `build/localization-closure/town-map-controlled/report.json`,
`town-map-trigger-native.txt`, `town-map-callback.txt`, `dynamic-owner-followup.txt`.

Inserted: private descriptors `[00961B1C,00961B7C)`, nine English strings in
`[00961A2C,00961B1C)` (individual resources and alignment gaps in the ledger),
and the checked pointer word at51FB0, through RomBuild. Null descriptors and
native selectors remain exact. Four labels widen from72px: Old man's house and
Torneko's house to96px, Synthesis shop to88px, Adventurer's Inn to104px. Each
keeps its original left/right outer edge (8px screen margin), y and one row.

All nine controlled native cases pass original setup, descriptor selection,
centering and exact visible glyph pixels, two redraws,31 in-table directional
inputs and native A destination IDs. Twenty-one transitions check18,960 vacated
background pixels against independent target-label captures. ABI/stack guards,
inventory and battery remain unchanged. Report:
`build/english/town-overview-validation/report.json`.

Existing EWRAM `[020102AA,020102AB)` is the selector; `[02010198,0201019C)` is
the redraw flag. Scoped native key-state probes use `[0200884C,0200884E)` only
during the complete51E4C callback and restore the exact original bytes on return.
This isolates the fixture's still-active town movement context; earlier ordinary
button experiments opened its unrelated travel picker. No PC/register/text-source
substitution or new RAM/save storage. Natural activation, five directional edges
into the separate travel-exit handler, and subsequent travel remain unproven.
That exit's source bindings are already English (level restriction, entry and
saved-village confirmation, plus the existing town scratch producer).

### October 3: second announcement reader and computed shield reflection

Verified against pinned original SHA `79986287eef366bba987393de8247141973d5564fa72fe2f3f6dd28684cd18aa`.
Addresses below distinguish cartridge file offsets from CPU addresses; range ends
are exclusive. See [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md) for ROM versions.

- Cartridge `[0002AC2C,0002AC30)` originally contains `68 0D 14 08`
  (`08140D68`). The full projectile/staff handler at CPU `0802AB84` uses it
  for formatting at `0802ABDE` and queueing at `0802ABE6`. It now shares the
  existing private announcement table with literal `[0002AA54,0002AA58)`.
  The original 28-byte monster definition has a signed announcement halfword
  at `+20` and a **one-byte** projectile identifier at `+22`; do not combine
  the unrelated `+23` byte. Four species, 84/85/121/122, select both an
  announcement and a projectile. The other projectile species use selector zero
  and skip the announcement. Original action dispatch `0802E0F6` calls this
  handler from `0802DE80`; it is separate from the ability announcement handler.
- CPU `0800CD38` saves its incoming selector `r3` at `SP+258` (hex) at `0800CD4C`.
  Five original direct callers pass `89`, `67`, `0`, `0`, `0`. At `0800CED4`
  the format is loaded through the saved selector. The zero case is not queued
  (`0800CEEC`–`0800CEF8`); it is not a displayed untranslated message.
  `89` selects shared-table byte offset `224`, original source `0806393C`,
  the shield-reflection damage message. `67` is ordinary damage.
- Cartridge `[0000CF50,0000CF54)` originally contains `68 0D 14 08`.
  `tools.shield_reflection_text` redirects only this owned literal to a private
  copy of the **compiled** shared table, preserving existing ordinary-damage
  translations. It changes only reflection slot `224` within that copy and
  leaves the global shared table's reflection entry unchanged.
- In candidate `b229bbb6…`, the shared allocator owns cartridge
  `[00961C70,00961CB6)` for the reflection format and
  `[00961CB8,009626F0)` for the private table. Alignment bytes and surrounding
  original ranges are not declared free. The exact allocation/patch ledger is
  `build/caller-audit-next/shield-candidate/build.json`.
- The full native reflection branch reads existing warrior-effect bit `400`
  at EWRAM `[020081D4,020081D8)` or shield property bit `10` returned by
  CPU `0800FF00`. The latter calls native equipped-category lookup `0800FE44`
  for category 3; a controlled equipped Blade Shield (item 37) reaches reflection
  with the warrior bit cleared. Actor action byte `+41` is set to 3 in these
  incoming-melee probes. The turn prelude resets effect flags, so recorded test
  setup occurs at handler entry. These are verified branch preconditions,
  **not newly allocated RAM or a claim about ordinary skill acquisition**.

Evidence: `build/caller-audit-next/projectile-parent.txt`,
`projectile-reader-baseline/report.json`, `projectile-reader-fixed-effects/report.json`,
`damage-wrappers.txt`, `shield-effect-getter.txt`, `equipped-shield-getter.txt`,
`shield-baseline-entry/report.json`, `shield-fixed/report.json` and
`shield-candidate/dynamic-selectors.json`. Full attacks return with the original
callee-saved registers/stack; native glyph pixels and formatter guards pass.

### Empty-ability equipment Info and conditional queue follow-up (2026-10-03)

ROM `[00017BF8,00017BFC)` is the previously missed category-table literal in
CPU `[08017BA6,08017BC4)`. Original bytes `183f1408` select the 14-pointer category
table at ROM `[00143F18,00143F50)`. A sword/shield record with fused bit `00200000`
and zero low-20 ability bits follows this fallback instead of the nonempty
ability renderer. Categories 6/3 select attack/defence descriptions respectively.
The existing item-text owner now patches this literal to its already allocated
private category table, as it already did for ROM `[00017E68,00017E6C)`.
The original table and both descriptions remain untouched. No new allocation,
stack change, item effect or save field is introduced.

On ROM `452394042d5be4c83adb79fa35eaba5ca261514533b2162604032b9561e44304`,
`tools.audit_empty_ability_info` observes the original copy at CPU `08017BB0`
into `[SP+8,SP+108)`, checks the 256-byte boundary guard, English glyphs and
complete Info return at `08017EEC`. Both equipment classes open/cancel three times
with identical restored inventory pixels and unchanged inventory/battery.
Controlled item flags and type-known fields are retained in the report; this
establishes the native branch, not ordinary synthesis/removal history.
Evidence: `build/caller-audit-next/empty-ability-baseline/report.json` and
`empty-ability-fixed/report.json`.

The conditional queue at CPU `[08015870,08015886)` forwards its incoming text
only when EWRAM byte `[0200C890,0200C891)` is zero. Its sole original direct call
is `080097A0`, after the terrain-damage formatter at `08009798`. That producer
uses shared byte slot `1C4`, already the English damage fragment, and the
original 256-byte output `[SP+150,SP+250)`. The native branch tests current-tile
flags `4000` and `2000` through the established map cell at
`020229A8 + (x*32+y)*28 + 20`. Two controlled full-turn probes retain the exact
field changes, execute both queue outcomes and verify HP 20→10, output/guard/ABI,
unchanged inventory and battery. No PC or text pointer is replaced. Evidence:
`build/caller-audit-next/info-candidate/terrain-damage-validation/report.json`.
These bytes are existing branch inputs, not storage reservations.

Six unresolved static copy arguments (`0800CE9C`, `0800CF9A`, `0800D70E`,
`0802D524`, `080392B8`, `08039984`) take `r1` directly from actor-name getter
`08009ACC`; byte-checked instruction spans are in the computed-selector report.
They do not introduce independent sentence selectors. Normal entries `08050BC4`
and `08050C14` branch to owned village/well helpers, while the original queue
instruction at `0802585E` is overwritten by the item-use hook. The audit preserves
these dispositions separately from native branch observations.
