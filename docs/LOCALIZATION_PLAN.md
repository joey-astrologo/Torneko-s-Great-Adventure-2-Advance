# Torneko 2 localization plan

Agreed workflow and translation policy, recorded on 2026-09-13. This is the
working plan for localizing the supplied Japanese Torneko 2 Advance ROM using
the tooling adapted from Torneko 3.

Build the insertion pipeline early, audit graphics alongside text, and playtest
throughout. Work in small batches that proceed through source verification,
translation, language review, insertion and native validation. Discovery and
coverage audits continue while verified families are being translated.

## Current standing authorization

Continue autonomously toward all player-facing text being translated, reviewed,
inserted and validated. Batches organize the work internally and do not require
fresh user approval. Ask only when a consequential unresolved decision requires
the user's insight or investigation. Maintain explicit discovery and validation
gaps; completing a known catalog is not proof of complete game coverage.

On 2026-09-29 the user reopened ending-credit discovery and requested credits
and arrival/dungeon-card audition systems following the Torneko 3 workflow.
These discovery and audition tasks may proceed before the remaining text work.
Title artwork and background-logo editing were initially deferred. Audition candidates
are separate from approved artwork and ROM insertion. Native screenshots for
text validation continue.

On 2026-09-30 the user selected the original GBA credits for preservation:
they are already English and their artwork should remain unchanged. The user
also requested arrival lettering based on `../Shiren/shiren-revamp-fixes`.
The reconstructed bitmap subset and its budgets are documented in
[SHIREN_ARRIVAL_FONT.md](SHIREN_ARRIVAL_FONT.md). Later that day the user approved
insertion and in-game validation. The [inserted cards](ARRIVAL_INSERTION.md)
now pass 30 native cases; the selected dialogue/menu font stays unchanged.
Natural late-game entry routes remain a playtesting gap.

The user subsequently requested a title-screen audition on 2026-09-30.
[TITLE_AUDITION.md](TITLE_AUDITION.md) records the wood-and-gold proposal,
Torneko 3-derived comparison tools, fresh native references and browser checks.
This reopens title artwork exploration. The user then approved the main title
and requested matching auditions for the five menu backgrounds. These now use
one shared transparent logo with exact preservation outside its corner rectangle.
The user explicitly rejected wood behind the corner lettering; revision 2
repairs the old Japanese logo areas and overlays floating English letters.
The user then approved all six images and requested insertion. They are now
[inserted and natively verified](TITLE_INSERTION.md): five ordinary background
selections plus the supplied-save route, 36 stable scenes and 640 controlled
colour probes. The editable studio retains its separate 85 browser checks.

Prefer a single line for combat messages whenever their complete meaning,
control behavior and widest supported substitutions fit the measured line and
buffer budgets. Do not retain Japanese line breaks mechanically. Use two lines
when required for fidelity or safe fit; do not omit mechanics, shrink text or
compress spacing to force a one-line result. Record maximum expanded widths
and native evidence for dynamic combat formats.

## Revised next batches: font and menu layout

Latest user direction (2026-09-19) supersedes the earlier T3 font selection:
prefer the **Torneko 2 compact English extension for readability**, and keep
Torneko 3's font as a fallback if the necessary T2 layouts are infeasible.
**Completed:** the [four-batch result](MENU_LAYOUTS.md) restores T2 as the build
default, inserts 16 reviewed early-menu resources, and validates the early menu
families. The sequence below records the authorized work. The audition now
compares original candidate wording and current approved wording; broader coverage gaps stay explicit.

**Visual correction:** user review rejected the widened borders. Approved labels
Swap, Info, Floor, Option, Remove and Take restore original 40 px windows,
34/36 px text budgets and 8 px border gaps. Buffer fixes remain. The widening
targets below are historical research, superseded by this correction.

Both fonts overflowed with the initial candidate labels, but they do not impose
identical geometry requirements. Keeping the measured insets, the smallest
eight-pixel tile widths that fit those initial candidates are:

| Region | Existing window / text budget | T2 prototype window / budget | T3 comparison window / budget |
|---|---|---|---|
| Dungeon main commands | 40 / 34 px | 48 / 42 px | 48 / 42 px |
| Item and ground actions, including Exchange | 40 / 36 px | 56 / 52 px | 48 / 44 px |

These are arithmetic targets, not tested layouts or sufficient budgets for all
future action variants. T2's Exchange is 48 px; T3's is 42 px. A T2 action panel
keeping the current right edge at screen x=232 would move from x=192 to x=176;
T3's would move to x=184. The inventory content currently ends at x=176, so
border, shading, counter and parent restoration behavior must be established
before claiming either layout is safe. Do not shrink the item-name area merely
to make an action label fit without checking complete formatted item rows.

The name editor and travel menu already demonstrate that some Torneko 2 windows
can be moved/widened and their native behavior validated. This is encouraging
evidence, not proof about inventory windows or their shared callers. Resizing
is also not logically mandatory if reviewed shorter wording fits; the preferred
approach is to test readable T2 labels before abbreviating to avoid the work.

1. **Prove the T2 layout on the tight early menus.** Trace creation, cursor,
   clipping/shading, allocation and close/restore callers. Establish exact patch
   ownership and string byte capacity. Build a disposable T2-font prototype of
   the 48 px main menu and 56 px inventory/ground action menus with representative
   labels, using checked ROM patches. Test all currently observed action sets,
   selection, cancellation and repeated opening; compare restored parent pixels
   against the pre-open state of the same build. Produce native before/after
   screenshots and a pass/fail report. If the preferred arrangement fails,
   investigate repositioning and the actual cause before trying the T3 fallback;
   T3 still needs its own layout proof. Outcome: evidence of feasibility for
   these panels, not a universal font-risk claim.

2. **Expand the budget inventory before freezing the menu layout.** Trace other
   item/action families and equipped, cursed, disabled and full-inventory states;
   map complete item-row formatters (markers, counts, names, enhancements and
   suffixes), bank amounts and populated storage/shop menus. Work in bounded
   families and keep unavailable states explicit. Extend the audition to show
   original and proposed geometry, both fonts and complete dynamic worst cases,
   including seven-character names. Record pixel limits separately from encoded
   byte/buffer limits. Outcome: a reviewed budget matrix for the first menu
   insertion batch and an explicit remaining-coverage list.

3. **Restore the preferred font and localize the proven menu families.** If the
   T2 prototype passes, restore the T2 font as the build default, update the
   audition selection and rebuild the existing translations. Apply established
   terminology review to actual menu meanings; the current English audition
   labels are candidates. Insert only families whose source ownership, geometry
   and dynamic/byte limits passed batches 1–2. Add fit checks that fail builds on
   overflow and native behavior checks for the changed panels. Outcome: a
   playable T2-font build with the first audited English menus. Use T3 only if
   its tested layout solves a demonstrated obstacle to the preferred font.

4. **Run cumulative acceptance, then resume localization.** Recheck all 95
   glyphs, name entry/save/load, existing opening/town/mansion routes, dialogue
   wrapping and the new menu variants on the same ROM. Verify clean ROM/BPS
   reproduction and save fresh screenshots and an acceptance receipt. Record
   untested menus explicitly. Then resume bank/storage/records and later text
   discovery using the new budget checks. Graphics auditions and broader
   playtesting remain on the roadmap, after this text-layout foundation.

The next implementation work is bank/storage/records discovery and English
formatter review using the established budgets. The expanded audit is bounded:
later populated shop/storage routes and nested pot contents still need native
coverage. Do not perform a blanket window resize or infer whole-game sign-off
from the completed early-menu batches.

## Current foundation

- The Japanese ROM identity is pinned in `config/rom.json`. Preserve the supplied
  original ROM and save; experiments and playtests use disposable copies.
- The local disassembly, native mGBA, assembler and BPS workflow is installed
  and validated. See [TOOLING.md](TOOLING.md) and [EXPLORATION.md](EXPLORATION.md).
- The [compact English font](COMPACT_FONT.md) covers all 95 printable ASCII
  characters, preserving the original compact capitals and digits and adding
  matching lowercase and missing symbols. All glyphs pass native menu checks.
- The font extension and one relocated menu specimen work in a 16 MiB cartridge.
  This verifies those resources and that route, not every text reader or full
  gameplay with the expanded ROM.
- The initial-menu specimen measures 88 pixels including its leading space in
  a 96-pixel window. Other windows, substitutions and buffers require their own
  measurements. A compact font does not guarantee every translation fits.

Torneko 3 supplies reusable workflows and terminology evidence. Its addresses,
encodings, commands, data structures, gameplay features and save assumptions
must not be imported without Torneko 2 evidence.

## Translation source and terminology

All inserted English must fit its measured width budget in the selected Torneko 2
font. Include cursor reserves, columns, icons, quantities, suffixes and the widest
supported dynamic substitutions. Check encoded byte capacity separately. Reword
or use a documented display form while preserving meaning; do not silently clip,
drop conditions, shrink the font or overlap neighboring window borders. Native
captures must confirm fit and spacing. An unknown budget blocks insertion for
that context until it is measured. This applies to prose as well as labels.

User clarification on 2026-09-29: **item names must remain on one line**, including
custom names. The earlier proposal to add lines for long Japanese custom names
is rejected. Resolve their widths within a single-row design; this instruction
does not approve clipping, price overlap, changes to saved names or font shrinking.

Use the pinned **Torneko 2 Japanese ROM** as the translation source and build
base. Author English independently. Fan translations may provide technical or
contextual leads; do not reuse their English or font assets.

The agreed terminology reference order is:

1. Modern official Dragon Quest English, with **XI / XI S as the baseline**
   for shared items, monsters, spells and series terms.
2. Other modern official localizations for gaps, including remakes and Monsters
   games. Record the particular game/version and assess later naming revisions
   individually.
3. The official PS1 **Torneko: The Last Hope** as a fallback for dungeon-specific
   terminology when a suitable modern match is not established.

Prefer official text, manuals or game captures. Wikis and other fan-maintained
references can document official wording but must be labelled secondary.
Record the reference game/version, source URL or capture, evidence quality,
confidence and review date. A failed search does not prove no official name
exists. Mark unresolved names and independent project choices explicitly.

Match the exact Japanese entity, source ID and context. Distinguish species,
variants, recolours, upgrades, nicknames, items and unidentified-item disguises.
Identical Japanese spellings need not describe the same entity. Preserve an
official localized pun when the identity matches; do not infer mechanics from
the pun or replace the official name with a literal translation.

Reuse an existing Torneko 3 glossary entry only after checking the Torneko 2
identity. Keep the full glossary name and use it consistently across relevant
menus, descriptions, dialogue, headings and defaults. Record necessary display
abbreviations separately after measuring the actual font and layout. Shortened
display forms do not become new official names.

Use sentence case for item labels, retaining proper names and acronyms. Use
**defence** and **armour** in the modern series style, and retain **HP**.
Established UI wording such as **Adventure Log** should be reused when its role
is confirmed here; Torneko 3's slot labels and menu structures are not evidence
of Torneko 2's layout or available slots.

Translate effects from **Torneko 2's Japanese**, preserving targets, amounts,
durations, conditions and exceptions. Other games supply naming references,
not replacement mechanics or ready-made description paragraphs. Record source
ambiguities for investigation instead of silently inventing or correcting rules.

These policies carry over from Torneko 3's
[terminology rules](../../torneko-3-gba/docs/TERMINOLOGY.md#reference-order) and
[project rules](../../torneko-3-gba/AGENTS.md#translation-source). The local
wording above is the Torneko 2 policy and remains usable without that sibling
checkout.

## Prose rules

The three established rules are:

1. **Natural English.**
2. **Consistent, sourced series terminology.**
3. **Fidelity to the Japanese meaning and character voice.**

In addition, every final display must meet the width-budget requirement above.

Preserve humour, dialect, childlike speech, monster cries, speaker reveals and
the meaning of choices. Read connected dialogue in actual event order, with
neighbouring responses and branch outcomes. Check that English questions retain
the original yes/no sense and that choices still invoke their original actions.

Prose review includes item descriptions, tutorials, help, services, combat and
results messages as well as story dialogue. Mechanics must remain precise even
when wording becomes more natural. Review compact display wording separately
so that shortening does not discard a condition or change meaning.

Perform a dedicated bilingual editorial pass after the initial translations.
Record the source identity, previous English, revision and reason. Preserve
reviewed English and notes when regenerating catalogs. Pattern scans and width
checks are useful validation, but do not count as bilingual reading.

Source: Torneko 3's [prose second pass](../../torneko-3-gba/docs/PROSE_REVIEW.md).
Its reviewed English and game-specific character choices are not a substitute
for reading Torneko 2's source.

## Work sequence

### 1. Map text systems and inventory visible resources

Find text encodings, readers, pointer tables, fixed records, event operands,
control commands, runtime substitutions and window limits. Trace displayed
text back to its source, including strings assembled or copied into RAM.
Investigate compressed resources and additional font/graphics paths where
evidence points to them.

Begin the graphics inventory alongside text: title artwork, other occurrences
of its logo, dungeon arrival cards, any town arrival cards, signs, interface
lettering, ending artwork and credits. Confirm which resource families exist;
a separate Torneko 2 town-card family is currently unverified.

Record discoveries in [MEMORY_MAP.md](MEMORY_MAP.md) before insertion, including
address space, exclusive ranges, purpose/owner, evidence and certainty.

### 2. Create a lossless Japanese extraction catalog

Retain stable source IDs, exact original bytes, decoded Japanese, command tokens,
source references, context, resource family and verification status. Keep
pointer-shaped candidates separate from verified pointer ownership. Preserve
table slots and shared references while counting unique sources separately.

Reconstruct Japanese from the original byte tokens and require byte-exact
round trips. Do not rely on Unicode re-encoding to preserve every source alias.
Keep editable English and review notes safe during re-extraction. Provide a
searchable bilingual inspection view with evidence and status filters.

### 3. Establish the cumulative build and test pipeline

Extend the existing font proof into one deterministic build from the pinned
Japanese base. Reuse `tools.rom_build.RomBuild` for checked patches and shared
allocation; do not stack independent proof patches or rewrite every integer
that resembles a pointer.

The pipeline should validate:

- Source identity, original bytes, owned pointer fields, allocation alignment,
  overlap and cartridge capacity; preserve all unowned original bytes.
- Extraction round trips, supported glyphs, command semantics and substitutions.
  Define Torneko 2 command tokens from its readers; do not copy Torneko 3 syntax.
- Actual pixel widths, line/page limits, spacing and fixed-width overrides.
  Check expanded byte lengths and RAM buffers separately from pixel fit.
- Representative and worst-case substitutions, including names, quantities and
  other dynamic fields, with native reader and renderer checks.
- BPS application to the pinned base reproducing the complete output byte for
  byte, with source/output hashes and an allocation/patch receipt.

Keep frozen source assets and build recipes sufficient to rebuild from a clean
generated-output directory with the documented toolchain installed. Do not
depend on an unexplained historical proof ROM or invoke image generation during
an ordinary build. Torneko 3's current convenience build still depends on
prepared resources and previous checkpoints; improve that dependency structure
here. See its [build notes](../../torneko-3-gba/docs/BUILD.md).

Provide a convenient build command, stable ROM/BPS/report paths and safe output
replacement. Report build checks separately from fresh emulator validation.

### 4. Audit coverage, then keep auditing

Combine broad scans with table enumeration, disassembly, native text-reader
traces and graphics inspection. Look for short labels, punctuation-only text,
format strings, computed references, compressed resources and lettering stored
as pixels. Trace RAM producers instead of assuming every display starts at a
ROM string pointer.

Give each candidate an explicit disposition: verified text/resource, unresolved,
internal/debug, duplicate, non-text, or intentionally retained. Keep unresolved
leads visible without counting them as confirmed translation sentences.

Track discovery evidence, translated unique sources, reviewed language, inserted
resources, native display checks and naturally reached gameplay separately.
**100% of the catalog translated is not proof that 100% of the game was found.**
Aim to account for all player-facing resources and resolve outstanding leads,
while stating the actual boundaries of scans and tested routes. Translation of
verified families can continue while the coverage audit expands.

Torneko 3's [coverage audit](../../torneko-3-gba/docs/TEXT_COVERAGE.md) found
formatting resources and already-English credits outside its Japanese-text
inventory. This is a reason to audit multiple resource types here, not evidence
that Torneko 2 has the same omissions or credit language.

### 5. Translate terminology and functional text in batches

Establish the glossary for names, commands, items, monsters, spells and places.
Then translate their descriptions, help, shops, status and gameplay messages.
For every verified family, use the same loop:

**Verify source → translate → review language → insert → test in mGBA.**

Use real context and measured layouts before choosing abbreviations. Apply the
prose rules to descriptive and instructional text. Update shared occurrences
consistently and preserve distinctions between full names and display forms.

### 6. Translate story in scene context and perform an editorial pass

Translate connected scenes with their original event order, choices and speaker
context. Insert and test progressively. Check command/choice preservation,
substitutions, paging and readability as part of each batch.

Follow the first translation pass with a dedicated bilingual review across
story and functional prose, including shortened display wording. Record the
reviewed source/build identities and rerun checks appropriate to revisions.

### 7. Audition and localize graphical lettering

Audit before redesigning. For confirmed arrival-card families, review the full
set at native size, including long place names, floors and special variants.
Provide original/candidate comparisons, saved settings and exported previews.
Do not treat a town-background mockup as proof of a native town-card system.

Audition the English title and every confirmed background/logo occurrence as
a coordinated design. Choose one English wording and logo treatment, adapting
it to each actual placement. Match repeated appearances without assuming they
share one underlying asset or palette.

Review native tile/palette constraints during the audition so conversion does
not introduce a late surprise. Freeze the selected artwork and settings, pack
deterministically, integrate through the shared allocator, and compare actual
in-game output. Check fades, animation, prompts, transitions and neighbouring
graphics as applicable.

### 8. Inspect credits and the ending before deciding what changes

Check staff roles, names, introductory cards, copyright and surrounding ending
artwork separately. Translate what needs localization. Treat restyling text
that is already English as a separate design decision.

Torneko 3's [credit text](../../torneko-3-gba/docs/CREDITS_AUDITION.md) was already
English; Torneko 2's status remains to be established. A text-layer export does
not establish that every ending graphic is localized or that the full ending
plays correctly. Inspect the natural ending sequence as part of playtesting.

### 9. Playtest continuously and finish with a release pass

Maintain a backlog of natural gameplay routes, unresolved defects and evidence.
Include progression, branch outcomes, long names, inventory extremes, message
history, save/load, dungeon transitions, defeat and endings. Cover available
save slots, suspend/resume and additional modes where those features exist.
Use disposable copies of saves and retain the exact ROM hash and input route
with bug reports and screenshots.

Controlled native-reader fixtures establish rendering or function behaviour
for their supplied inputs. They do not establish that every natural trigger,
choice consequence or gameplay mechanic works. Track both kinds of evidence.
Deferred personal playtesting does not prevent continued source research,
translation drafts or appropriate automated checks.

Before release, repeat the coverage audit, build from clean generated output,
verify BPS application, run relevant regressions on the exact resulting ROM,
and document save compatibility, known issues and untested routes. Preserve
original ROM/save files and keep localization status distinct from full-game
playtest status.

## First milestone and immediate work

The first integrated milestone is **a verified Japanese catalog and repeatable
English build covering the opening menu, name entry, opening dialogue and first
playable area**. This exercises the process before scaling it across the game.

Start with the original Japanese game. Capture the opening route, identify the
actual readers and source references for those screens, and record their window,
command and buffer constraints. Extend the current menu proof into lossless
extraction and checked insertion for these verified sources. Expand the broader
text and graphics inventories alongside this work.

Acceptance for that milestone:

- Name entry must accept at least seven Latin letters so the exact name
  `Torneko` can be entered. Verify selection, editing, confirmation, every
  relevant name display/substitution, and persistence after saving and a cold
  load. Do not abbreviate this required name to fit a Japanese limit. Character
  count, encoded byte capacity and display width are separate constraints;
  establish the original fields and their consumers before expanding them.
- Source bytes round-trip exactly; references and insertion ownership are
  documented rather than inferred from a scan alone.
- English follows this terminology/prose policy and retains original controls,
  choices and substitutions.
- The cumulative build can be reproduced from the pinned source and retained
  assets, with a verified BPS patch and allocation receipt.
- Native captures and normal input routes cover the listed opening contexts;
  applicable width, byte/buffer and save/load checks pass.
- Inventory gaps and later gameplay/graphics coverage remain explicitly tracked.

| Work | Status at plan creation |
|---|---|
| Toolchain and pinned Japanese base | Complete for documented acceptance scope |
| Compact English font and initial-menu specimen | Complete for documented native font scope |
| Translation policy and localization sequence | Documented here |
| Broad extraction and coverage audit | Planned |
| Opening-area integrated milestone | Planned; next implementation work |
| Remaining text, graphics, ending and full playtest | Planned |

## Progress after plan creation

2026-09-13: the [first opening-text discovery pass](OPENING_TEXT.md) is implemented.
A normal-input route reaches the first dungeon; 30 source strings are verified,
seven compressed banks pass native decoder comparisons, and a separate candidate
queue supports further discovery. The [graphics inventory](GRAPHICS_INVENTORY.md)
records observed appearances and unconfirmed families. Name-entry producer and
event-command/insertion research remain in progress. No bulk English translation
or completion of the integrated opening milestone is claimed by this pass.

2026-09-13: [name-entry research](NAME_ENTRY.md) confirms the opening editor's
six-character limit, indexed working/stored records and fixed 14-pixel advance.
The user's minimum is seven Latin letters for `Torneko`. The base-game probe
passes; English keyboard/mapping, layout changes and save/cold-load acceptance
remain part of the opening milestone.

2026-09-13: the [cumulative English build](BUILD.md) implements seven-character
shared/player name entry, both English cases and measured cursor/layout behavior.
All 69 selectable English characters pass native checks. `Torneko` survives
normal entry, first-floor save/suspend, a cold second-floor resume and movement.
A separately generated Japanese save also imports and resumes correctly on the
tested route. The save layout is unchanged. Next is opening event-command and
insertion work; remaining name contexts and item-specific behavior continue in
broader playtesting. The complete English opening milestone remains in progress.

2026-09-13: the [English opening batch](OPENING_ENGLISH.md) translates and reviews
36 catalog sources across both opening branches, the flashback, resume/menu
labels, stair options and all three introductory floor tutorials. Native source,
glyph, layout, page, event-side-effect and save/load checks pass within the
documented routes. The seven known event tables now account for 1,046 sources;
709 original scan candidates match exact table entries. Later dialogue, menu
flows, save-preview formatting, arrival artwork and whole-game coverage remain
ongoing. The next natural route extends through the first dungeon exit.

2026-09-13: that route now reaches the King's first audience and the five NPCs
around the throne. The current batch contains 44 reviewed/inserted text resources,
including both answers to the guard's question. Native name substitutions support
`Torneko` and seven widest English/Japanese glyphs; town controls resume after
the conversations. The accumulated source catalog contains 47 native sources.
The regenerated candidate queue has 2,716 entries: 701 exact known-table matches
and 2,015 unresolved. These supersede the earlier queue counts without implying
a whole-game completion percentage. Further castle/village states, other menu
and message families, graphical text and full playtesting remain ongoing.

2026-09-13: the current build also localizes the first destination menu, bringing
the reviewed/inserted text batch to 46 resources. Cancel, Home, cursor alignment
and seven widest Japanese/English name glyphs pass native checks. Returning home
naturally loads bank one; its first Tessie conversation is retained untranslated
for the next batch. There are now 50 native catalog sources and 2,714 scan
candidates (700 exact table matches, 2,014 unresolved). A replayable arrival-frame
viewer covers the first castle and home transitions; no separate title card was
observed on these specific routes. Other arrival families, title artwork and
ending credits still need their own discovery and auditions.

2026-09-14: the four-step [home-return batch](HOME_RETURN.md) is complete. The
cumulative build has 63 reviewed/inserted resources and 66 native catalog
sources. Fifteen bank-one strings, the item-sale explanation and its dynamic
money template cover the first evening/morning and three neighbouring NPCs,
including both Ed choices. Both ROMs pass all 214 bank-one getters; native
colour/heart rendering and twelve name/amount layout probes pass. The 34-test
unit/toolchain suite and earlier gameplay/save checks pass on the cumulative ROM.
The next text families are home-book/save/storehouse menus and the banker/mansion
route. Current candidates: 2,701, with 687 exact table matches and 2,014 unresolved.

The same batch identifies the first dungeon's separate 4bpp arrival atlas and
floor compositor, with 600 consecutive frames verified by native replay. The
large title and smaller menu logo use different uncompressed 8bpp resources;
the observed menu and name editor share one selected background. Five menu
background candidates are identified, with four still needing native audit.
Graphics auditions, other arrival states and credits remain pending; no graphics
have been inserted. These are measured scope increases, not whole-game coverage.

2026-09-19: the [home-book/banker batch](HOME_BOOKS.md) adds 16 reviewed resources,
bringing the build to 79 and the native catalog to 86. It covers all ten tips,
the broken-storehouse blue-book actions, save/cancel/quit and cold town reloads,
castle/square labels, both banker answers and the old-man scene, and the first
mansion entrance/movement. Three controlled village-name layouts fit the existing
128-byte overwrite buffer. A newly mapped shared town bank has 300 pointers and
204 unique sources, all pointer relocations checked in both ROMs without RAM
growth. Four green-book sources are discovered but remain untranslated. The
37-test suite and earlier native routes pass. Mansion recovery, populated item
and record lists, repaired services, graphics and full-game coverage remain open.

2026-09-19: the combined [mansion discovery/localization batch](MANSION_QUEST.md)
adds 25 reviewed resources, bringing the build to 104 and the native catalog to
112. A reproducible Japanese route reaches the 6F special room, defeats the Imp,
recovers the safe and returns home. English acceptance cold-loads a real Japanese
5F suspend and continues through recovery, both family questions and the bank's
opening; four branch replays include refusal/reconsideration and service-menu
cancellation. It is not an uninterrupted English 1F–6F run. Native centring passes
for `Torneko` and seven widest English/Japanese glyphs. The cumulative native
checks and 38-test suite pass. Banking transactions, populated inventories,
green-book records, other dungeon messages/results, graphics and full-game
coverage remain open. The candidate queue has 2,814 entries, including 2,005
unresolved leads; this is not a completion percentage.

2026-09-19: the user selected the original Torneko 3 Latin font 0. All 95 ASCII
glyphs are imported with their original pixels and advances, and pass native
Torneko 2 rendering checks. The cumulative 104-resource English build passes
its existing gameplay/save routes with this font; the unit suite now has 41
tests. The previous compact font remains available in the
[interactive font audition](../build/font-audition/index.html). It compares
14 contexts and 100 label/font cases, with downloadable per-font budgets.

The [menu audit](FONT_AUDITION.md) is now a required checkpoint before new menu
translation. Eight native routes establish early dungeon actions, ground
actions, options, inventory and bank regions. Repeated inventory action-menu
opening/cancellation preserves parent descriptors and tilemap/tile pixels.
The selected font improves fit but Tactics, Examine and Exchange still exceed
their measured regions. Resolve the relevant wording or geometry, establish
byte capacity and test dynamic extremes before inserting those menus. Later
menu families, restricted item states and bank amount limits remain unknown;
font selection does not constitute whole-game menu-layout acceptance.

2026-09-19: the user's final font choice is Torneko 2 compact English with
original-sized early windows and shorter action labels. The four
[service batches](SERVICE_BATCHES.md) now add Option/status UI, core banking, an
eight-item cohort and the naturally unlocked repaired-storage subset. All English
translations must fit measured width budgets including dynamic fields.
The visual follow-up keeps normal English item spacing, three-pixel word spaces,
matching compact numeric glyphs and continuous inverse price backgrounds; bank
labels include attached colons. Weapon replaces Sword in status. The build has
184 reviewed resources across separate source catalogs.

Storage's prerequisite castle quest and native save are reproduced with ordinary
inputs; deposited bread/wand survive an English save and cold reload. The bakery,
remaining storage child prompts, bank rewards, untranslated item identities and
later modes remain explicit follow-ups. These bounded batches do not establish
whole-game text, graphics or gameplay coverage.
