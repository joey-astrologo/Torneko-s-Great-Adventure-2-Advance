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
