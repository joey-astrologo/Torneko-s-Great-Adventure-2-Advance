# Dungeon UI, banking, items and services

The original four batches below are completed milestones. Current service
coverage is summarized here and in [the coverage matrix](COVERAGE_AUDIT.md);
the later matrix supersedes their initial exclusions. They were authorized as
continuous work after approval of the corrected early menu gallery. All English
must fit measured pixel and byte budgets; native
spacing remains part of acceptance. The Torneko 3 terminology/prose rules in
LOCALIZATION_PLAN.md remain authoritative.

1. Completed the Option submenu, dungeon status labels and further observed item
   commands, including child help/prompts and toggle/selection behavior.
2. Translated bank transaction formats and prompts; exercised deposit, withdrawal,
   cancellation, insufficient funds and overflow warnings on disposable saves.
3. Extracted item identities/descriptions and inserted a representative reviewed set.
   Established complete row budgets with markers, quantities, enhancements,
   unidentified names and prices, separately from description wrapping.
4. Reached and audited the first populated shop/storage services, translated the
   verified subset and recorded untested states without inferring unreachability.

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

## Current acceptance (2026-10-03)

The current ROM is identified in [the matrix](COVERAGE_AUDIT.md). The cumulative
[service receipt](english-services-validation.json) requires 2,006 item cases,
166 alias cases, 12 core bank cases, 21 bank-reward cases, three bank-persistence
cases, 13 bakery cases, three storage transaction cases and ten storage-service
cases. English custom names additionally pass 30 cases. Blacksmith, Gaibara, Remi,
mayor and other service families have their own case lists in that receipt.
These are bounded families, not complete service/quest coverage.

## Ordinary continuation and earlier cohorts

See [CALLER_FOLLOWUP.md](CALLER_FOLLOWUP.md) for the October 3 continuation:
ordinary gameplay now completes the Cemetery quest, unlocks the bakery and
buys Magic bread for 400G. Its item and 1,329G balance survive Save and continue
and a cold load on ROM `452394042d5be4c83adb79fa35eaba5ca261514533b2162604032b9561e44304`.
Ten storage-service cases also cover the second capacity-warning caller when
two selected items exceed one free slot. Controlled setup remains distinguished
from ordinary quest and purchase inputs.

Earlier [TEXT_PROGRESS.md](TEXT_PROGRESS.md) milestones covered the first 206
identified names, reviewed descriptions, storage child prompts, bank rewards/
persistence, controlled bakery purchases, 892 story passages and holy-flame text. All 154 unidentified appearances and further player-effect/
item-use messages now pass separate combined-ROM checks. Earlier counts and
exclusions below describe the original service milestone and are superseded
where explicitly covered. Ordinary bakery unlocking and saved purchase are now
covered by the October 3 route above.

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
catalog and native prototype/cumulative checks. The additional 15 special/reserved definitions, English custom naming and
inscription input are now integrated, with separate recorded consumer checks.

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

At that early checkpoint the bakery is unavailable and the baker is at the
haunted graveyard. Later receipts cover bakery transactions and ordinary unlocking,
storage sale/capacity/filled-pot prompts, bank rewards and saved transfer persistence.
They are no longer pending merely because the first service batch excluded them.
Unvisited upgrade/mode states and other consumers remain separate investigation
work. Trace their callers and use targeted assisted scene checks; an ordinary
quest replay is not required to inspect or localize those paths.

## Reproduction

`./build.sh` now rebuilds and checks all four batches, regenerates the Japanese
storage route/save, and writes the galleries. `./validate.sh` covers the unit and
toolchain checks. After generating the local browser audition checks, run
`.venv/bin/python -m tools.accept_services` to pin the cumulative reports and
artifacts. Each report and gallery is tied to its ROM SHA. Original supplied ROM
and save hashes remain unchanged.
