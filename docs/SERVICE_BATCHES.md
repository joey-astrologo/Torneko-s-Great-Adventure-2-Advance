# Dungeon UI, banking, items and services

Authorized as four continuous batches after approval of the corrected early
menu gallery. All English must fit measured pixel and byte budgets; native
spacing remains part of acceptance. The Torneko 3 terminology/prose rules in
LOCALIZATION_PLAN.md remain authoritative.

1. Finish the Option submenu, dungeon status labels and further observed item
   commands. Include child help/prompts and toggle/selection behavior.
2. Translate bank transaction formats and prompts. Exercise deposit, withdrawal,
   cancellation, insufficient funds and overflow warnings on disposable saves.
3. Extract item identities/descriptions and insert a representative reviewed set.
   Establish complete row budgets with markers, quantities, enhancements,
   unidentified names and prices, separately from description wrapping.
4. Reach and audit the first populated shop/storage services, translate the
   verified subset and preserve explicit unreachable/untested coverage.

Each batch records sources, reviewed wording, ownership, width/byte budgets,
native captures and checks. Controlled state probes remain distinct from routes
reached through ordinary inputs. Original ROM/save files remain protected.

## Research notes

- Option's 冒険の中止 means **Give up**, not Suspend: the child prompt warns
  that all carried items will be lost. English must retain that warning.
- Bank overflow paths explicitly ask whether excess gold may be lost. Preserve
  the warning and yes/no meaning; do not silently change original mechanics.

## Original service milestone (historical)

[Native review gallery](../build/services/index.html) ·
[Typography before/after](../build/typography/index.html) ·
[Acceptance receipt](english-services-validation.json)

| Batch | Inserted resources | Native checks |
|---|---:|---|
| Dungeon UI and additional commands | 23 UI resources; early-menu total now 25 | Six Option routes; status, help, prompts and restored toggle values; existing early-menu route/edge/action checks |
| Core bank transactions | 11 | Twelve cases: ordinary deposit/withdrawal/cancel/empty bank, plus explicitly controlled balance and overflow cases |
| First item cohort | 17: eight names, seven descriptions, two category descriptions | 52 item cases, including four naturally carried items; 286 broader controlled item/state probes |
| Repaired storage subset | 4 resources across five town-table slots | Three ordinary-input transaction/marking/cancel cases, plus saved deposit and cold-reload withdrawal of both items |

That milestone contained 184 reviewed text resources across these catalogs
and the existing 104-resource dialogue batch. Name-entry/start-label resources
are tracked separately. No whole-game completion percentage is claimed.

## Widths and typography

All inserted English must fit the chosen font's measured pixel and byte budgets.
Full rows include markers, quantities, suffixes, prices and substitutions.
Window fit never justifies compressed or overlapping text by itself.

The selected Torneko 2 font remains. The visual review changed Sword to Weapon,
connected native number formatters to matching compact digits, restored normal
English item spacing, narrowed authored word spaces to three pixels, kept price
backgrounds continuous and attached the bank colons to their labels. See
[TYPOGRAPHY.md](TYPOGRAPHY.md) for source codes and native checks.

| Current context | Pixel budget | Storage constraint |
|---|---:|---|
| Main commands / item actions | 34 / 36 | 64-byte root; 256-byte actions plus 64-byte scratch |
| Option labels | 65 | Formatted rows remain within the original observed 36 bytes |
| Status labels, left / right | 61 / 52 | Three native 64-byte buffers; numeric columns preserved |
| Bank label plus colon | 57 (x12..69) | 384-byte formatted bank buffer |
| Bank amount editor | 112; eight 12px selection cells | Compact six-pixel glyphs centered in native cells |
| Item base-name reserve / complete row | 80 / 162 | 31-byte name / 64-byte complete formatted row, including NUL |
| Info descriptions / ordinary prose | 216 per line | Info output checked at 256 bytes; other formats separately bounded |
| Repaired-storage menu columns | 100 each (x12..112, x124..224) | Four rows; direct ROM stream, no new RAM buffer |

Option's bounded single-byte spaces remain six pixels; ordinary authored English
uses three-pixel spaces. Unknown contexts still block their own insertion.

## Latest continuation

See [TEXT_PROGRESS.md](TEXT_PROGRESS.md) for the accepted 1,676-resource milestone
and current 1,848-resource candidate. All 206 identified item names and their
reviewed descriptions, storage child prompts, bank rewards/persistence, controlled
bakery purchases, 892 additional story passages and controlled holy-flame text
are covered there. All 154 unidentified appearances and further player-effect/
item-use messages now pass separate combined-ROM checks. Earlier counts and
exclusions below describe the original service milestone and are superseded
where explicitly covered; ordinary bakery unlocking remains open.

## Extraction correction

The item-definition audit uses 221 records ending at ROM 00143054. Earlier
289-attempt reports mistakenly included adjacent disguise data as three extra
item IDs and used an inscription bit as identification. The corrected sweep
uses 286 cases and actual known-name flags, with no excluded IDs. Item extraction
enumerates 221 identities and 222 description pointers: the extra pointer is an
invisible-item fallback. Enumeration and synthetic probes are separate from
natural acquisition and translation completeness.

The original eight-name cohort has expanded to all 206 non-placeholder identified
names in `translations/items-review.json`; terminology evidence and provisional
statuses remain in the glossary. The 154 appearance names have their own reviewed
catalog and native prototype/cumulative checks. Custom naming, inscriptions and
special records remain separately scoped.

## Storage provenance and limits

The warehouse is locked at the bank-opening checkpoint. Ordinary play reaches
the blacksmith's castle quest and retrieves the holy flame using a naturally
found Lightning staff. After the return scenes, the warehouse opens with 20 slots.
`config/routes/storage-japanese.json` records 599 inputs from the bank-opening
checkpoint through the repaired blue-book menu and a real book save.
`tools.trace_storage` reproduces the same battery hash. No quest flags, inventory
records or balances are injected on this route.

English storage validation cold-loads that save. The carried bread/wand can be
stored singly or together, marking can be cancelled, and the bread can be taken
back out. An English save with both items deposited is cold-loaded and both items
are withdrawn again. Stored item sorting changes their list order; the test
selects the observed bread row rather than assuming it is first.

The bakery remains unavailable at this story point: the native cutscene places
the baker at the haunted graveyard. Bakery transactions, storage sale/full-capacity
and filled-pot prompts, warehouse upgrades and later mode behavior remain explicit
follow-up work. Their root command labels being English does not approve those
child flows. Bank gift/reward text and saved bank-transfer persistence also remain
outside this batch's twelve transaction cases.

## Reproduction

`./build.sh` now rebuilds and checks all four batches, regenerates the Japanese
storage route/save, and writes the galleries. `./validate.sh` covers the unit and
toolchain checks. After generating the local browser audition checks, run
`.venv/bin/python -m tools.accept_services` to pin the cumulative reports and
artifacts. Each report and gallery is tied to its ROM SHA. Original supplied ROM
and save hashes remain unchanged.
