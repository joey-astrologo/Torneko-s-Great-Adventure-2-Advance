# Name entry: minimum English support

The localized name editor must accept **at least seven Latin letters**, including
the exact mixed-case name **`Torneko`**. This is a user requirement, not an optional
abbreviation. Entry, editing, confirmation, subsequent name displays/substitutions,
and persistence through a save and cold load must work before acceptance.

**Implemented and verified in the cumulative English build.** The shared editor
now supports seven characters, including both English cases, digits and basic
punctuation. The conditional player-name editor also supports seven. The existing
item-name editor retains its eight-character limit and shares the expanded
keyboard and glyph table.

```bash
./build.sh
```

This builds [torneko-2-english.gba](../build/english/torneko-2-english.gba), creates
a byte-verified [BPS patch](../build/english/torneko-2-english.bps), and runs native
name-entry/save tests. See [BUILD.md](BUILD.md) for current localized scope.

## Verified Japanese behavior

The opening editor is limited to **six characters**. Its caller at CPU
`08014BEA` passes six in r2 to `0801545C`. The normal-button probe enters a fifth
and sixth character, observes automatic selection of Finish, then returns to the
keyboard and chooses another character. That replaces the sixth character;
it does not append a seventh. Confirmation copies the entire 16-byte working
record back to the stored RAM field. Editing before confirmation leaves that
stored field unchanged.

This opening display uses the format `%s村` at ROM `00063D60`, appending the
Japanese word for village. The observed `トルネコ＊＊村` is therefore a formatted
display of the entered name plus two vacant slots and the suffix. It is not a
15-byte permanent player-name field. The producer is now traced: `0801545C`
converts indexed characters to two-byte glyph codes on the stack, formats the
suffix, and calls the reader at `0801557E`.

The window is 13 tiles / **104 pixels** wide and sets a **14-pixel fixed character
advance**. Its cursor also uses 14 pixels per slot in `08019F3C`. Seven name
characters plus the existing village suffix would occupy 112 pixels at this
advance. Raising the character limit alone is insufficient for this layout.

The selected [Torneko 2 compact font](FONT_AUDITION.md) measures `Torneko` at
**41 pixels** of glyph advance; the T3 comparison font measures 37.
Its text encoding is `F054 F06F F072 F06E F065 F06B F06F 00`: 14 glyph bytes plus
the terminator. Font measurements and native editor/save acceptance are separate;
both have now passed with the selected font and expanded indexed alphabet.

## Storage and consumer findings

The original name is stored as **one-byte character IDs**, not directly as its
two-byte displayed glyphs. The 16-byte working and stored records are at EWRAM
`0200CCF4` and `02003B46`. Initialization writes four IDs for `トルネコ`, four `01`
vacant-slot markers and eight zero bytes. Confirmation copies all 16 bytes.

The original ID-to-glyph table at ROM `00141A28` contains Japanese characters,
digits and symbols. Its observed glyph sequence has no Latin alphabet. The
English font extension does not automatically add keyboard selections or name
IDs. Three 64-byte keyboard selection pages start at ROM `00147F00`; the input
routine indexes them by page and selection, with `FE`/`FF` special actions.

Several existing converters explicitly handle up to eight IDs, stopping at
vacant-slot markers, and reserve space for 16 output bytes plus a terminator.
Examples are CPU `08041FD4` and the conversion inside `08020564`. The latter
also calls the editor with a six-character limit. The title-menu routine has
another conditional editor call with a four-character limit at `08014C30` and
a separate glyph-string field at `02003B58`; its trigger and gameplay behavior
remain to be traced. The opening village-name display must not be conflated
with that separate field.

State transfer code at `08006C60` copies the indexed name's full 16-byte record
to a caller-supplied record at offsets `2FE5` and `0214`. The counterpart at
`08007214` restores 16 bytes from offset `2FE5`. These are disassembly findings
about logical records, **not established physical flash offsets or a successful
cold-load test**. They suggest seven IDs may fit existing storage, but do not
yet establish every consumer, save mode or compatibility behavior.

## Implementation and acceptance scope

The build appends 69 IDs for `A–Z`, `a–z`, `0–9`, space, apostrophe, hyphen,
period, comma, exclamation and question mark. Original Japanese IDs retain their
meaning; the vacant-slot marker displays as an underscore. Five pages provide
uppercase, lowercase, original symbols, hiragana and katakana. `Sp` selects a
space. The page label cycles pages, Next/Back move the name cursor, B deletes,
and Start selects Done before A confirms. Japanese voiced/small-kana actions
remain available.

The shared field uses a 176-pixel window and VWF. The caret follows measured
glyph widths, including the separate player editor's `Name: ` prefix. Seven
letters occupy 14 encoded bytes plus NUL, within the existing 16-byte saved
glyph-string field. The implementation keeps that save layout and deliberately
uses seven as the shared maximum. The item editor's existing eight-ID record
and conversion buffer already support eight characters.

The [native acceptance report](../build/english/name-entry-validation/report.json)
covers all 69 selectable English characters and their prepared glyph pixels,
cursor positions/register preservation, wide/narrow seven-character samples,
deletion/re-entry, replacement at the limit, confirmation and adjacent-field
guards. The original six-ID secret still opens the conditional player editor;
adding a seventh character no longer matches that exact secret.

The required `Torneko` case is entered using normal buttons, carried through the
opening and first dungeon, and saved with the native stairs **save and suspend**
option. A fresh emulator session loads the battery file, displays
the name in the save preview, decodes and restores the complete game record,
resumes on floor two and moves through normal input. Both indexed and player
glyph-string fields match in RAM and in the actual flash records. Native full-name
and first-letter width controls are also checked in isolated restored snapshots.

A separate normal Japanese run creates a real save which the English build then
loads and resumes with its original Japanese names intact. This verifies that
tested import route. Saves containing new English IDs should remain paired with
the English build; the Japanese ROM has no glyph mappings for those IDs.

Later name contexts, mayor renaming/persistence, English item naming and inscription
input now have separate bounded acceptance; see [the coverage matrix](COVERAGE_AUDIT.md).
Unvisited name consumers and save combinations remain open. These broader families
are not established by the first-floor route alone. No claim of full-game localization or gameplay
coverage follows from these tests.

Evidence: [English acceptance receipt](english-name-entry-validation.json) and
[memory/save findings](MEMORY_MAP.md#native-save-records-and-name-persistence).
That receipt pins the earlier name-component build; its generated artifact paths
are subsequently reused by cumulative builds. The
[historical opening receipt](english-opening-validation.json) adds the King's
dialogue and home-destination substitutions, including seven widest original
Japanese glyphs, on that recorded ROM. Current per-family acceptance is linked
from the coverage matrix; generated paths can hold later matching-build reruns.

## Reproduce the base-game check

```bash
.venv/bin/python -m tools.trace_name_entry
```

The probe boots the pinned Japanese ROM in a disposable mGBA session. It uses
normal buttons with observational breakpoints, verifies four native name-display
calls and the confirmation copy, and checks that the supplied ROM/save hashes
remain unchanged. It does not alter RAM or CPU registers.

- [Trace, input schedule and assertions](../build/name-entry/base-trace/report.json)
- [Original six-character field](../build/name-entry/base-trace/native/six-characters-finish-selected.png)
- [Retained validation receipt](name-entry-validation.json)
- [Address findings](MEMORY_MAP.md#name-editor-research-2026-09-13)

Disassembly exports are under `build/name-entry/`: `editor-functions.txt`,
`input.txt`, `menu.txt`, `name-consumers.txt` and `state-transfer.txt`. These exports
use true function entries; conclusions above follow their instructions and
literal values, not provisional decompiler variable names.
