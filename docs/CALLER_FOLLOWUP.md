# Caller follow-up — October 3, 2026

This audit follows text producers, computed selectors and final consumers.
All three confirmed defects below are repaired, and cumulative acceptance passes
on the final ROM. Earlier receipts remain tied to their own ROM hashes.
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
base-register-in-list case. On the current candidate, its 1,294 direct-call patterns leave 98 arguments
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

## Reproduction and current validation

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
`completion.json` pins report hashes, ROM identity, the unchanged supplied ROM/save,
clean reproduction and the separate ordinary-route provenance. The original
62 shared/town sources without resolved readers and 34 classified event stubs
remain discovery limits; neither the case counts nor the source catalog establish
whole-game completion.
