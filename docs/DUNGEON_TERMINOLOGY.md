# Magic Dungeon dialogue correction — November 14, 2026

The user requested replacing every dialogue use of Mystery Dungeon with Magic
Dungeon. This follows the existing glossary: **Magic Dungeon** for the name,
**magic dungeon** for the generic phenomenon.

Exactly two inserted passages change:

- `event-bank-1.0d86`: Tessie says the castle basement has turned into a
  **magic dungeon**. The master and holy-flame review agree.
- `dungeon-story.14`: the old man says the **Magic Dungeon** has spread so far.

The superseded Soldier draft `shared.80c` is also corrected, with its static
measurement and disposition catalog hash refreshed. Its inserted review already
used magic dungeon. Historical review wording is retained as provenance, with
dated terminology revisions recording the new text. Title artwork is unchanged.

The case-insensitive scan covers 6,936 current English/draft fields and 3,961
compiled encoded records, allowing whitespace between words. There are no
remaining old-term matches in those fields or compiled strings. Comparing the
previous ledger proves exactly two encoded payloads changed. The existing
allocator accounts for shifted resources and pointer replacements; this adds
no resource or ownership range.

Native verification on ROM
`d8e2b42cfc345d7c1479facb07630f8018d49bc66f9419557610f300969e188c`:

- Tessie: all four pages, 153 glyph preparations, layout and reader return.
  Access uses a controlled source argument at an ordinarily reached reader.
- Old man: index 14 through its original table load and modal, all 11 pages
  and 35,196 pixel checks, caller return and save/item guards. Cutscene access
  is controlled; this run does not repeat the identity-choice branches.
- All seven native event-bank loads and 1,046 getters resolve their ROM-bound
  targets, including Tessie's changed source.
- The Issue 1 regression passes ten name-getter cases with recovery, eight
  combat cases and the separate hallucination-trap handler.
- Shared-draft source/placeholder/measurement audit, 192 unit tests and standard
  validation pass. Clean ROM/BPS reproduction, independent patch application
  and allocator-ledger reconstruction pass.

These are targeted checks, not a whole-game replay. Earlier family/save receipts
retain their own ROM identities. No new scene-reachability claim is made.

[Checkpoint ZIP](../build/releases/2026-11-14-dungeon-terminology.zip) ·
[Receipt](../build/accepted/3814-dungeon-terminology/completion.json) ·
[Catalog and compiled-string scan](../build/dungeon-terminology-candidate/terminology-validation/catalog-and-build.json) ·
[Tessie rendering](../build/dungeon-terminology-candidate/terminology-validation/tessie/report.json) ·
[Old-man rendering](../build/dungeon-terminology-candidate/dungeon-story-validation/report.json).

Reproduction from the repository root, after the candidate build:

```bash
.venv/bin/python -m tools.build_english --output build/dungeon-terminology-candidate
.venv/bin/python -c "import runpy; runpy.run_path('build/dungeon-terminology-candidate/verify_terminology.py')"
.venv/bin/python -m tools.verify_dungeon_story --source build/dungeon-terminology-candidate --only 14
.venv/bin/python -m tools.research_event_relocation --cumulative --source build/dungeon-terminology-candidate
.venv/bin/python -m tools.verify_actor_fallback --source build/dungeon-terminology-candidate
.venv/bin/python -m tools.audit_shared_drafts
./validate.sh
```

The focused script and its evidence are preserved in the checkpoint. The earlier
Issue 1 archive remains at `build/accepted/3814-actor-fallback/`.
