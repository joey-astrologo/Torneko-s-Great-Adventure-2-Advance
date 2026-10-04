# Caller follow-up — October 3, 2026

The continued branch audit below repairs two additional tutorial configurations.
Its ROM is `fc9b6f5ea20643a6aabda35768c55c545dbe94a66766d234704aefa931b57a7c`;
the resource count remains 3,814 because both repairs reuse existing English.
Cumulative native acceptance and 182 unit tests pass. The ROM/BPS and receipts
are archived in `build/accepted/3814-tutorials/`.
[Current acceptance receipt](../build/caller-branches/completion.json) ·
[Tutorial screenshots](../build/english/tutorial-bank-validation/index.html).
The earlier receipts and hashes below remain historical evidence.
Current cross-family status is in [the coverage matrix](COVERAGE_AUDIT.md).
Next work follows unresolved code/source/scene paths, using disposable assisted
access where helpful. Ordinary Mt. Fiery completion is not a localization gate;
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
