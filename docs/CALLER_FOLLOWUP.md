# Caller follow-up — October 3–7, 2026

October 7 link-error continuation: see [LINK_ERROR_AUDIT.md](LINK_ERROR_AUDIT.md)
for all five native error selectors, 15 English scenarios / 24 peer returns and
cold loads, and the original-ROM comparison. Text checks pass; two injected
post-save fault exits expose an original item-loss bug. It is separate from the
successful timeout restoration. The user chose to preserve original gameplay
behavior, so the finding is closed as documented original behavior with no repair
planned.

The current checkpoint repairs two bank-2 shopkeeper selectors and validates
actual two-core link trading. ROM SHA-256 is
`588dc92ce09104cb80d18fb4929e6e713f86836e65d8c12b135dfb4f4269b7ad`;
the root ROM/BPS are updated. See [the October 4 evidence](#npc-shop-selectors-and-two-core-link-trading).
The October 7 source-by-source continuation now gives all 96 formerly
unresolved records [bounded dispositions](TEXT_SOURCE_DISPOSITIONS.md). It also
fixes the spell-menu audit’s overwritten first observation. No ROM change was
needed. Earlier sections and receipts below describe their recorded builds
and the investigation classifications at those dates.

The continued branch audit below repairs two additional tutorial configurations.
Its ROM is `fc9b6f5ea20643a6aabda35768c55c545dbe94a66766d234704aefa931b57a7c`;
the resource count remains 3,814 because both repairs reuse existing English.
Cumulative native acceptance and 182 unit tests pass. The ROM/BPS and receipts
are archived in `build/accepted/3814-tutorials/`.
[Tutorial-build acceptance receipt](../build/caller-branches/completion.json) ·
[Tutorial screenshots](../build/english/tutorial-bank-validation/index.html).
The earlier receipts and hashes below remain historical evidence.
Current cross-family status is in [the coverage matrix](COVERAGE_AUDIT.md).
Next release-confidence work is broader independent playtesting and investigation
of concrete new text reports or uncovered caller/state combinations. Completed
source and link-error cohorts stay closed unless new evidence appears. Disposable
assisted access remains appropriate. Ordinary Mt. Fiery completion is not a localization gate;
its attempts below are retained integration evidence, not the next work priority.

The earlier pass below followed text producers, computed selectors and final
consumers. Its three confirmed defects are repaired, and cumulative acceptance
passed on ROM `45239404…`. Those receipts retain that earlier ROM identity.
[Native before/after gallery](../build/caller-audit-next/index.html) ·
[Acceptance receipt](../build/caller-audit-next/completion.json).

## Confirmed repairs

| Failure | Cause | Repair and evidence |
|---|---|---|
| Four monster staff announcements | The ability handler used the private English table, but the separate projectile handler retained the original table literal at ROM `0002AC2C`. | Both readers now share the owned 24-entry table. All four full projectile effects and 16 selector/field boundary cases pass. |
| Empty-ability sword/shield Info | The fused-equipment branch with zero remaining ability bits used original category table literal ROM `00017BF8`; its sibling at `00017E68` was already private. | Both readers now use the existing English category table. Sword and shield each pass three ordinary Info opens/cancels after controlled item setup, with exact copies, glyph checks, guards and parent restoration. |
| Shield reflection damage | The damage formatter at CPU `0800CED4` computes its selector from the parent's saved argument. Selector `89` still selected Japanese source `0806393C`; ordinary damage selector `67` was already English. | A private copy of the compiled shared table preserves ordinary damage and redirects reflection to “{actor} takes {amount} damage from the shield.” Five complete attack cases pass, including warrior reflection, equipped Blade Shield, field boundaries and colour. |

The shield format uses a conditional break only when the full sentence exceeds
the verified line budget. Maximum tested expansion is 139 bytes within the
original 256-byte output. Tests check actual glyph pixels, queue/caller guards,
complete attack return and the native damage effects. No RAM/save allocation,
window resize or font change is introduced.

Baseline ROM: `f47b6df310211585406c921d8070e1824a8e1cf76a324cd72c8b8669ad6ef865`.
Projectile-only ROM: `500aa2075df9d241e70b1d5dc2a8f010cff660c7b78ea861b9307ce54d48c4b5`.
Intermediate candidate with projectile and reflection repairs: `b229bbb6f6b4785c726c40be07369510b1a3540022b9858ac1e27829e5d8d42f`
(3,814 inserted text resources, 20 graphics).
Accepted ROM, including the Info repair:
`452394042d5be4c83adb79fa35eaba5ca261514533b2162604032b9561e44304`.
The Info change redirects one four-byte literal (three bytes differ); it adds no
resource allocation. All earlier allocations remain byte-identical to the
3,813-resource baseline. The new shield sentence/table are appended by the shared
allocator. No geometry, gameplay logic or save format changes are introduced.

Evidence under `build/caller-audit-next/`:

- `projectile-reader-baseline/report.json`: four original failing full effects.
- `projectile-reader-fixed-effects/report.json`: four repaired full effects.
- `candidate/projectile-announcement-validation/report.json`: 16 boundary cases.
- `shield-baseline-entry/report.json`: original Japanese reflection through the full attack.
- `shield-fixed-health/report.json`: five repaired reflection cases, with visible pixels and native HP changes.
- `empty-ability-baseline/report.json`: both original Japanese Info fallbacks.
- `empty-ability-fixed/report.json`: both English fallbacks, three opens/cancels each.
- `info-candidate/dynamic-selectors.json`: byte-checked computed bindings on the final candidate.
- `info-native/`: final-ROM unfiltered replays, including all three repaired paths.

These controlled probes retain their inputs and state changes. They establish
native handler behavior, not ordinary acquisition or a complete playthrough.

## Findings that did not require ROM changes

The equipped-item curse selector retains three Japanese source pointers on
purpose: the closed queue mapping translates them before display. Following the
table alone briefly produced an incorrect suspected defect. The full unfiltered
curse audit passes all 13 cases, including shield/weapon/ring priority, carried
items and resistance. The computed-selector audit now includes that mapping.
Evidence: `shield-native/curse/report.json` on the two-repair candidate.

The previously unobserved Throw landing format now executes through an ordinary
Throw action after controlled item/trajectory/RNG setup. “Bread fell to the
ground.” passes exact bytes, output guards, glyph checks and the complete native
Throw return (`throw-landing/report.json`, projectile-only ROM).

The static scanner now models ARM7 Thumb `LDMIA`, including writeback and the
base-register-in-list case. On that preceding candidate, its 1,294 direct-call patterns leave 98 arguments
unresolved after five private-entry models and the separate storage dispatch
analysis. This is a bounded data-flow limit, **not 98 confirmed failures**.
Computed selectors, producer evidence and unfiltered native observations are
recorded separately rather than silently treating unresolved arguments as safe.

## Unfiltered display checks

`tools.audit_native_callers` observes all shared consumers and glyphs while an
existing verifier runs. It preserves the verifier's callbacks and distinguishes
controlled probes from ordinary routes. Reports record the ROM, tool/verifier
hashes, inputs, calls and any unclassified glyphs. Tool hashes are captured at
the start of the run, with a separate check for changes during execution.

Japanese saved player/village names, optional kana keyboard pages and the
existing nine-kana promotion-password protocol remain intentional. Exceptions
require the exact native caller, input field, complete output and relevant
geometry; they cannot excuse neighboring authored Japanese prose. Negative
tests exercise wrong callers, changed fields, surrounding text and geometry.
The Remi fallback probe intentionally supplies Japanese templates as a negative
control; its findings are not waived or counted as English gameplay acceptance.

The final supplemental cohort comprises 35 verifier families and 813 sessions
on the final ROM. Five initial replay commands lacked prerequisite fixture
files; the existing native context recipes supplied them and all five reruns
passed. `final-replay-resolution.json` distinguishes those setup failures from
the passing final reports. The initial command log is retained, not used as
the acceptance receipt.

## Ordinary progression

The recorded ordinary route completes the castle flame quest, repairs storage,
performs deposit/withdrawal, accepts the baker's quest and cold-loads the earned
battery into the projectile-only ROM. It reaches Cemetery Dungeon with ordinary
inputs. The successful continuation completes all six dungeon floors and the grave
scene, returns home, opens the bakery through the native quest flags and saves
at the repaired storage book. Replays branch from earlier checkpoints earned by
ordinary inputs after failed attempts; no item, actor, map, register or save-byte
edits are used. The final candidate cold-loads that newly earned battery and
continues through the missing-King audience and an ordinary bakery purchase.
Magic bread costs exactly 400G (1,729→1,329), enters the inventory, and survives
Save and continue followed by a cold load of the earned battery on the final ROM.
Both the item and balance persist. The purchase, repeated-purchase menu,
farewell, native save and cold-load inventory have no unclassified glyphs or
layout violations. Class progression and ordinary ending access remain unclaimed.
Evidence: `ordinary/bakery-final/report.json` and
`ordinary/bakery-persistence/report.json`.

A further battery-only cold load reaches the Adventurer's Inn exterior through
ordinary travel and checks three conversations: the young woman's Bread-scroll
complaint, the lovestruck man's explanation and the adventurer's entry refusal.
All authored text is English; inventory, 1,329G and the battery remain unchanged.
The travel menu retained its earlier cursor selection, so the exploratory
worker's `old-man` filename is not the actual destination. The corrected
evidence is `ordinary/adventurers-inn/report.json`; no inn-interior or
Old man's house access is claimed.

The ordinary artifacts retain the complete input schedules and unchanged source
identities. Read-only map inspection chooses movement; it does not alter the
map, inventory, actors, registers or saves. Controlled service/ending acceptance
remains separate from these gameplay milestones.

## Dispositions for the remaining bounded-scan callers

`tools.audit_caller_dispositions` joins the static scan with unfiltered native
reports. It keeps current-ROM observations separate from historical ones and
retains the exact case paths. An observation does not prove every branch of that
caller. The final join is `final-static/accepted-observations.json`: **89 callers
observed on the current ROM, six verified actor-name copies and three old calls
bypassed by owned hooks**. None of these 98 callers remains without an
investigated disposition. Native branch coverage remains limited to the linked
cases; static dispositions are not counted as gameplay observations.

Several important static limitations have concrete explanations:

| CPU call(s) | Producer or selection | Evidence / remaining limit |
|---|---|---|
| `0800CE9C`, `0800CF9A`, `0800D70E`, `0802D524`, `080392B8`, `08039984` | Copy the result of native actor-name getter `08009ACC` | Name copies, not independent authored sentences. Actor identity and transformed/saved-name families own their source checks. |
| `0801587E` | Conditional forwarding of the sole direct caller at `080097A0` | The producer at `08009798` selects English combat slot `1C4`. Two complete native turn probes check the shown/suppressed queue outcomes, exact output/guards and HP 20→10. Controlled terrain/queue bytes are recorded. |
| `08016F28`, `08016F56`, `0801707E` | Floor modal and its temporary output | Full Floor-menu state audit; the original reported failure remains a regression case. |
| `08017BB0` | Empty-ability category fallback | Newly confirmed Japanese sword/shield descriptions, now repaired via `17BF8`. This branch was absent from the previous nonempty-ability cases. |
| `0801A774` | Redraw one Option value using the same row producer as full opening | Three additional vocation cases execute six single-row reads each with ordinary RIGHT/LEFT inputs and no unclassified glyphs. |
| `0801E6E6` | Town Trash confirmation, including filled pot | Entry `0801E490` installs a sparse private table. The original shared-town slots remain Japanese intentionally. The static entry model now includes this fifth hook. |
| `0801F584`, `0801F7EC` | Storage table passed by the dispatcher, retained in `SP+14C` / `r10` | Selectors `B6` and `BB` resolve to the reviewed capacity warning and withdrawal result. Ten native storage-service cases include the additional two-selected/one-free-slot rejection at `1F584`, without transferring or losing carried/stored items. |
| `0802585E` | Original item-use queue call | Replaced by the existing helper at `0802585A`; it is not a current executable queue instruction. |
| `080261BC` | Throw miss/landing formatter | Full native Throw landing audit, with controlled item/trajectory/RNG state. |
| `080282E6` | Stumble-trap item placement failure | Private slot `1D0`; nine unfiltered native Stumble cases cover drop, exhausted placement, resistance and field boundaries. |
| `0802ABDE` | Second monster announcement formatter | Newly repaired; all four selecting species and boundary fields tested. |
| `0803E1F0` | Warrior item-loss output | Private item-loss format at slot `1E0`; existing frame/format/queue preflight explicitly skips unrelated gameplay. |
| `0804BC64` | Positioned modal forwards incoming text | Its callers and resource bindings, rather than the generic wrapper alone, determine coverage. |
| `08050218`, `08050244` | Floor-progress group 7, indices 5–8 | Existing owned 288-byte output and 27 native selector/name cases. |
| `08050BFE`, `08050C30` | Original village-name / well-level formatters | Their original entry points redirect to replacement functions with separately owned buffers. The old interior calls are not acceptance targets for normal entry. |
| `08050E6A`, `080510CA` | Tutorial topic modals | Direct-prose topic tests are distinct from the 27 menu-only and four alternate-heading checks; bank-backed topics have their own selectors. |
| `08052E14` | House-fire record sequence | Full fixed-record dispatcher, private 512-byte stride and all 40 nonempty records. Scene staging and ordinary access remain separate. |
| `08057B84` | Link status window forwards incoming text | Two direct caller literals select the reviewed trading/saving notices. Actual multiplayer exchange remains outside the text probe. |

These explanations are not a substitute for native evidence or a claim that
unknown indirect callers cannot exist. The 62 remaining shared/town source
records have no resolved read in the refreshed bounded scan. The other 34 source
records are the original event stubs accounted for in
[EVENT_STUB_AUDIT.md](EVENT_STUB_AUDIT.md). The catalog now contains 3,552 reviewed
sources, 96 unresolved sources and 28 retained/component sources out of 3,676;
these are source counts, not whole-game completion percentages.

## Reproduction and validation of the preceding 3,814 ROM

`reproducibility.json` records identical clean ROM/BPS output, independent ledger
reconstruction and unchanged earlier allocations. `final-validate-after-info.log`
passes 174 unit tests, native emulator/save checks and the pinned toolchain.
`accepted-build.log` and `accepted-build-result.json` record the complete passing
cumulative build. The final font browser and service acceptance also pass,
including all 2,006 required item cases. The unfiltered supplement covers 35
verifier families, 813 sessions and 267,527 glyph observations on this ROM,
with zero unclassified glyphs, unreadable streams or layout violations.
The 98 bounded-scan callers have the dispositions listed above.

The ROM, BPS, build ledger and receipts are archived in `build/accepted/3814/`.

## Continued branch audit and tutorial repairs

The native getter investigation confirmed both tutorial mismatches previously
listed in `MEMORY_MAP.md`. They are present in the original Japanese ROM too;
relocating the surrounding prose does not repair their incorrect callers.

| Configuration / script context | Failure | Repair |
|---|---|---|
| 12, pot help; bank 4, map 11, NPC selectors 1 and 2 | Seven `(2,index)` selectors address a bank where group 2 is Aunt Maggie's conversation. Native getters return unrelated dialogue, partial strings and one remaining Japanese fragment on the English ROM. | Use the existing direct-prose handler with the seven reviewed bank-5 pot explanations. The same menu also works in banks 5 and 6 without depending on the active bank. |
| 14, early trick help; bank 5, map 4, NPC selector 1 | The label table begins with Mimic/Cancel, but its six-row descriptor reads into the next menu. Its topic selectors address Gon dialogue, partial strings and finally an invalid address. | Select the existing two-row menu geometry and bind the Mimic topic directly to its reviewed bank-6 explanation. Later trick-help configurations remain intact. |

The repair introduces no new prose, bank loads, RAM allocation or save format.
Pot explanations retain the seven existing topics. Six corresponding bank-5 and
bank-6 English explanations were already identical; the remaining Transformation
pot wording differs in phrasing, with the same meaning. The repaired menu uses
the bank-5 wording consistently. Mimic help reuses `event-bank-6.3278` verbatim.
The early menu's two-entry label prefix and the following configuration's table
starting at its third entry support the two-row repair; this is a caller/data
repair, not a translation of missing dialogue.

Only 27 ROM bytes differ from the previous accepted ROM: three changed dispatch
bytes within two owned three-byte records, plus eight pointers in two existing
private tutorial tables. Allocation addresses, all other resource bytes, the
shared geometry/cursor tables, event bank payloads and scripts are unchanged.
The BPS SHA-256 is
`0abed5a9b873844c978d1d10db9017d81cd1d3a10cb3f118e32277f73d064550`.

Native validation on the repaired ROM covers 22 bank/configuration cases, all
27 menu configurations, six direct-prose cases and four alternate headings.
Every topic/page, selection, cancellation and repeated opening passes, including
all three pot-help banks and the shared six-row geometry still used elsewhere.
The repaired Mimic menu also preserves the header frame and eight-pixel gap
through cursor movement and seven captures, and restores the display layers
after all three closes. Cumulative acceptance checks these saved pixels.
Three additional NPC-script probes execute the original selector, introduction,
mode-2 tutorial opcode, first explanation and farewell. They verify that the
active bank, inventory and battery remain intact. The host controls bank/map/NPC
setup and dispatches the original handlers, skipping WAIT; these are not claims
of ordinary story access. Acceptance now requires these three routes.

Evidence under `build/caller-branches/`:

- `tutorial-getters/report.json`: original and English native getter failures;
  the adjacent probe script retains the exact controlled calls.
- `native/pot-help-repaired/` and `native/mimic-help-repaired/`: focused repairs.
- `native/tutorial-bank-final/` and `native/tutorial-menus-final/`: unfiltered
  replays of all 22 bank cases and 27 menus on the repaired ROM.
- `native/mimic-parent-final/`: strengthened Mimic frame/gap and close checks.
- `tutorial-candidate/tutorial-script-validation/report.json`: all three actual
  NPC selector/script routes, with inputs, controls and screenshots.
- `tutorial-candidate/build.json`: checked patches and allocation ownership.

## Expanded discovery and verifier corrections

`tools.thumb_switches` recognizes the complete bounded Thumb
CMP/BHI/LSL/LDR/ADD/LDR/MOV-PC pattern. It requires unchanged code, literal and
table bytes, consistent registers and valid aligned targets. The tracer follows
each bounded selector plus the default branch. Six synthetic instruction tests
exercise those branches and reject changed or malformed patterns.

The new source-reader pass follows four previously blocked unknown switches.
It still finds no resolved reader for the 62 shared/town sources. Its five new
bindings are existing item-format templates and the owned gold-spacing format;
none is a newly found Japanese sentence. A separate reproducible scan seeds all
25 recognized guards (326 entries), finding 16 bindings and 13 shared-table
reads. One intermediate Japanese strengthening pointer is already translated
by the player-message wrapper; 12 unfiltered strengthening cases confirm this.
The initial all-guard scan has one seed budget limit at `080147F8` and nine path
length stops. A separate 800,000-step scan of that save-menu seed finishes without
a budget stop and finds no additional bindings. Thirteen path-length stops,
three indirect returns and four patched-instruction stops remain explicit in
that expanded scan; neither scan classifies unvisited code or sources as unused.
Reports: `source-readers-final.json`, `switch-readers-final.json` and
`save-switch-expanded.json`.

The broader unfiltered replay covers 19 verifier families and 1,042
sessions on the preceding accepted ROM. Initial save-preview runs lacked two
fixture files; rerunning with the existing native fixtures passed. Five glyph
findings were exact saved player names inside English staff-drain, pull and
identify-all messages. The observer now checks each disassembled producer,
argument address, destination and complete output before exempting only the
name's positions. Wrong callers, reused output buffers, changed names/outputs
and neighboring authored Japanese remain failures. The corrected 8-case monster,
40-case discovery and 15-case gold-theft replays pass. These are observer fixes,
not newly translated game sentences. Initial reports remain retained. `native-resolution.json` pins all 19 final
reports: 1,042 sessions and 256,870 glyph observations with no findings.

The skill item-loss verifier previously bypassed the native equipped-name cache
copy. It now executes `strcpy`, checks the full copied name and surrounding RAM,
and preserves ABI/guards. All 32 item-loss cases pass, including four cache cases
with a maximum tested 63-byte encoded string. This establishes those writes,
not new ownership of surrounding RAM or ordinary skill acquisition.

Ordinary input progression reaches the Old man's house, learns about the missing
King and unlocks Mt. Fiery. Earlier-ROM attempts reach 7F with a Copper sword and
Bronze shield; their defeat/results/retry screens are English. A continuation
from the earned 6F checkpoint finds a Silver shield, reaches level 6, and creates
a native Save & suspend. The repaired ROM cold-loads only that battery, preserves
the items/equipment and resumes on 7F. Subsequent ordinary play reaches 8F before
defeat, displays the English results/retry screens, and returns to the surface
through No. Another branch from the earned 8F checkpoint uses a carried Binding
scroll, passes the immobilized Troll, later suffers defeat and takes Yes to retry
with the native Big bread. All eight recorded route segments pass the unfiltered
text audit (13,499 glyphs and 2,147 recorded input/wait actions); `ordinary/summary.json`
pins their separate ROM hashes, ancestry and scope. Inputs and failed attempts
are retained; no inventory, actor, flag or save-byte overrides are used.
Quest completion and ordinary late-game/ending coverage remain open.

All cumulative native families pass on the repaired ROM, including 2,006 item
cases. The initial `build.sh` invocation stopped afterward because the tutorial
budget collector still expected 20 bank cases. Its required count and coverage
note now match the expanded 22-case cohort. The remaining report/font-generation
commands pass when resumed; `accepted-build-result.json` records the initial
failure and its resolution rather than replacing the failed log. WebKit initially
could not start inside the macOS sandbox; the same local check passes with the
required access: 315 contexts and 3,430 measurements, with no selected-font
overflow. Final service/menu acceptance and clean ROM/BPS reproduction pass.
The 182-test unit run and pinned toolchain checks also pass. Final artifacts are
archived in `build/accepted/3814-tutorials/`; the preceding archive is preserved.

`completion.json` pins report hashes, ROM identity, the unchanged supplied ROM/save,
clean reproduction and the separate ordinary-route provenance. The original
62 shared/town sources without resolved readers and 34 classified event stubs
remain discovery limits; neither the case counts nor the source catalog establish
whole-game completion.

## Release checkpoint and bounded continuation

The user requested periodic builds while usage is limited. The
[checkpoint ZIP](../build/releases/2026-10-03-tutorials.zip) contains the accepted
BPS, release notes, checksum list, original acceptance receipt and
[research follow-up receipt](../build/caller-branches/release-followup.json).
A fresh compile in `build/release-checkpoint-rebuild/` matches the accepted ROM
and BPS byte-for-byte; independent application also matches. No new ROM fix was
confirmed in this continuation, so the resource count and release hashes stay
unchanged. The 182-test archived full acceptance is preserved; the extended tool
suite now passes 184 tests.

`tools.audit_tutorial_reachability` checks 133 physical event-script instruction
regions and seven complete NPC payloads, with original/compiled equality. It
finds 22 script-selected configurations; the only paged selector is 18, whose
native page bound adds 19. Configurations 1/2/8/9 have no instruction-aligned
reference or known page entry. A configuration-8 byte motif in bank 4 is inside
another instruction, and 11 apparent configuration-255 NPC motifs are actor data
outside the instruction regions. All raw matches remain in the report.
Original configurations 1/2 interpret selector bytes as direct prose; 2/8/9 also cross a
two-row label prefix and misplace Cancel. These original records remain retained
with no known entry, not declared globally dead or repaired with invented prose.
The only literal Thumb pointer to handler `0804F8F4` is opcode-8 slot ROM
`0014CE4C`; its ordinary menu calls and sole paged call are enumerated. Unknown
arithmetic/indirect entry paths remain outside this bound.

The tracer now optionally records stop PCs, paired bytes, registers and repeated
path addresses without changing its decisions. Two regression tests verify that
observation preserves results and records changing-value loops accurately.
`tools.audit_switch_stop_dispositions` classifies 35 distinct exits from all 25
switch guards and the expanded save seed: 23 are POP/BX return locations, the
changed instruction is the owned name-limit patch at `08014BE6`, and the length
limits repeatedly traverse the save-menu row loop. Seeding its disassembled
selectors 0/1 in `tools.audit_save_menu_rows` resolves one/three rows and all four
English bindings. Other downstream states remain recorded; the 62 unresolved
source records are not closed by this finding.

Additional current-ROM unfiltered checks pass **189 sessions / 13,662 glyphs**:
67 town/dungeon travel-list states, 16 book/travel cases, 105 confirmation cases,
and a native town-save Continue. Initial save-preview and town-route launches
lacked fixture copies; these are retained setup failures, not game defects.
Matching-ROM fixtures were copied with hashes, and both reruns pass. The other
cases retain their controlled handler/state exclusions. No new ordinary late-game
progression is claimed.

Reproduce the static research with `tools.audit_tutorial_reachability`,
`tools.audit_save_menu_rows` and `tools.audit_switch_stop_dispositions`; commands
for generating their input scans are in [EXPLORATION.md](EXPLORATION.md).

## Computed readers, graphics and complete ending

[Aggregate audit/rebuild receipt](../build/caller-continuation/scene-audit-receipt.json)
pins the reports below separately from the original cumulative acceptance.

The next continuation adds observation at binary operations where an unknown
index discards a known table base. Two tests verify that this observation leaves
trace results unchanged and does not invent bindings. Across 636 literal seeds,
`tools.audit_computed_table_losses` identifies and classifies 41 sites: 37 point
into existing owned translated tables, one is the already-resolved save-row loop,
one is the equipped-curse path with its verified queue adapter, and two are
sprite-coordinate arithmetic that happens to overlap the town text RAM range.
The paired instruction bytes and compiled allocation ownership are in
`build/caller-continuation/computed-table-losses.json`. All 186 unit tests pass.
The 49 seed-budget limits and other conservative trace stops remain explicit;
this does not make the 62 unresolved catalog sources unused or identify 49
new display defects. No additional untranslated reader was found in this cohort.

The graphics audit follows both native descriptor families rather than searching
only translated strings. All 22 full-screen records (19 unique bases, nine
foreground records) pass native tile/map upload checks. Visual review finds the
six already-replaced title/logo occurrences and existing Latin publisher logos;
the remaining layers contain scenery. The separate scrolling table has 28
records / 23 unique bases, 11 flag replacements, 14 door records and 85 static
object instances / 79 distinct compositions. Its 53 selector states and 377
native getter calls pass; object decoding uses the initialized native palette
lookup. No additional Japanese lettering was found in these decoded families.
These are layer/selector checks, not proof of ordinary access to every scene.
Independent actor animation and other atlas consumers remain outside this bound.
See [the graphics inventory and galleries](GRAPHICS_INVENTORY.md).

The [complete ending probe](../build/ending-sequence-guarded/index.html) replaces
one ordinary bank-call entry with CPU `08054DA4` in a disposable native session.
After that, the original owner performs saving, all five scene setups, actor
movement, dialogue, fades, the English credit roll, END artwork and return.
No further PC/RAM/display overrides or skipped scene-update calls are used.
The exact stage order and caller callee-saved registers, stack pointer, return
address and 32-byte stack guard pass. All **57 ending resources** are observed
through those scene callers: **71 reads / 3,338 glyphs**, zero unexpected Japanese,
unreadable streams or layout violations. The fixture's Japanese player name is
preserved through exact saved-name substitutions (57 glyph exceptions); it is
not untranslated authored prose. The earlier isolated text/credit verifiers
retain their own narrower scope.

The ending gallery contains 161 sampled native frames. Representative scene,
credit and finale frames were visually reviewed; this is not a pixel comparison
of every frame. The full run was repeated with explicit ABI/guard assertions,
reproducing stage frames and text counts. Native saving changes only the
disposable battery; source ROM and supplied save hashes remain unchanged.
Ordinary endgame qualification and alternative entry-state combinations remain
unproved. This closes the missing complete controlled ending route, without
requiring an ordinary dungeon survival attempt.

The accepted ROM/BPS and 3,814-text / 20-graphics counts remain unchanged.
The [scene-audit checkpoint](../build/releases/2026-10-03-scene-audit.zip) includes
the same accepted patch with the new evidence summary. A fresh isolated compile
and independent patch application reproduce the accepted bytes. No new ROM fix
was necessary in this continuation, and no redundant full native-suite run is
claimed. The original tutorial checkpoint and accepted archive are preserved.

## NPC shop selectors and two-core link trading

The October 4 caller audit reproduces a bank-2 blacksmith failure through the
native town loop: ordinary movement and A from his left select the visible actor's
script at decoded `05E2`, beyond the instruction region `[0318,05E0)`. The
interpreter then consumes actor records as instructions and attempts to read an
unterminated text stream. Talking across the front counter uses another actor
and works, which explains why service-only tests missed the defect. The scene's
bank/map eligibility was controlled; this is not an ordinary unlocking claim.

Remi's visible actor has the same selector error, targeting `05DF`. Her normal
front-counter route works; contact with the visible actor was tested using one
recorded actor-argument override. The repair changes these two actor selector
bytes from 1 to 2, sharing each room's existing native service script. All other
populated story banks use those same services for the shopkeepers. This adds no
dialogue. An ownership check prevented changing Remi's shared offset-table word,
which another NPC uses correctly.

`tools.npc_shop_scripts` appends a replacement compressed bank through the shared
allocator and redirects its one loader pointer. The original compressed bank,
all script instructions, other actors and every preceding English allocation
remain unchanged. The resource count stays **3,814 text / 20 graphics**. Exact
ownership and native selection arithmetic are in [MEMORY_MAP.md](MEMORY_MAP.md#npc-shop-selector-ownership-2026-10-04).

`tools.verify_npc_shop_routes` checks blacksmith side/front and Remi front/visible
routes, three opens/cancellations/END returns each. All four cases pass complete
native bank decompression/header fixups, unfiltered text/glyph/layout checks and
item/gold/battery preservation. The visible Remi override is separate from the
three routes using ordinary movement after controlled scene entry.
[Route receipt](../build/npc-shop-candidate/npc-shop-routes/report.json).
The exploratory `gaibara-*` filenames record the blacksmith; the earlier working
NPC identification was corrected after native service execution.

`tools.verify_link_exchange` now joins two disposable emulator cores through the
pinned native mGBA serial driver. Both games execute their complete trade owner,
menus, receive formatting, saving, repeat and cancellation. Two bidirectional
trades exchange an Oaken club and Gold sword and then return them: **2,310 serial
transfers**, matching on both peers. Battery-only cold boots of the first trade's
results recover both received items. Storage capacity, carried items, gold,
caller registers and stack guards pass; no unexpected Japanese, unreadable text
or layout findings occur. Storage capacity at `02002C2A` is preserved, not treated
as an occupied-item count.
[Trade receipt](../build/npc-shop-candidate/link-exchange/report.json).

The link bridge supplies host scheduling around mGBA's existing lockstep driver;
it does not force a successful protocol result or patch the emulator library.
Controlled stored items and bank-call entry are recorded. The initial report excludes ordinary entry and other item classes; the green-book
follow-up below covers those specific additional cases. Asymmetric/disconnected
exchanges remain separate scopes.
See [TOOLING.md](TOOLING.md) for its pinned implementation and reproduction command.

`./validate.sh` passes **187 unit tests**, toolchain/source identity, fresh-save
native acceptance and Ghidra import. Current-ROM affected service checks pass
57 blacksmith text cases, 13 exchanges and 73 Remi text cases. The earlier full
cumulative suite remains evidence for ROM `fc9b6f5e…`; it is not relabeled as a
full replay of this ROM. The new NPC and link checks are included in `build.sh`.
The candidate and normal compiler reproduce identical bytes; ledger reconstruction
and independent BPS application pass. Source ROM/save hashes remain unchanged.
[Checkpoint receipt](../build/accepted/3814-npc-shops/completion.json) ·
[Patch and release notes](../build/releases/2026-10-04-npc-shops.zip).

These repairs close the two malformed NPC selector leads. The 62 unresolved
shared/town sources and 34 fragments remain a source inventory, not 96 confirmed
failures.

The subsequent handler audit corrects a research decoder discrepancy: opcode 33
consumes two operand bytes in its native handler, despite the original size table
saying one. All 134 extracted contexts have a zero third byte. Native advancement
passes, and corrected traversal preserves all previous dialogue references.
Following the handlers' direct selectors additionally checks 21 existing English
sources. The four retained tutorial configurations still have bounded no-entry
evidence on the new ROM. See [the fragment audit](EVENT_STUB_AUDIT.md) and
[handler receipt](../build/npc-handlers/report.json). No new ROM change was needed.


### Ordinary green-book entry and selector domains

`tools.verify_link_entry` cold-loads the earned storage save on both peers.
Ordinary buttons first verify the green book's English empty-storehouse refusal,
then deposit naturally carried Bread on one peer and Lightning staff on the other.
The green book's **Trade items** choice reaches the original owner through the
NPC script and town loop; no entry, item, flag, ROM or register override is used.
One complete exchange performs **1,200 serial transfers**, saves automatically,
returns both games to town, and survives battery-only cold loads. Received item
properties, remaining carried items, capacity and gold are preserved; both
unfiltered screen audits pass. [Ordinary-route receipt](../build/link-entry/report.json).
This is an ordinary home-book route, not a title-screen option. Story-bank
alternatives, disconnected/asymmetric timing and other item combinations remain
outside this particular receipt.

A stricter cold-load assertion initially compared unused inventory-slot bytes.
Native loading clears stale data in those unoccupied slots; the live items and
received records were unchanged. The corrected check compares every occupied
120-byte carried record and exact received storage records. The initial failure
log is retained as `build/oct04-continuation/link-entry-inactive-slot-assertion.log`.

The disassembled result-reason producer graph contains **58 direct calls across
12 functions**. Its argument domains do not include 28–31, so this graph cannot
select the unresolved legacy ranking string at reason 30. This bounds that
reader; it does not declare the source globally unused or exclude unknown RAM
producers. [Producer receipt](../build/oct04-continuation/result-reason-selectors.json).

Both spell consumers and both skill Info loads now have complete definition-domain
checks: **250 record cases / 378 computed reads**, all selecting inserted English.
The staff-effect constant D4h is an increment onto 59h, yielding 12Dh; it does not
select the unresolved source at D4h. All four staff/upgrade branch bindings pass.
[Definition receipt](../build/oct04-continuation/definition-selector-domains.json).
These are bounded static traces with downstream limits recorded, separate from
native gameplay. The 62-source / 34-fragment discovery counts remain unchanged.

### Soldier, monster and skill selector domains

The October 7 continuation is restricted to text; the user stopped further
graphics auditing. `tools.audit_actor_skill_selectors` adds **548 static cases /
356 English shared-table reads** on the unchanged accepted ROM:

- The soldier creation path supplies object type 2 and a random selector 0–6.
  Both direct calls to the object creator are accounted for; its other call
  supplies type 1, outside the soldier dialogue branch. All seven message
  selections resolve to existing English. This adds producer evidence to the
  earlier nine controlled native display cases, not ordinary soldier placement.
- All 141 monster definitions pass through both announcement readers. The
  45 nonzero definitions resolve to 24 English sources in each reader; the
  other 96 suppress the announcement. The second reader's full record domain
  deliberately includes species outside normal projectile eligibility.
- Skill actions use Set, disabled Set and Info codes 0/5/3. Both row-format
  branches pass for all 128 definitions: mode 6 with a nonzero hunger cost
  selects shared index `1F0h`; zero cost or any other mode selects `1F3h`.

[Text-domain receipt](../build/oct07-text/actor-skill-selectors.json). Selected
instruction/record domains are checked against the original and compiled ROM;
downstream stops and 96 downstream budget limits remain in the report. This is
not whole-function execution, a global RAM-write proof or a reason to declare
the unresolved sources unused. No additional untranslated path was found in
this cohort. The 62 shared/town sources and 34 fragments remain unresolved;
text is not fully signed off. The root ROM and BPS bytes remain unchanged.

### Event interpreter paths and fragment entry checks

The October 7 continuation distinguishes the setup interpreter (`0804F280`,
32 roots) from the scene interpreter (`0804EF40`, 101 roots). The setup caller
selects header type 1 and skips dialogue/choice commands; type 2 starts the
normal scene owner. Conservative branch traversal retains all 207 previously
extracted dialogue references, each selecting existing English. Both outcomes
of 120 flag branches and 21 choice branches pass **282 native handler checks**.
These use unchanged cartridge operands and recorded disposable flag/choice
controls; caller ABI and battery preservation pass.

Two original bank-1 branch offsets enter instruction operands. Their extra
paths add no dialogue, and a native dispatcher check confirms its one-byte
advance over the resulting unexpected opcode. They are recorded source-script
anomalies, not confirmed localization defects; ordinary flag eligibility and
complete scene behavior are separate from these handler checks.

Scanning every byte additionally tests whether fragments were missed because
of instruction alignment. Besides the three known NPC references after END,
one event candidate lies inside another instruction's operands and has no
entry in this graph. No additional fragment caller is found. The 34 fragments
retain their bounded, unresolved classification.
[Details](EVENT_STUB_AUDIT.md) ·
[Reproducible report](../build/oct07-text/event-script-paths/report.json).
The ROM/BPS bytes remain unchanged; no rebuild or full-suite replay is needed.

### Baker dialogue floor bounds

The recovered baker creation path requires dungeon 1 (Cemetery Dungeon) and
completion bit 1 clear, then supplies species `86h`. Its dialogue consumer selects
one of six existing English passages by floor. The progression owner compares
the next floor against the original threshold 7, runs completion, clears the
non-player actors and sets the dungeon-loop exit flag. This provides code evidence
for the six-floor domain in addition to the earlier ordinary quest completion.

`tools.audit_companion_domain` checks **24 native exit-predicate cases**: floors
1–6, normal +1 and alternate +5 progression, before and after completion.
All return the expected result and preserve caller ABI/battery. The six private
English bindings match this domain. This closes the floor-limit question for
the recovered producer/progression path; arbitrary actor changes, other RAM
writers and edited saves are outside that claim. No ROM repair was required.
[Producer and native-predicate receipt](../build/oct07-text/companion-domain/report.json).

### Expanded scan limits and unresolved pointer ownership

`tools.audit_text_limit_followup` revisits all 49 budget-limited literal seeds
with complementary 40,000-instruction/256-path and 200,000-instruction/900-path
profiles. Neither finds a new computed text-reader site. The deeper profile's
25 distinct non-length exits have dispositions: 22 native POP/BX returns, the
existing item/name patches and one long branch to a shared function epilogue.
At `0800BE88`, BL targets `0800CC82`, which restores the enclosing function's
stack/registers and pops its return address. The scanner's assumed fallthrough
at `0800BE8C` is therefore a literal-pool artifact. This is a research-model
disposition, not a ROM bug or a change to the general tracing engine.

Both profiles retain their path limits; the deeper one retains five instruction
budget limits (four main-loop seeds and the second monster-reader seed). They
are not five new missing translations. The earlier selector-specific checks
remain separate evidence; these expansions do not establish full function or
whole-game coverage. [Limit follow-up](../build/oct07-text/limit-followup.json).

`tools.audit_unresolved_text_owners` also checks exact source-start pointers
for all 62 unresolved shared/town records across the entire original ROM,
including unaligned occurrences. The 52 shared sources have pointers only in
the original shared table. The ten town sources have decoded pointers only in
their 300-word table; the one raw linked-address match belongs to that compressed
resource. No additional exact-pointer owner is found. Arithmetic/interior
pointers, other compressed resources and code reachability are explicitly
outside this census; it does not declare the sources globally unused.
[Pointer ownership receipt](../build/oct07-text/unresolved-pointer-owners.json).

### Individual source dispositions and audit correction (October 7)

The former 62-source / 34-fragment backlog now has a disposition for every ID
in [TEXT_SOURCE_DISPOSITIONS.md](TEXT_SOURCE_DISPOSITIONS.md) and the
hash-pinned `config/text-source-dispositions.json`. Town SSA accounts for 167
read sites in 20 services. Shared SSA accounts for 688 read sites in 293
function/block exports, including all 658 prior tracer sites. Explicit native
selector domains exclude all 62 retained sources in that recovered graph.

The current compiled actor records yield 458 NPC roots / 683 modal reference
contexts. Combined event, direct-getter and tutorial contexts exclude all 34
fragments: three after END, one operand coincidence, thirty without selectors.
Original source bytes remain preserved. These are bounded code/data findings,
not a global unreachable proof or ordinary scene coverage.

The independent cross-check caught a verification defect: the spell-menu audit
previously overwrote each seeded read with later loop visits. It now checks the
first read against the actual spell definition. All 61 records cover their nine
target labels in both menu and Info; 250 record cases / 378 reads and four
staff-effect bindings pass. Four older unconstrained-loop observations outside
that native record domain are retained with explicit rejection reasons.

All **191 unit tests** pass, including new branch-union, unknown-index, immutable
ROM-alias and mutable-RAM controls. The catalog preserves language counts while
reporting investigation status separately: zero untranslated records without a
disposition. No ROM fix was needed; root ROM/BPS and supplied source/save hashes
remain unchanged. This supersedes the earlier undifferentiated 62/34 backlog,
not the scope of historical native acceptance receipts.
