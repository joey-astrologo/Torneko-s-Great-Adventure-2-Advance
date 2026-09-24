# Home books and the first banker request

At this milestone the cumulative build inserted **79 reviewed catalog resources**.
The current build and subsequent quest acceptance are documented in
[MANSION_QUEST.md](MANSION_QUEST.md); this page preserves the book/banker batch scope.
This batch adds 16: all ten red-book tips; the blue-book menu while the
storehouse is broken; empty-inventory and save messages; the castle/square travel
labels; and the banker's first request, both answers, the old man's appearance,
and the reminder about the safe. Normal inputs reach mansion floor one and
resume movement. The original ROM and save remain unchanged.

[Native preview](../build/english/books-preview.png) ·
[Acceptance receipt](english-books-validation.json) ·
[English ROM](../build/english/torneko-2-english.gba) ·
[BPS patch](../build/english/torneko-2-english.bps)

## What was found

The red book uses the existing two-row story reader, including three native
centred headings. English keeps the title, author and ending centred, with
measured wrapping for the instructions. A separate review of native captures
removed awkward one-word spill pages without dropping item names or conditions.

The blue book currently offers **View items**, **Sell items**, **Save and
continue**, and **Save and quit**. Deposit/withdraw commands do not appear while
the storehouse is broken. Its menu and several replies come from a previously
unmapped shared town resource: 300 pointer slots, representing 204 unique source
starts. This is separate from the seven event-dialogue banks. Both the original
and English ROMs pass full native decompression and all 300 pointer relocations.
English changes four owned pointer slots and leaves the decoded resource at its
original 16,695 bytes. Strings live in checked appended ROM allocations.

The overwrite question copies the **existing save's village name** through one
native `%s` argument. It is distinct from the player-name substitution. The
translated question fits two rows with `Torneko` and seven widest English or
Japanese name glyphs. The original function's 128-byte stack buffer, preserved
registers, unwritten tail and following guard are checked. Save-and-quit combines
the save-success text and farewell in another 128-byte stack buffer; its combined
length and both centred lines are checked independently.

Accepting the banker's request triggers the old man's appearance and the banker's
alarmed reply. Talking again gives the GBA script's **uncertain location around
6F**, which the English preserves. The quest's completion and later bank service
are outside this batch.

The green book was also reached and captured. Its parent menu, initially empty
scroll-name list and records menu are four newly verified sources. They remain
Japanese: populated entries, selection behavior and the larger records screens
need further mapping. This discovery is not counted as completed localization.

## Language review

[The review record](../translations/home-books-review.json) retains all 16
Japanese sources, source hashes, drafts, final English and reasons. Drafting,
bilingual review and native page review were separate passes by the same
assistant; this is not independent human review.

The [glossary](../translations/glossary.json) distinguishes official modern names,
project compounds based on official spell names, and PS1 fallback evidence.
Lightning staff, Medicinal herb, Antidotal herb and Seed of strength use modern
series names. Zoom herb and the Bazoom/Fuddle/Snooze staff compounds are explicitly
labelled project compounds. Super herb and Misleader herb use the documented PS1
fallback instead of the sibling project's provisional Healing herb/Fright herb.
Their evidence is secondary; direct PS1 bilingual captures and later native GBA
item-description checks remain desirable. The Japanese GBA book supplies every
instruction and condition; guide prose and other games' mechanics were not copied.

## Native acceptance and reproduction

`./build.sh` now includes the new checks after regenerating its Japanese and
English home checkpoints. ROM construction requires the pinned original ROM,
source assets and catalog, without historical emulator fixtures.

```bash
./build.sh
./validate.sh

# Individual new acceptance commands, after the preceding build stages:
.venv/bin/python -m tools.trace_home_books \
  --fixture build/english/home-validation/japanese-home/village \
  --output build/english/books-validation/japanese
.venv/bin/python -m tools.verify_town_text
.venv/bin/python -m tools.verify_home_books
```

The [Japanese trace](../build/english/books-validation/japanese/trace.json) retains
nine ordinary-input routes and 22 sources, including the green-book discovery.
The [English report](../build/english/books-validation/report.json) retains eight
ordinary-input routes, exact source/glyph/palette/paging checks, both banker
choices, three separate controlled village-name cases, and four cold loads:
save-and-continue and save-and-quit in each ROM. Both indexed name records and
the rendered player name survive cold loading, and town movement resumes.
The save-preview screen is still partly Japanese and is not counted as localized.

[Shared-bank validation](../build/english/town-text-validation/report.json) checks
600 native pointer fixups across the two ROMs, with decoder guards/registers
and unchanged bytes outside the owned slots. Earlier opening, dungeon, castle,
name-entry, travel and home tests remain in the build. The home-roamer test now
faces slot 24's observed nearby position before talking: a changed loading time
can place him south rather than east. This uses ordinary directional input and
records the observed coordinates; no NPC or gameplay state is injected.

`./validate.sh` passes 37 unit tests plus original-ROM, toolchain, mGBA and
Ghidra acceptance. A separate clean-output rebuild reproduces the ROM and BPS
byte for byte. Exact identities and report hashes are pinned in the receipt.

## Coverage and next work

The catalog contains **86 naturally verified sources**: 79 reviewed/inserted,
four untranslated green-book sources, two replaced by existing menu/name
components, and one intentionally retained Japanese keyboard body. The seven
event tables contain 1,046 sources; the shared town table adds 204 distinct
sources. Of those known table sources, 56 event and four shared-town sources
have documented natural use. Enumeration is separate from reachability.

The regenerated candidate queue contains 2,835 entries: 827 exact matches in the
known tables and 2,008 unresolved leads. These counts are not a whole-game
completion percentage.

Next, follow the mansion's safe-recovery route and inventory/item-message
families, then revisit the resulting town services. Map the green-book lists and
records screens separately, including populated states. Repaired-storehouse
flows, later dialogue, arrival/title graphics, credits and full-game playtesting
remain open. Ownership, source ranges and expected bytes are recorded in
[MEMORY_MAP.md](MEMORY_MAP.md).
