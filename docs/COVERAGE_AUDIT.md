# Localization coverage matrix

Updated 2026-10-07. **Whole-game coverage is unverified; there is no defensible
whole-game completion percentage.** This is the current coverage reference.
Family guides and research journals retain their historical builds and counts.

## Accepted build and evidence

| Measure | Current result | Scope |
|---|---|---|
| English ROM SHA-256 | `588dc92ce09104cb80d18fb4929e6e713f86836e65d8c12b135dfb4f4269b7ad` | Latest accepted development build; root exports updated; archive `build/accepted/3814-npc-shops/` |
| BPS SHA-256 | `d019f1851e13176a8960db669198563c4d285f7878fde7297503c56d05361d7b` | Candidate/normal build reproduction, ledger reconstruction and independent patch application pass |
| Inserted resources | 3,814 text; 20 graphics | Compiled resources, not all reachable screens |
| Known source catalog | 3,676: 3,552 reviewed, 96 untranslated with investigated dispositions, 28 retained/components | Zero untranslated records without a disposition; bounded discovery inventory, not gameplay coverage |
| Latest research checks | 191 unit tests; corrected 250 definition cases / 378 reads; all 96 source dispositions | Research-only changes; no ROM patch or new full native-suite claim |
| Link-error continuation | 15 English scenarios / 24 peer routes and cold loads; two original-ROM scenarios / four peers and cold loads | All five English errors and complete cleanup/return paths verified. Two post-save fault exits reproduce an original item-loss bug; recovery does not pass for those exits. [Evidence](LINK_ERROR_AUDIT.md). |
| Current affected acceptance | 187 unit tests; four NPC routes / 12 opens, 57 blacksmith text cases, 13 exchanges, 73 Remi text cases, three real link trades and four cold loads | Exact cases on this ROM; toolchain/fresh-save/Ghidra checks pass |
| Preceding cumulative acceptance | 182 unit tests; native/menu/service checks pass | ROM `fc9b6f5e…`, archived separately; full suite not replayed on the new ROM |
| Selected-font browser checks | 315 contexts / 3,430 measurements; no selected-font overflows | Preceding ROM, identified regions and substitutions; new repair changes no text/font/geometry |

[Current release checkpoint ZIP](../build/releases/2026-10-07-text-audit.zip) ·
[Current affected-check receipt](../build/accepted/3814-npc-shops/completion.json) ·
[Preceding tutorial checkpoint ZIP](../build/releases/2026-10-03-tutorials.zip) ·
[Subsequent research receipt](../build/caller-branches/release-followup.json) ·
[Preceding cumulative receipt](../build/caller-branches/completion.json) ·
[Service receipt](english-services-validation.json) ·
[Menu receipt](english-menu-validation.json) ·
[Build ledger](../build/english/build.json) ·
[Detailed caller follow-up](CALLER_FOLLOWUP.md).

The October 7 refresh recompiles and independently applies the BPS; root ROM/BPS
bytes match the accepted October 4 checkpoint. The link-error continuation finds
no additional untranslated path. It reproduces original item loss on hardware-
error and extra-system exits after the intermediate save, with controlled fault
injection and original-ROM comparison. The user chose to preserve original
gameplay behavior. This finding is closed as documented original behavior;
successful text checks do not imply that these exits restore items.

The October 4 repair replaces two malformed bank-2 NPC selectors with their
rooms’ existing service scripts. The blacksmith failure is reproduced by ordinary
side contact after controlled scene entry; Remi’s visible-actor route is controlled
separately. Four repaired/neighboring routes pass native decoding, selection,
rendering and return. Two-core link trading passes actual serial exchange,
saving, repeat/cancel and received-item cold-load persistence. A separate ordinary
green-book route verifies empty refusal, natural deposits, bread/staff exchange,
town return and exact received-item persistence, with no state overrides.
See [the current evidence](CALLER_FOLLOWUP.md#npc-shop-selectors-and-two-core-link-trading).

The following historical checks belong to ROM `fc9b6f5e…`.
A subsequent clean compiler run reproduces that ROM/BPS exactly, with
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
| Other services | Native families cover blacksmith, Gaibara, Remi, mayor, priest, carpenter and dungeon shop. October 4 repairs two bank-2 shopkeeper selectors and checks four scene routes / 12 opens plus affected service cases. | Controlled bank/map eligibility remains separate; Remi visible-actor contact uses one documented argument override. |
| Combat, traps, spells and skills | Native formatter/queue/menu families, maximum substitutions and targeted reader repairs pass; skill-loss checks execute the original name-cache producer. All 61 spell / 128 skill definitions additionally pass 250 static cases / 378 computed text reads. October 7 adds 548 static cases / 356 reads across soldier selectors, both monster announcement readers and skill-menu labels. | Unvisited caller branches, compound states and entry assumptions remain discovery work. The 192 zero-announcement cases suppress text; these static domains are not encounter counts. |
| Tutorial help | All 27 menus, 22 bank/topic contexts, six direct prose cases, four alternate headers and three controlled NPC-script routes pass. Configurations 12 (pot) and 14 (Mimic) repaired. | Configurations 1, 2, 8 and 9 have no instruction-aligned entry in the scanned scripts or known page path. Original malformed mappings retained; unknown entry paths remain unproved. See the entry audit below. |
| Story and event stubs | Reviewed banks and controlled getters; two approved one-character reconstructions inserted and verified. Both interpreters: 133 roots, 207 English references, 282 native branch outcomes. An additional byte candidate is inside another instruction without a graph entry. [Event audit](EVENT_STUB_AUDIT.md). | All 34 now have individual no-entry dispositions in the shipped script graph; this does not establish ordinary scene eligibility or global unreachability. |
| Results, records, saves and link text | 336 result, 664 result-UI, 54 history-UI, nine history-menu, 15 records, four password and 56 save-preview cases; successful trades, four received-item cold loads and a 58-call result-reason graph. The [link-error continuation](LINK_ERROR_AUDIT.md) adds 15 scenarios / 24 peer routes and cold loads across all five errors, disconnection phases, asymmetric timing and cancellation. | Two injected post-save fault exits reproduce original item loss; closed as original behavior, intentionally preserved by user instruction. Physical cable behavior, other timing offsets, item combinations and story banks remain outside this cohort. Password kana is intentional protocol data. |
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
| Repaired tutorial screens | Preceding ROM `fc9b6f5e…`; 22 bank sessions / 51,601 glyphs, 27 menu sessions / 7,431 glyphs, one Mimic-parent session / 562 glyphs | Whole-stream checks include header, border gap and restoration; three script probes additionally execute native selectors/handlers. |
| Release-checkpoint supplement | Preceding ROM `fc9b6f5e…`; 189 sessions / 13,662 glyphs | 67 town/dungeon travel-list, 16 book/travel, 105 travel-confirmation and one native town-save continuation cases; all unfiltered checks pass. [Receipt](../build/caller-branches/release-followup.json). |
| Complete controlled ending | Preceding ROM `fc9b6f5e…`; one complete route / 71 reads / 3,338 glyphs, repeated with caller ABI/stack guard checks | One bank-call entry override; native save, all five scenes, all 57 ending resources, fades, credits, END artwork and return. [Receipt](../build/ending-sequence-guarded/report.json). Saved-name exceptions remain exact. |
| NPC shop routes and link trades | Current ROM `588dc92c…`; four shop routes / 12 opens and two real trades / two cold loads | Full native scene/service selection, unfiltered visible text, native serial driver and persistence. [Receipt](../build/accepted/3814-npc-shops/completion.json). Controlled setup is recorded. |
| Ordinary green-book trade | Current ROM `588dc92c…`; two ordinary entries / one exchange / two cold loads | Empty gate, natural deposits, exact received properties, live carried records, storage capacity, native town return and unfiltered text. No state overrides. [Receipt](../build/link-entry/report.json). |
| Link-error callers and recovery | Current ROM `588dc92c…`; 15 scenarios / 24 peer routes and cold loads, plus original-ROM comparison | Native green-book entry, all five error selectors, full cleanup/return, asymmetric inputs and four disconnect phases. Explicit faults reproduce two original post-save item-loss exits. [Report](../build/link-errors/verified/report.json), [scope](LINK_ERROR_AUDIT.md). |
| Ordinary continuation | Eight segments / 13,499 glyphs / 2,147 input/wait actions; individual ROM hashes retained | Mt. Fiery unlock, native suspend/current-ROM cold resume, 8F, defeat and both retry outcomes. [Summary](../build/caller-branches/ordinary/summary.json). Quest completion unproved. |

Cohorts can overlap; do not add them as unique-screen coverage. Preceding-ROM
audits are not current-ROM replays. Ordinary routes provide integration/save
evidence; repeated attempts to survive a dungeon are not an acceptance requirement.

## Remaining work, in investigation order

The specific link-error cohort is now investigated. Its text checks pass; the
separate original gameplay/save-recovery defect is closed under the user's
instruction to preserve original behavior. No gameplay repair is planned.
Do not recycle “all link errors untested” as the next task. Physical cable tests,
arbitrary timing faults and power interruption are not implied by emulator cases.

1. **Keep the completed source cohort closed.** The former 62 shared/town
   sources and 34 fragments now have [individual dispositions](TEXT_SOURCE_DISPOSITIONS.md).
   Town: 20 services / 167 reads. Shared: 293 exports / 688 sites, including all
   658 earlier tracer sites. Events: 458 current NPC roots plus both event
   interpreters and direct/tutorial getter contexts. None selects those retained
   sources under the stated native-data bounds. Reopen only with new evidence.
   Tutorial configurations 1/2/8/9 retain their separate bounded no-entry result.
2. **Keep analysis honest.** A new cross-check fixed the spell-menu audit's
   overwritten first observation. All 61 records now verify their actual nine
   target labels in both consumers. Four older loop-trace observations outside
   the native record domain are explicitly rejected in the receipt. SSA avoids
   the previous path-budget cutoffs for the exported read graph; unknown
   synthesized entries and corrupt RAM remain outside its bounds. Original
   dormant bytes are preserved, and language-review totals have not increased.
3. **Probe uncovered scene/branch contexts.** Identify entry conditions through
   disassembly, then use disposable saves, controlled state or documented
   invincibility/damage patches to reach later scenes efficiently. Exercise native
   callers/selectors/renderers; check all visible fields, pixels and transitions.
   Keep unmodified damage/death cases when those branches are under test.
   Calling a renderer alone does not prove its scene caller works.
4. **Check text repairs and release them.** Fix confirmed issues, check related
   consumers, update this matrix and complete affected regressions and required
   acceptance before the next release. Further graphics auditing was stopped at
   the user's request on 2026-10-07; prior graphics evidence remains historical.

No additional dungeon/pickup scenario has been identified beyond the repaired
reports. It is not counted as a confirmed outstanding defect. A new reproducible
report should be investigated with retained saves, code and unfiltered probes.

Disassembly leads discovery. Runtime checks establish which bank/state reaches a
reader, whether dynamic fields fit, and whether drawing/restoration is correct.
Record every override, input schedule and ROM/save hash. No invincibility patch
is required for the completed ending probe; its one entry override and native
save changes are recorded separately from ordinary progression.
