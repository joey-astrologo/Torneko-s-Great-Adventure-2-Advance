# Text investigations and layout constraints

Current assessment: ready for release-candidate testing (`1.0-rc1` recommended).
No confirmed outstanding localization defect remains in the investigated paths.
Broader independent playtesting and scene/state coverage are still incomplete.
The closed findings below document evidence and constraints, not pending repair
requests. Build identity and exact acceptance scopes are in the coverage matrix.

Current continuation: [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md). The latest
accepted build has 3,814 resources and includes the caller/tutorial repairs below
plus two bank-2 shopkeeper selector repairs. Four scene routes, affected service
checks, real two-core link trades and cold-save persistence pass on the current
ROM. Ordinary green-book entry, empty refusal, naturally deposited bread/staff
exchange and town return also pass without state overrides. All spell/skill
definition-domain reads and the bounded result-reason producer graph pass; these
are now incorporated into the source-by-source dispositions below. The October 7
text pass also bounds soldier creation to its seven translated messages and
checks both monster announcement readers and skill-menu selectors (548 static
cases). No additional untranslated selection was found in that cohort. Text
has no confirmed outstanding defect in the former 62-source / 34-fragment
cohort: all 96 now have [individual source dispositions](TEXT_SOURCE_DISPOSITIONS.md). Whole-game
caller/state coverage remains unproved. Further graphics auditing
is stopped at the user's request; it is not the reason text remains open.
Both event interpreters now have bounded branch traversal: 133 roots, 207
English dialogue references and 282 native branch outcomes. The additional
fragment byte candidate has no entry in that graph. See [the event audit](EVENT_STUB_AUDIT.md).
The baker's six dialogue floors now also have creation/exit producer evidence
and 24 native predicate checks; that specific domain is accounted for.
October 4 release acceptance passed 187 unit tests and required toolchain/
fresh-save checks. The latest research suite passes 191; the earlier full
cumulative acceptance retains its preceding ROM identity.

The continued branch audit also repairs pot-help and early Mimic-help selectors
that returned unrelated dialogue, fragments or an invalid address. Both reuse
existing reviewed prose; no missing dialogue was invented. Their native script
and menu evidence is in [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md). These are separate
from the remaining 34 original one-character records below.

Native captures: [text decision gallery](../build/text-decisions/index.html).
These are controlled probes, with ROM hashes, actual inputs and overrides in
linked reports. They are not proof of ordinary story access. The preceding October 2 root
ROM had 3,813 inserted resources. The item-name layout decision is settled:
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
is retained in the catalog and build ledger. The other 34 records now have
individual dispositions: three after END, one operand-byte coincidence and
thirty without selectors in the shipped script graph. Current actor records,
both event interpreters and direct/tutorial getters select none of them.
Original bytes remain preserved; unknown synthesized entries are outside this bound.

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

## Current evidence and remaining limits

The October 7 [link-error caller audit](LINK_ERROR_AUDIT.md) verifies all five
English errors and their actual cleanup/return paths. It also reproduces an
original gameplay bug: hardware-error and extra-system exits after the
intermediate save lose the offered item, including after cold loading. Both
Japanese and English ROMs behave alike under the recorded fault injections.
The user chose to preserve original gameplay behavior, so this finding is closed
as documented original behavior, with no repair planned. Normal disconnection/
timeout restoration passes. The refreshed root ROM/BPS retain the accepted game
bytes; no gameplay repair is inserted.

The [coverage matrix](COVERAGE_AUDIT.md) owns current counts and evidence scope.
The Floor/empty-inventory defects, seven expiry messages, 55 earlier caller
bindings, all 20 continuation leads and nine additional failures are repaired.
The October 3 announcement, reflection, empty-ability Info and pot/Mimic tutorial
repairs are also accepted. The October 4 blacksmith/Remi selector repairs and
actual two-core link trades are detailed in
[the current continuation](CALLER_FOLLOWUP.md#npc-shop-selectors-and-two-core-link-trading).
Those defects are not an outstanding work list.

The completed code pass classifies all 41 observed table-base losses without finding
another untranslated reader. Graphics discovery covers both background tables,
their replacement tiles and static objects. A complete controlled ending now
passes all five scenes, all 57 sources, native saving, fades, credits and END
through return. These completed cohorts are detailed in
[CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md#computed-readers-graphics-and-complete-ending).
They do not establish ordinary ending access. The later source-disposition pass
below now accounts for each of the previously unresolved catalog records.

| Investigation | Known evidence | Next step |
|---|---|---|
| 62 shared/town sources | Ten town records excluded by 167 service read sites; 52 shared records excluded by 688 read sites and bounded computed domains. | Closed in the recovered graph; reopen with concrete contrary evidence. [individual source dispositions](TEXT_SOURCE_DISPOSITIONS.md) cover every ID. |
| 34 event fragments | Current NPC graph: 458 roots; event/direct/tutorial getters add no fragment reference. Three after END, one operand coincidence, thirty without selectors. | Closed for shipped scripts and recovered getters; preserve original bytes and reopen only with new entry evidence. |
| Tutorial configurations 1, 2, 8, 9 | Menu/cursor evidence; whole-payload/decoded-script scan and paged dispatcher find no known entry. Original malformed mappings retained. | Revisit with new entry evidence; do not claim global unreachability or invent replacement prose. |
| Static-analysis contexts | Observed 25-guard/expanded-save stops now classified: 23 return locations, owned name-limit patch, and unknown row-count loops. Both row selectors resolve English. | Follow other unknown arguments and downstream contexts; the classified exits are not unexplained failures. [Receipt](../build/caller-branches/switch-stop-dispositions.json). |
| Later text scene integration | Complete controlled ending passes native staging, saving, all dialogue and return | Follow other text entry-state combinations; ordinary ending access remains separate. Further graphics auditing is stopped. |

The 96 untranslated catalog sources are these 62 sources plus 34 fragments.
All now have investigation dispositions; they are not 96 outstanding display
failures or a measure of remaining engineering work. All 98 callers in the
preceding bounded-call cohort have investigated dispositions; that does not resolve
every source, branch or unknown reader. Earlier 529/102-call figures were scan stages.

Ordinary Mt. Fiery completion and late-game/ending access remain unproved.
They are provenance gaps, not prerequisites for localization investigation.
Disassembly leads discovery; disposable invincibility/state setup may provide
scene access. Native execution still checks actual selection, dynamic fields,
rendering and return transitions. Record assistance and preserve unmodified
behavior for damage/death tests.

No additional dungeon/pickup scenario has been identified beyond the repaired
reports. This is not counted as a confirmed outstanding defect. Investigate any
new reproducible report through retained saves, code and unfiltered probes.
