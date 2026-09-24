# Mansion safe recovery and bank opening

This page records the initial mansion milestone. Its 38-test/7,971-glyph figures
refer to that font/build; the current [font selection and refreshed acceptance](FONT_AUDITION.md)
use Torneko 3's Latin font and preserve the same 104 reviewed translations.

The combined discovery/localization batch adds **25 reviewed English resources**,
bringing the cumulative build to **104**. It covers the anonymous 6F voice, the
Imp's challenge, safe recovery, the successful-quest result, the banker's thanks,
both family questions and their responses, the following morning's blacksmith
scene, and permission to open the bank. The bank greeting and farewell are also
translated. Deposit/withdrawal menus and transactions remain a separate batch.

[Native preview](../build/english/mansion-preview.png) ·
[Acceptance receipt](english-mansion-validation.json) ·
[English ROM](../build/english/torneko-2-english.gba) ·
[BPS patch](../build/english/torneko-2-english.bps)

## Discovery and ownership

The mansion's ordinary 6F stairs do not complete the quest. A separate marked
room contains the Imp. Defeating it drops the banker's safe; picking up the safe
triggers the return. The retained Japanese route reaches this room through
ordinary movement, equipment selection, combat and resting. A fixed input
schedule records the tested layout; this is not a general dungeon solver.

The Japanese prefix contains 1,040 ordinary input actions, followed by the quest
and home scenes. Four checkpoint replays cover the two independent family
questions. One also refuses the bank request, observes the repeated plea, then
accepts. Every branch cancels the service menu and verifies resumed town movement.
No health, inventory, actor, map, RNG or quest-state memory is patched on these
native routes. Failed exploratory layouts are retained as research, not counted
as successful acceptance.

The [memory map](MEMORY_MAP.md#mansion-safe-recovery-and-bank-opening-2026-09-19)
records four direct pointer fields, 19 event-bank-one slots and two shared-town
slots. Source bytes, tokens and hashes are checked before insertion. Bank sizes
and all unrelated decoded bytes remain unchanged. Shared `RomBuild` allocations
hold the English; no new dialogue RAM or save storage is used.

Two adjacent centred lines required a small compiler extension. Each explicit
line retains its own centre command, and both fit on the same two-row page.
The recovery message keeps its player substitution. The successful-quest result
uses a separate single-line window with a 12-pixel initial inset, so its English
is limited to 212 pixels. Neither case relies on character-count estimates.

## Language and page review

[mansion-review.json](../translations/mansion-review.json) retains all Japanese
sources, exact source hashes, first drafts, final English and review reasons.
Drafting, bilingual review and native capture review were separate passes by the
same assistant; this is not independent human review.

The first family question still asks whether there were many monsters. The
second asks whether things will be all right after the old man's visit: Yes
reassures Tessie; No leads to caution. Refusing the bank request produces another
plea rather than a permanent refusal. These meanings and native branch results
are preserved. The old man's identity remains unrevealed.

The [glossary](../translations/glossary.json) records **Imp** for ベビーサタン,
with labelled secondary evidence for the modern English species name. It is
distinct from Minidemon. **Sacred flame** is explicitly a provisional project
rendering of 聖なる炎; an official PS1 equivalent has not been established.
The blacksmith's Japanese dialogue supplies its context beneath the castle.
No Torneko 3 entity or borrowed prose is substituted.

Tipper's ゲンキン remark combines the banker's mercenary change of mood with a
cash homophone. “Money sure cheers him up!” retains the money association and
childlike teasing without inventing a new transaction. Yellow emphasis, monster
cries, speaker order and all source control commands remain intact.

## Acceptance and reproduction

```bash
./build.sh
./validate.sh

# These also run at the end of build.sh, after its fresh Japanese home route:
.venv/bin/python -m tools.trace_mansion
.venv/bin/python -m tools.verify_mansion

# Refresh source inventory while preserving translations/reviews:
.venv/bin/python -m tools.extract_text --trace build/mansion/native/trace.json
.venv/bin/python -m tools.audit_event_tables
.venv/bin/python -m tools.verify_text_sources

# Assemble the native preview after acceptance:
.venv/bin/python -m tools.review_mansion
```

The [Japanese report](../build/mansion/native/trace.json) records 29 distinct
nonempty sources, including reused resources and the still-Japanese dungeon
name. It verifies a native save call and exports the actual 5F suspend battery.
The [English report](../build/english/mansion-validation/report.json) cold-loads
that battery on the English ROM and resumes on 6F. A recorded 204-frame menu wait
selects the tested layout; navigation reads map/actor data and issues ordinary
buttons. This continuation reaches the Imp, wins the battle, recovers the safe
and returns home, then replays all four family combinations through bank opening.

This is **an English cold continuation from a native Japanese suspend**, not an
uninterrupted English 1F–6F playthrough. The earlier home-book acceptance covers
English mansion entry separately. No save state is imported across different
ROM hashes. `build.sh` regenerates the Japanese route and save from its earlier
stages, so it does not depend on historical research checkpoints.

The new English acceptance checks 86 completed text reads and 7,971 glyphs across
five routes. It checks native glyph addresses/bitmaps/advances, window bounds,
page waits, colour spans, substitutions, centring, preserved registers/SP,
choice results and resumed controls. Three separate controlled name-record
probes test `Torneko`, seven widest English glyphs and seven widest Japanese
glyphs. Both recovery lines centre correctly; name guards and battery bytes
remain unchanged. These probes are display tests, not newly created gameplay saves.

All earlier cumulative routes, shared-town relocations, name/save checks, the
38-test suite and toolchain acceptance pass on the recorded build. The receipt
also pins a clean output-directory rebuild with byte-identical ROM and BPS,
verified BPS application, source audit, review and screenshot identities.
Original ROM/save files are preserved.

## Coverage and next work

The accumulated catalog has **112 native sources**: 104 reviewed, five still
untranslated, two replaced by existing menu/name components, and the intentionally
retained Japanese keyboard. The known tables still contain 1,250 unique sources.
The refreshed broad scan has 2,814 candidates: 809 exact table matches and 2,005
unresolved leads. These are discovery counts, not a whole-game percentage.

Next is the bank's transaction/menu producer and populated inventory services,
followed by green-book records and save-preview formatting. Combat/item names,
other result fields, the dungeon-name resource, defeat/retry dialogue, alternate
safe-room states and later NPC conversations remain outside this acceptance.
Title/background/arrival artwork, credits and full-game playtesting are still
pending. No graphical assets are changed by this batch.
