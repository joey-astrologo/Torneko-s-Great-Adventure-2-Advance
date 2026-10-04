# Continued localization audit — 2026-10-02

This page records the October 2 build. The accepted October 3 continuation and current matrix
are documented in [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md); the hashes and counts
below remain historical evidence rather than acceptance of the newer build.

This records the four requested steps. It does not declare whole-game coverage.
The original ROM and supplied save are preserved. Research uses disposable
sessions; each native report records its ROM identity, inputs and state overrides.

[3,811 audit receipt](../build/localization-closure/completion.json) ·
[Approved repair receipt](../build/event-stub-repair/receipt.json) ·
[Before/after captures](../build/localization-closure/index.html).

## 1. English custom item names: inserted

The October 2 development build contained **3,813 text resources and 20 graphics**.
ROM SHA-256:
`f47b6df310211585406c921d8070e1824a8e1cf76a324cd72c8b8669ad6ef865`.
The two approved event repairs are recorded below; the preceding 3,811 ROM/BPS
and ledger are retained in `build/event-stub-repair/before/`.
The preceding 3,785 build is retained in `build/localization-closure/before/`.

[`tools/custom_item_text.py`](../tools/custom_item_text.py) inserts 14 category
labels and two format shapes from
[`translations/custom-items-review.json`](../translations/custom-items-review.json).
These resolve 11 previously unresolved category-label sources; the other three
labels already had reviewed equivalents. The formats preserve category, entered
name and count order, native colour controls and the original 64-byte formatter
scratch. A private table and six checked pointer replacements preserve the
original shared table. There are no new RAM/save allocations or window changes.

The formats are `Category:name` and `Category:name[count]`. Ordinary custom
names still use the **Name** action and the existing eight-character limit.
Blank-scroll **Write** inputs are separate; see [BLANK_SCROLLS.md](BLANK_SCROLLS.md).

[`tools.verify_custom_items`](../tools/verify_custom_items.py) passes 30 native cases:

- Six nameable categories, using eight widest supported English letters, in
  inventory and storage, each with and without prices: 24 cases.
- Pot counts 0, 1 and 20, alongside the synthetic count-99 cases.
- Equipped/cursed ring markers and a short name.
- Exact native format bytes, 64-byte guards, caller registers/stack, all visible
  glyphs, numeric cells and unchanged name/save bytes.
- Three action opens/cancellations per inventory case with identical restored
  parent pixels; actual deposit/withdrawal in each storage case.

All names occupy one line. Observed name ink ends at 88–105px; the tested price
column starts at 121px. Storage item lists have 168px windows. The separate
100px storage columns belong to **commands**, not item-name rows. The original
8px border gaps remain. Maximum Japanese custom-name width is outside acceptance
per the user's October 2 direction; it remains historical diagnostic evidence.

Candidate report: [30 cases](../build/localization-closure/candidate/custom-items-validation/report.json).
The cumulative gate also runs this verifier through `build.sh`.

## 2. Caller-led shared/town audit: bounded findings

[`tools.audit_source_readers`](../tools/audit_source_readers.py) extends the
15-consumer scan with paired original/compiled town RAM images, stack-relative
arguments, producer calls even when their format is unknown, and verified native
entry helpers for blacksmith, Gaibara, Remi and the mayor. It propagates the town
table from actual dispatcher calls into additional services. Changed stack-frame
sizes are modeled separately for the original and compiled ROM.

The scan includes all 1,294 original direct-call patterns to those consumers.
It does not filter callers by translation review status. The previous 529
unresolved arguments now divide into 102 bound English-resource calls, 307
buffer calls with producer candidates, five buffers still needing producer
resolution in the automatic scan, and 115 unresolved data-flow calls. Producer candidates are not
automatically counted as English. Current details, paths, limits, exact source
identities and classifications are in
[source-readers-deep.json](../build/localization-closure/source-readers-deep.json).
The longer service contexts resolve 18 more calls than the initial 900-instruction
pass. All four private service-entry contexts finish without a path/budget cutoff;
other bounded contexts retain their explicit cutoff counts.

The separate [storage switch audit](../tools/audit_storage_readers.py) verifies
the native eight-entry dispatch table and follows calls passing the town table
in either argument register. Its 19 contexts yield 17 town-table reads and no
reader of the ten unresolved town sources. Three contexts reach the configured
step budget; this is retained in [storage-readers.json](../build/localization-closure/storage-readers.json).
It additionally resolves 13 calls left unknown by the general scan, including
storage capacity, filled-pot confirmation, empty/full lists, sale confirmation
and saving cancellation. The combined reports therefore bind 115 of the original
529 calls to English resources and leave 102 with unresolved data flow; the
307 producer candidates and five manually followed buffers retain their separate
categories. The 13 added bindings are enumerated in `buffer-producers.json`.

Disassembly identifies the producers of all five automatic buffer leads:

| Consumer call (CPU address) | Actual producer | Native verification family |
| --- | --- | --- |
| `08016294` | The amount editor writes eight numeric glyphs directly at SP+`1C`, then appends the caller's currency suffix at `08016284`. Its only two direct callers are bank deposit/withdrawal. | Bank amount cancellation exercises all ten digits and eight cells; numeric aliases are checked independently. |
| `08019490` | Item-action formats at `0801940C`/`08019446` are concatenated at `0801944E` into the menu buffer. | Main action-label/variant checks, materialized bytes, caller guards and open/cancel restoration. |
| `080196DC` | Child-action formats at `08019656`/`08019692` are concatenated at `0801969A`. | Child action-label checks and container action routes. |
| `08019DD4` | The status formatter at `08019B0E` writes SP+`10` from the private service-UI table, slot `50`. | Dungeon UI and all-field location-banner checks. |
| `08019E08` | Vocation-specific root formats at `08019CB6`/`08019CC6` write SP+`110`, then append the ground action and Option at `08019D48`/`08019D50`. | All three command modes, ground/stairs/trap variants and root buffer guards. |

The raw automatic classifications remain unchanged so that manual findings are
not presented as symbolic execution results. The disassembly is retained in
[unresolved-buffer-functions.txt](../build/localization-closure/unresolved-buffer-functions.txt)
and [dungeon-panel-producers.txt](../build/localization-closure/dungeon-panel-producers.txt).
This accounts for the five concrete buffer leads; it does not close the 307
producer candidates or the combined 102 unknown data-flow calls as a group.

The [producer-context follow-up](../tools/audit_buffer_producers.py) examines all
1,200 distinct producer/argument contexts behind those candidate links: 856 use
reviewed English formats, 198 use other ROM formats, 91 have unknown formats,
44 invoke other helpers, and 11 contexts (five physical calls) copy complete
static Japanese notices. The latter calls are `0803328A`, `0803394C`,
`080339B4`, `08035A60` and `08035A94`. Their unchanged static output reaches
the existing queue adapter, which matches the entire copied string including
its terminator and selects English. The four mapped notices are “Maximum
fullness cannot rise further.”, “But nothing happened.”, “Strength is restored.”
and “You're full!” Both queue flags have passing copied-string native cases
on this ROM. See [buffer-producers.json](../build/localization-closure/buffer-producers.json)
and [producer-to-queue disassembly](../build/localization-closure/copied-producer-leads.txt).
These intermediate Japanese bytes are accounted for; the unknown formats and
other helper outputs remain explicit analysis limits.

Disassembly of computed callers found **two additional failures**, both fixed:

- The final wind warning selects shared slot `458` using a five-element index
  table. Its player wrapper formats the Japanese before the queue adapter sees
  it. A private table now supplies **“The wind swept {player} away!”**. Six native
  cases cover stages 2/3 and stage 4 with original and boundary names, complete
  formatted bytes, 256-byte guards, every visible glyph, ABI and the original
  wind-expulsion outcome. The widest saved name fits one line at 207px.
- The separate town overview reads nine centred location labels from twelve
  descriptors. These sources were missing from the earlier catalog. A private
  descriptor table translates all nine. Four complete labels need wider
  standalone windows; their original screen edges, 8px margins and single rows
  remain. Nine native cases check all labels, in-table directions, destination
  results, centring/pixels, repeated window recreation and background restoration.
  Activation, selection and callback-scoped key state are controlled. Ordinary
  access and directions into the separate travel-exit handler are not claimed.

The overview probe initially sent ordinary direction buttons to two concurrent
contexts: the controlled overview and the fixture's underlying town movement.
That opened a separate travel picker. The final verifier isolates key state to
one complete overview callback and restores the original bytes on return. No
PC, register or source pointer is substituted. This is an explicit controlled
rendering/navigation check, not a natural overview gameplay receipt.

The remaining inspected computed readers bind to existing skill, projectile,
stumble-trap, item-loss, fire-scene, ending and travel resources. The three
curse-helper parents select static notices already handled by the complete-string
queue adapter. The town overview's travel-exit confirmations use existing English
resources and the previously verified town scratch producer. Exact bindings are
in [computed-reader-followup.json](../build/localization-closure/computed-reader-followup.json).
This manual finding layer is separate from the bounded symbolic-execution totals.

The final **53 unresolved shared sources and 10 town sources** still have no
resolved read in the bounded source analysis. This does not prove them unused.
Computed branches, unmodeled RAM and indirect readers remain explicit limits.
The earlier 54-source automatic result missed the wind reader; its archived
report is retained as `source-readers-deep-3801.json`.

The catalog now has **3,676 unique sources: 3,551 reviewed, 97 unresolved and
28 retained/component records**. Reviewed includes the two explicitly approved
editorial reconstructions below. These are source-review counts, not a percentage
of gameplay that displays English. The new overview sources demonstrate why
catalog completion would not establish complete discovery.

## 3. Single-character event records: two approved repairs inserted

[EVENT_STUB_AUDIT.md](EVENT_STUB_AUDIT.md) records all 36: two referenced by NPC
branch traversal, three only after unconditional END, and 31 without references
in the extracted roots. Six native follow-on cases confirm both Saruyama choice
outcomes and the boy's first/repeat flag paths. The original sources lack the
sentences needed to finish these two translations. The user approved the exact
contextual repairs on 2026-10-02; both now use the existing event-bank allocator.
Eight new native cases verify both Saruyama selectors with Yes/No/B and the boy's
first/repeat flag paths. Original branches, full English reads, every glyph,
window bounds, visible repair pixels and caller guards pass. Original inventory
and battery bytes are preserved. Natural map access remains unproven.

## 4. Cumulative validation and further ordinary gameplay

Every stage of the cumulative build completed on the **3,801-resource baseline**,
including the 2,006-case item matrix. This was an initial invocation plus recorded
continuations after gate repairs, not one uninterrupted passing `./build.sh`.
[The archived receipt](../build/localization-closure/full-suite-3801/receipt.json)
retains its ROM, ledger, build script and 1,293 report hashes/copies. Logs preserve
the original title/screen gate failures and their successful continuations. The title acceptance gate previously compared allocation
addresses against a current build made without title artwork; later resources
necessarily move in that comparison. It now verifies both complete ownership
ledgers, identical non-title resource identities/counts, original art/credits,
and all existing native pixel checks. Its strict insertion-only comparison
remains available with `--insertion-delta`.

The ordinary quest audit completed the mansion, bank opening and castle quest
acceptance, then reached castle 4F before defeat. The failed attempts are retained
in `later-quest/` and `later-quest-retry/`; they are not successful quest-completion
receipts. An exact 333-input replay separately passes 77 reads and 5,104 glyphs,
including the native defeat/results and castle-retry prompt; see
[quest-replay/report.json](../build/localization-closure/quest-replay/report.json).
Unfiltered observations distinguish exact saved Japanese village/player names
and native equipment markers from game-authored Japanese. Copied player fields
are exempted only when their verified native producer, complete formatted bytes
and exact glyph positions match. The original wind probe still reports its nine
Japanese sentence glyphs outside the saved name.

A separate English cold continuation uses a native suspend save earned through
ordinary Japanese gameplay. Its 114 ordinary inputs reach the sacred flame,
blacksmith lock repair, warehouse opening, full warehouse instructions and the
first storage deposit/withdrawal. All 79 reads and 4,303 glyphs pass with zero
unclassified glyphs, unreadable streams or layout violations. Its input and screen evidence is in
[castle-continuation/report.json](../build/localization-closure/castle-continuation/report.json).
This is not an uninterrupted English run from the quest's beginning. Later story,
services and endings still need ordinary route coverage beyond these checks.

The preceding **3,811-resource ROM** has a clean, identical rebuild and independently
verified BPS. The complete ownership ledger passes. Relative to the completed
3,801 baseline, all existing allocations/patches and all other earlier bytes are
identical: only **two original pointer words and twelve appended allocations**
implement wind and overview. See
[reproducibility-3811.json](../build/localization-closure/reproducibility-3811.json).
Relative to the preceding 3,785 release, the custom-name insertion adds another
six pointer words and seventeen allocations.

Final checks repeat the affected wind/overview/custom-name/writing families,
Floor, status expiry, every location-banner field, copied notices, the unfiltered
11-screen matrix, and the ordinary quest replay/castle continuation. The historical
Japanese-banner and gold-spacing controls still fail as expected. `./validate.sh`
passes 160 unit tests and toolchain/fresh-save checks. The broader 2,006 item cases
and remaining cumulative families are carried as the explicitly identified 3,801
baseline receipt; they are not represented as fresh runs on 3,811.

The approved **3,813-resource ROM** also rebuilds identically and its BPS
reproduces the exported ROM. All seven native event loads and 1,046 getters pass;
the eight repaired-branch cases and 14 Floor/menu regressions pass on this ROM.
`./validate.sh` passes 160 unit tests plus toolchain/fresh-save checks. These are
the checks rerun for this repair, not a new full-suite claim.

[The complete delta](../build/event-stub-repair/delta.json) accounts for all
4,064 prior allocations and 730 native patches. Existing bytes are identical
after exact allocation-relative pointer relocation, including the documented
compressed event/town/actor tables. Only two event slots gain new bindings and
two new text allocations are added. Existing scripts, prose, geometry and
RAM/save allocation are unchanged. Editorial provenance and approval travel
with the catalog, build ledger and source inventory.

The editorial decision is resolved. The remaining 34 single-character event
records have not been assigned invented dialogue.
The unresolved source/data-flow counts and untested natural routes above remain
coverage limits, not passing results or declarations of unused code.
