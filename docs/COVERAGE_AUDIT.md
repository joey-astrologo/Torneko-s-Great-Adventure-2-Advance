# Localization coverage matrix

Updated 2026-10-03. **Whole-game coverage is unverified; there is no defensible
whole-game completion percentage.** This is the current coverage reference.
Family guides and research journals retain their historical builds and counts.

## Accepted build and evidence

| Measure | Current result | Scope |
|---|---|---|
| English ROM SHA-256 | `fc9b6f5ea20643a6aabda35768c55c545dbe94a66766d234704aefa931b57a7c` | Latest accepted development build; archive `build/accepted/3814-tutorials/` |
| BPS SHA-256 | `0abed5a9b873844c978d1d10db9017d81cd1d3a10cb3f118e32277f73d064550` | Clean reproduction and independent patch reconstruction pass |
| Inserted resources | 3,814 text; 20 graphics | Compiled resources, not all reachable screens |
| Known source catalog | 3,676: 3,552 reviewed, 96 unresolved, 28 retained/components | Discovery inventory, not gameplay coverage |
| Cumulative acceptance | 182 unit tests; native/menu/service checks pass | Exact recorded cases on this ROM |
| Selected-font browser checks | 315 contexts / 3,430 measurements; no selected-font overflows | Identified regions and substitutions |

[Release checkpoint ZIP](../build/releases/2026-10-03-tutorials.zip) ·
[Subsequent research receipt](../build/caller-branches/release-followup.json) ·
[Completion receipt](../build/caller-branches/completion.json) ·
[Service receipt](english-services-validation.json) ·
[Menu receipt](english-menu-validation.json) ·
[Build ledger](../build/english/build.json) ·
[Detailed caller follow-up](CALLER_FOLLOWUP.md).

A subsequent clean compiler run reproduces the accepted ROM/BPS exactly, with
independent patch application. Research-tool changes pass 184 unit tests and
189 additional unfiltered native sessions / 13,662 glyphs. These are separate
from the archived 182-test full acceptance above; no new ROM fix or full native
suite rerun was needed. The ZIP includes both receipts and release notes.

The further caller/scene audit passes **186 unit tests**, classifies 41 computed
table-base losses and checks both background tables: 22 full-screen records and
28 scrolling records, including flag/door replacements and all static objects.
The complete controlled ending now runs its native save, five scenes, credits,
END artwork and return. All 57 ending sources appear: 71 reads / 3,338 glyphs,
with no unexpected Japanese or layout findings. These are additional checks of
the same accepted ROM, not new translations. See [the continuation](CALLER_FOLLOWUP.md#computed-readers-graphics-and-complete-ending)
and [graphics evidence](GRAPHICS_INVENTORY.md).
The [scene-audit checkpoint ZIP](../build/releases/2026-10-03-scene-audit.zip)
packages that unchanged BPS and a separate receipt for these additional checks.

The cumulative build completed its native checks, then stopped at a stale
20-case tutorial expectation in report generation. That expectation was corrected
to 22; the resumed report/font stage and aggregate acceptance passed. The receipt
preserves the initial failure and resolved tail; this was not an uninterrupted
successful `build.sh` invocation. Original ROM and supplied save hashes are unchanged.

Some cumulative receipt fields preserve an earlier family subset: use
`total_reviewed_inserted_resources` for the overall insertion count, not
`inserted_reviewed_text_resources`. Inherited opening/service `scope` fields
also do not summarize later independent quest receipts. Read each evidence
record's ROM and case scope.

## Coverage by family

Counts below are bounded acceptance cases, not percentages or necessarily unique
game states. A passing family test does not establish an unfiltered audit of every
screen. Independent audit cohorts are identified separately below.

| Area | Established evidence | Remaining limit / next investigation |
|---|---|---|
| Dungeon root and location banner | All five visible fields, 13 locations × three modes; repeated opening and original geometry. [Banner](LOCATION_BANNER.md). | Other readers and unvisited states require accounting. |
| Floor, ground items and traps | 14 modal cases, all four direct callers: empty inventory/Floor, items, stairs, trap/class/status refusals and cancellation. [Reader audit](READER_PATH_AUDIT.md). | Standing on a trap is included; controlled trap/class setup does not establish ordinary encounters. |
| Status expiry | Seven missed messages repaired; 44 cases cover all 20 timer branches, widest saved/transformed names and simultaneous expiry. | Other handlers and acquisition branches remain separate. |
| Earlier caller repairs | 55 bindings / 308 cases, then all 20 leads plus nine additional failures / 110 cases and 13 blacksmith exchanges. [Caller audit](CALLER_COVERAGE_AUDIT.md). | These leads are closed; earlier unresolved-call counts describe historical scan stages. |
| October 3 caller repairs | Second monster announcement reader, shield reflection, empty-ability sword/shield Info, then pot/Mimic tutorials repaired. [Follow-up](CALLER_FOLLOWUP.md). | Reviewed sources do not automatically close their other consumers. |
| Items, aliases and custom names | 221 definitions / 2,006 item cases; 154 appearance labels / 166 cases; 30 English custom-name cases including prices, markers, pot counts and storage persistence. [Items](ITEM_TEXT.md). | Unvisited consumers and combined states; Japanese maximum custom-name width is outside acceptance. |
| Item actions, pots and blank scrolls | Owned main/contained/town consumers; 54 container, 11 pot-view, 102 writing, nine editor and 584 writing-lookup cases. [Blank scrolls](BLANK_SCROLLS.md), [menus](MENU_LAYOUTS.md). | Specific consumer/lookup cases, not every inventory combination. |
| Bank, bakery and storage | 12 core bank, 21 reward, three bank persistence, 13 bakery, ten storage-service and three storage transaction cases. Ordinary holy-flame/storage and Cemetery/bakery routes recorded. [Services](SERVICE_BATCHES.md). | Later states/consumers remain open. Ordinary bakery persistence was recorded on the preceding ROM. |
| Other services | Native families cover blacksmith, Gaibara, Remi, mayor, priest, carpenter and dungeon shop; exact cases in the service receipt. | Controlled entry/transactions do not establish all unlock branches or scene integration. |
| Combat, traps, spells and skills | Native formatter/queue/menu families, maximum substitutions and targeted reader repairs pass; skill-loss checks now execute the original name-cache producer. | Unvisited caller branches, compound states and entry assumptions remain discovery work. |
| Tutorial help | All 27 menus, 22 bank/topic contexts, six direct prose cases, four alternate headers and three controlled NPC-script routes pass. Configurations 12 (pot) and 14 (Mimic) repaired. | Configurations 1, 2, 8 and 9 have no instruction-aligned entry in the scanned scripts or known page path. Original malformed mappings retained; unknown entry paths remain unproved. See the entry audit below. |
| Story and event stubs | Reviewed banks and controlled getters; two approved one-character reconstructions inserted and verified. [Event audit](EVENT_STUB_AUDIT.md). | 34 other one-character records unresolved; do not invent dialogue or infer global unreachability. |
| Results, records, saves and link text | 336 result, 664 result-UI, 54 history-UI, nine history-menu, 15 records, four password and 56 save-preview cases; link text/pickers tested. | Actual multiplayer and unvisited combinations excluded. Password kana is intentional protocol data. |
| Later dungeons, classes and ending | 85 ending-text and 25 dungeon-travel cases plus class/spell/skill families. Complete controlled ending additionally runs all five scenes, saving, credits, finale and return with native staging. | Other entry states and callers, including ordinary ending access, remain unverified. Assisted entry is appropriate; ordinary full-game progression is not a prerequisite. |
| Title, arrivals and credits | Main title + five floating logos; 13 arrival names + Level; original English credits preserved. All 22 full-screen and 28 scrolling descriptors decoded, including their foregrounds, replacements and 85 static object instances. [Graphics matrix](GRAPHICS_INVENTORY.md). | No additional Japanese lettering found in these families. Independently animated actors, other atlas consumers and other scene integrations remain separate. |

## Independent display audits and build provenance

The missed banner and empty-Floor message exposed checks filtered to known English
pointers. Independent audits observe readers and glyph output before that filtering.
Exceptions must match an exact producer/context (saved names or password protocol,
for example), never all Japanese.

| Cohort | Build / result | Scope |
|---|---|---|
| First dungeon/town audit | Historical 11 scenarios / 7,068 glyph draws; [gallery](../build/coverage-audit/index.html) | Found gold-spacing defect; negative controls reject old banner and gold output. |
| Broad caller follow-up | Preceding ROM `452394042d5be4c83adb79fa35eaba5ca261514533b2162604032b9561e44304`; 35 families / 813 sessions / 267,527 glyphs | All 98 bounded-scan callers disposed: 89 observed, six actor-name copies, three bypassed old calls. [Receipt](../build/caller-audit-next/completion.json). |
| Branch-audit supplement | Same preceding ROM; 19 families / 1,042 sessions / 256,870 glyphs | Exact saved-name handling corrected; initial failures and final resolutions retained. [Resolution](../build/caller-branches/native-resolution.json). |
| Repaired tutorial screens | Current ROM; 22 bank sessions / 51,601 glyphs, 27 menu sessions / 7,431 glyphs, one Mimic-parent session / 562 glyphs | Whole-stream checks include header, border gap and restoration; three script probes additionally execute native selectors/handlers. |
| Release-checkpoint supplement | Current ROM; 189 sessions / 13,662 glyphs | 67 town/dungeon travel-list, 16 book/travel, 105 travel-confirmation and one native town-save continuation cases; all unfiltered checks pass. [Receipt](../build/caller-branches/release-followup.json). |
| Complete controlled ending | Current ROM; one complete route / 71 reads / 3,338 glyphs, repeated with caller ABI/stack guard checks | One bank-call entry override; native save, all five scenes, all 57 ending resources, fades, credits, END artwork and return. [Receipt](../build/ending-sequence-guarded/report.json). Saved-name exceptions remain exact. |
| Ordinary continuation | Eight segments / 13,499 glyphs / 2,147 input/wait actions; individual ROM hashes retained | Mt. Fiery unlock, native suspend/current-ROM cold resume, 8F, defeat and both retry outcomes. [Summary](../build/caller-branches/ordinary/summary.json). Quest completion unproved. |

Cohorts can overlap; do not add them as unique-screen coverage. Preceding-ROM
audits are not current-ROM replays. Ordinary routes provide integration/save
evidence; repeated attempts to survive a dungeon are not an acceptance requirement.

## Remaining work, in investigation order

1. **Resolve code and source gaps.** Follow the 62 unresolved shared/town sources
   (52 shared/system, ten town/service), 34 event fragments and tutorial
   configurations 1, 2, 8 and 9 only when new entry evidence is found. The
   [entry audit](../build/caller-branches/tutorial-reachability.json) examines 133
   event roots plus seven complete NPC payloads: 22 configurations have script
   candidates and configuration 19 is the bounded second page of 18. One raw
   configuration-8 byte match lies inside another instruction's operands. The
   four retained configurations are absent from the decoded entries and known
   paged path; this is not a proof of global unreachability.
   The 28 retained/components comprise 21 nonlinguistic, four components and
   three deliberately retained Japanese records.
2. **Follow remaining data-flow contexts.** The 25-guard scan and expanded save
   seed now have [35 distinct stop dispositions](../build/caller-branches/switch-stop-dispositions.json):
   23 locations are native POP/BX epilogues; the instruction patch is the existing
   six-to-seven-character name limit; repeated save-row traversal results from an
   unknown selector/count. Seeding its two native selector values resolves all
   four English row bindings. Do not repeat these as unexplained failures.
   Downstream stops from the separate row-seed probe and other unknown arguments
   remain explicit; these dispositions do not resolve the 62 source records.
   A further diagnostic observes where unknown indexes discard known table bases:
   all 41 resulting sites have dispositions (37 relocated consumers, two existing
   save/curse paths, two sprite-coordinate coincidences). Its 49 seed-budget
   limits remain recorded, not evidence of 49 defects. No additional untranslated
   reader was identified in this cohort.
3. **Probe uncovered scene/branch contexts.** Identify entry conditions through
   disassembly, then use disposable saves, controlled state or documented
   invincibility/damage patches to reach later scenes efficiently. Exercise native
   callers/selectors/renderers; check all visible fields, pixels and transitions.
   Keep unmodified damage/death cases when those branches are under test.
   Calling a renderer alone does not prove its scene caller works.
4. **Trace graphical text and check repairs.** Follow scene loaders, decompression
   and remaining atlas consumers; both identified background tables, their static
   layers and the complete controlled ending are now checked. Inspect additional
   artwork and actual frames. Fix confirmed
   issues, check related consumers, update this matrix and complete affected
   regressions and required acceptance before the next release.

The user's earlier unspecified Japanese dungeon/pickup report has no independently
identified scenario beyond the defects already reproduced. Bounded pickup routes
do not disprove it; use retained saves, code and unfiltered probes before requesting
more user investigation.

Disassembly leads discovery. Runtime checks establish which bank/state reaches a
reader, whether dynamic fields fit, and whether drawing/restoration is correct.
Record every override, input schedule and ROM/save hash. No invincibility patch
is required for the completed ending probe; its one entry override and native
save changes are recorded separately from ordinary progression.
