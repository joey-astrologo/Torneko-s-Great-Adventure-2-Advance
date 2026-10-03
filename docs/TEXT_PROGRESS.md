# Autonomous text-localization progress

**Whole-game completion: unknown.** The 97.3% figure below measures review of
identified catalog sources only. It does not measure the fraction of gameplay
that displays English. The missed location banner demonstrated an additional
class of gaps: untranslated readers of already-reviewed sources. The 97-source
backlog is therefore not a complete estimate of remaining work. Existing test
counts must not be used as evidence that complete screens were audited.
See [the coverage assessment and independent audit requirements](COVERAGE_AUDIT.md).

All player-facing text is authorized for continued work without batch approvals.
The Torneko 3-derived rules in `LOCALIZATION_PLAN.md` apply, with Torneko 2's
Japanese as the source and measured T2 font/window budgets mandatory. Graphics
editing and auditions were initially deferred until text completion. On
2026-09-29 the user reopened ending-credit discovery and credits/arrival-card
auditions. On 2026-09-30 the user also requested the
[title-screen audition](TITLE_AUDITION.md), then approved insertion of the main
title and all five corner logos. These are now
[inserted and natively verified](TITLE_INSERTION.md). The five backgrounds use
floating lettering with no wood backing; all pixels outside their corner
rectangles remain exact. See
[the graphics studios and evidence](GRAPHICS_AUDITION.md). The GBA credits are
already English (67 raster lines); this discovery does not add 67 translated
dialogue sources or change the text/insertion percentages below.
On 2026-09-30 the user approved keeping that original credit artwork unchanged.
The user then approved [insertion of the Shiren arrival cards](ARRIVAL_INSERTION.md).
All 13 names plus Level are inserted and pass 30 native renderer cases, including
the widened Ordeal Mansion. The first entry continues through the English
tutorial and ordinary movement; other selectors use documented controlled probes.

## Accepted milestone and current candidate

The [October 2 continuation](LOCALIZATION_CLOSURE.md) inserts the custom-name
category family, deepens RAM/stack caller analysis, repairs the two referenced
event stubs with explicit user approval, and extends ordinary quest/service evidence.

The latest accepted milestone has **3,768 inserted resources**, ROM
`a7a05791570d2ced3b6182cc9705e7071f772afc721f71199bd582a4bd1adf28`.
Its ROM, BPS, ledger and receipts are preserved in `build/accepted/3768/`.
Full cumulative regression, 2,006 item cases, 135 unit tests, 314 WebKit contexts /
3,428 measurements, clean rebuild and independent BPS application pass. Logs:
`build/services/complete-build-3768.log`, `font-browser-3768.log`,
`unit-3768.log`, `accept-3768.log` and `repro-3768.json`.
Earlier accepted milestones remain archived separately.

The current development candidate has **3,813 inserted text resources plus
20 English graphics** (14 arrival graphics, the title and five backgrounds),
exported to `build/torneko-2-english.gba` and `build/torneko-2-english.bps`.
Its ROM hash is
`f47b6df310211585406c921d8070e1824a8e1cf76a324cd72c8b8669ad6ef865`.
The two approved [event repairs](EVENT_STUB_AUDIT.md) pass eight native branch
cases and all 1,046 event getters. Existing resources differ only by pointer
relocation; the repair adds no script, geometry or RAM/save changes.
Current custom-name, caller, event and gameplay evidence is consolidated in
[LOCALIZATION_CLOSURE.md](LOCALIZATION_CLOSURE.md). The earlier repair milestones
below retain their original unit counts and byte-delta receipts.
The [reader-path audit](READER_PATH_AUDIT.md) now accounts for all four direct
callers of the Floor/status modal. It found the empty-inventory caller missed
by the preceding fix and binds it to “You have no items.” The extended14-case
native check passes and rejects the preceding ROM's empty-inventory case.
The seven Japanese expiry messages found by20 automated timer probes are also
fixed. A private table binds the computed reader to English while preserving
the other647 selectors and native timer logic. Five sources reuse reviewed
wording; sleep and fear add two newly reviewed/inserted sources. All44 native
cases pass:20 timer branches,14 maximum saved-name cases, seven transformed-name
cases and three simultaneous-expiry cases. Exact formats,256-byte guards,
registers/stack and glyph bitmaps pass; the old ROM reproduces exactly seven
Japanese baseline failures. The14-case menu regression and 135 unit tests pass;
the tested and exported ROMs are byte-identical and BPS application is verified.
Static bindings and the native expiry gate now run from `build.sh`. No whole-game
failure count is yet available. Evidence: `build/status-expiry/acceptance.json`.

The continued [caller audit](CALLER_COVERAGE_AUDIT.md) found 54 untranslated
caller sites, all now repaired, plus a compact-font correction for the
recognition-blocked item placeholder. **55 exact bindings pass 308 native
cases**, with whole-screen glyph checks, exact formats/copies, buffer guards,
ABI, maximum field widths/bytes and colours. Normal-button Which?, blocked
Info and marked-pot Take each pass three opens; Take transfers both contents.
The earlier 14 Floor and 44 expiry cases and four pot-explosion sibling cases
pass on the same ROM. All prior allocations are byte-identical, only the 53
owned original literals change, and clean ROM/BPS reproduction passes.
`./validate.sh` passes 147 unit tests plus toolchain/fresh-save acceptance.
The caller regression now runs from `build.sh`. Evidence:
`build/caller-repair/receipt.json` and `acceptance/report.json`.

The continuation reproduced and fixed all 20 outstanding Japanese-argument leads,
then nine additional caller failures: Stone's murmur acquisition, two link
warnings and six blacksmith item-name producers. The copied refusal and Remi's
numeric Iron-safe price load are confirmed English controls. All 110 continuation
cases, 13 complete blacksmith exchanges,308 earlier caller cases, 14 Floor cases,
44 expiry cases and 17 result/history sibling cases passed on that 3,785-resource ROM.
`./validate.sh` passes 150 unit tests plus toolchain/fresh-save checks. All 4,014
prior allocations remain exact;78 original-ROM bytes change inside 26 owned
literal words. Clean ROM/BPS reproduction passes. Evidence:
`build/caller-continuation/receipt.json` and `index.html`.

The initial 15-consumer scan covers 1,294 direct call patterns and finds no remaining
resolved direct Japanese-string binding. Its 529 unresolved arguments were
static-analysis limits, not confirmed untranslated paths. The new RAM/stack
and storage-dispatch passes bind 115 of those calls to English resources,
identify 307 producer candidates, follow five buffer producers manually, and
leave 102 unknown data-flow calls explicit. The computed-reader follow-up then found and fixed the final wind warning and
nine separate town-overview labels. All80 direct item-
definition loads in the bounded code region are accounted for: 27 owned English
table loads and 53 numeric-only loads. The catalog now has 3,676 sources: 3,551
reviewed (including two approved editorial reconstructions), 97 unresolved and
28 retained/component entries. Source review and
insertion counts still do not measure whole-game English coverage.

On the preceding `dd21b782…` build,
the [Floor-menu correction](FLOOR_MENU.md) resolves another user-reported
first-floor Japanese reader: the empty-Floor notice and related status refusals
bypassed the already-translated queue path. Thirteen complete menu scenarios
pass (three ordinary routes, ten controlled cases), with repeated reopening,
unfiltered glyph checks, original geometry and parent restoration. The same
audit rejects the old ROM's ten modal cases for Japanese output. Thirty-nine
root-menu cases, six Step/Stairs choice cases and 135 unit tests also pass.
The root ROM/BPS pair is updated and independently patch-verified. Existing
allocations and unrelated bytes remain identical; this fixes readers of
already-reviewed sources and does not increase the insertion count or establish
whole-game completion. `build.sh` now includes this menu-state audit.

On the preceding ROM
`c93c573ae1d0d4c643a580c04c8b385bd3d1b5381913763aca2abab078c22ea4`,
the [independent dungeon/town audit](DUNGEON_SCREEN_AUDIT.md) passed 11 bounded
scenarios, including all 14 natural tutorial pickups on three floors, earned
gold/arrow pickups, item use, bank and storage round trips. Two capacity/amount
cases are explicitly controlled. It fixes `321Gold` to `321 Gold` through one
private formatter literal; every previous allocation and unrelated ROM byte
remains identical. The previous banner-fix ROM
`7716f8c51c452499a1bb651acd24ccd20d3833531188fa66f0732cf3bb8307c8`
is archived in `build/coverage-audit/pre-fix/`. Native glyph/window checks,
22 item cases, five walking-pickup cases and 135 unit tests pass; historical
negative controls reject the missing separator and Japanese banner. This is
bounded evidence for that recorded build, not full cumulative or whole-game acceptance.

The [dungeon-menu banner correction](LOCATION_BANNER.md) fixes a user-reported
missed reader: all 13 names in that field were still Japanese. The new whole-menu
checks pass 39 cases / 117 openings and reject the old build. One pointer changes;
all allocations and other ROM bytes remain identical. Counts and review
percentages do not increase because these names were already reviewed/inserted
for other readers. The pre-fix ROM is in `build/location-banner/pre-fix/`.

The preceding title-insertion ROM
`bd61d3f6f2db7af8119ecc6ee757f7560808d55ddec192c670368523a2708ab3`
retains its original native reports. The title delta preserves every previous text/arrival allocation and patch,
original credits and unrelated ROM bytes. All 36 title/menu snapshots, 640
controlled colour probes, 30 arrival cases, both opening branches, name entry
and save/cold-load checks, 135 unit tests and clean ROM/BPS reproduction pass.
[Title insertion evidence and limits](TITLE_INSERTION.md) ·
[arrival evidence](ARRIVAL_INSERTION.md).

The preceding arrival-only graphics build
`c6cf871bcb20060b91ca226d203bdf78713d89aa8cb1643170286e0b011f96c5`
is archived in `build/title-insertion/pre-insertion/`; historical reports
retain their original build identity.

The preceding text-only 3,770 ROM
`838f42fa1a126ebff1959a1f4a0f618859aa377101c87581617d82148beada70`
is archived under `build/arrival-cards/pre-insertion/`.
Its two text additions cover the floor-Remove fragment and a monster identity format.
The latter is formatted but discarded by its original owner; no new on-screen
message is claimed. On that text-only ROM, two ground-Remove cases, 145 identity
cases, 44 existing item-action cases, 40 discovery cases and five walking-pickup
cases pass, along with 135 unit tests and clean ROM/BPS reproduction. The byte
delta against accepted 3,768 is limited to two owned literals and four appended
allocations; all previous allocations and other ROM bytes remain identical.
Evidence: `build/services/delta-3770.json`, `repro-3770.json` and the matching
family/unit logs. Full cumulative acceptance remains at 3,768; its reports retain
their original ROM hash. The release manifest marks the root build as development
because discovery and full-game playtesting remain incomplete.

The ten additions accepted at 3,768 cover nine older town/dungeon destination
labels and one guard form refusal. All 67 travel-list and ten refusal cases pass,
along with first-dungeon/castle/destination checks, both opening branches and the
fresh three-floor tutorial pickup audit.

The 51 additions accepted at 3,758 cover nine carpenter repair passages, 40 house-fire
scene passages and two dungeon-entry/saved-village overwrite prompts. Accepted 3,768
also passes a fresh-game, ordinary-input tutorial pickup regression: three floors
and 14 pickups, with no Japanese text glyph leads. These checks do not establish
complete game discovery or natural access to every translated branch.

The current inventory accounts for 3,676 unique sources: 3,551 reviewed,
97 unresolved (catalog status `untranslated`) and 28 retained/component sources.
The earlier **96.1%** figure divides reviewed English by every catalog source.
Its remaining3.9% included accounted-for sources that do not need another English
translation. The current breakdown is 21 nonlinguistic entries, four sources replaced by English UI
components, and three deliberately retained Japanese sources (the optional kana
input pages and an internal appearance-table sentinel).

Excluding those 28 accounted-for sources, **3,551 of 3,648 sources (97.3%) have
reviewed English; 97 (2.7%) remain unresolved**. Reviewed includes two approved
editorial reconstructions. This is a review metric for the
known catalog, not whole-game completion or proof that every reader displays
English. Some unresolved sources already have English drafts but still need
reader, context or layout verification. Neither percentage measures engineering
time remaining. The ten sources added at 3,768 were newly identified. A separate
byte/consumer audit classified the eight empty name-cell IDs as nonlinguistic
data; no Japanese text was removed.
Remaining work includes 34 single-character event stubs,
legacy system strings and shared-reader audits. The reviewed-source percentage
does not count these investigation gaps as complete.

The 97 unresolved sources currently divide as follows:

| Sources | Family | Remaining work |
|---:|---|---|
| 34 | Single-character event placeholders | Three appear only after END; 31 lack a reference in the extracted roots. The two referenced records have approved, inserted repairs; ordinary access remains unproven. |
| 53 | Shared system/combat/old menu strings | Trace remaining readers, including memory-card-era text and duplicate formats. |
| 10 | Town/service table sources | Establish active readers and their actual formatting/layout requirements. |

The [native screenshot gallery](../build/text-decisions/index.html) and
[investigation notes](TEXT_OPEN_QUESTIONS.md) explain these cases. The user has
confirmed that **item names cannot take more than one line**. The earlier request
to choose “Sa/Na” versus an ellipsis was premature; subsequent caller investigation
supported the two contextual repairs now approved and inserted. The custom-name category
labels and both formats are now inserted; 30 native English-name cases pass
in inventory and storage, including prices, counts, markers and reopening.
See [the current continuation](LOCALIZATION_CLOSURE.md).
Earlier Japanese-name layout blockers in the historical entries below are
superseded by the October 2 scope clarification in `TEXT_OPEN_QUESTIONS.md`.

This is a source count, not a percentage of engineering time remaining. Retained
internal data, reviewed English, native insertion and natural gameplay coverage
must remain separate.

The floor-Remove fragment passed two native queue/action checks and all 44
existing Equip/Remove/Drop regressions in `build/ground-remove-prototype/` before
integration. New source audits map all 133 ordinary event-script roots and the
seven NPC resource banks. Six historical controlled native checks confirm that
the two single-character placeholders render through their selected branches;
their replacements now pass eight English branch cases. Ordinary reachability
remains unproven. The audit also records two
mismatched original help-menu bank/configuration combinations. Natural access
and their proper explanations remain unresolved. Appearance alias154 is proven
to be an assignment sentinel, with three native initializer checks; that
internal record is now explicitly retained as metadata, adding no insertion.
These investigations do not establish whole-game completion or increase the accepted insertion count.

The 95 additions accepted at 3,707 cover 75 further tutorial resources,
11 link-trade resources, eight pickup tutorial tips and an ending save notice.
The five original inconsistent tutorial selection mappings remain explicit
investigation gaps; their displayed text is translated and mapping behavior
preserved. Both occurrences of Seal staff in the bank6 dialogue now use Sealing
staff. A natural fresh tutorial run on that ROM completed all three floors,
14 pickups and 14 English tips, with no Japanese glyph leads; full-game and
arrival-artwork coverage remain separate.

The98 additions accepted at3,612 cover dungeon-entry restrictions(4), timed
ending dialogue(57), dungeon destination labels/heading(8), and the first29
soldier/adventurer tutorial resources. Older staged notes below are prototype
history unless explicitly marked as an unresolved investigation.

The 71 additions accepted at 3,514 cover legacy record/travel prompts (8),
fused-equipment Info descriptions (41), dungeon cutscene prose (21) and the
empty-inventory Read refusal (1).

The 152 additions accepted at3,443 cover English inscription inputs, fused-ability
loss messages, talk refusals, Step/Stairs choices and pot-content labels. Eight
additional compact numeric aliases cover16–20 and(1)–(3), without increasing
the text resource count. All prototype/staged notes below are historical unless
explicitly called out as unresolved; the four families listed above are now
included in the root development build.

The 113 resources added between3,144 and3,257 cover dungeon effects/status/fullness, spell
messages and spellbook rows, discovery/transformation, staff draining/waving,
pulling, inscribed-scroll names, writing results, item loss/pot results, and
player recovery/no-staff notices. Evidence is bound to each tested ROM; earlier
reports are not relabelled as current evidence.

The following independently tested prototypes were integrated at3,291;
current galleries are under `build/english/` with the matching family names:
`build/dungeon-shop-prototype/` adds five resources for three price/half-price
confirmations and thank-you/insufficient-funds panels. All 16 rendering cases
pass with original Yes/No geometry, numeric colours and maximum decimal values.
Actual commerce outcomes and the separate dropped-item offer remain open.
`build/save-notices-prototype/` adds damaged-save and improper-suspension
notices; both native modal checks pass. The latter retains all consequences
and the original two-row window, with a native page wait between its four
lines. Save validation/reset outcomes are excluded from these render probes.
The reference-list prototype also passes nine cases across all27 scroll,100
skill and50 spell names, eligible/locked states, every page, cursor wrapping,
refusal and repeated reopening. Original windows and8px gaps are preserved.
Gallery: `build/reference-lists-prototype/reference-lists-validation/index.html`.
The save-preview prototype passes56 cases, including real town/dungeon
Continue, every destination/town/completion selector and maximum stored names
and positive signed16-bit numeric fields. The existing bottom-left castle
graphic has a20px text reserve; window/artwork are unchanged. Two full native
priest-expiry calls also pass with actual timer/actor-flag outcomes. Galleries:
`build/save-preview-prototype/save-preview-validation/index.html` and
`build/priest-warning-prototype/priest-warning-validation/index.html`.
The separate town Items/Option root passes four native menu cases. Its
32px window becomes40px to supply the required34px label region; it closes
before either child opens. Native selection, empty/populated inventory,
Option, cancellation and repeated reopening pass. Gallery:
`build/town-root-prototype/town-root-validation/index.html`.
A staged accounting audit identifies23 numeric/control, keyboard and already
localized component sources; it makes no unused-code claims and does not count
these as new ROM insertions. The unresolved single-character stubs remain open.
All34 new resources are included in the root build. Their source dispositions
are accounted separately and add no insertion count.

On 3,257, 37 battle-result render cases pass: damage absorption, Cop Out,
and both area-effect/spell readers for kill totals, total EXP and reached level.
Tests include zero and maximum nonnegative decimal substitutions, longest names
and visible pixels. The 88 dungeon-leaf and 12 strengthening cases also pass
after the numeric verifier extension. These message-block checks do not claim
the underlying combat outcomes.
Gallery: `build/english/battle-results-validation/index.html`.

On 3,251, all 512 skill-name attack/finisher cases and 384 skill-acquisition
selector/player-name cases pass. The latter include native learned-flag changes
and the sword/shield follow-up explanations selected by all128 original definitions.
The retained bare-hand explanation is not selected by this native table; its
bit is always overridden by a nonzero shield mask. Battle cries fit
one line; the acquisition popup retains its original two-row layout.
Galleries: `build/english/skill-shouts-validation/index.html` and
`build/english/skill-learning-validation/index.html`.

On 3,245, all 88 dungeon-leaf cases pass, including three Kerplunk callers
and the grabbed/unable-to-move message. Combat outcomes are explicitly outside
the controlled message-block checks.

On 3,243, both player strengthening messages pass 12 native effect checks,
including all three player-name cases and ordinary/capped item and stat states.
The complete 258-case player-wrapper routing/rendering cohort passes.
Gallery: `build/english/strengthening-validation/index.html`.

On 3,241, 32 item-loss/pot field cases andsix player-name notice cases pass,
along with112 unit tests. Complete loss/breakage/explosion messages fit one line
with maximum item names. Skill-item removal and player recovery/refusal changes
execute natively; the other loss/pot cases explicitly exercise their original
message blocks and frames while excluding gameplay conditions/outcomes.

On3,236, all102 writing target/refusal cases and the earlier72 dungeon-leaf,
56 status,40 discovery,eight monster-interaction andeight staff-use cases pass.
Writing checks include actual item identity, inscription flags and spell-ID
changes, preserving the distinction between a used scroll and an ever-learned
spell. Ordinary text-input matching remains separate. Identification retains
complete old/new names and the surprise cue, with ordinary examples on one line.

On3,230,77 inscribed-scroll rows,125 spellbook rows, mansion/main menus,
17 priest-service branches and142 WebKit contexts /1,502 measurements pass.
Explicit labels such as `Blank: Sheen` replace the unsafe Japanese six-byte
suffix truncation. The maximum scroll base is101px in the110px name region;
the conservative complete row bound is63/64bytes. Spellbooks use `Sp.` with
complete spell names (maximum97px). Original windows and continuous inverse
price backgrounds are preserved. Custom names and ordinary writing eligibility
remain separate. Galleries: `build/english/scroll-item-validation/index.html`
and `build/english/writing-validation/index.html`; check each report's ROM hash.

Earlier3,180 checks cover384 cast/learn/forget cases, including HP gates/payment
and actual learned/history flag changes. Individual spell targeting/effects
remain separate. The3,173 targeted cohort also covers25 bonus effects,
12 fullness changes,246 common player-wrapper cases andfive walking pickups.
These results do not replace cumulative regression of the latest candidate.

The accepted 3,144 milestone added five theft/wait formats, 266 skill Info
bindings and 19 skill-menu bindings. Native checks pass 25 theft, 131 Info,
four full list/navigation, seven equipment-preview, one actual Set/cancel and
three retained-action render-only cases. Those retained actions are never
executed; the ordinary warrior action builder emits Set/disabled Set plus Info,
or Info alone when already assigned. Original menu geometry and 8px border
gaps are preserved.

The September26 report of Japanese pickup/dungeon messages remains actionable.
Five additional walking cases passed on the accepted build: native item,
gold, arrow merging, full inventory and the controlled standing flag. The
native item case uses ordinary Drop and directional buttons without memory or
register overrides. These routes do not establish completion of other actions.
Gallery: `build/english/walking-pickup-validation/index.html` (regenerated for
current development builds; check the matching report hash).

The accepted2,670 milestone added25 priest resources, five Throw formats,
24 species-selected monster announcements and six baker companion passages.
Tests include35 priest text and 17 service cases,20 Throw field/colour cases,
all45 monster selectors plus72 field-bound cases, and six companion selectors.
Native encounters, projectile collision outcomes and companion progression
remain distinct from these controlled checks.

The accepted2,854 milestone added184 resources:30 bindings for15 special/reserved item
definitions, seven Controls-help bindings, three recovery/warp formats, seven
wounded-soldier passages,132 spell Info resources and five spell-menu resources.
Isolated tests passed19 recovery, four Controls-mode, nine soldier,64 spell Info
and nine spell-menu cases before integration. Spell menus cover all50 eligible
names in affordable/unaffordable states, page/cursor wrapping, Info, actual
Set/Unset toggles and close/reopen behavior. Original geometry is preserved.
All61 spell records have independently translated descriptions and original
native HP costs/targets. Spell acquisition/casting outcomes remain separate.
The display qualifier "Room Kacrack" distinguishes ヒャダイン from マヒャド;
both retain canonical Kacrack in the glossary. User preference remains pending.

Item153 uses a spell ID in its amount byte and opens spell Info. Forcing it
unidentified produces alias999, outside the original155-record appearance
table; that invalid synthetic state is explicitly excluded. All other required
row states and every spell Info selector remain tested. Special/reserved
records are not being declared unused or ordinarily obtainable.

Unique reviewed sources are **3,500/3,644 (96.0% language review)**, with117
untranslated and27 explicitly retained/component dispositions. These consist
of21 nonlinguistic streams, four replaced components and two optional Japanese
keyboard pages; none is being silently classified as unused. These counts include
the61 spell and128 skill definitions/descriptions. Skill Info body/footer text
has210px after the native6px inset, three body rows and footer row4. The
19 new audition contexts include all100 menu-eligible skill names and actual
cost/confirmation budgets; both fonts fit, with T2 remaining selected.
Discovery is ongoing;
reviewed sources and inserted resources are separate counts, and neither proves
that every shared caller or every game text family is localized. Remaining work
includes combat, item naming/inscriptions, skill/input menus, other shared
consumers and source disposition research. Work continues without batch approval.

Build font validation now uses a strictly scoped immutable snapshot, validated
on entry and exit. Independent calls remain strict. This reproduces the accepted
ROM/BPS byte for byte while reducing build time from roughly100seconds to3seconds.
Evidence: `build/text-next/font-snapshot-repro.json` and dedicated mutation tests.

The following2,159 summary is retained as milestone history.

The archived receipt is `build/accepted/2159/english-services-validation.json`: **2,159 inserted
resources**, ROM SHA-256
`f00ffbad98c02fd29e0151e77db9dbb200d3ce242769d4d8c14284a2372d6a4a`.
ROM/BPS/ledger/receipt are preserved in `build/accepted/2159/`. Full cumulative
checks pass, including1,872 item cases,21 bank rewards,13 bakery cases,331 core
combat/status cases,39 additional effects,60 item-use and166 appearance cases.
The added45 story-command,45 condition,44 equipment/removal/drop and36 pickup
cases also pass. All1,076 ordinary prose cases,157 special-consumer cases and
1,046 native getter targets through seven ROM-loaded banks pass. Bank/storage
persistence,84 unit tests,90 WebKit contexts and890 font measurements pass.
A clean build reproduces both ROM and BPS byte for byte. Source ROM/save,
selected T2 font,3px spaces and original menu geometry remain unchanged.
Log: `build/services/complete-build-more-traps.log`. The independent
late-item worker uses the unchanged verifier; the main run revalidates its
ROM/dependency/fixture/capture cache keys and complete required case set.

Accepted resource counts:1,040 dialogue,46 menus,23 UI,405 items,141 actor names,
ten combat,17 bank,ten storage,seven bakery,three status,ten private well labels,
154 appearances,13 effects,five item-use,nine conditions,nine equipment/removal/
drop,six pickup,five Swap,15 container,six town inventory,33 player-message
43 blacksmith,34 synthesis,one selection prompt,60 Remi,ten warp-name,six mayor,two well-picker,five hunger,five status-trap,two warp-trap,four equipment-removal-trap,five mud-trap,four damage-trap andeleven acid/rust resources.
Story includes874 ordinary passages and33 owned special passages. These counts
describe insertion and bounded native validation; ordinary later-story
progression, bakery unlocking and whole-game coverage remain separate.

An earlier47 resources add21 action labels, five Swap formats,15 container
formats/prefix/kind labels andsix town inventory messages/labels. The separate
contained-item action producer retains original geometry with checked256-byte
output and64-byte scratch regions. All108 additional cumulative cases pass:
12 main-label,12 contained-label,20 Swap,54 container and10 town inventory cases.
The town Trash label fits34px; filled-pot confirmation warns about losing the
contents too. Ordinary blue-book View with empty inventory also passes using
the identical approved “You are not carrying any items.” source alias.
The previous1,887-resource build remains archived in `build/accepted/1887/`.

An earlier 76 resources add 33 player-name messages and 43 blacksmith
resources. All 216 player-wrapper cases, 57 blacksmith rendering/format cases
and 13 exchange/tip/counter-cap cases pass cumulatively. The preceding
1,934-resource ROM/BPS/receipt remains archived in `build/accepted/1934/`.
The108-source town prose preflight is reviewed and rendered, with35 of those
plain passages now assigned to the owned blacksmith consumer. Remaining town
service insertion, actual windows and branch flows still need their own checks.

The new inventory messages retain their native 192-byte outputs and separate
64-byte item fields. Automatic walking has an independently audited 256-byte
output. Checks cover native equipment flags, dropped items, pickup counts,
gold totals, arrow merging, refusal paths, buffer guards, registers and pixels.
Conditional line-break control `0E 0A 49` joins actual widths through 215px and
wraps longer substitutions; fixed messages can use the verified 216px region.
Eleven native boundary/colour/Japanese-glyph probes establish that rule.
Full meaning is retained in every fallback, without font or window changes.

The A-command's audited native callback requests only its original jingle;
gifts and dungeon unlocks happen in surrounding scripts. Condition checks
include native strength loss bounded to 1..3, sleep, wakefulness and immediate
movement recovery. Controlled dispatch/state substitutions are recorded and
remain distinct from ordinary acquisition or later-story progression.

Separate prototype galleries remain available in
`build/{story-command,player-condition,inventory-action,pickup}-prototype/`.
Cumulative galleries are generated from passing matching-ROM reports in
`build/english/{story-command,player-condition,inventory-action,pickup}-validation/`.
The previous 1,676- and 774-resource milestones remain archived separately.

The identified-item catalog has 206 non-placeholder names and 38 compact display
forms. Full names/evidence remain in the glossary. Base names have an 80px /
31-byte reserve; complete rows have 162px / 64 bytes. All nine row states per
name and applicable Info-description routes are checked. Blank scroll and
item 151 use Write instead of Info; their descriptions are explicitly excluded
from that route's rendering claim. Custom names, inscriptions, special records
and unknown menu families remain separately scoped. See `ITEM_TEXT.md`.

The repaired-storage quest recipe uses ordinary inputs and native saves.
Bank/storage transaction persistence passes. Bakery availability and later-story
progression remain separate from their controlled consumer checks. The original
Japanese sacred-flame quest route was observed; a complete ordinary English
quest run is not yet accepted.

## Discovery and remaining coverage

Current accounting: **3,400 unique sources**,3,256 reviewed,117 unresolved,
and27 retained/component dispositions. This includes154 original inscription
lookup rows (deduplicated by source) and40 fused-ability label pointers.
The inventory joins seven event banks, the300-slot shared town table,654 shared
system/combat/menu pointers, 221 item definitions and descriptions, both 141-ID
actor-name tables, 154 unidentified appearances plus their end marker, category
labels, five item-use announcement sources, ten well-level labels, and owned menu/UI reviews. Source aliases are deduplicated. Language
review does not establish insertion through every shared consumer. Both actor
name tables, result/history consumers and fixed history Torneko field are now
in the accepted cumulative build. The catalog-specific draft history below
records earlier research and is superseded by the current totals above.

`translations/town-remaining-draft.json` has 177 source drafts with a dedicated
bilingual pass, including six superseded by the active bank review. Remaining
service consumers, dynamic fields, speaker naming evidence, control timing and
Yes/No flow still need native review. `translations/item-aliases-draft.json`
records 154 appearance translations and a separate marker record, with exact T2
identities checked against T3 project terminology. The subsequent T2 bilingual
review and native prototype cover all 154 appearances within 80px and 31 encoded
bytes, with nineteen compact forms. The canonical review supersedes the draft
wording where recorded below. Cumulative appearance insertion is accepted in the 1,848-resource build; custom
naming and inscription support remain pending.
`translations/shared-messages-draft.json` now holds 621 shared-message and UI
drafts. The other 33 pointer slots have explicit source dispositions: the original nine core
combat formats already reviewed, empty resources, character/control tables and
numeric markers needing consumer investigation. All 654 slots are accounted
for; this is not a claim that every slot is live GBA text. The shared audit checks
source identities, printf fields, argument multiplicity and static widths. A
dedicated second semantic pass covers all 621 drafts; context-sensitive
fragments and native rendering remain pending. The remaining opening bank adds 53 translated drafts and three single-kana
fragments; the remaining home bank adds 135 translated drafts and ten short
source fragments. Both prose sets have a dedicated bilingual pass. These
staging catalogs are not counted as accepted translations. The missing-King
bank adds 90 translated drafts and five short fragments. Missing-King, forest
and sage now also have dedicated bilingual passes. The forest, sage,
final-quest and postgame banks add 100, 116, 185 and 228 translated drafts
respectively. Final-quest has a dedicated bilingual pass; postgame has 143
direct bilingual reviews and 85 exact normalized-source reconciliations with
previously reviewed T2 wording. Across the prose catalogs there are 1,082 translated drafts from
1,120 sources (including superseded drafts and unclassified fragments). These
counts are staging work, not accepted insertion. Source identity and
recorded layout checks for the prose staging catalogs are repeatable with
`python -m tools.audit_prose_drafts`. The 7F player-initial control has four
passing native reader/centering probes using production expectations. Compiler
integration reserves 14px for the initial and 98px for the full name, and retains
exact control order. @A support and a centered gift reflow resolve 19 previously
blocked draft layouts. All fourteen printf/custom-name formats, two additional
static formatter sources and two medal reward commands now have tested consumers
in the accepted story build. The fifteen further A-command sources are now
in the accepted1,887-resource build with passing native checks. This does not establish native progression through later banks.

Open work includes remaining combat/system/town consumers, custom-name priced
rows, unidentified script fragments and legacy resources whose GBA consumers
are not established. English inscriptions and pot labels are integrated in
3,514 and undergoing cumulative checks. Other text tables and unclassified
scan leads still require discovery.
The source inventory is not proof of complete extraction.

`tools.audit_text_staging` separately reports 2,044 reviewed sources and 700
additional known sources with draft wording available by exact source bytes.
Seventy-one still need wording or classification; these include 36 short event
fragments, control/character tables, numeric markers, reserved item definitions,
the appearance-table end marker and blank resources. This is not a completion
percentage: drafts still need final terminology, layout and native-consumer
validation, and unidentified ROM text can remain outside this inventory.

## Combat policy and evidence

Incoming actor/damage fragments form one complete message. The queue adapter
measures actual native glyph widths before removing soft breaks, retaining a
safe fallback for longer substitutions. The existing nine combat formats pass
173 controlled cases, of which 159 fit one line. Cumulative validation rechecks
exact names/numbers, glyph pixels, buffers, registers, stack, fragment suppression
and unchanged actor statistics during formatting. These are display checks,
not proof of every combat outcome through ordinary play.

Native dungeon resource loading and 12 actor-name getter cases cover level
suffixes through the signed 16-bit maximum. A separate missed-attack prototype
passes 149 cases across both native callers, covering every actor name, maximum
level suffixes and player-name extremes. Every message fits one line; the widest
is 201px within the 216px budget. Its candidate and report are in
`build/combat-miss-prototype/`; the miss format is now integrated and accepted in the 764-resource build.
Other status/combat messages remain separate work. Do not force one line by dropping meaning or narrowing the font.

`tools.audit_terminology` now rejects conflicting glossary entries and requires
every active item name to match its canonical glossary term. Existing documented
PS1 fallback names **Super herb** and **Misleader herb** take precedence over the
T3 provisional Healing herb/Fright herb choices; this keeps the items consistent
with the already translated tutorial.

## Earlier bakery prototype (now integrated)

An isolated seven-resource bakery prototype passes 13 native cases, with all
three breads/prices, buy-again, cancellation/decline, insufficient/exact gold,
full inventory and maximum-width player names. Original window geometry and
256-byte formatter bounds pass. Native delivery, gold deductions, pixels and
ABI are checked. `build/bakery-prototype/report.json` pins its separate ROM;
its seven resources are now included in the accepted cumulative count. Entry is explicitly redirected
from a bank call; ordinary bakery unlock and saved bakery purchases remain open.

## Earlier one-line player-status prototype (now integrated)

Three isolated player-only messages (hallucination, blindness and failed
blindness) pass nine native Drink/effect cases at all supported player-name
extremes. Maximum widths are 205, 155 and 105px within 216px; all use one line.
The source table copy is supplied only to the two audited player routines.
`build/player-status-prototype/report.json` records buffers, ABI, exact queue,
pixels, controlled inventory/status/name setup and save preservation. These
were prototype resources and are now in the cumulative accepted total.

## Prose rendering preflight

A separate candidate appends 876 reviewed event drafts solely for controlled
reader checks. Event tables stay unchanged. The preflight tests actual glyph
pixels, paging, row bounds, return ABI and player-name extremes; its per-case
reports and screenshots are under `build/prose-preflight/`. Thirty-one drafts
with special format consumers or event side-effect commands are excluded from
this context-independent rendering pass. All **1,082 cases** passed, covering
**184,015 glyph bitmap checks**. This is not event insertion or ordinary
story/branch acceptance. A separate native relocation probe passed all 1,046
getter entries across seven banks, including 876 controlled English offsets.

One additional insertion caveat was found during consumer disassembly:
`event-bank-5.2747` has no printf field, but still passes through the special
`080501DC` formatter into shared temporary RAM. Its reviewed encoded English
is 266 bytes versus 131 original bytes; the ordinary dialogue preflight does
not establish sufficient temporary capacity. Keep this source out of general
event insertion until that consumer is adapted and checked.

The next prototype initially bound **875 sources in the ROM banks** and passed
all 1,046 native getter cases without substituting table words in RAM. Its
1,079 native rendering cases also pass. The wellkeeper's dynamic fields, floor
progress and event side-effect commands remain outside that count. A native
page review shortened the Goldfish's final request, retaining the outside
water jar and promised thanks while removing a three-word orphan page; both
story variants were updated and the complete prototype checks rerun. Subsequent
medal-consumer tracing found that static source `event-bank-6.465b` also goes
through a temporary formatter; it is excluded along with the numeric medal
messages. The ordinary insertion candidate now contains **874** sources and
passes 1,076 rendering cases / 183,352 glyph checks plus all 1,046 getters on
SHA `1b785b71b7e8cd4d76a4eb2e280937d47ebebc6849e988f5b66d4bcf1dfbe4e7`.
Rendering/getter checks alone do not prove that an
unexamined consumer has enough temporary storage.

The floor-progress consumer now has a separately tested 288-byte stack buffer.
All four messages pass 27 native selector/name cases, including the otherwise
static floor-27 message. The prototype preserves the original caller ABI,
items/gold and battery; ordinary final-quest reachability remains unaccepted.
See `build/floor-progress-prototype/report.json` and `MEMORY_MAP.md`.

A further wellkeeper prototype translates both level acknowledgements and a
private copy of the ten Level 1–10 labels. Forty native calls cover both banks,
every level and the original completion bit initially clear/set. Exact format,
256-byte stack storage, pixels/paging, return ABI, original shared temporary
bytes, items/gold and battery all pass. This does not translate the level
selection menu or establish ordinary access to the well. Evidence:
`build/well-level-prototype/report.json`. These prototypes are separate from
the 774-resource cumulative candidate until integration and regression pass.

The three village-name formats also pass a separate twelve-case prototype.
The native name producer is retained, with disjoint 448-byte output and
32-byte name-argument regions on the stack. Tests cover the required Torneko
name, the producer's eight-glyph English/Japanese maxima and empty-name branch;
the approved seven-character editor remains unchanged. Native formatting,
guard/ABI, paging/pixels and save preservation pass. Evidence is under
`build/village-prose-prototype/`; normal access to those later scenes is still
outside the recorded playthrough routes.

The medal-service prototype now validates nine further sources through its
native 480-byte stack formatter and original reward logic. Thirty-three cases
cover donations, sword/shield rewards, a full inventory of medals, the 999 limit
and three name widths. They check rendered text, counts, actual gifts, flags,
return ABI and unchanged battery. The otherwise unobserved shield-introduction
source is explicitly forced at the native getter and is not claimed as normal
progression. Evidence: `build/medal-prototype/report.json`. These resources are
ready for cumulative integration with the other tested story consumers.

## Unidentified appearance prototype

The 154 appearance names now have a dedicated bilingual/display review in
`translations/item-aliases-review.json`. A private display-table copy preserves
the original assignment table, metadata and End Mark sentinel. All names meet
80px/31-byte budgets; nineteen use distinct documented compact forms.

The separate prototype passes **166 native cases**, including every name,
the widest priced and identified case per category, numeric/glyph checks and
repeated action-panel restoration. See the [native gallery](../build/item-alias-prototype/index.html).
It is not yet part of the 1,676-resource cumulative story candidate. Custom item
names and inscriptions remain separate consumers with unresolved constraints.

The review replaces the Kaede/Momiji romanizations with Maple staff and Japanese
maple staff (display: Jpn. maple stf.), keeping the disguises distinct using the
[botanical specialist's English distinction](https://www.momijikaedelab.jp/カエデ属調査研究報告/もみじとかえでの違い/).
褐色 overlaps the other brown label in [Shogakukan's dictionary](https://kotobank.jp/jeword/褐色).
Umber herb is an independent brown-family naming choice to distinguish it;
[Collins](https://www.collinsdictionary.com/us/dictionary/english/umber) supports
the color family, not an exact Japanese equivalence or official game name.

## Pending equipment/removal/drop integration

Nine further reviewed sources now pass a separate insertion prototype, using
owned copies of their shared pointers and the native conditional line break.
All44 controlled native-menu cases pass:48 messages,32 one line and16 complete
two-line fallbacks. Existing192-byte output buffers and64-byte item fields are
preserved. Equipment/removal flags and dropped item/inventory results also pass.
`build/inventory-action-prototype/index.html` contains all screenshots; its report
records field/state overrides and exact input schedules. ROM SHA-256:
`071cd8052b4fc226e02d8ff41c61e54d029a4b3991aa51ebc21873887f1e7e80`.
These reviews are now included in inventory accounting and the 1,887-resource
candidate; full cumulative acceptance remains pending. The incomplete Japanese
ground-removal fragment090 remains unchanged pending contextual investigation.

Six central pickup sources also pass a separate 36-case prototype: ordinary item,
gold, arrow merging, both full-inventory messages, pickup inability, floor sticking
and standing. The additional automatic-walk standing reader also passes controlled native checks.
There are 26 one-line and 10 two-line messages. Checks include native
inventory/gold/arrow outcomes,192-byte buffers,64-byte item fields and pixels.
See `build/pickup-prototype/index.html`, SHA-256
`f57a4cfd25aa757fb2b74023890d13385069e60ae6697663a5cece2a50ed5c3a`.
Ordinary automatic walking remains separate from its controlled wrapper proof. These six reviews
are included in inventory accounting and the 1,887-resource candidate; full
cumulative acceptance remains pending.

## Pending Floor/Swap consumer

A separate five-resource Floor/Swap prototype passes20 native cases and742 glyph
checks. Thirteen messages fit one line and seven use complete two-line fallbacks.
Both item arguments keep their native roles; the successful case swaps the
actual floor/inventory identities. Native192-byte output and two64-byte fields,
refusal cases, registers and battery all pass. See `build/swap-prototype/index.html`,
SHA-256 `17d9a58b5cfda3d9588f730ddff9d03e75d5cc6f0eed643dd9c24d03d99ea830`.
Three source reviews are new; curse/sticking wording reuses the already reviewed
messages for this additional owned consumer. This prototype and those three new
reviews are not yet counted in the cumulative build/inventory totals above.

The next separate container prototype passes54 native cases for12 message
formats, a floor-item prefix and two newly identified generic labels (“pot” and “jewel box”). Bulk
and partial summaries fit one line; long single-item messages keep all meaning
with a conditional second line. Transfers conserve item identities and counts.
[Container screenshots and measured widths](../build/container-prototype/index.html)
include explicit controlled-state/input records. These15 resources are not yet
in the accepted1,887-resource archive; they are integrated in the new1,934-resource candidate. Single Put success retains its
floor-item prefix; special container mechanics and ordinary bulk selection remain
separate from this controlled consumer validation.

Separate menu prototypes now cover21 additional labels in the private action
copy, plus the independently audited contained-item producer. Both retain original
window geometry, normal font spacing and8px border gaps; enabled/disabled rendering,
selection, cancellation/reopening and parent restoration pass24 combined cases.
[Main-action gallery](../build/additional-actions-prototype/index.html) and
[contained-action gallery](../build/child-actions-prototype/index.html) list each
label's measured budget. These tests control available IDs; native availability
and action semantics remain separate. Extraction corrected the full original
pointer table to45 slots, including a separate pending discard label at ID44.

## Next player-message and town-prose work

A separate33-resource player-message prototype passes216 cases, with190 one-line
and26 two-line results across required and maximum English/Japanese names and
both native queue flags. It covers recovery, movement/sleep, fullness, stat changes,
identification, arrow catching, uncursing and one-time Kerplunk revival. A private
mapping is restricted to the existing256-byte player-name formatter; unknown
pointers pass through unchanged. All5,562 glyph checks and wrapper/buffer/save
checks pass. [Native gallery](../build/player-messages-prototype/index.html).
These33 resources are included in the accepted2,010-resource archive and current inventory.

`translations/town-prose-review.json` records a second bilingual pass for108 plain
town passages: blacksmith tips, Gaibara's synthesis dialogue, Remi's services and
other remaining town prose. Synthesis examples retain both inherited properties
and summed bonuses; the one-trillion-gold joke is preserved. Swords remain the
explicit tutorial example, while the general status label remains Weapon.
All108 sources pass114 rendering-preflight cases and8,619 native glyph checks,
including the three player-name extremes where applicable. The prototype SHA is
`cfa1039e343c4cacace8a6d1ffdced7418f5ea3f45cab9655c93bfa55dc3c941`.
[Japanese/English and native page gallery](../build/town-prose-preflight/index.html).
The preflight uses the ordinary resume reader with controlled source arguments;
town bindings, actual service windows, branch outcomes and ordinary progression
remain separate. Language reviews are now included in the inventory. Only the35 plain blacksmith passages have an owned insertion in the2,010-resource candidate; other town bindings remain unchanged.

The blacksmith now has a separate43-resource private-table prototype. Its35 plain
passages and eight formats pass57 native rendering cases/6,711 glyph checks.
Thirteen further exchange cases use controlled requested items/inventories and
ordinary buttons: the native service removes both payment items, strengthens the
selected weapon by its native bonus, updates the job count, selects every tip and
keeps the counter at120 on a further job. Formats preserve item order/multiplicity,
job counts and complete prose within the original512-byte output; the largest
formatted English result is464 bytes. ABI/guards, gold and battery checks pass.
[Blacksmith text and exchange gallery](../build/blacksmith-prototype/index.html).
SHA-256: `6acc7d5348aba4b4340034ce16111de15b913b80336c53b8824d12bfd09af20d`.
Ordinary unlocking, other town services and unowned blacksmith sources1/2/68
remain separate. These43 resources are included in the accepted2,010-resource archive.

## Next synthesis/selector prototype

Gaibara's34 owned text sources and the shared selector's “Which?” heading now
pass72 native cases:39 prose/format, five root-menu,25 actual synthesis and three
selection/Info-restoration cases. Both answers to every joke, base-item identity,
+3/+4 becoming+7, displayed/native gold deduction, empty inventory, first greeting,
all root choices and repeated reopening pass. All21,126 native glyph checks pass.
The existing256-byte formatter and64-byte full item field are preserved.
Synthesise55px fits its60px cursor-adjusted menu region; Which?33px fits40px.
Window positions/sizes and the8px outer-border gap remain unchanged.
[Source text and native gallery](../build/gaibara-prototype/index.html).
Prototype SHA: `21b1499a02dca6c6aa9275bb3c8b66460a5eda8bbe227c474afd6232e8214ddf`.
These35 resources are included in the current2,115-resource candidate and inventory,
but remain outside the accepted2,010-resource archive. Ordinary unlocking, other synthesis categories and unowned source
fragments remain explicit follow-ups.

## Accepted synthesis and Remi milestone2,115

The2,010-resource cumulative build passed and was archived with its ROM/BPS,
ledger and acceptance receipt. The next candidate combines Gaibara/selector35
and Remi70 resources, bringing reviewed insertion to2,115. Its SHA-256 is
`6c150efdece6cabe9c6f5ba433f4b308d83f4f5081d71bcc5be764ac4b9f0e2e`.
Full cumulative regression passed, including all72 synthesis/selector and 170 Remi cases. The clean rebuild and final89-context/888-measurement WebKit check pass. ROM/BPS/ledger/receipt are archived in `build/accepted/2115/`.

Remi's60 reviewed service slots and10 separately owned warp-menu names passed
170 native prototype cases before the final overwrite-warning wording revision:
73 prose/format,10 roots,21 English number selectors,3 original-selector
fallbacks,18 vocation choices,6 saved-village warnings,6 Iron safe purchases,
6 staff-charge transactions,5 level-up transactions,17 warp-menu cases and
5 warp-payment cases. That prototype SHA was
`324abc7c72db56ef2b49c3da4238dda66ea815d4949f083facf4dd6244d83781`.

Visual review then kept the saved village name and “Village save.” together on
one page. The final warning preserves the actual saved-name control, complete
overwrite condition and price. The revised prototype SHA
`d21e78fa34beb2ee0e570443bfbbea8d9cc06f9b3e9b61ac9d72a2048e015f7c`
passes73 prose/format and6 saved-name cases; the entire170-case family now passes
on the cumulative accepted ROM. The widest Japanese name still fits its200px line.

The number selector enables proportional spacing only for three private Remi
formats; unknown templates retain12px spacing. Original geometry remains:
88px number panel,112px root,72px vocation menu and128px warp menu.
The warp menu has122px available after its6px cursor inset. Six controlled
availability profiles pass repeated page switching/restoration; all ten listed
destination IDs retain their native selection values. See MEMORY_MAP.md for
source ownership and exact bounds.

Native transaction checks establish2000G Iron safe purchases,5000G per staff
charge, actual level changes and1000G per selected warp floor. Warp proof stops
at the owned service's return record, with payment and inventory checked; the
later dispatcher transition, actual village overwrite/cold reload and ordinary
service unlocking remain separate. Graphics remain deferred.


## Initial mayor prototype during the2,115 regression

The six village-renaming sources now pass20 native cases on prototype SHA
`2c193162b58451954496b6da8dbd21c5926243001b420adc8740810b04f25be7`:12 prose/format renders,5 keyboard/choice flows and3 book-save/cold-load
round trips. Torneko, seven wide English letters and a name corrected after
rejection persist; the separate player name remains intact. Cancellation uses
B on an empty editor. Both formatted messages preserve meaning within the
existing256-byte output, with112px reserved for eight legacy Japanese glyphs.
[Mayor source/English and native gallery](../build/mayor-prototype/index.html).

These six resources are not yet in the2,115 cumulative candidate. Four plain
passages already had language reviews; two formats have new independent reviews.
The inventory will include this catalog at the next source update. Controlled
service entry and ordinary follow-on saving are recorded separately from
unverified mayor unlocking. See MEMORY_MAP.md for precise ownership.


The separate well picker prototype adds its two remaining Japanese prompt/template
bindings, reusing the already measured Remi level-number resource. All20 cases
pass with original88px geometry: five progress/cap inputs and four choice/boundary
paths. [Well picker source and native gallery](../build/well-picker-prototype/index.html).
These are also held outside the2,115 candidate until its regression finishes.
Ordinary well access/progression and actual dungeon entry remain separate.


Five hunger warnings now pass a separate seven-case prototype on SHA`7418292ff709c777237807b7ba1a16706fbfc98f913592cee075afc99020917d`.
All retain complete meaning on one line, including the collapse warning, without
font compression. Ordinary attacks after controlled fullness/counter setup
trigger the native threshold/warning selection; expected starvation damage and
two quiet branches pass. [Hunger warning gallery](../build/hunger-prototype/index.html).
These resources join mayor/well as the next staged additions, outside2,115.


The five sleep/hallucination/confusion trap notices pass18 separate native
handler/name/activation cases on prototype SHA
`901c2e4eabe8c5d2b26094b547de51697078bdbcb40563be3e2ec5ecd5975df0`.
Complete notice/effect chains fit one line; native status timers, queue/caller
registers and stack, HP/items/gold/save pass. Controlled entry and cleared
resistance fields are recorded; ordinary trap discovery and additional
resistance branches remain open.
[Status trap gallery](../build/status-traps-prototype/index.html).
Together with mayor, well picker and hunger,18 additional resource bindings
are staged outside the accepted2,115 build. Their catalogs still need inclusion
in the source inventory and their checks need cumulative integration.


## Accepted 2,133 milestone after archived 2,115

Mayor6, well picker2, hunger5 and status-trap5 are integrated and pass all
65 new cumulative native cases. The full regression, 84 unit tests and final
90-context/890-measurement WebKit check pass. A clean rebuild reproduces both
ROM and BPS byte for byte. ROM/BPS/ledger/receipt are archived in
`build/accepted/2133/`; the previous 2,115 archive remains intact.

The source inventory includes these reviews: 2,820 unique sources, 2,246
reviewed, 500 with draft wording, 71 unresolved, two replaced by components
and one intentionally retained Japanese. The next separate trap prototypes
below are not counted in this milestone or inventory.
Accepted ROM SHA `37cd7f5b7ea543db411798e1a8375a5be8f112aad40e2b208c248eece8fb90aa`.


A separate two-binding warp-trap prototype passes six native activation/name
cases, including actual native teleport movement and unchanged failure position.
Both messages fit one line, and HP/items/gold/save remain intact.
[Warp-trap gallery](../build/warp-trap-prototype/index.html).
Its source review/insertion remains outside the2,133 regression and current
inventory pending the next cumulative update.


The separate equipment-removal trap prototype adds four bindings and passes
four native branches: removal of the naturally equipped shield, failed
activation, nothing equipped and protection. The active case clears only the
equipped flag; other inventory bytes and all HP/gold/save state are preserved.
The protection flag is controlled at its native read, since earlier turn logic
refreshes gear flags. All messages fit one line.
[Equipment-removal trap gallery](../build/unequip-trap-prototype/index.html).
These four bindings and the two warp-trap bindings remain staged outside2,133.


The separate mud-trap prototype adds five bindings and passes ten native cases
covering every bread ID203..210, failed activation and no bread. Six susceptible
types become Rotten bread; Rotten bread and Golden bread remain unchanged.
Exact native item/identification flags, other inventory bytes, complete one-line
messages and HP/gold/save pass.
[Mud-trap gallery](../build/mud-trap-prototype/index.html).
There are now11 next-stage bindings across warp, equipment-removal and mud
prototypes, outside the2,133 regression and current source-review inventory.


Poison-arrow and falling-rock trap prototypes add four bindings with12 passing
native activation/name cases. Existing strength/damage translations complete
the message chains; active cases lose5HP, and poison arrows also lose1strength
in the tested unprotected fixture. Failure preserves both fields. All messages
fit one line with existing formatter buffers, unchanged items/gold/save and
checked native return state.
[Damage-trap gallery](../build/damage-traps-prototype/index.html).
The next staged set now totals15 bindings across four trap prototypes with
32 passing native cases; none are counted in the2,133 cumulative candidate.


The next traced consumer is acid/rust. A controlled native acid trap currently
shows Japanese resistance prose around the translated Leather shield name.
The shield formatter has separate64-byte item and256-byte output fields;
mode-dependent sword/shield consumers and their shared-table literals are
recorded in MEMORY_MAP.md. These remain investigation leads, not reviewed
English insertion or claimed gameplay coverage.


Acid/rust now has a separate eleven-binding English prototype with19 passing
native cases. It covers actual shield/weapon rust, material protection, missing
equipment, controlled ring/protection branches, the-99 enhancement bound and
maximal/coloured item fields. Native material properties come from the item
definition records. Ordinary named messages stay on one line; the widest
allowed field uses the verified two-line fallback, preserving its full name.
[Rust gallery](../build/rust-prototype/index.html).
The next staged set totals26 bindings and51 native cases across five trap/rust
prototypes. They remain outside2,133 and the current source-review inventory.


## Accepted 2,159 milestone after archived 2,133

The five trap/rust prototypes above are now integrated: 26 owned bindings,
with all 51 cumulative native cases passing on ROM SHA
`f00ffbad98c02fd29e0151e77db9dbb200d3ce242769d4d8c14284a2372d6a4a`.
The source inventory includes these reviews (16 additional unique sources;
shared warning bindings are deduplicated). Full regression, 84 unit tests, 90 WebKit contexts/890 font measurements and
clean ROM/BPS reproduction pass. The accepted archive is `build/accepted/2159/`;
the previous 2,133 archive remains intact.
`build/services/complete-build-more-traps.log` records the full run.
Cumulative galleries live in `build/english/{warp-trap,unequip-trap,mud-trap,damage-traps,rust}-validation/`.


A separate summoning-trap prototype now adds four bindings with four passing
native cases. Both native spawn modes create four monsters; refusal preserves
them, and a controlled zero-count call reaches the native no-monsters branch.
Messages fit one line. Original actor state is compared from handler entry to
return, after the triggering turn's ordinary movement. The explicit branch/count
overrides and ordinary discovery exclusions are retained in the report.
[Summoning trap gallery](../build/summon-trap-prototype/index.html).
This prototype remains outside the 2,159 candidate and source-review count.


The separate mine/iron-ball prototype adds four bindings with12 passing native
activation/name cases. Both notices and the existing damage acknowledgement
fit one line. The tested29HP fixture loses14HP to the mine and5HP to the iron
ball, with unchanged strength/items/gold/save and checked native call returns.
[Mine and iron-ball gallery](../build/blast-traps-prototype/index.html).
Together with summoning, eight next-stage bindings pass16 native cases outside
the2,159 cumulative candidate. Pitfall and stumbling consumers remain traced
investigation leads, including the pitfall's separate delayed damage consumer.


A read-only build profile (`build/text-next/build-profile.{txt,pstats}`) identifies
an upcoming tooling improvement: one build took40.3s, including3,432 font loads
and37.7s cumulatively in `load_font`. Most time repeatedly validates the same
base/glyph provenance while compiling different text rows. The current
regression keeps that implementation unchanged. A future explicit build-scoped
validated font snapshot could remove repeated work; it must preserve provenance
checks, reject modified assets and produce identical ROM bytes before adoption.
Do not replace strict verification with an unkeyed process-wide cache.


The separate pitfall prototype now translates three bindings, including the
otherwise missed delayed damage message. Four native branches pass; successful
falling verifies the complete message and actual29-to24HP reduction at the
caller's delayed damage boundary. Controlled protection and special-floor
branches preserveHP. All messages fit one line, with original ABI/stack,
items/gold/save preserved. Final next-floor arrival and death remain unclaimed.
[Pitfall gallery](../build/pitfall-prototype/index.html).
The next staged set totals11 bindings and20 passing native cases across
summoning, mine/iron-ball and pitfall prototypes, outside2,159 and the current
source-review inventory. The stumbling handler remains an investigation lead.

The current known-source remainder is concentrated in454 shared-system drafts.
Smaller groups are ten town drafts, eleven item-category labels, three item
sources and six other native labels. These numbers are language-review gaps,
not a count of all unpatched consumers of already-reviewed sources.

The71 unresolved sources include36 event entries containing exactly one
Japanese glyph plus NUL,20 shared-system entries (keyboards, numeric/internal
labels and control streams),11 item records, one appearance end marker, one
other native empty string and two empty/newline town entries. Exact examples
`event-bank-0.1041` (`837C00`), `event-bank-1.513c` (`834500`) and
`event-bank-6.426d` (`8EB100`) have NUL terminators in the original bank data;
these are not automatically extraction truncation errors. Their runtime role
must be established before replacing or excluding them. Reserved-looking item
names and numeric strings likewise remain unresolved until consumer/reachability
evidence establishes their disposition. None is silently counted as translated.


An isolated follow-up benchmark (`build/text-next/font-snapshot-benchmark.json`)
used a deep-copied, content-keyed font snapshot only inside its temporary Python
process. It reduced strict font validations from3,432 to1 and built the identical
2,159-resource ROM in2.58s. Source ROM and font hashes were checked before/after.
This is feasibility evidence, not a production optimization or a replacement
for the unchanged validation currently running. Production adoption still needs
scoped lifetime and changed-input/mutability tests.


The 2,159 milestone's late-item evidence is preserved in
`build/english/item-probes-2159-late/report.json` (SHA
`e72f86b9a8ff3c16dfb3b8885e002069f7d855659069c131441cf9e00659ff1c`).
The unchanged verifier passed1,430 worker cases;1,426 relevant completed cases
were staged with matching ROM/fixture/dependency/font/capture keys. The main
run revalidated those keys and the complete1,872-case set. The 11 newer trap
bindings remain separate prototypes with20 passing cases, outside this archive.

## Continuation: root outputs and remaining gameplay notices

The default compiler now exports a matching ROM/BPS pair directly under `build/`,
with a manifest and independent patch-apply verification. A rejected patch
export preserves the previous outputs; the new round-trip/corruption test passes.
Explicit alternate compiler output directories remain isolated. These latest
files are development outputs; accepted milestone archives remain separate.

The2,255 candidate adds85 reviewed static notices at the owned dialogue queue,
with176 native mapping/flag/fallback cases passing. Original shared strings and
other consumers are preserved. The source inventory now has2,353 reviewed,
393 draft,71 unresolved, two replaced and one retained-Japanese sources out of
2,820 identified sources. Complete ordinary-gameplay discovery is not implied.
Full cumulative regression is running in `build/services/complete-build-2255.log`.

The next separate bear-trap prototype adds three bindings with seven passing
native cases, including both configured grabbing-monster types and actor-field
width/byte/colour boundaries. The widest field correctly uses two lines; natural
names and narrow maximum-byte fields use one. Native hold release, timer value6,
caller/queue/formatter ABI and HP/items/gold/save preservation pass. Recovery
turn count and ordinary trap/grab acquisition remain separate.
[Bear-trap gallery](../build/bear-trap-prototype/index.html).

The separate stumbling-trap prototype adds four bindings with nine passing
native cases: empty/evasion/protection/Surefoot staff, actual successful floor
drop, item loss after controlled pool exhaustion, and item-field width/byte/
colour boundaries. The complete ordinary loss warning now fits one201px line;
large fields retain conditional fallback lines without compression. Floor-item
identity and inventory-loss counts are checked alongside ABI, buffers and save.
[Stumbling-trap gallery](../build/stumble-trap-prototype/index.html).
Together, bear and stumbling prototypes stage seven bindings with16 native cases
outside the2,255 cumulative build; pot-breaking/contents and ordinary acquisition
remain separate coverage work.

The separate curse prototype adds two bindings and 13 passing native cases. It
confirms the fallback affects one carried item and uses “An item was cursed!”
Bear/stumble/curse together stage nine bindings and29 cases for later cumulative
integration; they are not yet included in the2,255 build or source totals.
The exact-copy queue prototype passes348 cases, covering existing85 notices
after native RAM formatting as well as direct pointers. It preserves unrelated
and near-match text and does not increase the unique translation count.

Strength/max-HP drain and level drain add six staged bindings and37 passing
native cases. The former checks actual versus maximum stats and clamps; the
latter checks one/two-level loss, minimum level, transformation and resistance.
Together with bear/stumble/curse,15 bindings and66 cases are ready for cumulative
integration after the ongoing2,255 regression. An additional38 static notices
are undergoing direct-pointer and exact-copy native checks in an isolated build.
These staged additions do not yet change the cumulative source totals.

Gold theft adds four staged bindings and15 passing native cases, including
conserved zero/partial/maximum gold transfers and combined maximum fields.
The staged trap/monster families now total19 bindings and81 cases. All500
checks also pass for the123-notice direct/exact-copy queue map, adding38 reviewed
static sources. These remain isolated until cumulative integration; the latest
root ROM/BPS still match the2,255 build currently completing regression.

## Integrated2,312 candidate

The preceding bear, stumbling, curse, strength/max-HP drain, level drain and
gold-theft prototypes are now integrated:19 bindings with81 required native
cases. The static queue map now contains123 reviewed sources, with500 required
direct/copy/flag/fallback cases. ROM/BPS root exports match this candidate; the
accepted2,255 archive remains unchanged while cumulative regression runs.
Unique reviewed sources are2,405/2,820 (85.3%);341 have draft wording and71 remain
unresolved. This percentage measures language review, not all-consumer insertion
or complete discovery. The builder has2,312 resource bindings; aliases and
consumer-specific copies mean that count has a different denominator.

## Queue preview correction and next staged text

Visual inspection found that the generic direct-turn queue probe could prepare
correct native glyph tiles while its message window was hidden in the captured
frame. The2,255 queue reports therefore establish bytes/renderer/ABI checks,
not visible screenshots. The current verifier instead follows a native Life herb
Drink action before substituting the source/flag at its queue or player wrapper.
It now compares every authored glyph against the actual final screen, using the
measured8,120 origin and16px row pitch and accounting for native scrolling.
Both source text lines must remain visible. The2,312 regression uses this stronger
check; earlier archived receipts are retained with this explicit limitation.

An exploratory four-line suspension warning passed byte/glyph checks but scrolled
its opening text out of view. Four-line warnings52C/5C4 remain excluded pending
their actual dialogue/choice consumers. Fourteen further static notices now fit
at most two visible216px lines, preserving all warning conditions; their revised
prototype is undergoing complete screen-pixel checks. This is not yet cumulative
insertion. Three additional monster-condition bindings pass27 native cases:
fullness loss/clamp/rounding, player spell sealing and monster Kaclang, including
resistance and existing-state branches. Captures for ordinary states have been
visually checked; these bindings remain separate from the2,312 build.

### Results/history actor prototype

The second raw actor table now has an isolated insertion prototype in
`build/results-prototype/`, with282 passing cases and a matching native gallery
at `validation/index.html`. Every141 actor IDs is checked in each consumer:
results ID0 uses Someone, history ID0 follows the native distinct fixed Torneko
source, and raw ID131 remains False priest. The full English defeat line reaches
182px, within the tighter212px remaining in the original results panel; history
has224px. Final-frame pixel comparisons, complete formats, untouched256/128-byte
buffer tails/guards, caller ABI and unchanged battery pass. All other results/
history text and ordinary defeat/record persistence remain separate. The new
143 resources are staged, not yet included in the2,312 root build or counted as
accepted insertion. This adds both reviewed raw name usage and the separately
reviewed monster-defeat format, without modifying the shared original tables.

The results follow-up adds27 defeat causes and their complete “Fell {cause}.”
wrapper:171 staged resources total. All336 native results/history cases pass in
`build/results-causes-prototype/validation/`, including54 non-monster causes.
The longest full cause line is208px in the original212px results region.
Putrid bread and the reviewed full staff/ring names are retained; triggering
removal/equipping/falling and spell failure are not dropped to force fit.
The earlier143-resource actor-only prototype remains preserved separately.

### Further result UI staging after2,500

22 further sources are reviewed in `translations/results-ui-review.json` and
inserted only into `build/results-ui-prototype/`:13 destination labels plus
location/from formats, None, trip heading, score/rank and EXP/strength. All42
controlled native cases pass complete final-frame pixel/colour, formatter, tail,
guard and ABI checks. The explicitly invalid negative-input probe preserves the native
low-byte decimal behavior; it does not claim general signed-number support. These remain separate from the running2,500
regression; equipment labels and other exit text are the next consumer work.

The equipment-label follow-up now has642 passing cases in
`build/results-ui-equipment-prototype/ui-validation/`, including all75 reviewed
weapon/shield/ring identities across eight states. Complete item fields and
price separation pass with Weapon/Shield/Ring in the original window. This
25-resource prototype supersedes the22-resource UI scope without replacing its
separate artifacts. It remains outside the frozen2,500 cumulative candidate.

### Result outcomes and high-score history staging

The next isolated candidate contains33 result UI sources andnine further
history literals (42 additions beyond2,500). The33-source results prototype
passes648 result cases and48 history-location/outcome cases in
`build/results-ui-complete-prototype/`. This includes every original exit
method and the distinct safe Meadow passage, quest completion, wind, priest
and give-up outcomes. Escape uses the PS1 fallback name with explicit secondary
naming evidence and medium confidence in the review catalog; the Japanese
source/native discriminator establish its distinction from scroll and spell.

`build/history-ui-prototype/` additionally translates the high-score heading,
empty state, rank/points/floor/depths and complete HP/level/strength, EXP/gold,
trip/time rows. Its54 history cases pass, including maximum fields, rank50,
empty history and native next/previous selection. The combined ROM also passes648 result UI and336 actor/cause cases. Root exports remain the2,500
candidate until its cumulative regression is accepted; these prototype counts
are not silently included in current language/acceptance totals.

### 3,291 cumulative route retry

The first cumulative attempt stopped at a native floor-three defeat (no ROM
crash or injected-state test). Its log/failure inputs are retained in
`build/services/complete-build-3291-attempt1.log` and the original castle
walk-failure report. A staged ordinary-button route leaves and re-enters the
floor-two stairs before descent; it passes first-dungeon and all castle
audience checks without RAM/register changes. That recorded round trip is
now part of `verify_first_dungeon`; cumulative checks resume from that verifier,
using the already passing current-ROM name-entry/opening checks.

### Staged English inscription input

An isolated writing prototype passes584 native lookup cases, nine actual
Write/Name editor cases and the existing shared-name-editor input regression.
It accepts full English spell/effect names and displayed scroll names, without
case sensitivity, while preserving original kana entries and native history
requirements. Special writing inputs allow15characters; ordinary item names
stay8 and player/village limits stay7. No save layout changes. It remains
outside the root build until integration after the3,291 cumulative run.

### Staged fused-ability and talk refusals

The synthesized-ability loss prototype adds40 ability labels and its complete
message. All39 cases pass: every20 sword/16 shield bit admitted by the native
wrapper, plus three field bounds. The original removal logic executes; a
recorded valid RNG result selects the tested bit. Normal and widest captures
were visually inspected. Gallery: `build/fused-loss-prototype/fused-loss-validation/index.html`.
The separate talk-refusal prototype passes12 cases across both original
message blocks, three player-name profiles and three actor-field bounds.
Actual conversation conditions are excluded from these controlled block probes.
Gallery: `build/cannot-talk-prototype/cannot-talk-validation/index.html`.
Neither prototype is counted in the3,291 root build.

The3,291 monster-announcement verifier encountered a repeated debugger
observation of the same glyph preparation (41 glyphs,42 observations). Its
check now validates identical preparation state before counting it once, as
in the existing dungeon-leaf verifier. The failing case and full announcement
cohort pass exact final-frame pixel checks; no ROM change was required.

The separate Step/Stairs prototype passes six native menu cases with two
cancellation/reopening cycles each, final B/Stay/action choices, exact command
results, original geometry and final pixels. It adds two resources and remains
outside3,291. Gallery: `build/step-stairs-prototype/step-stairs-validation/index.html`.

Custom-item category/punctuation research confirms eight-character English
names fit the tested six category rows with native prices. The initial Japanese
sample used eight13px glyphs and overlapped price cells in all six categories;
its normal rows remained within168px (the pot row reached161px). That sample
was not the actual maximum. The prototype is deliberately not
integrated or signed off. Captures and actual inputs are retained in
`build/custom-item-prototype/probe/`; this is a layout blocker, not evidence
that ordinary English names need a narrower font.

The pot View prototype adds concealed/empty-content labels and passes11
native inventory/View states with three opens each. The Thief-pot path also
checks all9 native label copies and their64-byte guards. Its original07/08
bytes were verified as inert GBA controls and retained. Gallery:
`build/pot-view-prototype/pot-view-validation/index.html`.
These two resources remain staged while3,291 cumulative checks finish.

### Staged legacy record menu and travel prompts

`build/book-travel-prototype/` adds eight resources: Records/Scores/Trade items,
the stored-item requirement, Meadow traversal, Yes/No, saved-village overwrite
and travel confirmation. All16 native cases pass, with two cancel/reopen
cycles per case, native choices/results, original windows, exact pixels and
caller ABI/guards. The overwrite warning also passes eight widest English and
Japanese saved-name glyphs through the original save-header/name getter.
Native save-header substitutions are explicitly controlled; ordinary script
routing and actual trading/travel/save effects remain separate. The gallery
was visually reviewed. These resources are not yet in the3,443 root build.

### Coverage and custom-name follow-up

The original name keyboard permits14px glyphs, including `げ` (82B0).
Eight such glyphs in the staged English pot/category row exceed the original
168px window even without a price: the bracket starts at166px, and visible
ink reaches169px. The normal text-bounds checker rejects this case. Diagnostic
captures preserve the clipped result separately; they are not passing checks.
Evidence: `build/custom-item-maximum-prototype/probe-maximum-japanese/partial.json`
and `probe-pot-overflow/`. Custom-name insertion remains blocked pending a
layout that preserves the full legacy name, category, count and price.

A fresh scan found219 pointer-backed Japanese candidates outside the current
inventory ranges (`build/text-next/unaccounted-rom-pointers-3443.json`). These
include possible duplicate/legacy text and false-positive data; each requires
source ownership and consumer validation before changing coverage totals.
One confirmed gap is the separate40-entry fused-equipment Info table and its
alternate material-monster description. All45 native cases now pass, including
every slot, the alternate, combined-property selection, colour masks and two
reopens. Gallery: `build/ability-info-prototype/ability-info-validation/index.html`.
The41 resources remain staged outside3,443. Property badges are sprites and
remain on the deferred graphics list. The catalog percentage is not a
whole-game completion percentage.

The same discovery pass confirms21 additional text resources for the baker's
grave, forest relic/old man and flame relic/King scenes. All33 controlled native
cases pass, including complete page colours/pixels, widest name/initial fields
and the original Yes/No/B response branches. The grave and voice inscriptions
retain yellow at each native page clear. Gallery:
`build/dungeon-story-prototype/dungeon-story-validation/index.html`.
These21 resources are staged outside3,443; movement, quest state and natural
scene access remain separate. Two stored farewell strings lack established
readers in these owners and remain unchanged, with no global-unused claim.

## Next private-table text prototypes after3,514

Four dungeon-entry restrictions pass11 native cases in
`build/travel-gate-prototype/travel-gate-validation/`: maximum items,
store/discard, sell/discard and level1, including both item-message placements
and original128-byte scratch bounds. Actual travel/unlock outcomes remain separate.

Fifty-seven ending dialogue sources pass85 native cases in
`build/ending-prototype/ending-validation/`. All five scene tables preserve
native flags/timers, exact W/w delays and mode commands; auto pages work without
advancing input, including the widest English/Japanese player names. Bilingual
review uses Joy Chest and the established speaker names. These are text-only
changes; actor staging, natural ending progression and credits artwork remain
outside the controlled render probes. Both families are prepared but not yet
integrated into the3,514-resource root candidate while its regression is running.

Eight dungeon destination-picker resources also pass25 cases at
`build/dungeon-travel-prototype/dungeon-travel-validation/`, with original
geometry, cursor wrapping, positive selections and repeated reopening.
The stored Meadow label is explicitly a controlled selector case.

Another29 prepared sources cover soldier status topics and 13 complete
soldier/adventurer explanations. Six full menu cases pass every owned topic,
both soldier pages, all prose pages and repeated reopening at
`build/tutorial-help-prototype/tutorial-help-validation/`. The original
27-configuration tutorial system also contains21 other configurations; those
remain a separate active task. Japanese two-byte bank/group references are
preserved as data, not misclassified as text. All98 prepared additions remain
outside3,514 until its regression is accepted and the next cohort is integrated.


The four prototypes described above are now integrated at 3,612. A separate
75-source extension for the other tutorial topic menus is reviewed and under
layout/native investigation. It is **not** in the root build: the equipment
picker exposed a different native cursor inset, and several legacy descriptor
configurations have incoherent original label/explanation mappings that still
need reachability/disposition work. No universal menu sign-off is claimed.

## Prepared after the 3,612 candidate

A separate tutorial expansion adds75 reviewed sources to the first29. Its
104-source prototype passes27 configuration render/cursor cases, six complete
direct-help cases,20 correct-bank explanation cases and four controlled
alternate-header cases. Gallery folders are under
`build/tutorial-all-prototype/`. Equipment labels start11px into their original
window because that cursor starts at x5; every other column uses its own
measured cursor/text region. Original window geometry is preserved. Five
inconsistent original configurations remain explicit selection/reachability
gaps, with their original nontext mappings unchanged; no unused-code claim.

The11-source link-trade prototype passes21 message/Yes/No/cancel/maximum-field
cases and three picker/Info/Trade-selection cases. Its original40px action
window,168px parent and8px outer border gap pass exact restoration checks.
Actual cable transfer remains separate. Gallery:
`build/link-prototype/link-picker-validation/index.html` and
`link-message-validation/index.html` in the same prototype.

A one-source pre-ending save-cancellation prototype also passes both A/B
acknowledgements, preserving the original secondary wait and window closure.
Gallery: `build/ending-notice-prototype/ending-notice-validation/index.html`.
These87 additional resources remain staged while3,612 completes cumulative
regression. They are not yet included in the root ROM or current inventory totals.
One earlier prose spelling, Seal staff, also needs canonical Sealing staff in
the next build. Great room scroll was checked against the glossary and already
uses the correct full name.

### Additional tutorial pickup messages found (2026-09-27)

Eight previously unaccounted Japanese tips follow successful pickups in mode11.
They cover bread, weapon/shield equipment, ranged staff use, room-damage scrolls,
HP recovery, fire breathing and level gain. This is a plausible source of the
reported Japanese pickup text, separate from the already translated ordinary
pickup message; the user's exact route/build is still unknown.

The separate pickup-help prototype translates and reviews all eight, preserves
native controls and passes13 actual walking-dispatch probes for all11 item IDs
and two negatives. Glyph pixels, complete wording, original wait flags, byte
bounds, inventory/gold outcomes and caller ABI pass. Item identities and the
mode load are controlled, not naturally reached tutorial progression. The
queued reader interprets09 as a flag, not the dialogue reader's tab; this was
confirmed before finalizing budgets. Native gallery:
`build/pickup-help-prototype/pickup-help-validation/index.html`.
These eight are staged for the next cumulative build with the additional75
NPC tutorial resources,11 link-menu resources and one ending save notice.

### Warehouse repair text staged (2026-09-27)

Nine more direct carpenter messages are now translated and reviewed in an
isolated prototype. These include work in progress, completed repairs, changing
capacity, the1,000-gold proposal, acceptance/refusal and insufficient funds.
All28 native full-function cases pass, including both original window positions,
all pages, Yes/No/B, actual payment and capacity/flag outcomes, formatter bounds
and visible pixels. Entry and initial state are controlled; ordinary unlock,
completion scheduling and save persistence are not claimed. Gallery:
`build/carpenter-prototype/carpenter-validation/index.html`.
This family is staged after3,707 and is not yet in the root development build.

### Ordinary tutorial pickups verified on3,707 (2026-09-27)

A fresh English opening/name-entry checkpoint now continues with ordinary buttons
through all three tutorial floors. Read-only map-guided walking, native attacks
and acknowledgements produce14 actual floor-item pickups and14 complete English
tips, with no Japanese glyph leads in the monitored text renderer. The natural
cohort includes weapon, shield, bread, healing herb, room-damage scroll and
ranged staff tips. Fire-herb and level-herb tips remain covered by the explicit
controlled selector tests, not this natural run. No RAM/register substitutions,
item identity edits or progression overrides occur. Original arrival artwork is
deferred and outside this text check.

Evidence: `build/text-next/native-tutorial-walk/report.json` and its
`index.html` gallery, bound to ROM373287eefc1a7b3601d410666935c125184d67daed4f51a5aa5127b2e338ea01
and the current fresh-opening fixture hash/input provenance. An earlier route
policy stalled while waiting for a distant monster in a passage; it was corrected
to use ordinary movement/adjacent combat and the complete run was replayed.
This verifies the reported pickup context in normal tutorial gameplay, not
all later dungeons or a100% text-discovery claim.

### Newly identified fixed-block fire scene (staged)

A computed-address reader uncovered40 further passages outside the event banks,
covering Lulu/Tipper leaving to play, the monsters' attack, the wandering
swordsman's apprentice boast and Tessie inside the burning house. All40 have an
independent bilingual review with existing T2 character names. The private
512-byte ROM records preserve the original two-row window and full meaning;
no font or RAM changes. All56 native dispatcher checks pass, including maximum
player names, consecutive batches, every page, visible pixels and ABI/guard
checks. Gallery:`build/fire-scene-prototype/fire-scene-validation/index.html`.
This is staged beyond the3,707 candidate; the actual scene trigger, actor
animation and story progression remain separate. A second byte-identical source
block has no proven reader yet and is kept as an explicit discovery lead.

Two further direct travel questions were absent from the previous inventory:
entering the selected dungeon and confirming overwrite of saved village data.
Their six literal consumers are independently patched in the staged travel
confirmation prototype; all105 native branch/layout/name/Yes/No/B cases pass.
Gallery:`build/travel-confirm-prototype/travel-confirm-validation/index.html`.
Saved Japanese village names remain user/save data; the surrounding prompt is
English. Actual overwrite and travel outcomes are separate from these checks.
Together with carpenter and fire-scene text,51 new resources are staged for
integration after the3,707 cumulative candidate passes.

Custom-name layout research also confirms that the existing Japanese-label
layout already overlaps the inverse price column for an eight-glyph Japanese
pot name: visible name right151px versus price left121px, on the3,707 ROM.
The English category prototype requires additional layout work, including an
unpriced maximum pot row. English eight-letter names fit the measured inventory
rows. This is not sign-off for custom names or other list consumers. Evidence:
`build/text-next/custom-japanese-baseline/partial.json` and the previously
recorded custom-name prototypes. The later user clarification requires all item
names to stay on one line; the proposed additional-line solution is rejected.

Further menu discovery after that staging: the older town travel menus also
index the pointer region`14BE98..14BED0`. Only the previously audited castle,
home and square labels there are currently patched. `0804CB10` selects up to
six rows from eight town labels using stage/unlock masks; `0804CC70` selects
three dungeon rows with an independent heading. The unreviewed list includes
Adventurer's Inn, graveyard, old man's house, dungeon/cancel, and the separate
Mt. Fiery/Lost Forest/Toro Ruins source aliases. Their English must be measured
in the actual140px town and76px dungeon cursor-adjusted regions before
insertion, with all masks, selection and repeated reopening tested. This is
an active discovery lead, not an accepted menu family. Evidence:
`build/text-next/town-destination-menu.txt`, `town-destination-owners.txt`.
