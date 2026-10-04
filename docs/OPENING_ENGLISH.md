# English opening through mansion recovery and bank opening

This page records the historical **104-source opening/mansion milestone**.
Current build identity, acceptance and remaining work are in
[the coverage matrix](COVERAGE_AUDIT.md). That milestone translated 104 sources. The first 46 cover 26 opening event strings,
shared Yes/No, first-floor help, eight first-dungeon/resume resources, the King's
first audience, seven subsequent castle NPC strings, and two travel-menu labels. This
includes both responses to Tipper's invitation, the complete opening flashback,
all three introductory floor tutorials, stair options, and five nearby castle
NPCs with both answers to the guard's question, and the first destination menu.
The [home-return batch](HOME_RETURN.md) adds 17 sources covering the first
evening/morning, sale proceeds and three village NPCs with both Ed answers.
The [home-book/banker batch](HOME_BOOKS.md) adds 16 more: red-book tips, blue-book
actions/save flows, castle/square travel labels, and the first banker/old-man scene.
The [mansion quest batch](MANSION_QUEST.md) adds 25: safe recovery, family choices,
the next morning, bank opening, and the bank greeting/farewell.
The earlier
English font, seven-letter name editor and Start adventure label remain included.

Run `./build.sh`. The development ROM is
[build/english/torneko-2-english.gba](../build/english/torneko-2-english.gba).
Original ROM/save files are preserved. Later dialogue, menus/messages, save
previews, erase confirmations, records and approved artwork now have separate
insertion/validation families. They are outside this opening report's scope,
not all still Japanese.
Two earlier catalog sources are replaced by the
menu/name components; the Japanese keyboard body is intentionally retained.

[Latest native preview](../build/english/mansion-preview.png) ·
[Cumulative acceptance receipt](english-services-validation.json) ·
[Verified BPS patch](../build/english/torneko-2-english.bps)

The current ROM/BPS hashes, source/assets/tool hashes and the cumulative per-family native
acceptance reports are pinned in the receipt. A clean output-directory rebuild
produces identical ROM and BPS bytes. The earlier
[46-resource](english-opening-validation.json) and
[63-resource](english-home-validation.json) and
[79-resource](english-books-validation.json) receipts are historical records;
generated report paths now contain the current build.
The [initial mansion receipt](english-mansion-validation.json) also remains
historical. Current acceptance uses the user-selected
[Torneko 2 compact font](FONT_AUDITION.md); existing translations are unchanged,
with wrapping and native validation regenerated for its advances.

## Text and language review

[master.json](../translations/master.json) retains Japanese bytes, source hashes,
native evidence and editable English. Blank lines in English mark editorial page
boundaries. The compiler wraps within those sections using actual compact-font
advances, reserving eight pixels inside the 224-pixel story window. It preserves
speaker changes and rejects unsupported characters, unknown command families,
changed source tokens, and missing or reordered event commands.

[opening-review.json](../translations/opening-review.json) retains the drafts and
separate bilingual revisions. [first-dungeon-review.json](../translations/first-dungeon-review.json)
records the tutorial/UI review. [castle-review.json](../translations/castle-review.json)
and [castle-conversations-review.json](../translations/castle-conversations-review.json)
retain the royal audience and NPC drafts and revisions. These are separate
editorial passes by the same assistant, not independent human reviews.
Native screenshot review removed isolated fragments on extra pages; choice
invitations are phrased as explicit questions. NPC roles such as Chancellor
remain contextual project labels until official localized labels are established.
[destination-review.json](../translations/destination-review.json) records the
travel-menu review. [home-return-review.json](../translations/home-return-review.json) records the
home/village prose and dynamic sale notice review. The source/translation statuses in the viewer are separate
from the build's native acceptance receipts.

[glossary.json](../translations/glossary.json) records identities and evidence
quality. Tessie and Tipper follow modern DQ IV names, with secondary identity
references. Joy Chest, Joy Chamber and the named Magic Dungeon use PS1 fallback
terminology supported by secondary references; primary captures remain desirable.
The unnamed old man and friendly villager keep role labels. The prophecy's
`holy spirit` is a provisional rendering pending later context; no Torneko 3
entity is assumed. All prose is independently translated from the Japanese GBA
source, rather than reused from the PS1 localization.

## Insertion

The bank-zero header describes 17 groups and 90 four-byte text offsets. Native
consumers add the string base, group base and entry offset. Checked replacement
offsets resolve selected strings to appended ROM addresses. The bank is repacked
as a deterministic type-10 literal stream, still exactly 12,132 bytes after
decompression. Its original text and all unselected offset words remain intact.
Bank one uses the same mechanism for 15 selected offsets and remains 29,157
bytes after decompression. No RAM allocation or save-format change is needed.

Direct menu/help strings use individually verified pointer fields. Stair labels
retain their three rows and six-pixel inset; `Save & suspend` measures 84 of the
90 available pixels. The resume menu uses compact labels in its existing width;
`Erase log` is the display abbreviation for erasing the Adventure Log.
The travel question uses `Where to?`. Its home label keeps `{player}'s home` and
12 pixels of cursor clearance. The moved 152-pixel list accommodates seven of
the widest original name glyphs plus the English suffix; the question uses a
separate 56-pixel window. Selection behavior and destination IDs are unchanged.

`@B@` and `@C@` are event callbacks, not page breaks. Both native Japanese and
English routes preserve their order and flag effects, `14 → 0C → 14` in hex.
Left/Yes returns 1 and Right/No returns 0. The No branch uses the separately
verified family response at `event-bank-0.1190` and then rejoins the main scene.
The King's two `{player}` placeholders emit native byte `7E`. Each reserves 98
pixels, covering seven of the widest original name glyphs. Native rendering
reads the existing name record directly; no larger intermediate name buffer is
introduced. The original Japanese glyph fallback remains available.
See [MEMORY_MAP.md](MEMORY_MAP.md) for addresses, ownership and evidence.

## Native acceptance

- [Opening report](../build/english/dialogue-validation/report.json): both normal
  button routes reach first-floor movement; 58 reader calls and 5,805 glyphs pass
  source, bitmap, advance, width, row and page-wait checks. Rebuilt-bank output,
  adjacent memory guards and preserved registers match expectations.
- The same report includes 180 controlled getter calls: all 90 bank-zero
  group/index pairs on Japanese and English ROMs. Selected entries resolve to
  their appended strings; every untranslated entry keeps its original target.
  These calls are distinguished from natural gameplay coverage.
- [First-dungeon report](../build/english/first-dungeon-validation/report.json):
  nine UI reads and 409 glyphs pass; English resume reaches floor two, normal
  movement reaches its stairs, Stay remains there, and a checked branch snapshot
  verifies Descend to floor three and further movement. No-resume inventory loss
  and the erase action are not exercised.
- [Name/save report](../build/english/name-entry-validation/report.json): English
  names, real first-floor save/suspend, cold resume, movement and native Japanese
  save import pass on the cumulative ROM. Save-route input timing now follows
  the actual tutorial reader instead of a fixed number of A presses.
- [Royal audience report](../build/english/castle-validation/report.json): normal
  continuation through floor three reaches the English King, then returns town
  movement; 595 natural glyphs pass. Separate controlled reader probes cover `Torneko`, seven widest
  selectable English glyphs, and seven widest original Japanese name glyphs,
  checking substitution glyphs, widths, preserved registers and adjacent name
  fields. Only these controlled probes override the existing name record.
- [Castle NPC report](../build/english/castle-conversations-validation/report.json):
  six normal-input routes to five NPCs verify ten text reads and 640 glyphs, both guard choices
  (1/0), and movement after every conversation. Routes restore the same naturally
  reached English audience checkpoint between cases; later castle story states
  remain outside this scope.
- [Destination report](../build/english/destination-validation/report.json):
  English labels and cursor geometry pass in five cases. Normal routes verify
  Cancel (255) and resumed castle movement, or Home (1) and the expected
  rebuilt bank-one load. Three controlled name-record probes cover required English and
  widest English/Japanese names. The subsequent English home dialogue is checked in the separate home report.
- [Home report](../build/english/home-validation/report.json): five normal routes
  verify 20 reads and 2,366 glyphs, both Ed choices, sale formatting, colour
  spans, the heart and village movement. It also contains 428 controlled
  bank-one getters and 12 controlled name/amount display cases.
- [Books/banker report](../build/english/books-validation/report.json): eight
  natural routes verify the red/blue books, save choices, both banker branches,
  the old-man scene and mansion entrance/movement. Three controlled village-name
  displays and four cold save/load cases are separate from natural dialogue.
- [Shared-town report](../build/english/town-text-validation/report.json): original
  and English native loads, all 300 pointer relocations per ROM, unchanged
  allocation size and guarded decompression.
- [Mansion report](../build/english/mansion-validation/report.json): English cold
  continuation from a native Japanese 5F suspend through the Imp battle and safe
  return; all four family combinations, bank refusal/reconsideration and service
  cancellation. It checks 86 reads and 7,971 glyphs, plus three separately
  controlled seven-character name displays. This is not a full English 1F–6F run.
- The 44-test suite and original-ROM/toolchain acceptance pass. All 95 selected
  glyphs also pass separate native acceptance. The [resized early menus](MENU_LAYOUTS.md)
  pass their own checks; original-window candidate overflows remain visible in
  the audition. Later menu families remain outside that acceptance.

The test route reads the map and nearby actor records to choose ordinary inputs.
It now finishes adjacent fights, allows native HP recovery away from enemies,
and waits in a narrow passage for approaching groups to enter one at a time;
the earlier route could walk away while enemies attacked from behind. It never
patches health, inventory, random state or gameplay RAM. Later floors and other
enemy/terrain mechanics require further playtesting.

## Coverage audit

`python -m tools.audit_event_tables` (using the local `.venv`) enumerates all
1,046 entries across the seven known event-bank tables. The
[table inventory](../build/text-extraction/event-tables.json) retains source bytes,
identities, groups, indices and unresolved controls. The
[audit](../build/text-extraction/event-table-audit.json) also enumerates the
shared-town table: 300 pointers and 204 unique sources. It ties 809 of the current
2,814 scan candidates to exact known-table sources; 2,005 remain unresolved. Newly
verified sources are removed from the candidate queue when it regenerates.
There are 112 accumulated native sources: 75 in the event tables and six in
the shared town table.
Table
enumeration is separate from natural reachability and translation status.

These counts describe the known tables and documented routes. They do not
measure a percentage of all player-visible text or graphics in the game.

## Reproduce source discovery

```bash
# Both Japanese opening choices and their event commands.
.venv/bin/python -m tools.trace_opening_events

# Uses the disposable Japanese save produced by verify_name_entry.
.venv/bin/python -m tools.trace_first_dungeon --castle --output build/castle-arrival/research
.venv/bin/python -m tools.trace_castle_conversations
.venv/bin/python -m tools.trace_destination_menu
.venv/bin/python -m tools.trace_home_return

# Preserve accumulated editorial work; refresh the viewer and broad audit.
.venv/bin/python -m tools.extract_text
.venv/bin/python -m tools.audit_event_tables
.venv/bin/python -m tools.verify_text_sources
```

The first source trace (`tools.trace_opening`) supplies the original bank-load
checkpoint used by the seven-bank decoder verifier. Source discovery receipts
are separate from the English build's normal-input acceptance.

The [arrival-frame viewer](../build/arrival-research/index.html) records the
first dungeon entry, first castle transition, castle exit menu and return home.
The 600 new dungeon-entry frames and 480 earlier frames match fresh native
replays in their respective receipts. See [GRAPHICS_INVENTORY.md](GRAPHICS_INVENTORY.md)
for what is observed and what still needs discovery.

## Completed follow-up and next work

The four-step home-return batch is complete: native home/NPC discovery,
bank-one ownership and all getters, reviewed/validated English, and first
arrival/title resource tracing. [HOME_RETURN.md](HOME_RETURN.md) documents the
result and limits. The first dungeon card is separate tile artwork; title and
menu logos belong to different background resources.

The [home-book/banker follow-up](HOME_BOOKS.md) is also complete for its stated
scope. Green-book/reference/record and repaired-storage consumers subsequently
received separate native acceptance; see the current matrix.

The [mansion safe-recovery follow-up](MANSION_QUEST.md) is complete through bank
opening, including family choices and the next morning's blacksmith scene.

Bank transactions, populated inventory, record menus and the approved graphics
have since been integrated. Current next work is caller/branch and scene discovery
as listed in the matrix, using targeted native probes after disassembly.
