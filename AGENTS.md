# Torneko 2 research workflow

Use the local `.venv/bin/python` and the commands in `README.md` and
`docs/EXPLORATION.md`. Native mGBA uses the project build; desktop mGBA and
Ghidra are shared installations. Read `docs/TOOLING.md` before changing pins.

Follow `docs/LOCALIZATION_PLAN.md` for the agreed translation source,
terminology/prose rules, coverage reporting and localization work sequence.
The user authorizes autonomous work through all text localization; no per-batch
approval is required. Interrupt only for necessary user insight/investigation.
The user reopened ending-credit discovery and credits/arrival-card auditions on
2026-09-29; these may proceed now. On 2026-09-30 the user also requested a title-screen
audition; follow `docs/TITLE_AUDITION.md`. The user subsequently approved and
requested insertion of the main title and all five corner logos. These are now
inserted; follow `docs/TITLE_INSERTION.md` and the hash-checked frozen assets in
`assets/title-screen/approved.json`. The five corner logos must use floating lettering,
with no wooden backing; the user rejected the plaque variant. Follow the
transparent-logo revision in `docs/TITLE_AUDITION.md`. Prefer one-line combat
messages when full meaning and maximum substitutions fit verified budgets;
never force fit by omitting meaning or compressing the approved font.
On 2026-09-30 the user approved preserving the original English GBA credits
unchanged and requested Shiren SNES source lettering for arrival auditions.
See `docs/SHIREN_ARRIVAL_FONT.md`; recovered glyphs and derived/missing characters
must remain distinguishable. The user subsequently approved insertion of these
13 cards and Level, including a wider Ordeal Mansion. Follow
`docs/ARRIVAL_INSERTION.md`, `config/arrival-art.json` and the shared allocator;
native acceptance covers all selectors, with late-game natural routes still open.

Use `config/rom.json` as the Japanese base identity. Preserve the supplied ROM
and save. Emulation uses `tools.emulator.Session` or a separate desktop copy
from `tools.prepare_playtest`; never run write-producing experiments on source
files. Keep source hashes and actual input schedules with research artifacts.

Record ROM/RAM/save discoveries in `docs/MEMORY_MAP.md`, with address space,
exclusive ranges, evidence and certainty. Original bytes, unidentified gaps,
padding and relocated text are not automatically free space. Before future
insertion, establish ownership, expected source bytes and shared allocation/
overlap checks. The compact English extension has explicit patch/resource
ownership in `docs/MEMORY_MAP.md` and uses `tools.rom_build.RomBuild`. Reuse that
allocator for future resources; it does not establish ownership of other source
ranges or any new RAM/save storage.

Torneko 3 is a tooling reference. Its encoding, addresses, fonts, expansion,
translation catalogs and gameplay/save assumptions do not apply until verified
in Torneko 2. Distinguish controlled emulator probes from native gameplay
observations and verified insertion from reviewed translation.

Run the relevant checks after changes. `./validate.sh` covers toolchain and
fresh-save acceptance. It does not establish full game or translation coverage.

The selected build font is the Torneko 2 compact extension in
`assets/fonts/compact-english.json`. Early menus use approved shorter labels and original window geometry;
Torneko 3 remains a comparison/fallback asset. Follow `docs/MENU_LAYOUTS.md`,
`docs/FONT_AUDITION.md` and `config/font-audition.json` before
new menu insertion. Establish the actual text region after cursor/column space,
per-item/state action variants, dynamic fields and byte capacity. Candidate
labels must fit the selected font in that region; dialogue fit is not evidence
for menu fit. After any geometry change, check selection, clipping/shading and
parent panels through opening, cancellation and repeated reopening. Unknown
menu families and unresolved candidate overflows block menu-layout sign-off;
they are not silently accepted because the font or earlier routes passed.
The dungeon-menu location banner has 13 names in a 168px one-line region.
Its separate reader was missed by earlier command/status checks; follow
`docs/LOCATION_BANNER.md`. `tools.verify_location_banner` now checks every glyph
and all five visible text fields, including the banner, in all three command
modes. Never infer an English screen from checks limited to selected resources.
The first action-label table is copied for its owned consumer; never translate
the shared original table without auditing its other consumers. Current early
action/main buffers are 256/64 bytes, with checked stack-frame changes. Item
rows have 162 usable pixels including markers/counts/suffixes in the original
168-pixel parent window. Item names, including custom names, must stay on one
line; do not solve width problems with additional item-name rows. Preserve the
8-pixel gaps between outer menu borders;
text fit and restoration alone do not establish visual acceptance. Keep native
routes distinct from controlled item/mode probes and explicit exclusions.

Use `docs/SERVICE_BATCHES.md` and `docs/TYPOGRAPHY.md` for current service/font
constraints. English word spaces are three pixels; letter spacing is normal.
Dynamic native number aliases use matching compact digits. Inverse price cells
must have continuous backgrounds. Bank labels include attached colons within
the 57px region; repaired-storage columns each have 100px. Never infer complete
service coverage from translated root labels. The item definition table has
221 records, not 224; controlled known-name tests must not set inscription bit
00400000. The storage quest recipe uses ordinary inputs and native saves.
