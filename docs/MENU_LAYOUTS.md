# Torneko 2 font and original-sized early menus

The four font/layout batches restore **Torneko 2's compact English font** as the
build default and localize the first audited dungeon menus. The original compact
capitals/digits and authored matching lowercase remain unchanged. Torneko 3's
font is retained for comparison; it is not needed for these panels.

[Native before/after gallery](../build/menu-resize/index.html) ·
[Interactive font audition](../build/font-audition/index.html) ·
[Per-font budgets](../build/font-audition/contexts.csv) ·
[Dynamic name budgets](../build/font-audition/dynamic-budgets.csv) ·
[Acceptance receipt](english-menu-validation.json)

## What is inserted

The existing 104 reviewed dialogue/menu resources remain in the cumulative
build. A separate [reviewed menu catalog](../translations/menus-review.json)
adds 16 resources: nine action labels and seven main-menu format fragments.
They do not inflate the earlier extraction catalog's native-source count.

- Main commands: Items, Floor, Option; conditional Stairs/Trap and the
  Skills/Spells rows retain their original selection and colour behavior.
- Common item/ground actions: Shoot, Equip, Remove, Drop, Swap, Throw, Eat,
  Take and Info. **Info** translates 説明, the item information action.
- Other action labels and item names remain Japanese. Only the dungeon action
  builder uses the new copied label table; the other three consumers keep the
  original table and their original budgets.

## Geometry and storage

| Region | Original | Current T2 build | Text allowance |
|---|---|---|---|
| Main commands | 40 px wide | Original 40 px, x=8 | 34 px after cursor |
| Item/ground actions | 40 px at x=192 | Original 40 px, x=192 | 36 px after cursor |
| Inventory parent | 168 px at x=8 | Same | 162 px including all fields |

User review rejected the previous wider panels because their borders interfered
with adjacent windows. Text fit and restoration had passed but did not establish
acceptable spacing. The current build removes all three geometry patches and
uses the approved labels Swap (24 px), Info (22), Floor (26), Option (31), Remove
(36) and Take (24). Remove exactly uses the action text allowance. The dungeon-name
banner and item list keep their full original sizes.

Native descriptors now verify **8 px between outer borders** for main/banner and
item/action panels (11 checks across seven routes). The gallery includes the
previous wide layout beside the corrected layout, plus the original Japanese
comparison. Parent restoration is checked separately after cancellation.

Shorter labels do not eliminate the need for the text-buffer fixes. The action builder previously had a
64-byte combined string and a separate 64-byte temporary. It now has **256 +
64 bytes** in its own stack frame (192 extra stack bytes). The worst seven-row
English action string, including disabled colours, needs at most 113 bytes
including the intermediate trailing newline; the final seven-Remove stress
string is 112 bytes. The main builder's stack grows by 64 bytes, providing a
64-byte combined command region and a relocated temporary; its longest compiled
four-row command string is 58 bytes. No permanent RAM or save-format allocation
is added. Checked ROM patches and the shared allocator own all modifications.

## Expanded audit and validation

The native original bank audit now includes the amount editor: eight digits in
112 pixels, a 99,999,999 bank cap, 52 pixels before the verb's amount column,
and a 384-byte existing bank formatting region. Natural entry/cancellation and
controlled zero/one/maximum balances pass. At maximum, original bank menu ink
ends at x=166 of 176; amount-entry ink ends at x=105 of 112. Native digits still
use the original font, independently of either English font.

Evidence distinguishes normal play from synthetic probes:

- Seven ordinary-input menu routes from a cold-save-derived English checkpoint;
  nine parent restoration checks compare against the state **before first open**.
- Six ordinary-input action cases check equipment flags, Info, dropping,
  picking up and Swap, including a shorter input schedule that exercises
  repeated debugger observations during drawing.
- Twelve controlled edge cases cover a full **20-item** inventory and third
  page, full-inventory ground pickup refusal, seven disabled rows, and three
  main-menu modes crossed with ground/stairs/trap labels. Alternate-mode UI
  rendering is not a claim of completed later-mode gameplay. Full inventory
  leaves Take selectable; its native action refuses the pickup without
  changing carried or ground items. It is not assumed to grey the label out.
- 289 controlled item/state attempts cover 224 item IDs plus selected equipped,
  cursed, unidentified, priced and maximum-field variants. 287 produce action
  panels; IDs 222/223 do not in this synthetic setup and remain explicit
  exclusions. The matrix validates native English/fallback glyphs, string
  bounds, stack restoration and parent restoration. These are not naturally
  acquired items or proof of every legal combination.
- All 95 font glyphs, existing name/save/opening/castle/home/books/mansion
  regressions and the 44-test suite are checked on the cumulative build.
  Clean ROM/BPS reproduction is pinned in the acceptance receipt.

The glyph verifier validates each sampled prepared bitmap and cursor advance.
An interrupt may produce a repeated observation of the same pre-instruction
breakpoint; the verifier now counts once per glyph draw while still validating
both observations. It does not discard a mismatched glyph or missing draw.

## Remaining coverage

The early families above are accepted; whole-game menu-layout sign-off remains
open. Populated shop/storage services, repaired storage, nested pot contents,
other modes' gameplay and complete English item-name formatting need their own
native routes and reviewed wording. Existing inventories exercise original
Japanese names only. Bank English transaction text and committed transactions
are not included. Item-specific action choices beyond the nine translated
labels remain Japanese, in the original-sized shared panel.

Seven-character player names remain supported, including `Torneko` (41 px in
T2's font). The audition separately reserves 98 px for seven widest original
Japanese glyphs; with the 42 px T2 possessive suffix, the existing 140 px travel
text region is exactly occupied. Dialogue keeps its independent 216 px budget.

## Reproduce

```bash
./build.sh
./validate.sh
.venv/bin/python -m tools.review_menus
.venv/bin/python -m tools.review_mansion
bash tools/verify_font_audition.sh
```

`build.sh` includes the natural menus/actions, controlled edges/item matrix,
original bank audit, glyph validation and audition generation. Prototype-only
research can be reproduced with `tools.probe_menu_resize` without `--english`.
Keep acceptance logs under `build/menu-resize`, then run
`tools.accept_menu_layouts` to pin a reviewed build. Generated artifacts are
local; the supplied original ROM and save remain unchanged.

## September 19 service and typography update

The current build has 25 early-menu resources (18 action IDs plus seven root
formats), 23 Option/status resources, 11 core bank resources and a 17-resource
item cohort. [Service batches](SERVICE_BATCHES.md) track these separately from
the earlier acceptance snapshot above. The original early-window geometry is
retained. [Typography](TYPOGRAPHY.md) documents Weapon, matching compact numbers,
normal English item spacing, three-pixel word spaces, continuous inverse price
backgrounds and attached bank colons. Current bank label/colon budget is 57px
(x12..69); the original Japanese verb column measured earlier remains 52px.

The former 289 controlled item attempts included three non-definition records
and used the wrong identification flag. They are historical, superseded by
286 cases across the correct 221 definitions, with no exclusions. Passing these
synthetic states still does not establish natural acquisition or later-mode
gameplay. The first eight English names additionally have 52 detailed native
row/Info checks including price-column separation and parent restoration.

## Additional action consumers (current candidate)

The1,934-resource candidate covers all39 nonempty IDs in the existing private
IDs0..43 action copy. Their labels remain within36px. A separate contained-item
producer uses that copy with a checked256-byte output and64-byte scratch buffer;
its original40px window,4px inset and8px outer-border gap are preserved. Twelve
grouped enabled/disabled cases per producer check every label, three open/cancel
cycles, selection, parent pixels, native glyphs and stack/register guards.
Availability in those grouped cases is controlled, not an ordinary unlock claim.

The full original action table has45 slots, not44. Its final ID44 is the town
inventory discard command. That separate consumer uses a private45-slot copy
with only View/Trash/Info changed. The town menu starts at6px, leaving34px;
Trash measures29px, while Discard would be38px. Ten native controlled-invocation
cases validate selection, cancellation, View/Info, empty inventory and both
answers to normal/filled-pot discard confirmation. The filled-pot warning
explicitly includes all contents. Original256-byte output and window geometry
remain unchanged. Ordinary town menu access remains separate.

Current cumulative galleries, generated only from matching-ROM passing reports:
`build/english/additional-action-validation/index.html`,
`build/english/child-action-validation/index.html`, and
`build/english/town-action-validation/index.html`.
The font audition adds each enabled controlled label group with its measured
region and screenshot; the second font remains a comparison asset.

## Results, records and Password text

The owned result/history/records families retain their original geometry.
Result body rows have212px after their largest inset; the trip heading has224px.
Weapon/Shield/Ring include the complete existing item formatter, with64-byte
item fields and fixed price cells ending at210px in the224px window. The75
reviewed equipment identities pass eight states each; custom names/inscriptions
remain separate. High-score history has56px heading,72/108/44px rank/score/floor
columns,144px empty-message panel and224px body; native output is128bytes.

The parent records menu has64px width and58px conservative text budget for
Scores/Records/Password. Two- andthree-option variants preserve cursor wrap,
selection on return and repeated child reopening. Its report folder is
`history-menu-validation`, distinct from early `menu-validation`.

Adventure records have224px single-line rows, six per page. The firsteight
numeric fields retain native right alignment; labels stop at least6px before
the widest supported field. Complete rank titles fit with the Arms merchant
level label in224px. Password retains64/128/224px heading/code/notice windows;
the notice usesfive four-row pages and216px line budget. The generated kana
code is protocol data and remains unchanged. See the compiler ledgers for byte
bounds and native galleries for final pixels and state coverage.
