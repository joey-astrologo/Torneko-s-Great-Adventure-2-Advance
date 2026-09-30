# Torneko 2 documentation

Start with [TEXT_PROGRESS.md](TEXT_PROGRESS.md) for current coverage, accepted
milestones and remaining work. Older batch reports retain their original ROM
hashes and validation scope.

[Coverage assessment](COVERAGE_AUDIT.md) explains what those figures establish,
the missed-reader failure, and which complete-screen audits are still pending.

## Everyday work

| Task | Guide |
|---|---|
| Install or reproduce the tools | [TOOLING.md](TOOLING.md) |
| Compile the ROM, export a BPS or run checks | [BUILD.md](BUILD.md) |
| Translate and revise | [LOCALIZATION_PLAN.md](LOCALIZATION_PLAN.md), [glossary](../translations/glossary.json) |
| Investigate unresolved text | [TEXT_OPEN_QUESTIONS.md](TEXT_OPEN_QUESTIONS.md) |
| Capture gameplay or use Ghidra | [EXPLORATION.md](EXPLORATION.md) |
| Reproduce the README screenshots | [SCREENSHOTS.md](SCREENSHOTS.md) |

## Fonts, layout and services

- [Selected font and comparisons](FONT_AUDITION.md), [compact English extension](COMPACT_FONT.md)
  and [original font research](FONTS.md).
- [Menu geometry and action budgets](MENU_LAYOUTS.md).
- [Dungeon-menu location banner correction and coverage gap](LOCATION_BANNER.md).
- [Numbers, spacing and bank labels](TYPOGRAPHY.md).
- [Service coverage and constraints](SERVICE_BATCHES.md).
- [Item names and descriptions](ITEM_TEXT.md).
- [Seven-character name entry and save compatibility](NAME_ENTRY.md).

## Graphics

- [Inserted title and five corner logos](TITLE_INSERTION.md), with native screenshots.
- [Title audition and asset provenance](TITLE_AUDITION.md).
- [Inserted arrival cards](ARRIVAL_INSERTION.md), including Ordeal Mansion and Well suppression.
- [Shiren source lettering](SHIREN_ARRIVAL_FONT.md).
- [Credits and arrival studios](GRAPHICS_AUDITION.md); the original English GBA credits are preserved.
- [Remaining graphics discovery](GRAPHICS_INVENTORY.md).

Audition previews and frozen build artwork are distinct. Follow each insertion
guide's ownership, palette and native-validation requirements when revising art.

## Research and earlier milestones

- [Memory map and allocation ownership](MEMORY_MAP.md).
- [Initial opening discovery](OPENING_TEXT.md) and [English opening routes](OPENING_ENGLISH.md).
- [First home return](HOME_RETURN.md), [books and banker](HOME_BOOKS.md)
  and [mansion quest](MANSION_QUEST.md).
- [Cumulative acceptance receipt](english-services-validation.json).

The [searchable text catalog](../build/text-extraction/index.html),
[font studio](../build/font-audition/index.html),
[menu gallery](../build/menu-resize/index.html),
[typography gallery](../build/typography/index.html) and
[service gallery](../build/services/index.html) are generated local artifacts.
Their source/build hashes matter; an older gallery does not establish acceptance
of a newer build.
