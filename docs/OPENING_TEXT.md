# Opening text discovery and extraction

The first discovery pass is implemented. A recorded route reaches the first
dungeon using normal buttons, and **30 distinct text sources** are matched to
their original resources through **32 native string-reader calls**. Twenty-five
sources belong to a compressed event bank; five are direct ROM strings. One
additional name-entry display comes from a transient RAM buffer. Its producer
and six-character Japanese editor limit are traced in [NAME_ENTRY.md](NAME_ENTRY.md).
The cumulative build now implements seven-character English input and verifies
native save persistence; that later work is separate from this discovery pass.

Open the [searchable Japanese catalog](../build/text-extraction/index.html).
The editable verified inventory is
[translations/master.json](../translations/master.json). English fields are
now populated for the [English opening batch](OPENING_ENGLISH.md). The following
research describes the initial source-discovery/extraction pass. The accumulated
catalog at that early stage contained 50 sources. Current insertion and gameplay
acceptance are documented in [the coverage matrix](COVERAGE_AUDIT.md); the opening
batch report retains its historical scope.

## Native route and source provenance

[config/routes/opening.json](../config/routes/opening.json) records the actual
input schedule: title/menu, the name editor with the displayed default retained,
the opening conversation and flashback, the first play-together choice answered
yes, first-dungeon help, and a movement input. Redundant inputs/waits are retained
so the original capture can be reproduced. The route ends at frame 19,688.

No gameplay RAM or register overrides are used on this route. Native breakpoints
observe reader arguments and bank loads. Screenshots preserve dialogue page
context; source-reader order retains the actual event order separately from
the catalog's sorted IDs. The later English batch covers both opening branches,
the remaining tutorial floors and first-castle conversations with additional
Japanese source traces; those were outside this initial route.

The menu and keyboard use ROM strings. The opening dialogue instead comes
from a decompressed bank at EWRAM `020241AC`. A write watchpoint identified the
type-10 LZ77 BIOS wrapper at `0805B48C` and its caller `0804D722`. The loader uses
the table at ROM `0014CD84`; the opening selects bank zero at ROM `0043FAAC`.

Immediately after the natural load, all **12,132 decoded bytes** match the
Python decoder. At each string-reader entry, the current bank identity and
offset locate the original decoded bytes, which must equal the actual RAM
bytes being read. This avoids assigning a permanent source identity to a RAM
address that another bank could later reuse.

Seven consecutive bank pointers have been decoded. Their total decoded data
includes scripts, tables and text; it is not all translation content. Each
record includes compressed start/exclusive end, compressed hash, decoded size
and decoded hash. Their individual decoded sizes range from 12,132 to 43,652
bytes. The exact ranges and native evidence are indexed in
[MEMORY_MAP.md](MEMORY_MAP.md#opening-text-and-compressed-bank-discovery-2026-09-13).

The [native trace](../build/opening-text/trace.json) also records the story-window
API at `08015A50`, window descriptors, dynamic text and screenshots. It does not
yet establish every story argument, script operand or insertion point.

## Lossless source catalog

Every verified entry retains:

- A stable ID and source space: direct ROM or a particular decoded bank.
- Start and exclusive end in that source space, exact original bytes and hash.
- Decoded Japanese with explicit byte-preserving command/glyph tokens.
- Native source-read evidence, frame, reader and window descriptor.
- Separate editable `english`, `notes` and `language_status` fields.

The tokenizer models native character consumption, including two-byte Japanese,
halfwidth characters, command operands and newline. For example, `04 40` is a
position command whose operand happens to be `@`; it must not begin an `@...@`
command. A zero-valued operand likewise must not terminate the field.

CP932 decoding is a readable view, not the source-byte authority. Unmapped
native glyphs remain explicit. `@...@` sequences retain their original bytes
while unverified event semantics remain unresolved. The later English batch
establishes `@B@`, `@C@` and player token `7E`; other command families remain open.
Unknown command semantics are
not treated as insertion-ready merely because their bytes can round-trip.

All 30 verified sources round-trip to the original bytes and retain their
token boundaries. Re-extraction preserves English, notes, language-review status
and other editorial metadata; previously retained sources from other routes
are not silently deleted. Duplicate IDs, changed source bytes and a different
base ROM are rejected.

## Broad scan and coverage limits

The first scan examines NUL-boundary starts across the original 8 MiB ROM and
the seven decoded banks. Its current filter requires at least four Japanese
characters, at least 35% Japanese among decoded text characters, no unresolved
tokens, and a maximum 8,192-byte source field.

The initial scan yielded **2,729 unverified candidates**. With the accumulated
50-source catalog excluded, regeneration now yields **2,714 candidates**, stored in
[candidates.json](../build/text-extraction/candidates.json). These are leads,
not confirmed source boundaries, pointer owners or player-visible sentences.
The catalog viewer defaults to verified sources and has a separate candidate
filter. The [scan report](../build/text-extraction/report.json) records examined
starts, rejections and per-resource counts.

The filter can miss short labels, command-heavy text, strings without a preceding
NUL, and alternate encodings. Candidate ranges may overlap or be false positives
inside code, tables, fonts or graphics. Rejection does not prove non-text.
Other compression families, computed references, graphic lettering and unvisited
gameplay remain outside this pass. There is no whole-game completion percentage.

## Verification and reproduction

```bash
.venv/bin/python -m tools.trace_opening
.venv/bin/python -m tools.extract_text
.venv/bin/python -m tools.verify_text_sources
./validate.sh
```

The trace creates a checkpoint immediately before the real bank-loader call.
The decoder verifier replays that call for all seven original bank resources,
changing only its source argument in a disposable session. Every output byte
matches the Python decoder; leading/trailing guards, callee-saved registers and
SP remain intact. The checkpoint is restored between cases. These six additional
bank selections are controlled decoder checks, not naturally reached scenes.

The BIOS performs a timing stall after decompression. These valid calls exceed
the generic debugger's default 100,000-step probe budget, so the verifier permits
up to 3,000,000 steps while still requiring the actual caller return breakpoint.

Failure-path tests cover truncated/invalid compression, overlapping back-references,
embedded control operands, unmapped glyphs, unterminated text and preservation of
editorial work during extraction. Full tooling acceptance remains separate from
text-source and gameplay coverage.

Evidence:

- [Native opening trace and source matches](../build/opening-text/trace.json)
- [Extraction and candidate counts](../build/text-extraction/report.json)
- [Seven native decoder cases and catalog round trips](../build/text-extraction/verification/report.json)
- [Retained acceptance receipt](opening-text-validation.json)

The supplied original ROM and save are unchanged. No new English insertion or
original ROM patch is part of this discovery pass.

## Subsequent work and current investigation

Opening command/relative-table insertion, castle/home/books/mansion text and
seven-character English name entry are completed milestones. Their original
recipes remain in [OPENING_ENGLISH.md](OPENING_ENGLISH.md) and
[NAME_ENTRY.md](NAME_ENTRY.md), including native save/cold-resume and Japanese-save
import. Later families include services, records, English inscriptions and custom
item names; consult [the current matrix](COVERAGE_AUDIT.md) for their exact scope.

Lead remaining source/caller discovery with disassembly, including computed
selectors and RAM producers, then execute targeted native scene checks. Assisted
access in disposable copies is appropriate; an ordinary playthrough does not gate
research. Graphics discovery continues in [GRAPHICS_INVENTORY.md](GRAPHICS_INVENTORY.md).
