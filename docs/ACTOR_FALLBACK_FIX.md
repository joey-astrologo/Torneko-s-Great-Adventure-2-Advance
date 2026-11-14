# Unknown actor names in combat

The November 14, 2026 user report describes Japanese monster names after a
hallucination trap and when fighting invisible enemies. The combat name getter
still selected `何者か` even though its approved translation, **Someone**, was
already inserted for results screens. This is a localization reader omission.

## Repair

Getter `08009ACC` has two unknown-name return paths. Loads `08009B3E` and
`08009B6E` select shared-table slot `414h` through literals at ROM `00009B48`
and `00009B78`. Both originally returned `08062DCC` (`何者か`).

The repair redirects those two literals to a private copy of the shared table.
Only its `414h` slot differs: it points to the existing reviewed results
ID0/Someone at `088C49A0`. The original table and strings, all selector and
gameplay instructions, other actor-name branches and save format are preserved.
The allocator owns the new table at ROM `[00963010,00963A48)`; it adds 2,616
bytes of table data within the existing 16 MiB ROM. The text count stays 3,814.

The fallback also applies to blindness and the native species-name concealment
flag. The repair preserves the original selection rules, including invisibility
precedence and the see-invisible exception. It never reveals a hidden identity.
Someone is 15 encoded bytes including termination and 42 pixels wide, below
the established 64-byte actor field and the previously accepted name maxima.

## Verification

`tools.verify_actor_fallback` cold-loads a copied native battery save into the
matching ROM; it does not relabel an old core state. Its controlled cases use
real actors and original code, with every RAM/register override and input
schedule recorded. No source name or function result is substituted.

- Ten native getter cases cover visible, hallucinating, blind, invisible,
  combined conditions, see-invisible, concealed species and level 32767.
  Each also checks the normal name after controlled condition removal.
- Eight complete combat-owner cases cover outgoing and incoming attacks in
  normal, hallucination, invisibility and blindness states. They check the
  actual getter result, combat log, glyphs, layout and original handler return.
- A separate complete hallucination-trap handler case checks its messages,
  native timer value 50 and the resulting unknown name.
- Getter scratch guards and ABI, combat/trap ABI, source files and battery saves
  are checked. Combat scene access uses controlled actors, positions and HP;
  these are non-death tests, not ordinary encounter or trap-placement evidence.

The same cases run on the preceding release as a negative control: they must
observe Japanese in the affected combat logs. Compare their gameplay outcomes
with the repaired ROM rather than treating text differences as gameplay changes.

```sh
.venv/bin/python -m tools.build_english --output build/actor-fallback-candidate
.venv/bin/python -m tools.verify_actor_fallback --source build/actor-fallback-candidate
.venv/bin/python -m tools.verify_name_entry --output build/actor-fallback-candidate/name-entry-validation
./validate.sh
```

The focused verifier also runs in `build.sh`. The previous complete cumulative
suite retains its own ROM identity; this repair does not claim a fresh replay
of every localization family.

Accepted ROM: `82e2204f95c5c300054b619ebacefa6fb3f4b4ea4e1e92b6c8f47f7b87de02d6`.
Standard validation passes 192 unit tests; English save/cold-load checks,
independent ledger reconstruction, BPS application and clean ROM/BPS rebuilding
pass. All eight paired combat outcomes preserve the complete player/target
actor records and inventory compared with the preceding release.

[Checkpoint ZIP](../build/releases/2026-11-14-actor-fallback.zip) ·
[Acceptance receipt](../build/accepted/3814-actor-fallback/completion.json) ·
[Native report](../build/actor-fallback-candidate/actor-fallback-validation/report.json) ·
[Previous-release negative control](../build/actor-fallback-candidate/negative-control/report.json).

## Other findings

The broader read-only screening found a separate `False priest` name branch
still selecting Japanese. Its scene reachability and display require follow-up;
this repair leaves it unchanged. The two confirmed Mystery Dungeon/Magic Dungeon
dialogue inconsistencies also remain separate from this Issue 1 fix.
They are corrected in the subsequent [Issue 2 checkpoint](DUNGEON_TERMINOLOGY.md).
The False-priest branch is corrected and natively checked in the later
[name-reader checkpoint](FALSE_PRIEST_FIX.md).

The earlier reader report already retained both unknown-name reads, but its
unresolved-source summary filtered on language status and family. Someone was
classified as a reviewed actor name. Future screening must inspect actual
consumer bindings for reviewed/inserted sources too, including later translation
hooks; an unchanged Japanese pointer alone is not proof of a display defect.
