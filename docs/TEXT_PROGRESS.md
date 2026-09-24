# Autonomous text-localization progress

All player-facing text is authorized for continued work without batch approvals.
The Torneko 3-derived rules in `LOCALIZATION_PLAN.md` apply, with Torneko 2's
Japanese as the source and measured T2 font/window budgets mandatory. Graphics
editing and auditions remain deferred until the text is complete.

## Accepted milestone and current candidate

The latest accepted milestone is **2,500 inserted resources**, ROM
`b08d16b210a30b6a313c3e18eeda3e22a8aa8e059c309f0e2811bd97494e189a`.
Its ROM/BPS/ledger/receipt are preserved in `build/accepted/2500/`.
The receipt is also `docs/english-services-validation.json`. Full cumulative
regression,85 unit tests,90 WebKit contexts/890 measurements, clean rebuild
and independent BPS application pass. This includes1,872 item cases,556 visible
static-notice cases,27 monster-condition cases and336 results/history cases.
Logs: `build/services/complete-build-2500.log`, `accept-2500.log`.
The earlier2,312 and2,255 milestones remain archived separately.

The latest **development candidate has2,610 inserted resources**, exported as
`build/torneko-2-english.gba` and `build/torneko-2-english.bps`. The matching
manifest pins source/ROM/patch hashes and independently verifies application.
ROM: `bb45e403ac90272571d925f204af3535fa3187b61807bcf7c34371bde8eebb61`.
It adds110 resources beyond2,500:33 result UI,nine history,two parent-menu,
64 adventure-record andtwo Password resources. Matching full regression is
running;85 unit tests pass. Isolated native checks include648 result UI,54
history,336 actor/cause,nine parent-menu,15 records andfour Password cases.

Unique reviewed sources are2,546/2,897 (87.9% language review), with348 still
untranslated andthree prior retained/component dispositions. Discovery now
includes the private results/history/record/password literals. This is separate
from inserted-resource counts and does not establish complete consumer or game
coverage. Work continues on remaining identified dungeon combat, priest/service,
input/skill/spell menus, item/category and retained-source investigation.

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

The source inventory now accounts for **2,821 unique sources**, with 2,448 language
reviews (including the integrated trap and static-notice catalogs).
Another 299 sources have draft wording, and 71 lack resolved drafts; two are
replaced by components and one is intentionally retained Japanese. It joins seven event banks, the 300-slot shared town table, 654 shared
system/combat/menu pointers, 221 item definitions and descriptions, both 141-ID
actor-name tables, 154 unidentified appearances plus their end marker, category
labels, five item-use announcement sources, ten well-level labels, and owned menu/UI reviews. Source aliases are deduplicated. Language
review does not establish insertion through every shared consumer; both actor
name tables are now inserted in the2,500 candidate, with raw result/history
consumer acceptance pending its cumulative regression. The new fixed history
Torneko field adds one explicitly identified source.

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

Open work includes remaining combat/system/town consumers, custom-named items,
scroll inscription, special item definitions, bakery and other services,
results/history actor-name consumers, warrior skills, nested pots and later
modes. Other text tables and unclassified scan leads still require discovery.
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
Full cumulative regression passed, including all72 synthesis/selector and170 Remi cases. The clean rebuild and final89-context/888-measurement WebKit check pass. ROM/BPS/ledger/receipt are archived in `build/accepted/2115/`.

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

The separate curse prototype adds two bindings and13 passing native cases. It
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
