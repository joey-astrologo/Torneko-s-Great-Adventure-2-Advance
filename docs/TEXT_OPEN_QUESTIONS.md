# Text investigations and layout constraints

Current continuation: [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md). The latest
accepted build has 3,814 resources and includes the second monster announcement
reader, shield-reflection/empty-ability Info repairs and the two tutorial fixes
below. Cumulative native acceptance, 182 unit tests and clean reproduction pass;
the preceding 3,813 milestone remains separately documented.

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

## Current unresolved investigations

The [coverage matrix](COVERAGE_AUDIT.md) owns current counts and evidence scope.
The Floor/empty-inventory defects, seven expiry messages, 55 earlier caller
bindings, all 20 continuation leads and nine additional failures are repaired.
The October 3 announcement, reflection, empty-ability Info and pot/Mimic tutorial
repairs are also accepted. Those defects are not an outstanding work list.

The next code pass classifies all 41 observed table-base losses without finding
another untranslated reader. Graphics discovery covers both background tables,
their replacement tiles and static objects. A complete controlled ending now
passes all five scenes, all 57 sources, native saving, fades, credits and END
through return. These completed cohorts are detailed in
[CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md#computed-readers-graphics-and-complete-ending).
They do not establish ordinary ending access or eliminate the unresolved source
inventory below.

| Investigation | Known evidence | Next step |
|---|---|---|
| 62 shared/town sources | 52 shared/system and ten town/service records still lack resolved readers in the bounded scan | Trace computed selectors and RAM producers from verified entries; do not call them unused. |
| 34 event fragments | Three appear only after unconditional END in extracted scripts; 31 lack references in extracted roots | Investigate other entry points/readers; no authority to invent replacement dialogue. |
| Tutorial configurations 1, 2, 8, 9 | Menu/cursor evidence; whole-payload/decoded-script scan and paged dispatcher find no known entry. Original malformed mappings retained. | Revisit with new entry evidence; do not claim global unreachability or invent replacement prose. |
| Static-analysis contexts | Observed 25-guard/expanded-save stops now classified: 23 return locations, owned name-limit patch, and unknown row-count loops. Both row selectors resolve English. | Follow other unknown arguments and downstream contexts; the classified exits are not unexplained failures. [Receipt](../build/caller-branches/switch-stop-dispositions.json). |
| Later scene and graphics integration | Both background tables and static objects audited; complete controlled ending passes native staging, saving, fades, credits and finale | Follow other atlas consumers, independently animated actors and other entry-state combinations; ordinary ending access remains separate. |

The 96 unresolved catalog sources are these 62 sources plus 34 fragments, not
96 proven display failures or the complete remaining work. All 98 callers in the
preceding bounded-call cohort have investigated dispositions; that does not resolve
every source, branch or unknown reader. Earlier 529/102-call figures were scan stages.

Ordinary Mt. Fiery completion and late-game/ending access remain unproved.
They are provenance gaps, not prerequisites for localization investigation.
Disassembly leads discovery; disposable invincibility/state setup may provide
scene access. Native execution still checks actual selection, dynamic fields,
rendering and return transitions. Record assistance and preserve unmodified
behavior for damage/death tests.

The earlier unspecified Japanese dungeon/pickup report remains unmatched to an
independent scenario beyond the reproduced defects. Existing bounded pickup
routes do not disprove it. Continue using retained saves, disassembly and
unfiltered probes before asking the user for more investigation.
