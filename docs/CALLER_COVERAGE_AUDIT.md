# Caller coverage audit and repairs

**The original 20 outstanding leads are now reproduced and fixed.** Following
those callers also found and fixed nine more failures: the Stone's murmur
acquisition, two link-progress warnings and six blacksmith item-name producers.
The copied identification refusal already reaches English through the queue;
a native control confirms it. Remi's suspected item-name load reads the Iron
safe price instead, and its offer is already English.

This page records the historical 3,785-resource repair milestone. Current build,
resolved later scan stages and outstanding investigations are in
[the coverage matrix](COVERAGE_AUDIT.md) and [October 3 follow-up](CALLER_FOLLOWUP.md).

Historical ROM: `81f8b1aa13f6d67d0d9d83ebe4abaef276887e30d46b60442bffe4082e5275d6`.
The root ROM/BPS have since advanced. This historical build contains 3,785 text resources and 20 English
graphics; the catalog contains 3,666 sources (3,527 reviewed, 111 unresolved,
28 retained/component entries). Catalog counts do not establish whole-game coverage.

[Continuation gallery](../build/caller-continuation/index.html) ·
[Acceptance receipt](../build/caller-continuation/receipt.json) ·
[110 native cases](../build/caller-continuation/release-acceptance/report.json) ·
[Exact reviewed bindings](../translations/remaining-callers-review.json)

The 29 repaired caller paths cover retry/erase prompts, the safe/Imp encounter,
late dungeon narration and family voices, shop greeting, locked doors,
strong-monster travel/overwrite prompts, result/history defaults, arrow and
disarmed-item notices, three link notices, and six blacksmith messages.
Original source loads and dynamic producers run inside their complete native
frames; source pointers/readers are not substituted. All 37 family-voice timing
commands retain their original order/callback. Saved-village names retain eight
cells; English surroundings pass with English/Japanese names, empty headers and
read failure. Native modal choices pass Yes/No/B, including the original retry/
erase confirmations that reject B. Result/history default0x32 is an explicit
controlled defensive selector, not a claim about ordinary reachability.

Private table copies preserve every previously translated sibling. Projectile
and blacksmith raw-name loads now use the existing English item-definition
copy. All 4,014 earlier allocations remain byte-identical; 21 allocations are
appended and 78 original-ROM bytes change inside 26 owned literal words. There is
no new RAM/save allocation or menu geometry change. Clean compilation reproduces
the ROM/BPS exactly, and independent BPS application reproduces the ROM.

Acceptance on this exact ROM:

- 110 continuation cases, with all visible glyphs, native bitmap draws,
  exact formatted bytes, output guards, register/stack preservation, pages,
  choices and timed callbacks checked. Formatter-only field extremes are
  explicitly distinguished from native producer/recipe/name profiles.
- 13 actual blacksmith exchanges from controlled entry/inventory: payment
  removal, enhancement, all ten tip selections and job-count cap pass. The
  transaction test now rejects Japanese output instead of merely comparing
  against whatever item string its formatter received.
- 308 earlier caller cases, 14 Floor/trap cases, 44 expiry cases and 17
  result/history sibling cases pass. `./validate.sh` passes 150 unit tests,
  toolchain checks and fresh-save acceptance.

The continued static scan inventories 1,294 direct call patterns to 15 readers/
forwarders in Thumb code[08000000,0805E000). It finds no remaining direct
Japanese-string binding among its resolved arguments. Its 529 unresolved
arguments are analysis limits (including RAM/computed sources and patched
entries), not 529 confirmed defects or 529 translated paths. The 87 unclassified
resolved arguments were inspected: they are existing English allocations,
formatting/control templates, RAM inputs or an invalid-zero provisional path;
none identifies another untranslated ROM sentence. Copied notices have their
separate downstream queue evidence. This does not prove whole-game reachability
or cover unknown readers and graphics.

The complementary [item-definition audit](../build/caller-continuation/item-definition-callers.json)
accounts for all 80 direct literal loads into the original definition table in
that code interval: 27 use owned English tables, 53 read numeric record fields.
No interior-table literal adds another name path. Field offsets and pinned
instruction contexts are retained in
[the consumer inventory](../config/item-definition-consumers.json). The skill
footer's existing 48-record subset is checked separately from 221-record copies.

`build.sh` now runs both the110-case continuation gate and the definition
consumer audit. Story progression, actual save deletion/cable transfer and
natural late-game routes are outside these controlled probes.

```bash
.venv/bin/python -m tools.audit_remaining_callers --source build/english --extended
.venv/bin/python -m tools.audit_item_definition_callers --source build/english
.venv/bin/python -m tools.verify_blacksmith_transactions --source build/english
.venv/bin/python -m tools.audit_text_callers --source build/english --expand-local-seeds --include-wrappers --include-forwarders --output build/caller-continuation/current-static.json
```

## Earlier 55-binding repair (frozen c19475ee evidence)

**All 54 confirmed untranslated caller sites are fixed.** Whole-screen acceptance
also exposed the original wide question-mark item placeholder while recognition
is blocked; that caller now uses the compact English question marks. This adds
one binding, for **55 repaired caller bindings** and 35 resource variants.

Earlier ROM: `c19475eee8cd5c77601a634654b036301d779a59b3bb0adf7cc092b585fc4b7a`. Its original evidence is retained.
[Repair gallery](../build/caller-repair/index.html) ·
[Acceptance receipt and remaining candidates](../build/caller-repair/receipt.json) ·
[Native checks](../build/caller-repair/acceptance/report.json) ·
[Reviewed sources and exact bindings](../translations/caller-repairs-review.json)

The repair redirects 53 owned literals through 37 private table copies or the
separate Take label. Each copy changes only the slots for its confirmed callers.
The pot-spill literal inherits its existing English table, preserving the other
pot-result messages. The original shared table, source strings, gameplay code,
window geometry and all 3,965 previously allocated resources remain unchanged.
Actor messages now account for generic monster names as well as player names.
Conditional wrapping keeps the complete message on one line when it fits.

Acceptance passes **308 native cases**: 77 scenarios with their native fields,
then maximum-width, maximum-byte and colour/zero-number profiles. Those three
profiles explicitly substitute formatter fields in existing scratch memory;
they do not replace a source pointer or text reader and are rendering checks,
not naturally occurring names or gameplay values. Every repaired binding is
reached in every profile. Exact formatter/copy bytes, output guards, ABI and
all observed glyphs pass. Some handler messages clear within the same frame;
glyph traces establish their output, not a blank final screenshot.

Which?, blocked Info and marked-pot Take pass repeated cancellation/reopening.
The Take action also transfers both marked contents. The eight previously
confirmed button routes display English, including **Found a trap!** when an
adjacent hidden trap is revealed. Standing on a trap and selecting Floor remains
a separate passing route. The saved-name/current-name handling and previous
Floor/expiry fixes also pass: 14 Floor cases, 44 expiry cases and four existing
pot-explosion sibling cases. `./validate.sh` passes 147 unit tests plus toolchain
and fresh-save acceptance. A clean rebuild reproduces both ROM and BPS exactly;
independent patch application matches the ROM.

`tools.verify_caller_repairs` is now a failing regression gate in `build.sh`.
It checks all 55 bindings and refuses incomplete or non-English output.
`tools.accept_caller_repairs` joins this evidence to the frozen 54-failure audit.
The old discovery reports below retain their original ROM/tool hashes; they are
historical evidence, not acceptance reports for the repaired ROM.

**At that earlier checkpoint**, the expanded scan retained20 unconfirmed
Japanese-argument candidates, one unresolved copied-source lead and 412 calls
whose arguments it cannot resolve. The two incomplete projectile/landing probes
are explicitly excluded from the repair gate; they are not English passes.
The source catalog now contains 3,655 sources: 3,516 reviewed, 111 unresolved
and 28 retained/component entries. The build contains 3,774 inserted resources
and 20 English graphics. None of these counts establishes whole-game completion.

Reproduce the repair checks:

```bash
.venv/bin/python -m tools.verify_caller_repairs --source build/english
.venv/bin/python -m tools.audit_text_callers --source build/english --expand-local-seeds --include-wrappers --output build/caller-repair/static.json
```

## Frozen failure audit before repair

The continued October 2 audit confirms **54 untranslated caller sites** on the
pre-repair ROM, **31 more than the first pass**. They select 34 distinct source
addresses with English wording already reviewed elsewhere. **These findings are now repaired as described above.** This is a lower bound, not a complete remaining-defect count.

The earlier quoted status-expiry finding remains fixed: it was fear/dancing
recovery at queue return `080096F9`, covered by the seven-message repair.

Audited ROM: `aa12a37b76e49d44f8a336642d334fa8324d92c2d98457200482742ea5b46723`.
The following discovery record describes the old ROM; its evidence remains frozen.
The first pass stopped without an external blocker; its completion did not
close the outstanding discovery work.

[Visible failures](../build/caller-audit/index.html) ·
[Individual callers and downstream evidence](../build/caller-audit/summary.json) ·
[Continued native probes](../build/caller-audit/followup/report.json) ·
[Expanded static inventory](../build/caller-audit/static-wrappers.json)

## Failures reached through normal buttons

These eight scenarios use the fresh first-floor fixture. Inventory, status or
trap placement is controlled and recorded; the subsequent actions use normal
buttons. They do not substitute a program counter, source pointer or text
reader, and do not establish natural acquisition of the test items.

| Trigger | Japanese output | Caller |
| --- | --- | --- |
| Read a Peep scroll | Target-selection heading, “Which?” | `0801768A` |
| Item Info while recognition is blocked | Refusal body | `08017A9C` |
| Eat Giant bread | Maximum-fullness increase | `080332AE` |
| Eat Putrid bread | Strength loss | `080334B8` |
| Drink Seed of str. | Strength increase | `08033A5C` |
| View a Storage pot, mark two contents with R, then press A | The separate Take menu | `08018002` |
| Select Use on a currently invisible H. Pocus scroll | “This item is invisible!” | `080258CA` |
| Face an undiscovered adjacent trap and press A | “Found a trap!” | `080241FA` |

The last three are new normal-button confirmations. Their final panels were
visually inspected. Storage-pot selection exposes a literal outside the catalog's
pointer list: source `[0806B5B0,0806B5B5)`, selected through literal `08018024`.
It contains the same Japanese wording as the reviewed Take action at `08064940`.
The ordinary action-table translation does not bind this separate reader.
Earlier container tests controlled the bulk selector and validated transfer
messages; that did not cover the marked-item action panel.

Trap discovery is distinct from standing on a visible trap and selecting Floor.
The existing Floor-menu Step/Stay tests pass; revealing an adjacent trap reaches
the unbound choice-modal wrapper at `080241FA` and displays Japanese.

## What happened to the original 34 candidates

| Disposition | Count | Evidence |
| --- | ---: | --- |
| Newly confirmed Japanese callers | 28 | Native execution, with the selected source linked through actual buffers to Japanese glyphs |
| Excluded impossible selector | 1 | Options help at `0801A9B0`; its four eight-entry rows never select the cursed notice |
| Still unresolved | 5 | Listed below; no English pass inferred |

The 28 confirmations include resisted Putrid/Rotten bread effects, partial
strength recovery, item-based blindness recovery, resisted sleep, room paralysis,
nearby healing, successful and failed summons, Rotten bread random effects,
Kaclang refusal, strength-halving attacks, H. Pocus level loss, full Thief pot,
stuck floor items, reflected staff hits, and failed landing/spill/scatter cases.

The five original leads still open are:

- `0801CD00` and `080570F0`: result/history fallback “nothing happened.” Ghidra
  shows a default selector before reason-specific overrides. Its ordinary
  reachability still needs to be established; a static path alone is insufficient.
- `0802AF54`: the monster projectile's Silver-arrow hit branch. The first-floor
  monster-definition snapshot has no species selecting item 80; other definition
  states and incoming routes have not been excluded.
- `0802B0FC` and `0802CD7E`: monster-projectile and disarmed-item landing notices.
  Follow-up runs returned but did not reach these expected callers. They remain
  incomplete probes, not confirmed failures or English controls. Their inputs,
  state changes and branch observations are retained.

The other three additions to the original 23 are the marked Storage-pot menu,
trap discovery, and the direct golden-item floor-empty modal at `08036C22`.
Together: 23 + 28 + 3 = 54 confirmed caller sites.

## Expanded discovery beyond the first six consumers

The scanner now follows known CMP outcomes, invalidates flags after unmodeled
flag-writing operations/calls, evaluates additional constant ALU operations,
tries bounded local seeds for unresolved calls, and decodes Japanese arguments
outside the catalog's pointer list. Matching source bytes can identify a reviewed
alias, but are never treated as proof that the caller uses English.

Ghidra establishes three additional modal wrappers/readers and a native string
copy routine. Their call patterns are now included:

| Consumer | Direct call patterns |
| --- | ---: |
| Formatter `08000FB8` | 420 |
| Player wrapper `08015848` | 58 |
| Queue `0801588C` | 409 |
| Floor modal `08017068` | 4 |
| Window reader `08002298` | 133 |
| Text reader `080021B4` | 1 |
| Choice-modal wrapper `08015A18` | 78 |
| Positioned-modal wrapper `08015A34` | 27 |
| Modal reader `08015A50` | 4 |
| String copy `0805CF54` | 37 |
| Total | 1,171 |

There are 759 call sites with candidate arguments and **412 unresolved argument
sites**. On the original six-consumer scope, local seeds reduce unresolved sites
from 375 to 362; adding the four consumers adds another 50. The larger 412 is an
expanded inventory, not a count of new failures.

The expanded scan retains 74 Japanese-argument candidates: 54 are confirmed,
**20 remain unconfirmed**. Beyond the five older leads above, the remaining
leads cover retry/erase prompts, a bank-safe notice, story/voice sequences, a
shop greeting, a locked-door notice, travel warnings and link-trade success.
Some point to previously uncatalogued sources. Exact sources, call sites and
review status are in the machine-readable summary; these are not promoted to
confirmed bugs merely because their source bytes are Japanese.

The link success format at `0805866E`, source `0806ED58`, is a concrete insertion
omission lead: the existing link family owns prompts/errors but excludes the
transfer-success path. The disassembled success block formats this source and
passes its result to `08057BDC`. No two-device transfer or success-block runtime
probe has been performed; it remains static evidence.

Four additional Japanese string-copy sources require downstream analysis.
Three level-one “nothing happened” controls (`08033410`, `08033864`, `08035AFC`)
pass in English after the queue's existing remapping. They are **not failures**.
The fourth, identification refusal at `08033B9C`, remains unconfirmed.

## Native evidence and limits

The two native reports contain 79 scenarios: 73 with confirmed Japanese output,
four English controls, and two incomplete routes. These are scenario counts,
not 73 separate bugs. The 54-site count requires a matching caller/argument and
Japanese glyphs associated with its native destination buffer or direct reader.
The join also follows observed copies inside the player wrapper; unrelated
Japanese elsewhere in the same scenario is insufficient evidence.

Other than the eight normal-button cases, probes invoke disassembled native
handlers with recorded arguments and state. Seven random-effect scenarios select
an allowed result after the native RNG runs. Capacity cases occupy the existing
128-slot floor-item pool; summon failures block neighboring tiles. Stack
arguments are restored at the handler return. These are controlled branches,
not naturally encountered combat, full gameplay outcomes or evidence authorizing
new RAM ownership. Source pointers and text consumers are never substituted.
Completed handlers preserve saved registers/SP, and every probe preserves its
fixture battery and the supplied source ROM/save. Some handler-only messages
draw and clear within a frame; their glyph traces, rather than blank final
screenshots, establish the output.

The static scan remains bounded to Thumb `[08000000,0805E000)`. A full-ROM search
finds no extra direct BL patterns to these ten targets outside that interval;
that does not exclude indirect calls, ARM code, additional readers or graphics.
There are 794 budget-limited seed traversals, plus computed selectors, unknown
RAM values and patched-code boundaries. Candidates can include incompatible
branches and instruction-shaped data. These remain explicit discovery gaps.

The original nearest-PUSH heuristic mistook literal `08017648` for a prologue;
Ghidra ownership and the normal Peep-scroll route corrected it to `080175B4`.
The refined comparator also removes the impossible Options-help cursed notice.
Neither a disassembler nor a passing source inventory supplies whole-game
coverage by itself.

Seven focused tracer tests pass, including relocated tables, unknown RAM loads,
changed instructions, call clobbers, impossible branches, stale flags and signed
comparison overflow. The same scanner still rejects the old empty-Floor and
empty-inventory bindings and recognizes their corrected current bindings.
Four output-correlation tests also pass: matching destinations, unrelated glyph
rejection, player-wrapper forwarding and incomplete-route exclusion.

## Historical evidence and remaining discovery

The old reports use the pre-repair ROM `aa12a37b…`, preserved with its ledger
and BPS in `build/caller-repair/pre-fix/`. Their fixture was generated from that
ROM. The frozen summary and reports retain their original tool hashes; current
repair tools have subsequently gained exact binding/format checks and corrected
recognition of blank menu markers. Do not overwrite the failure-evidence folder
with a current-ROM run. The current commands are at the top of this document.

That checkpoint's20 direct/format/modal candidates and copied refusal are now
resolved by the continuation at the top of this document. The old412 unresolved
arguments belong to the earlier ten-reader scan; the expanded15-reader analysis
retains529 unresolved arguments as explicit static limits. Diagnostic scan
success is separate from caller binding, fit and complete-screen acceptance.
