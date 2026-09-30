# Coverage assessment after the missed menu banner

**Whole-game localization coverage is unverified. There is no defensible
whole-game completion percentage yet.** The user-reported Japanese location
banner showed that translated catalog entries, inserted resources and passing
family tests can coexist with an untranslated ordinary gameplay screen.

The visual review also missed that text. More passing cases from the same
selected-resource checks would not resolve this coverage problem.

## What the existing figures establish

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| 3,512 of 3,625 catalog sources reviewed (96.9%) | Review progress within the identified catalog, excluding 29 accounted-for retained/component sources | Percentage of playable text in English, all readers redirected, or all text discovered |
| 3,770 text resources inserted | English resources present in the compiled build under checked ownership | Every place that displays those concepts actually uses the inserted English |
| 113 unresolved catalog sources | Known source-level investigation backlog | The complete remaining work; missed consumers of already-reviewed sources are additional gaps |
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
| Inventory, item actions, descriptions and custom naming | Existing resource/layout tests retained; independent complete-screen audit pending. Custom-name constraints remain unresolved. |
| Options, bank, shops and storage | Existing route/resource checks retained; independent complete-screen audit pending. |
| Story, pickups and combat | Existing translation and native route evidence retained; game-wide reader/route accounting pending. Earlier reported Japanese dungeon messages remain an open investigation. |
| Later dungeons, classes, records and ending | Controlled and bounded route evidence exists; complete natural-route coverage unverified. |
| Title, five corner logos, identified arrival cards and credits | Named assets have their own evidence. Additional graphical text discovery and natural late-game/ending coverage remain open. |

This document corrects the interpretation of existing evidence and sets the
next audit requirements. It does **not** claim that the pending audit has run
or that the remaining gaps have been found.
