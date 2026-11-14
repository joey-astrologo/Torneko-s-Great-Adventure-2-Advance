# False priest name-reader repair — November 14, 2026

The high-confidence reader audit found one remaining name branch selecting
Japanese despite an existing English translation. The user subsequently
authorized this fix. Its native negative control now reproduces `にせ神父` in
combat; the repaired ROM displays **False priest**.

## Change

Actor getter `08009ACC` loads the special name at `08009BAC`. Its table-base
literal, ROM `[00009BB4,00009BB8)`, now selects the existing private actor-fallback
table. Slot `10h` in that table points to reviewed results name ID 131 at
`088C55E4`. The name is 25 encoded bytes including termination and 60 pixels wide.
Dungeon actor ID 131 remains the distinct Hallucination identity.

Relative to the terminology checkpoint, only six bytes change across two words:
the reader literal and private table slot at ROM `[00963018,0096301C)`.
All other ROM bytes are identical. Allocations retain their addresses and sizes;
no new text, table allocation, gameplay instruction or save storage is added.
The original shared table and Japanese strings remain intact.

The branch still follows the original designation at EWRAM `[02003BA0,02003BA4)`.
Hallucination, blindness and invisibility retain their native priority; the
see-invisible exception and player-name exclusion are preserved. Removing the
designation restores the ordinary species name, including its level suffix.

## Verification and scope

The existing `tools.verify_actor_fallback` gate now includes this branch and
runs automatically through `build.sh`:

- 17 getter cases cover the previous Someone states, False priest, combined
  concealment, see-invisible, level 32767, designation removal and player-name
  exclusion. Source bytes, branch selection, scratch guards and return ABI pass.
- 12 complete outgoing/incoming combat cases check the getter's actual output,
  drawn name, full glyph/language/layout audit and native handler return. A
  separate hallucination-trap case still checks the native timer and Someone.
- The preceding terminology ROM passes the same cases as a negative control,
  requiring Japanese specifically for False priest. All 12 paired combat
  outcomes match for HP, complete player/target records and inventory.
- The ownership test checks all three reader literals and both changed private
  slots while preserving every other table entry. Standard validation passes
  192 tests. Independent ledger reconstruction, patch application and clean
  ROM/BPS reproduction pass.

Scene access uses disposable controlled actor states and original native
handlers. No text pointer or function result is substituted. This proves the
selected branch and actual combat rendering; ordinary False-priest encounter
activation remains untested. This initial checkpoint used focused checks;
the subsequent [release verification](RELEASE_VALIDATION.md) now completes the
full build, cumulative acceptance and save/reset checks on these same ROM bytes.
Historical family/save receipts retain their own ROM hashes.

ROM SHA-256: `9f127400b8e289f6acbb96bc5658663f6ba3a9780e064c642e4579199b5af746`.
BPS SHA-256: `d652dc4038663bbfeec5058db7006709c1868abeea3afecd39e8019e4200753f`.
The build remains development status, with 3,814 text resources and 20 graphics.
The title remains Mystery Dungeon; in-game dungeon wording remains Magic Dungeon.

[Checkpoint ZIP](../build/releases/2026-11-14-false-priest.zip) ·
[Receipt](../build/accepted/3814-false-priest/completion.json) ·
[Native report](../build/false-priest-candidate/actor-fallback-validation/report.json) ·
[Negative control](../build/false-priest-candidate/negative-control/report.json) ·
[Exact byte scope](../build/false-priest-candidate/change-scope.json) ·
[Paired outcomes](../build/false-priest-candidate/paired-comparison.json) ·
[Pre-fix audit](../build/reader-audit-nov14/README.md).

```sh
.venv/bin/python -m tools.build_english --output build/false-priest-candidate
.venv/bin/python -m tools.verify_actor_fallback --source build/false-priest-candidate
.venv/bin/python -m tools.verify_actor_fallback --source build/accepted/3814-dungeon-terminology --output build/false-priest-candidate/negative-control --expect-japanese-priest
./validate.sh
.venv/bin/python -m tools.build_english --output build/false-priest-rebuild
```

The accepted terminology checkpoint and all earlier releases remain available.
