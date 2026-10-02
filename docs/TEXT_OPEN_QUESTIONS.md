# Text investigations and layout constraints

Native captures: [text decision gallery](../build/text-decisions/index.html).
These are controlled probes, with ROM hashes, actual inputs and overrides in
linked reports. They are not proof of ordinary story access. The current root
ROM has 3,785 inserted resources. The item-name layout decision is settled:
**every item name stays on one line**. The one-character dialogue needs more
investigation before asking for a translation preference.

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

The earlier choice between romanization and an ellipsis was premature and is
withdrawn pending context/reachability research. In particular, an ellipsis would
not explain what the Yes/No prompt asks. No replacement has been inserted, and
no wording has been approved. Thirty-four other one-character records still
need reader/reachability accounting. A controlled native call is not evidence
of ordinary story access.

## Long Japanese custom item names

Eight wide English letters fit the measured inventory examples with the English
category labels. An eight-glyph Japanese pot name can cross the price column:

| Controlled row | Name right edge | Price starts |
|---|---:|---:|
| Existing Japanese category label |151px|121px|
| English category prototype |169px|121px|

The unpriced English-category version also overflows the name region. Its strict
verifier fails at advance172 in the168px parent; the separate diagnostic capture
does not weaken that check. The original168px window provides162 usable text
pixels after the marker reserve. Other item lists, including the100px storage
columns, need their own full-name checks.

The user explicitly rejected additional item-name lines on 2026-09-29. Keep
single-row item names and solve any remaining layout problems within that
constraint. This does not approve clipping, overlapping prices, truncating saved
names, shrinking the selected font or a Japanese-name compatibility exclusion.

The demonstrated problem concerns long **player-assigned Japanese custom names**,
including names from Japanese saves; it is not a requirement to wrap ordinary
English item names. In the existing controlled prototype, all six tested nameable
categories fit eight wide English letters on one inventory line, both with and
without prices: visible name edges are 88–105px and the tested price column begins
at121px. This is bounded inventory evidence, not acceptance for every price,
quantity, category or the separate100px storage columns.

English category translations remain in a separate prototype and are not counted
as completed inventory sources. Their eventual insertion still needs verified
single-line layouts, the selected font at normal spacing and8px border gaps.

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
refusal is confirmed English. The 15-reader scan retains 529 unresolved arguments
as static limits; its resolved direct bindings reveal no further Japanese
sentence. Discovery, source review and caller repair remain separate work.

A repeatable ordinary-input run on accepted3,768 reaches all three tutorial
floors,14 pickups and14 English tips without Japanese text glyph leads. Current
3,770 previously passed five automatic walking-pickup cases, including items, gold,
arrow merging, full inventory and the standing option. Those bounded routes do
not identify the Japanese dungeon messages the user previously reported on a
local playtest. A specific affected build/save and action would help reproduce
that remaining report; it is not treated as disproven by the automated routes.
