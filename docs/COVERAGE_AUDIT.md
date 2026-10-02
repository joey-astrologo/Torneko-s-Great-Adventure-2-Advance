# Coverage assessment after the missed menu banner

**Whole-game localization coverage is unverified. There is no defensible
whole-game completion percentage yet.** The user-reported Japanese location
banner showed that translated catalog entries, inserted resources and passing
family tests can coexist with an untranslated ordinary gameplay screen.

The visual review also missed that text. More passing cases from the same
selected-resource checks would not resolve this coverage problem.

On 2026-10-02 the user found another ordinary first-floor failure: selecting
Floor on an empty tile displayed Japanese. The earlier independent screen
matrix omitted that selection. The [Floor-menu correction](FLOOR_MENU.md)
adds this route and related item/trap/stairs/refusal states to `build.sh`;
its unfiltered audit rejects the old ROM. This repeated miss reinforces that
unvisited states remain gaps even when the root menu has passed.

The [subsequent code-path audit](READER_PATH_AUDIT.md) enumerates all four direct
callers of that modal and found an additional empty-inventory reader, now fixed.
It also confirmed seven Japanese status-expiry messages through20 automated
timer probes. All seven are now fixed;44 native cases cover all20 branches,
maximum saved/transformed names and simultaneous expiry. The old ROM still
fails exactly those seven baseline cases. The shared-reader triage now retains
already-reviewed sources; an inserted translation is not a disposition for
every caller of its original source.

The continued [caller audit](CALLER_COVERAGE_AUDIT.md) found 54 untranslated
caller sites, 31 more than its first pass. Eight scenarios reach failures using
normal buttons after controlled setup, now including marked Storage-pot actions
and trap discovery. Other findings use explicit native handler/state probes.
All 54 are now repaired, plus the recognition-blocked placeholder; 55 bindings
pass308 native cases. The continuation has now reproduced and fixed all 20
outstanding leads and nine additional failures;110 controlled cases and 13 full
blacksmith exchanges pass. The copied refusal is confirmed English. The expanded
15-reader scan has no remaining resolved direct Japanese binding, while529
arguments remain beyond its static resolution. Those limits are not a defect count.

## What the existing figures establish

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| 3,527 of 3,638 catalog sources reviewed (96.9%) | Review progress within the identified catalog, excluding 28 accounted-for retained/component sources | Percentage of playable text in English, all readers redirected, or all text discovered |
| 3,785 text resources inserted | English resources present in the compiled build under checked ownership | Every place that displays those concepts actually uses the inserted English |
| 111 unresolved catalog sources | Known source-level investigation backlog | The complete remaining work; missed consumers of already-reviewed sources are additional gaps |
| Family test passes | The specified inputs, formats, rendering paths and bounds passed on the recorded ROM | Every visible field in the screen or every state/route in the game was checked |
| Controlled native probes | Tested selectors and arguments render through the native functions | Ordinary access, unlocking or full playthrough coverage |
| ROM/BPS reproduction | Deterministic packaging and correct patch application | Language coverage |

## Concrete failure and correction

`TextChecks` starts validation for registered resource pointers.
`MenuChecks` can ignore an unrecognized reader when no tracked stream is active.
`UiChecks` validates known formatting resources. These are useful insertion
tests, but their selected input lists cannot establish complete screen coverage.

The dungeon location names were already reviewed and inserted for results and
history. The separate main-menu reader still used the Japanese table. The
[banner correction](LOCATION_BANNER.md) fixes that reader and adds a complete
five-field check, including rejection of unexpected Japanese glyphs. It rejects
the previous ROM. That stronger check currently covers this menu family; it
must not be described as a game-wide coverage gate.

## Required independent audit

1. Inventory complete screens and their states from ordinary gameplay. Record
   every visible label, header, footer, help panel, message and dynamic field,
   including text outside the currently selected resource catalogs.
2. Observe text readers and glyph output without first filtering to known
   translated pointers. Unaccounted-for readers and Japanese output become
   explicit failures of that screen's coverage check. Any permitted exception,
   such as an optional kana keyboard or a player-entered Japanese name, needs
   a specific context and recorded reason; no blanket Japanese exclusion.
3. Trace each missed reader to its sources and other consumers. A reviewed
   translation does not close the issue until the affected display paths use it.
4. Inspect complete native screenshots and transitions. Reader traces alone
   miss baked-in artwork and other graphics paths. Keep original image evidence,
   input schedules, build hashes and the exact ordinary/controlled distinction.
5. Publish a screen/route matrix with demonstrated English fields, remaining
   Japanese, unaccounted-for text and unvisited states. Close issues with an
   independently reproduced before/after failure, not a higher test count.

Audit ordinary early-game UI and the previously reported dungeon/pickup text
first, then town/services, later dungeons/modes and the ending. The user's earlier
Japanese pickup/message report remains unresolved at the scenario level; existing
passing pickup probes do not disprove it. Reuse retained saves and routes before
asking the user for additional investigation.

## Current audit status

| Area | Independent complete-screen coverage status |
|---|---|
| Dungeon root menu and location banner | Five text fields checked across 13 location selectors and three command modes, including reopening. Natural first-floor case; remaining selectors/modes are controlled. Broader gameplay states remain separate. |
| Floor command and related modals | 14 scenarios cover empty Floor/inventory, a dropped item, stairs, controlled trap/class/status states and repeated cancellation. Four ordinary routes, ten controlled cases; all four direct modal callers statically checked. See [reader-path audit](READER_PATH_AUDIT.md). |
| Status expiry | All20 recovered timer branches display English after the seven-message repair;44 native cases also cover maximum saved/transformed names and simultaneous expiries. Whole-stream audit plus exact repaired-message bytes, guards, ABI and glyph pixels. Ordinary status acquisition and other handlers remain separate. |
| Other callers of translated sentences | 54 confirmed failures repaired plus the item placeholder; 55 exact bindings pass 308 cases. The 20 earlier leads and nine additional failures are now fixed and covered by 110 continuation cases;13 blacksmith exchanges also pass. Eight cases use normal buttons after state setup; see [caller audit](CALLER_COVERAGE_AUDIT.md) for controls, source gaps and unresolved candidates. |
| Inventory, item actions, descriptions and custom naming | Unfiltered audit now covers the naturally carried mansion inventory, Big bread Info/Eat/Drop, walking pickup and controlled inventory-full refusal. Other item states, effects and custom-name constraints remain open. |
| Options, bank, shops and storage | Ordinary town-root reopening, earned-money bank round trip and repaired-storage deposit/withdrawal/empty acknowledgement audited without resource filters. Thirteen controlled blacksmith exchanges now include all-glyph checks; other service, shop and Option states still need the independent audit. |
| Story, pickups and combat | Exact fresh tutorial replay reaches 14 pickups on three floors; natural mansion gold/arrow merge and associated combat audited. No unexpected Japanese in these scenarios; the earlier report remains unresolved outside this bounded matrix. Broader routes and readers remain pending. |
| Later dungeons, classes, records and ending | Controlled and bounded route evidence exists; complete natural-route coverage unverified. |
| Title, five corner logos, identified arrival cards and credits | Named assets have their own evidence. Additional graphical text discovery and natural late-game/ending coverage remain open. |

The first [dungeon/town audit](DUNGEON_SCREEN_AUDIT.md) now covers 11 scenarios
with 7,068 observed glyph draws and explicit exceptions for native symbols and
the exact player name retained in an imported Japanese save. It found and fixed
missing spacing in gold pickup text. Historical controls prove that the new
audit rejects both the old gold output and the missed Japanese banner.
The [gallery and matrix](../build/coverage-audit/index.html) retain actual frames,
input schedules and the ordinary/controlled distinction. These results do not
close the other pending areas or establish a whole-game percentage.
