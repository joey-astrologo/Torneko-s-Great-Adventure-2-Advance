# Torneko 2 localization plan

Agreed workflow and translation policy, recorded on 2026-09-13. This is the
working plan for localizing the supplied Japanese Torneko 2 Advance ROM using
the tooling adapted from Torneko 3.

Build the insertion pipeline early, audit graphics alongside text, and playtest
throughout. Work in small batches that proceed through source verification,
translation, language review, insertion and native validation. Discovery and
coverage audits continue while verified families are being translated.

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
