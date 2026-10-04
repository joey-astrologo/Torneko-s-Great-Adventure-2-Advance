# Floor menu localization and regression checks

The user reported Japanese after selecting **Floor** on an empty tile on the
first floor of Mysterious Meadow. This was reproduced with ordinary buttons
from a fresh English opening on 2026-10-02. It now displays
**There is nothing underfoot.**

The subsequent [reader-path audit](READER_PATH_AUDIT.md) found and fixed the
fourth caller of this same modal: empty inventory. The current check has14
cases. The13-case results and hashes below record the initial Floor correction;
the additional finding is in that follow-up. Current build identity and later
acceptance are in [the coverage matrix](COVERAGE_AUDIT.md).

The earlier note about a separate Japanese status-expiry message referred to
fear/dancing recovery through queue return080096F9. Those are slots3E0/3C0 in
the subsequent seven-message expiry repair, not an eighth outstanding message.
Both repairs remain in cumulative native formatting/rendering checks;
see [status-expiry evidence](../build/status-expiry/acceptance.json).

[Before screenshot](../build/floor-menu/negative-control/empty-merchant/panel-0.png) ·
[Fixed screenshot](../build/floor-menu/native/empty-merchant/panel-0.png) ·
[Full native gallery](../build/floor-menu/native/index.html) ·
[Acceptance receipt](../build/floor-menu/acceptance.json)

## Why the previous checks missed it

The sentence was already reviewed and inserted as a static message-queue
notice. The Floor command displays it through a separate direct modal reader,
which still fetched the Japanese pointer. Testing the translated queue notice
did not test this menu consumer.

The independent dungeon audit opened the root menu but never selected Floor on
an empty tile. Its 11 scenarios therefore could pass while this ordinary menu
was still Japanese. This is another concrete coverage failure, alongside the
previously missed location banner. It does not support a complete-localization
claim.

## What changed

Two original table-pointer literals now select a private copy for the empty
Floor message and the related Items, Trap and Stairs refusal messages. Four
notices reuse existing English resources. The transformed refusal uses
**Can't do that while transformed.** in this narrower context, preserving the
full condition within 162 of the original 168 pixels. The empty-floor notice
uses 139 pixels; the other refusals use at most 166.

The original one-line window, font, spacing, status behavior and save layout
are unchanged. Every previous allocation and all unrelated ROM bytes are
preserved; the [delta receipt](../build/floor-menu/delta.json) identifies both
pointer patches and the two appended allocations. These are additional readers
of existing reviewed sources, so the count remains 3,770 text resources and
20 graphics.

## Verified scenarios

Every case uses normal menu buttons after the recorded setup, opens the panel
three times and cancels without executing the selected item, trap or stairs
action. The text audit observes all shared-reader glyphs rather than accepting
only known translated pointers.

| Scenario | Setup and result |
| --- | --- |
| Empty Floor on Mysterious Meadow 1F | Ordinary fresh opening; English notice, original geometry and parent restoration pass. |
| Empty Floor in warrior and mage command modes | Controlled vocation byte; complete menu and notice pass in both layouts. This does not establish native class unlocking. |
| Floor with an item | Naturally carried Big bread dropped through the ordinary inventory menu in the earned mansion save; Big bread and Take, Eat, Throw, Swap, Info appear in English. |
| Stairs | Ordinary first-floor walk, cancellation of the automatic prompt, then root-menu Stairs; Descend, Stay here, Save & suspend appear in English. |
| Trap | Controlled visible trap selector underfoot; ordinary selection displays Step and Stay. Trap activation is excluded. |
| Floor while transformed or frightened | Controlled existing status byte; both refusals display in English. |
| Trap while transformed, frightened or dancing | Controlled trap/status setup; all three refusals display in English. |
| Stairs while frightened or dancing | Real staircase with controlled existing status byte; both refusals display in English. |

All **13 cases pass**, comprising three ordinary routes and ten controlled
cases, with **7,808 observed glyph draws** and **30 complete modal returns**.
The checks cover single-line bounds, repeated pixels, native caller/stack
preservation, restoration of the location/status panels and background beneath
the modal, and unchanged inventory, inspected tile and battery after cancellation.
Background restoration is compared independently of animated character sprites.
Complete screenshots of the empty, transformed, frightened, item, trap and
stairs panels were visually inspected.

The same audit rejects the old ROM in all ten modal cases for actual Japanese
glyph output, without needing a registered translated resource pointer. The
three other branches pass on both builds. The ground-item row's original blank
marker has an explicit exception restricted to its first glyph, original
coordinates and one-row window; there is no general Japanese-glyph allowance.

ROM SHA-256:
`dd21b782b9a0bfa98722e664036cc29825afb466f3994c442d8059b08c8e0c89`.
BPS SHA-256:
`d10819b6f3ae184f1e8a332c7b2a983c3f1309b2c6cce5c5e385c32ca0be2f3a`.
Both root build artifacts are updated; applying the patch reproduces the ROM.
The previous ROM and ledger remain in `build/floor-menu/pre-fix/`.
The additional39 root-menu cases, six Step/Stairs choice cases and135 unit tests
also pass on this build. The earlier11-scenario dungeon/town audit was not rerun
as part of this bounded correction.

## Reproduce

```sh
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.verify_floor_menu
```

The new check runs from `build.sh`. Its item case uses the retained quest-earned
save already required by the service checks. The empty and stairs cases replay
the recorded fresh opening. Fixture hashes, source hashes and actual inputs
are retained in the reports.

To inspect the historical failing control when the archived build is available:

```sh
.venv/bin/python -m tools.verify_floor_menu --source build/floor-menu/pre-fix --output build/floor-menu/negative-control --allow-findings
```

The fallback “But nothing happened.” pointer is also bound to English, but its
selector is not reached by the successful menu routes above. Item effects,
trap activation, status expiry, other vocations' gameplay and other menu
families remain separate. This correction does not constitute a new full
cumulative regression or establish whole-game localization coverage.

Source ownership and address ranges are recorded in
[Memory map](MEMORY_MAP.md#floor-command-and-status-refusal-modals-2026-10-02).
