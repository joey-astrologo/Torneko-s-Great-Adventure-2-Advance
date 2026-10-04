# First home return and nearby village batch

This is the historical 63-resource checkpoint. The current cumulative build and
acceptance are documented in [HOME_BOOKS.md](HOME_BOOKS.md); generated report paths
may now contain the newer build.

The cumulative English build now inserts **63 reviewed text resources**, adding
17 in this batch: 15 bank-one strings, Tessie's direct item-sale explanation,
and the native money-notification template. The shared Yes/No resource is reused.
The original ROM and save are unchanged.

[English ROM](../build/english/torneko-2-english.gba) ·
[Native preview](../build/english/home-preview.png) ·
[Acceptance receipt](english-home-validation.json) ·
[Bilingual review](../translations/home-return-review.json)

## What is playable in English

After the first royal audience, choosing Home continues through Tessie's account
of the damaged storehouse, item-sale proceeds, Tipper's return, the three-book
explanation, bedtime, the banker's cries, and the next morning's departure.
Normal movement resumes in the village. Ed's introduction and both Yes/No
responses, the gossip about Mondo, and the neighbouring villager's mansion
rumour are also translated.

The [Japanese trace](../build/home-return/research/trace.json) records five
ordinary-input routes. The evening/morning is continuous; subsequent NPC cases
restore the naturally reached village checkpoint. It retains source bytes,
windows, selected table slots, input schedules, colour changes and the heart's
native bitmap. The sale notice is assembled in RAM, so its **ROM formatter
template** is recorded separately from the resulting runtime text. This is why
a bank-only text scan would have missed two parts of the scene.

## Language decisions

Translations were drafted from the Japanese GBA sources, then given a separate
bilingual editorial pass by the same assistant. The review records every draft,
revision and reason; it is not an independent human review. Page edits avoid
isolated sentence fragments without dropping the repair delay, book order,
bank plan or either choice's meaning.

Tessie, Tipper, the Joy Chest and Adventure Log retain established project
terminology. Ed, Mondo and Exploration Log have PS1 fallback evidence labelled
secondary in the [glossary](../translations/glossary.json). **Ten Tips for
Adventurers**, **Ed & Mondo Carpentry**, and **the western city** are explicitly
provisional project renderings. The three books' menus and contents were
localized in subsequent book/reference-list/record families. The banker's identity remains hidden in his initial cries
until Tessie identifies his voice.

The source's apparent `⑮` is actually a heart in this ROM. `{heart}` preserves
that original glyph. `{color:6}` / `{/color}` preserve yellow book titles; the
money amount uses native colour 5 (palette entry 13). The compiler rejects
missing, reordered, duplicated or unsupported controls and heart substitutions.

## Insertion and native checks

Bank one has 26 groups and 214 relative text offsets. Its selected 15 words now
resolve to appended English strings through the unchanged native getter and
event selector. The rebuilt bank still decompresses to **29,157 bytes**. The
original text, header layout and all other words are preserved. Bank zero keeps
its separate checked reconstruction. Both banks share `RomBuild` allocation and
overlap checks, with no new RAM or save storage. Exact fields, expected bytes and
ownership are in [MEMORY_MAP.md](MEMORY_MAP.md).

The money notice retains its single `%-ld` argument and native player token.
Its two rows accommodate seven of the widest original Japanese name glyphs and
a ten-digit nonnegative signed-long amount. The English template is 30 bytes,
one byte shorter than the original, so formatting the same argument cannot
increase its buffer footprint. Native decimal digits retain their original
seven-pixel font. No sale amount or inventory logic changes.

The [English report](../build/english/home-validation/report.json) verifies:

- Five natural routes, 20 reader calls and 2,366 glyphs, including native bitmap,
  foreground colour, cursor advance, row/width and page-wait checks.
- Both Ed outcomes: Yes returns 1, No returns 0. The original `@A@` sale callback
  keeps flags `0C → 0C`. Village movement resumes after the morning scene.
- Natural bank-one decompression matches every expected byte, with adjacent
  memory guards and preserved registers/SP unchanged.
- **428 controlled getters**: all 214 group/index pairs in the Japanese and
  English ROMs. Untranslated entries retain their original targets.
- Twelve separate sale-format/display probes: `Torneko`, widest selectable
  English name, and widest original Japanese name, each at amounts 0, 1, 100
  and 2,147,483,647. Native formatting, rendering and buffer/name guards pass.
  These are controlled layout cases, not claims that those amounts were earned.

All earlier name/save, opening, dungeon, castle and destination checks also pass
on this ROM. The unit/toolchain suite passes 34 tests, and all seven original
bank decodes and 66 catalog source round trips pass. The build receipt pins the
exact reports, code, source/catalog hashes and ROM/BPS identities.

## Reproduce

```bash
./build.sh
./validate.sh
```

The build script generates both the English home checkpoint and a fresh Japanese
home checkpoint from its native Japanese save test. It does not need historical
home-research fixtures. ROM construction itself remains independent of all
emulator checkpoints. For the existing Japanese research chain:

```bash
.venv/bin/python -m tools.trace_home_return
.venv/bin/python -m tools.verify_home_return
.venv/bin/python -m tools.verify_text_sources
```

The first command starts at `build/destination-menu/research/home-menu`. Its
village checkpoint is at `build/home-return/research/village`; the English one
is at `build/english/home-validation/village`. Snapshot metadata pins ROM,
emulator, state and battery hashes, preventing cross-build reuse.

## Historical graphics discovery and subsequent work

The fourth planned step confirmed the first dungeon's separate arrival card
and identified the title/menu background families. See
[GRAPHICS_INVENTORY.md](GRAPHICS_INVENTORY.md) and the expanded
[arrival-frame viewer](../build/arrival-research/index.html). No graphics have
been localized at that initial discovery stage.

Subsequent work localized books, banker/mansion, services and many gameplay
families. The main title, five floating logos and 13 arrival names plus Level
are approved and inserted; original English credits are preserved. See
[the current matrix](COVERAGE_AUDIT.md) for remaining caller, source and scene gaps.

This historical catalog had 66 verified sources: 63 reviewed and inserted, two replaced
by existing UI components, and one retained Japanese keyboard resource. That
is not whole-game completion. The known seven tables contain 1,046 sources;
49 have native observations. Of 2,701 remaining scan candidates, 687 exactly
match table sources and 2,014 remain unresolved.
