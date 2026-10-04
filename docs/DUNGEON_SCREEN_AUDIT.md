# Dungeon and town screen audit — September 30

This page retains the first bounded screen-audit cohort. Later unfiltered cohorts,
the current build and remaining gaps are in [the coverage matrix](COVERAGE_AUDIT.md).
A generated gallery's own report hash determines which build its frames show.

[Native screenshot gallery](../build/coverage-audit/index.html) ·
[Scenario matrix and receipt](../build/coverage-audit/acceptance.json)

This audit checks **11 bounded scenarios: nine ordinary routes and two
controlled cases**. It does not establish whole-game completion. The earlier
Japanese pickup report was not reproduced in these routes; other dungeon,
item and save states remain open.

## Observed scenarios

| Scenario | Evidence and result |
|---|---|
| Fresh Mysterious Meadow, floors 1–3 | Ordinary opening and exact input replay reach all 14 expected pickups, their tutorials, combat, stairs and first royal dialogue. No unclassified drawn glyphs. |
| Mansion 6F arrows and gold | Earned save, ordinary walking: 6 Iron arrows merge into the carried stack; 321 gold increases the wallet correctly. Bodkin archer damage/defeat messages also observed. |
| Item Info | Ordinary Big bread selection; inventory, action list, description and return to inventory checked. |
| Eat bread | Ordinary Eat consumes the item; both the item-use message and “You're full!” are observed. |
| Drop and walk back | Ordinary Drop creates the floor item; walking away and returning picks it up. |
| Inventory full | **Controlled:** vacant inventory records are filled after a native Drop. Walking back displays both refusal and standing-on-item clauses; inventory and floor item are preserved. |
| Maximum gold | **Controlled:** existing floor gold is changed from 321 to 32767. Real walking, collection, wallet update and one-line message follow. |
| Town root outdoors | Ordinary B/cancel/reopen outside the bank: Items and Option, no location banner. |
| Town root indoors | Ordinary B/cancel/reopen at the home/shop book: same two fields, no location banner. |
| Bank round trip | Ordinary deposit and withdrawal of the earned 1166 gold, including root labels, amount editor, balances and acknowledgements. Final balances match the start. |
| Repaired storage round trip | Ordinary marking, deposit, stored-item list, withdrawal and empty-storage acknowledgement. Naturally carried bread/staff retained; no save written. |

The complete run records **149 shared reader calls, 130 nonempty rendered
message-queue payloads and 7,068 glyph draws**. There are no unclassified glyphs,
unreadable captured streams or native-window boundary violations in these
cases. These are observed events, not unique translated-source counts.

## What changed in the checks

`tools.screen_text_audit` observes every call to the shared reader, formatter,
message queue and glyph renderer during a scenario. It does not start with a
list of translated resource pointers and does not skip unknown readers.
The reports retain raw bytes, source/caller pointers, actual drawn glyphs,
window coordinates, inputs, source/build/fixture hashes and tool hashes.

Queue entry can still receive a Japanese source pointer which the existing
localization hook replaces. The audit also observes the **post-hook payload at
CPU 080158CE and its actual glyph draws**, so entry arguments are not mistaken
for visible text. The native full-belly notice demonstrates this distinction.
Incoming combat fragments likewise become one complete English line when they
fit; the pre-hook fragments alone are not the displayed message.

Timed screenshots are captured inside the existing input frame schedule after
text settles. They add no emulated idle frames, and retain short-lived messages
that have disappeared by the end of a button's normal wait. Adding one idle
frame changed later dungeon generation in an exploratory replay; that failed
route is retained under `build/coverage-audit/tutorial/`, not counted as a pass.
The accepted exact replay independently requires all 14 pickup identities,
floors and positions to match.

Exceptions are narrow and recorded: original inventory markers at their row
start, native punctuation from its specific handler, and an exact saved player
name at the start of a queued substitution. The earned Japanese save uses
**トルネコ**; “トルネコ ate Big bread.” retains that name intentionally. The
fresh tutorial save uses **Torneko**. There is no blanket Japanese-glyph allowance.

HUD/artwork use other rendering paths. Selected complete screenshots were also
visually inspected, including gold, arrows, food, full inventory, description,
bank and storage screens. This does not claim every graphics path or every
transient frame has been audited.

## Gold spacing correction

The ordinary gold pickup exposed **“Picked up 321Gold.”** The corrected message
is **“Picked up 321 Gold.”** A single private formatter adds the approved
three-pixel space. The one-line messages end at 99px for 321 and 111px for
32767, below the 216px message budget.

Only ROM literal `[0000F444,0000F448)` and one appended 11-byte format change.
Every previous allocation, patch and unrelated ROM byte remains identical;
no font, window, numeric value or save field changes. Ownership and signed
halfword bounds are recorded in [MEMORY_MAP.md](MEMORY_MAP.md).

Additional checks pass: 22 item-format/description cases covering both gold
definitions and four native inventory items; five walking-pickup regressions;
135 unit tests. The new check rejects the retained pre-fix gold build. The
unfiltered glyph audit also rejects the archived Japanese location banner,
without registering that reader as a translated resource first.

ROM SHA256 for this September 30 audit:
`c93c573ae1d0d4c643a580c04c8b385bd3d1b5381913763aca2abab078c22ea4`.
BPS SHA256:
`72af3d0f428cd60d483ea684f364ab2b6eef785aa46a24dcb7b9c0a77379a67c`.
The root ROM/BPS pair is updated and patch application reproduces the ROM.
The historical correction kept 3,770 reviewed text resources and 20 graphics; this is a format
correction, not another reviewed Japanese source or full cumulative acceptance.

The October 2 [Floor-menu correction](FLOOR_MENU.md) supersedes this exported
ROM. This earlier11-scenario matrix did not select Floor on an empty tile and
must not be cited as coverage of that menu state. Its reports retain the
September30 build identity.

## Reproduce

```sh
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.audit_dungeon_screens
.venv/bin/python -m tools.audit_town_screens
.venv/bin/python -m tools.accept_screen_audit
```

The retained quest-earned battery saves documented in the existing service
workflow are required. These commands run from `build.sh` too. Historical
negative controls additionally require the archived builds:

```sh
.venv/bin/python -m tools.check_screen_audit_controls
.venv/bin/python -m tools.accept_screen_audit --historical-controls
```

Pending work includes other item-use effects and refusals, custom/unidentified
names, further town services and their states, later dungeons/classes, records
and ending routes. The [coverage assessment](COVERAGE_AUDIT.md) keeps those gaps
separate from this completed scenario matrix.
