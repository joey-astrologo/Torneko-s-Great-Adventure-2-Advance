# Reader paths and known localization failures

The October 2 follow-up uses disassembly to enumerate callers and status
branches, then runs automated native probes for those branches. **There is
still no complete count of broken paths across the ROM.** This bounded audit
found an additional empty-inventory defect and seven untranslated status-expiry
messages. **All eight are now fixed.** The expiry correction passes 44 native
cases, including every one of the 20 recovered timer branches.

The subsequent [broader caller audit](CALLER_COVERAGE_AUDIT.md) confirms 54
untranslated caller sites, 31 more than its first pass.
Those separate findings remain open; the fixed modal/timer results below do
not establish coverage of those other callers.

## Findings

| Area | Result | Evidence |
| --- | --- | --- |
| Empty inventory | Was Japanese; now “You have no items.” | Ordinary Eat of the opening bread, then Items; old ROM fails, corrected ROM passes. |
| Standing on a visible trap and selecting Trap | Step and Stay are English; transformed, frightened and dancing refusals are English. | Controlled trap/status setup followed by normal menu buttons, cancellation and reopening. |
| Status expiry | All 20 recovered timer branches display English. | 44 native cases cover individual timers, maximum saved names, transformed names and simultaneous expiry. The previous ROM reproduces exactly seven Japanese failures. |
| Other callers | 54 sites confirmed untranslated; broader coverage incomplete. | [Caller coverage audit](CALLER_COVERAGE_AUDIT.md):79 scenarios,20 other unconfirmed candidates, one copied-source lead and412 unresolved arguments in the expanded ten-consumer scan. |

[Corrected menu gallery](../build/reader-audit/native/index.html) ·
[Menu acceptance](../build/reader-audit/acceptance.json) ·
[Static reader report](../build/status-expiry/routes.json) ·
[Status-expiry acceptance](../build/status-expiry/acceptance.json) ·
[Repaired-message gallery](../build/status-expiry/native/index.html) ·
[Status-expiry native report](../build/status-expiry/native/report.json) ·
[Previous-ROM failures](../build/status-expiry/negative-control/report.json)

## What the disassembly established

The direct modal renderer has **four Thumb call sites**, confirmed in Ghidra:

| Caller | Meaning | Binding |
| --- | --- | --- |
| 08016F28 | Trap or stairs refusal | Corrected private refusal table |
| 08016F56 | Item or Floor refusal | Corrected private refusal table |
| 08016FAA | Empty Floor | Corrected private table, slot030 |
| 08017224 | Empty inventory | Previously missed original table, slot034; now corrected |

The fourth caller was found by searching the executable call pattern, not by
waiting to encounter it in a playthrough. The new static check accounts for
all four direct calls and their six source-selector bindings. It rejects the
previous Floor-fix ROM because the empty-inventory binding is still original.
It also fails if an additional matching call appears without an explicit
disposition. Indirect-call completeness remains a separate question.

The old exploratory shared-text scripts kept broader machine-readable leads,
but their printed triage lists filtered to catalog entries marked untranslated.
That was the wrong filter for reader coverage: an English sentence may exist
while another caller still reads its original Japanese source. The new audit
retains shared-table literal uses regardless of catalog review status.

The scan finds623 candidate literal loads in the same bounded native
code interval as the earlier scripts:306 still use original values and317 have
changed literals. **These are not623 defects.** Some original pointers are
translated by queue hooks; some changed tables retain original entries for
other selectors. Instruction-shaped data, computed indices and indirect
references also need classification. Each candidate records its load, literal,
compiled value and patch owner instead of being silently marked complete.

## Seven repaired status expiry failures

The native turn handler has20 timer branches in the audited cohort. Its
common expiry loop formats selected text with the player name before queuing
it. Seven such formatted sentences bypassed the existing translation hooks:

| Expiring condition | Actor byte | Shared slot | Corrected output with the normal name |
| --- | --- | --- | --- |
| Confusion | +95 | 17C | Torneko's confusion ended. |
| Hallucination | +96 | 180 | Torneko stopped hallucinating. |
| Sleep | +97 | 184 | Torneko woke up. |
| Blindness | +98 | 188 | Torneko can see again. |
| Dancing | +9A | 3C0 | Torneko stopped dancing. |
| Fear | +9C | 3E0 | Torneko is no longer afraid. |
| Inability to recognize items | +AB | 8FC | Torneko can identify items again. |

`tools.status_expiry_text` changes the reader's table literal at ROM09748 to an
allocated private copy. Only these seven pointers change; the other647 entries
retain their original values. No status logic or shared original table is
rewritten. Five sources reuse reviewed wording; sleep and fear add two reviewed
sources, bringing the insertion count to3,772. Three existing payloads are reused
byte-for-byte; confusion and hallucination get conditional-break variants.

The disassembled getter also returns a monster name while transformed. The
maximum field is therefore114px /44 bytes (Crack-billed platypunk), compared
with98px /14 bytes for a seven-glyph saved name. The native output region is
256 bytes at SP+50; the next scratch starts at SP+150. The largest expanded
format is100 bytes. Conditional breaks keep complete messages within216px
without shrinking the font. All seven fit one line with the name Torneko.

Each probe restores the same fresh first-floor state, sets just the selected
timer to one at the ordinary turn-handler entry, and lets the native code
decrement it, choose the message and render it. It records the actual source,
selector, post-hook queue text, glyphs, screenshots and inputs. The source ROM
and save are unchanged. This proves those controlled expiry paths; it does
not claim ordinary acquisition of all the statuses.

Thirteen other timer branches display English through the existing static
notice translation. Transformation ends through a separate direct queue call;
its earlier scratch selector25C is cleared before the common expiry loop.
Two movement timers share one message and two speed timers share another, so
20 branches are not20 distinct sentences. These distinctions are retained in
the reports.

The new regression checks the entire observed text stream, not just registered
English pointers. For repaired formats it additionally checks exact expanded
bytes, the256-byte buffer guard, formatter/queue/handler registers and stack,
queue flags, every rendered glyph's bitmap/cursor, name preservation and timer
decrement. Saved Japanese name glyphs are permitted only as the exact name
prefix; the message following that name must be English.

The44 cases comprise20 individual timer branches,14 additional maximum-name
cases, seven transformed-name cases and three simultaneous-seven-expiry cases.
They pass49 exact repaired-message queues and1,358 exact glyph draws, with
1,609 total glyph draws observed without a resource filter. The same baseline
on the previous ROM produces13 passes and exactly seven Japanese failures,
with no route errors. Source ROM/save and each fixture's battery remain intact.
Ordinary acquisition of these statuses and other handlers remain separate.

## Validation and reproduction

The corrected menu passes14 automated scenarios and33 modal returns, with
8,513 observed glyph draws. Four scenarios follow ordinary routes; ten use
explicit controlled state. The previous ROM passes the original13 scenarios
but fails the added empty-inventory case. The ROM delta consists only of the
empty-inventory table literal and its entry in the existing private table;
all other ROM bytes and every allocation address are preserved.

The expiry build also passes the14-case Floor/menu regression and135 unit tests.
Its only changes relative to the preceding ROM are the four-byte table literal
and owned appended resources/padding. All previous allocation addresses and
payloads are preserved. A fresh build reproduces the tested ROM exactly, and
independent BPS application reproduces every ROM byte.

Current ROM:
`aa12a37b76e49d44f8a336642d334fa8324d92c2d98457200482742ea5b46723`.
Current BPS:
`e346e261be634346c94240d4990296894b392a9b6e9ae93242e5083b01ac3f76`.

```sh
.venv/bin/python -m tools.audit_reader_routes
.venv/bin/python -m tools.verify_floor_menu
.venv/bin/python -m tools.audit_status_expiry
```

All three checks run from `build.sh` and fail on findings by default. The expiry
audit makes its own fresh fixture; an optional fixture must match the ROM hash.
Use `--baseline-only --allow-findings` only to retain negative-control evidence.
The static gate checks all seven expiry bindings and the preserved sibling slots.

Disassembly:
`build/reader-audit/menu-siblings.txt`,
`build/reader-audit/status-expiry-owner.txt`,
`build/status-expiry/player-getter.txt`, and the preceding
`build/floor-menu/floor-conditions.txt`.
Ownership and source ranges are recorded in [Memory map](MEMORY_MAP.md).
