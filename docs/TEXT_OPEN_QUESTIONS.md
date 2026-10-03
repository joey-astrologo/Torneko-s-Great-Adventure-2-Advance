# Text investigations and layout constraints

Native captures: [text decision gallery](../build/text-decisions/index.html).
These are controlled probes, with ROM hashes, actual inputs and overrides in
linked reports. They are not proof of ordinary story access. The current root
ROM has 3,813 inserted resources. The item-name layout decision is settled:
**every item name stays on one line**. The two referenced one-character dialogue
records now have approved, inserted contextual repairs in
[EVENT_STUB_AUDIT.md](EVENT_STUB_AUDIT.md).

## Original one-character dialogue

Two original event sources render through their native selectors/handlers:
`event-bank-3.3ec2` contains only `サ`, followed by a Yes/No choice;
`event-bank-4.0d25` contains only `な` on a flag-dependent repeat conversation.
The first conversation with that boy contains full prose and is already English.
There is no missing sentence in these source records to translate.

“Sa” and “Na” were phonetic readings of those characters, not proposed character
names. The neighboring sources identify Saruyama (`サルヤーマ`) and the bratty boy
(`なまいきな少年`); each isolated character is the first character of its speaker
label. This supports the inference of unfinished or placeholder entries, but
it does not prove that ordinary gameplay reaches them or establish missing words.
Saruyama's two following branches are an apology and a Synthesis-pot tutorial;
the boy's first conversation is about his busy father.

Six new controlled follow-on cases confirm that Yes opens the Synthesis-pot
tutorial and No opens the apology; the boy's flagged repeat ends immediately
after the single character. No handler supplies a missing sentence. The
[approved repair](EVENT_STUB_AUDIT.md) reconstructs that question and reuses
the boy's existing first paragraph. Both are inserted following the user's
2026-10-02 approval. Eight new native cases verify the English reads, Yes/No/B
outcomes, repeat flag, glyphs, fit and caller guards. Their editorial provenance
is retained in the catalog and build ledger. Of the other 34 records, three occur only after an unconditional
END and 31 have no reference in the extracted roots. Ordinary story access and
other potential readers remain unproven.

## Custom item-name acceptance scope

User clarification on 2026-10-02: **English custom names, category labels, counts
and prices determine layout acceptance.** Maximum Japanese custom-name width is
outside that requirement. Both its price overlap and the English prototype's
window-edge spill with Japanese names are historical diagnostics, not localization
blockers or required fixes. This supersedes earlier requirements to resolve those
Japanese-name cases before inserting the English category labels.

Item names must still occupy one line, as requested on 2026-09-29. Preserve the
selected font, saved-name data and buffer bounds. Check the widest supported
English custom names with the labels, markers, quantities and prices used by each
consumer. The inventory has 162 usable text pixels in its original 168px parent;
the storage item lists also use 168px windows. The separate 100px storage
columns are command labels, not item-name rows. Preserve the 8px gaps between
menu borders.

The 11 previously unresolved category-label sources are now reviewed and
inserted. The private family contains 14 labels and two format shapes (16 text
resources). All 30 controlled native cases pass, covering six nameable categories
in inventory and storage, with and without prices; pot counts; equipped/cursed
markers; and repeated action opening/cancellation. Eight widest English letters
stay on one line, with name ink ending at 88–105px and the tested price column
starting at 121px. Native storage deposit/withdrawal and unchanged saved-name
bytes are checked. See [LOCALIZATION_CLOSURE.md](LOCALIZATION_CLOSURE.md).

For the historical comparison, the earlier baseline was an English development
ROM retaining Japanese category labels. A later probe confirmed Japanese-name
price overlap on the pinned, untouched Japanese ROM in all six tested categories.
With eight kana and a pot count of 1, name ink ends at 146px while the price starts
at 121px; a synthetic count of 99 ends at 153px. All 24 cases preserve the original
ROM, renderer, geometry and source pointers. Controlled inventory/name/price flags
and ordinary menu inputs are recorded; original ROM/save hashes and the battery
remain unchanged. The English category prototype's Japanese-name edge reaches
169px, with an unpriced advance of 172px. These measurements do not impose a
Japanese-name layout requirement.
[Original-ROM report](../build/custom-name-parity/original/report.json) ·
[Original Japanese pot screenshot](../build/custom-name-parity/original/154-count-1-priced-True/inventory.png).

## Remaining gameplay evidence

The October2 [Floor-menu defect](FLOOR_MENU.md) and the subsequently discovered
empty-inventory caller are fixed. A [disassembly-led follow-up](READER_PATH_AUDIT.md)
identified seven Japanese expiry messages, now fixed:
confusion, hallucination, sleep, blindness, dancing, fear and item-recognition
recovery. They share the computed formatter/queue path at096EC/096F4.
All20 recovered timer branches now display English. The44 native cases verify
256-byte output bounds, exact glyphs, maximum saved/transformed names and
simultaneous expiry. Controlled one-turn timers do not establish ordinary
status acquisition, and other handlers still need reader-level accounting.

The continued [caller audit](CALLER_COVERAGE_AUDIT.md) found 54 other
untranslated caller sites; all are now repaired. The continuation added 31,
including marked Storage-pot actions and ordinary trap discovery after controlled
setup. Together with the item-placeholder correction, 55 bindings pass 308
native cases. The continuation has now fixed all 20 outstanding leads and nine
more caller failures, with 110 native cases and 13 blacksmith exchanges. The copied
refusal is confirmed English. The deeper [source-reader audit](LOCALIZATION_CLOSURE.md)
follows town RAM tables, verified entry helpers, stack buffers and their
producers. Of the earlier 529 unresolved calls, 102 now bind English resources;
307 have producer candidates, five require manual producer analysis, and 115 retain unknown
data flow. Disassembly identifies all five remaining buffer producers as the
bank amount editor, main/child action builders, status row and root commands;
their native verification families are recorded in the audit. An additional
eight-branch storage dispatch scan binds 13 more calls to English, leaving
102 unknown data-flow calls across the combined reports, and finds no
unresolved-town-source reader.
The computed-reader follow-up then found and fixed the final wind warning
and all nine labels in a separate town overview. The latter sources were absent
from the previous catalog. The remaining 63 unresolved shared/town sources are
not declared unused from missing bounded references. Final evidence and the
controlled overview's scope are in [LOCALIZATION_CLOSURE.md](LOCALIZATION_CLOSURE.md).

A repeatable ordinary-input run on accepted3,768 reaches all three tutorial
floors,14 pickups and14 English tips without Japanese text glyph leads. Current
3,770 previously passed five automatic walking-pickup cases, including items, gold,
arrow merging, full inventory and the standing option. Those bounded routes do
not identify the Japanese dungeon messages the user previously reported on a
local playtest. A specific affected build/save and action would help reproduce
that remaining report; it is not treated as disproven by the automated routes.
