# Cumulative English build

Run from the repository root with the documented toolchain installed:

```bash
./build.sh
```

The latest compiled outputs are also exported directly to the `build/` root:

- `build/torneko-2-english.gba` — patched English ROM for local playtesting.
- `build/torneko-2-english.bps` — BPS patch against the pinned Japanese ROM.
- `build/torneko-2-english.release.json` — matching source/ROM/patch hashes,
  inserted-resource count and development status.

Both `./build.sh` and `.venv/bin/python -m tools.build_english` update this pair
after compilation and an independent patch application reproduces the ROM.
The manifest is installed last; consumers should check both file hashes against
it. Failed patch-packaging validation leaves the previous exports intact.
Gameplay checks run after compilation; their failure does not roll back the
already exported development pair. Explicit compiler
`--output` directories are isolated and do not replace the default exports.
To re-export existing compiler output, run
`.venv/bin/python -m tools.export_release`. Native acceptance is recorded
separately in the matching validation receipt; these convenient latest-build
files remain development outputs while localization/playtesting is incomplete.
Archived accepted milestones under `build/accepted/` are preserved.
The [independent screen audit](DUNGEON_SCREEN_AUDIT.md) runs 11 bounded dungeon
and town scenarios without filtering readers to registered translations.
`tools.accept_screen_audit` checks matching build/tool/image hashes and writes
the scenario matrix and native gallery under `build/coverage-audit/`.
The [location-banner check](LOCATION_BANNER.md) covers all five dungeon-menu
text fields across 13 location labels and three command modes, including
cancellation and reopening. It rejects unexpected Japanese glyphs on that
screen, which earlier resource-specific menu checks missed.

The [Floor-menu check](FLOOR_MENU.md) also runs from `build.sh`. It selects
the empty Floor command and covers item, trap, stairs and related status-refusal
panels through cancellation and reopening. This closes a separate ordinary
first-floor path omitted by the earlier root-menu audit.

The [reader-path checks](READER_PATH_AUDIT.md) enumerate all four direct modal
callers and verify seven repaired timer-expiry bindings. The native expiry gate
runs44 cases: all20 recovered timer branches, maximum saved/transformed names
and simultaneous expiries. It rejects unexpected Japanese, clipping, incorrect
formatting, buffer corruption and ABI changes. These checks run from `build.sh`;
their scope remains the identified readers and controlled timer states.

The [caller repair gate](CALLER_COVERAGE_AUDIT.md) also runs from `build.sh`.
It reaches every one of the 55 repaired bindings in 308 native cases, checks
complete screens, exact format/copy bytes, guards and ABI, and exercises field
limits and repeated menu use. It rejects incomplete routes. The continuation
now closes the20 outstanding leads, including the projectile probes, and nine
additional caller failures. Its separate110-case gate exercises native source/
field producers, narration callbacks, saved-name limits and choices. The80-load
item-definition consumer audit also runs from `build.sh`, and the blacksmith
transaction verifier now rejects unexpected Japanese glyphs. These gates do
not establish complete caller discovery.

The [English custom-item gate](LOCALIZATION_CLOSURE.md) runs 30 native cases
through `tools.verify_custom_items`: six nameable categories, English name
widths, prices, counts, markers, action restoration and storage round trips.
Japanese custom-name width is outside this acceptance scope; saved-name bytes
and buffer bounds remain checked. The caller/event investigations and further
ordinary gameplay audits have separate reproduction commands in
[EXPLORATION.md](EXPLORATION.md).

The build starts from the pinned Japanese ROM and retained source assets. It
adds the selected Torneko 2 compact font and [original-sized early menus](MENU_LAYOUTS.md), English name entry, opening dialogue, resume/menu labels,
first-dungeon tutorials, first-castle conversations, the first travel menu, and
the reviewed story catalogs and bounded special formatters in one `RomBuild`
allocation/patch ledger. It also includes the approved Shiren arrival cards and
[title plus five background logos](TITLE_INSERTION.md), using frozen source
assets and checked graphics ownership. It does not depend on a prior
proof ROM, generated resource dump or emulator checkpoint. Source ROM/save files
are preserved. ROM, BPS and report files are staged and verified before replacing
generated outputs; the directory's existing playtest saves are retained.

Outputs:

- [English ROM](../build/english/torneko-2-english.gba), 16 MiB.
- [BPS patch](../build/english/torneko-2-english.bps), verified by applying it to
  the pinned Japanese base and comparing every output byte.
- [Build ledger](../build/english/build.json), including allocations, expected
  original bytes, patch owners, hashes and helper source.
- [Native acceptance report](../build/english/name-entry-validation/report.json),
  normal input schedules, screenshots and isolated disposable saves.
- [Cumulative acceptance receipt](english-services-validation.json), linking the
  ten gameplay/text reports, four additional menu reports, source verification
  and reproducible build.
- [Typography correction gallery](../build/typography/index.html), matching numbers,
  normal item spacing, three-pixel word spaces and attached bank colons.
- [Latest native preview](../build/english/mansion-preview.png).
- [Font audition and menu budgets](../build/font-audition/index.html), including
  original-window overflows, passing approved labels and native geometry evidence.

The [English opening batch](OPENING_ENGLISH.md) includes both choice branches,
the complete opening flashback, initial menu labels, resume prompts, stair
options, the first three floor tutorials, the King's first audience and five
nearby NPCs, including both answers to the guard, plus the travel question and
player's home label. The [home-return batch](HOME_RETURN.md) adds the first
evening/morning, sale proceeds and three village NPCs, including both Ed choices.
The [home-book/banker batch](HOME_BOOKS.md) adds all ten tips, the blue-book
actions/save flows, the first banker choices and mansion entrance. The
[mansion quest batch](MANSION_QUEST.md) adds safe recovery, both family questions,
the next morning and bank opening. Subsequent service work includes 206
non-placeholder item names, reviewed descriptions, bank rewards, repaired
storage, bakery purchases, dungeon actor names and the currently checked combat
and status messages.

The archived **2,500-resource milestone** is an earlier accepted build. Its stable
ROM, BPS, ledger and receipt are retained in `build/accepted/2500/`. Full
regression,85 unit tests,90 WebKit contexts/890 measurements and byte-identical
ROM/BPS rebuilding pass. This includes1,872 item cases,556 visibly verified
static notices,27 monster-condition cases and336 result/history cases.
Earlier milestones remain archived. The following historical candidate added110
result UI/history/menu/record/Password resources; their matching cumulative checks are recorded
separately. See [TEXT_PROGRESS.md](TEXT_PROGRESS.md) for current coverage.
Native checks distinguish controlled renderer/getter/formatter calls and state
substitutions from ordinary gameplay routes.

Current remaining work and accepted/development build identities are maintained
in [TEXT_PROGRESS.md](TEXT_PROGRESS.md). A completed known catalog does not
establish complete game coverage. Approved title/background and arrival graphics
are now inserted; their validation and remaining natural-route gaps are recorded
in the corresponding graphics guides.

Individual commands:

```bash
# Assemble and verify BPS output without replaying gameplay.
.venv/bin/python -m tools.build_english

# Rebuild in memory and verify name entry, real saves and cold gameplay loading.
.venv/bin/python -m tools.verify_name_entry

# Both English opening branches and all 90 bank-zero text getter targets.
.venv/bin/python -m tools.verify_opening_dialogue

# Resume, remaining tutorials, and Stay/Descend stair outcomes.
# Uses the disposable native save generated by verify_name_entry above.
.venv/bin/python -m tools.verify_first_dungeon

# Continue its generated floor-three checkpoint to the first audience;
# also probe seven-glyph English/Japanese name substitutions separately.
.venv/bin/python -m tools.verify_castle_arrival

# Six normal-input NPC routes from that audience-completion checkpoint.
.venv/bin/python -m tools.verify_castle_conversations

# Travel labels, worst-case name widths, native cursor, Cancel and Home.
.venv/bin/python -m tools.verify_destination_menu

# First home scene, sale proceeds, Ed choices, 214 getters per ROM and name/amount probes.
# Standalone default uses the retained Japanese home research checkpoint.
.venv/bin/python -m tools.verify_home_return

# Shared town loader: two native loads, all 300 pointers in each ROM.
.venv/bin/python -m tools.verify_town_text

# Red/blue books, banker branches, mansion entry and save/cold-load acceptance.
# Requires the fresh Japanese book trace generated by build.sh.
.venv/bin/python -m tools.verify_home_books

# Original mansion route and native suspend, then English cold continuation,
# safe recovery, family branches, bank opening and name-width probes.
.venv/bin/python -m tools.trace_mansion
.venv/bin/python -m tools.verify_mansion

# Later-story renderer checks, then actual ROM-bank getter resolution.
.venv/bin/python -m tools.verify_prose_preflight --cumulative
.venv/bin/python -m tools.research_event_relocation --cumulative

# Specific native formatting consumers, with bounded temporary storage.
.venv/bin/python -m tools.verify_floor_progress_prototype --cumulative
.venv/bin/python -m tools.verify_well_level_prototype --cumulative
.venv/bin/python -m tools.verify_village_prose_prototype --cumulative
.venv/bin/python -m tools.verify_medal_prototype --cumulative

# Early menu geometry/parent checks and font comparison; also in build.sh.
.venv/bin/python -m tools.audit_menu_layouts
.venv/bin/python -m tools.verify_compact_font --output build/font-audition/native
.venv/bin/python -m tools.audition_fonts

# Original toolchain/base-game checks and the unit suite.
./validate.sh
```

`build_english` and `verify_name_entry` accept `--output DIRECTORY`, allowing
validation from clean generated output without deleting research artifacts.
The gameplay commands above depend on the disposable save/checkpoints produced
by the preceding commands; `./build.sh` runs them in that order. ROM construction
itself has no checkpoint dependency. Before home acceptance, the build script
recreates a Japanese castle/destination/home chain under
`build/english/home-validation/japanese-*`, using the native save generated by
`verify_name_entry`, then passes that fresh fixture to the bank-one getter checks.
Historical home-research checkpoints are not required by `./build.sh`.
The mansion stages also regenerate their Japanese prefix and real dungeon
suspend. English acceptance cold-loads that battery and continues through 6F and
the return scenes; it does not claim an uninterrupted English 1F–6F run.
Native tests operate on separate temporary cartridge/save pairs. To play in
desktop mGBA, open the generated English ROM; it uses its own English save file
beside the build, separate from the supplied Japanese files.

Names support uppercase/lowercase English, digits and basic punctuation, with
seven characters in the shared village/player editor. The original Japanese
keyboard pages remain available. The save format is unchanged, and a native
Japanese save passes import and resume in the English build. New English IDs
require the English build to display correctly; do not pair those saves with
the original Japanese ROM. See [NAME_ENTRY.md](NAME_ENTRY.md) for tested scope.

The service pipeline additionally runs `verify_service_ui`, `verify_bank`,
`extract_items`, `verify_items`, `trace_storage`, `verify_storage` and
`verify_numeric_font`. The storage recipe regenerates a real Japanese book save
from the earned bank-opening checkpoint, including the castle prerequisite quest.
English storage checks cold-load it, perform ordinary transactions, save a deposit
and cold-load/withdraw both naturally acquired items. See
[SERVICE_BATCHES.md](SERVICE_BATCHES.md) for exact coverage and exclusions.

Cumulative status/queue/trap/monster probes reuse the shared ordinary-input
6F service checkpoint, with per-family snapshots and source/input provenance.
Before enabling reuse, the independently produced2,255 service, status and queue
fixtures were compared: core state, battery and held keys were byte-identical.
The state hash was981c0f18f8f1eb3e1bab1427d0856e85e9ea9e734e16f74a5ead2754217302b3.
This removes repeated setup replays; each actual native case still runs on the
current ROM with its original checks. Isolated prototypes retain separate setup.

Item cohorts can use `tools.verify_items --item ID --output DIRECTORY` with
separate output directories. All assertions are identical to the full run;
each successful case is written atomically after its captures. Independent
workers preserve their complete reports and only stage matching-ROM, fixture,
verifier/font-hash and capture evidence. The full run still requires the exact
complete case set and revalidates all cache keys/captures. No concurrent worker
uses the main verifier's output directory while executing cases.


The computed wind and town-overview checks also run from `build.sh`:
`tools.verify_wind` covers six native wind-stage/name cases;
`tools.verify_town_overview` covers the nine separate map labels, original
selector/navigation code, window centring, widening, repeated redraws and vacated
backgrounds. Their controlled setup and natural-route limits are recorded in
[LOCALIZATION_CLOSURE.md](LOCALIZATION_CLOSURE.md). That document also distinguishes
the completed3,801 full-suite baseline from the final3,811 affected checks and
byte-identical unchanged-resource proof.

The approved event repairs have a separate 3,813-resource receipt in
`build/event-stub-repair/receipt.json`. `tools.verify_event_repairs`, now in
`build.sh`, checks eight original selector/choice/flag branches, English reads,
glyphs, visible pixels and caller guards. The before/after ledger comparison
accounts for relocation of existing pointers and exactly two new event texts;
it does not describe prior allocations as byte-identical at their old addresses.
See [EVENT_STUB_AUDIT.md](EVENT_STUB_AUDIT.md) for editorial provenance and
controlled-route limits.
