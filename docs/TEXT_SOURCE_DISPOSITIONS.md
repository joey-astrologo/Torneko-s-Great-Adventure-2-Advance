# Dispositions for the former 62-source / 34-fragment backlog

Updated 2026-10-07. **All 96 records now have individual investigation
dispositions; none has a confirmed active untranslated reader in the audited
graph.** They are no longer an undifferentiated list awaiting the same searches.
Their source bytes remain untranslated and preserved. No ROM insertion or new
release was warranted by this pass.

“Dormant” below means excluded by the recovered callers and valid native data
domains. It does not mean globally unreachable under arbitrary machine execution,
safe to delete, or proof that every game scene has been observed. Reopen a record
when a concrete new caller, script entry or valid selector contradicts its bound.
Unknown synthesized pointers and corrupt/imported out-of-domain RAM are excluded.

## What changed in the investigation

- Town: 20 service functions, 167 table-read sites and 185 selected slots.
  SSA covers branch joins without the earlier path budgets. Blacksmith tips are
  clamped to slots 12–22. Gaibara’s sole caller produces 0–12; zero skips its
  extra line, so that read uses slots 39–50. Remi’s profiles, vocation maps and
  storage’s children are accounted for. None selects the ten retained records.
- Shared text: 293 function/block exports, 688 distinct read sites, including
  every one of the older tracer’s 658 sites. ROM literals remain immutable
  across decompiler call aliases; unknown RAM stays unknown. Computed domains
  come from the native lookup tables, caller constants and record producers.
  None selects the 52 retained sources. The exact-pointer census independently
  limits their literal ownership to the original shared table.
- Event fragments: rebuild the current ROM’s NPC roots from its actual actor
  records, including the two repaired shopkeeper selectors. The 458 roots have
  683 modal reference contexts. Both event interpreters, the nine direct getter
  call sites and 93 bank-relative tutorial topics in the recovered contexts add
  no fragment reader. Three candidate references are after END; one is an
  operand-byte coincidence; thirty have no selector in the script spans.

The cross-check also found and fixed a **verification bug** in
`audit_definition_selector_domains`: later spell-menu loop visits overwrote the
first read for the seeded definition. The audit now retains that first read and
checks it against the definition’s target kind. All 61 spells now cover their
actual nine target labels, in both menu and Info paths. The 250 definition cases,
378 reads and four staff-effect bindings pass. Four older unconstrained-loop
observations are rejected because their target indexes cannot come from any of
the 61 native records; those observations and reasons remain in the receipt.
No game-text change resulted from this correction. All 191 unit tests pass,
including four new data-flow controls.

The catalog now reports language and investigation status separately:
3,552 reviewed sources, 96 untranslated sources with these dispositions, and
28 retained/component records. **Untranslated sources without an investigation
disposition: 0.** This is source accounting, not a whole-game completion percentage.

Reproducible checks:

```sh
.venv/bin/python -m tools.audit_definition_selector_domains
.venv/bin/python -m tools.audit_town_source_dispositions
.venv/bin/python -m tools.audit_shared_source_dispositions
.venv/bin/python -m tools.audit_event_fragment_dispositions
.venv/bin/python -m tools.text_inventory
```

The inventory consumes the checked-in, source-hash-pinned
[disposition record](../config/text-source-dispositions.json). Its recorded
receipt hashes identify this audit; changing the source cohort or discovering
another selector requires reconciling those dispositions.
[Town receipt](../build/oct07-source-dispositions/town-dispositions.json) ·
[Shared receipt](../build/oct07-source-dispositions/shared-dispositions.json) ·
[All shared read domains](../build/oct07-source-dispositions/shared-read-domains.json) ·
[Event receipt](../build/oct07-source-dispositions/event-fragment-dispositions.json).

## Ten town records

All are dormant in the recovered service graph. Table indexes are decimal.

| Source | Slots | Description |
|---|---|---|
| `town-common.1085` | 1 | Superseded two-item blacksmith offer |
| `town-common.10b7` | 2 | Superseded matching-item blacksmith offer |
| `town-common.20e7` | 35 | Old synthesis farewell |
| `town-common.212e` | 37 | Old synthesis selection instructions |
| `town-common.2ae2` | 214–299 | Version-error filler in 86 unused table slots |
| `town-common.3e36` | 180 | Old storage deposit-choice menu |
| `town-common.3fb5` | 185 | Old storage withdrawal-choice menu |
| `town-common.40db` | 193 | Old storage save question |
| `town-common.410d` | 195 | Old storage save confirmation |
| `town-common.4122` | 196 | Old storage farewell |

## Fifty-two shared records

All are dormant in the recovered shared-reader graph. Table indexes are hex.
Descriptions identify retained sources; they are not new translation proposals.

| Source | Slots | Description |
|---|---|---|
| `rom.00060344` | 25D | Legacy spell immunity message |
| `rom.00060984` | 214 | Rejected Spellbook inscription |
| `rom.000611e0` | 1D8 | Old Items / Spells menu |
| `rom.000611f4` | 1D7 | Old Items / Map menu |
| `rom.00061248` | 1D4 | Attached label |
| `rom.00061294` | 1D0 | Old skill editor label |
| `rom.000615a4` | 1B4 | Legacy rank / score result (reason 30) |
| `rom.000618a8` | 18F | Priest does not notice |
| `rom.00061918` | 18D | Stone of Whispers acquisition |
| `rom.000619b4` | 185 | Master’s grave |
| `rom.00061cb4` | 170 | Memory-card recheck |
| `rom.00061cd0` | 16F | Sound label |
| `rom.00061d90` | 165 | Memory-card log created |
| `rom.00061df0` | 163 | Create a two-block memory-card log |
| `rom.00061e60` | 162 | Memory-card read retry |
| `rom.00061ea0` | 161 | Memory card not inserted |
| `rom.00061f00` | 15F | Memory-card reading |
| `rom.00061f50` | 15E | Continue reading memory card |
| `rom.00061f74` | 15D | Unformatted memory card |
| `rom.00061fa4` | 15C | Insufficient memory-card blocks |
| `rom.0006201c` | 15A | Memory-card checking |
| `rom.0006206c` | 159 | Memory card exchanged |
| `rom.000620a8` | 157 | No memory-card log |
| `rom.000620f0` | 155 | Memory-card writing |
| `rom.00062140` | 154 | Memory-card format failure |
| `rom.0006216c` | 153 | Memory-card format completed |
| `rom.00062188` | 152 | Memory-card formatting |
| `rom.000621c4` | 151 | Continue memory-card recording |
| `rom.000621e4` | 150 | Format memory-card question |
| `rom.0006223c` | 14F | Memory-card read failure |
| `rom.00062264` | 14E | Checking card slot 1 |
| `rom.000622b0` | 14D, 167 | Memory card not properly inserted |
| `rom.00062324` | 14B | Legacy suspend warning |
| `rom.00062b58` | 11A | Half-price shop offer |
| `rom.00062edc` | FA | Actor hit message |
| `rom.00063140` | E3 | Appearance message |
| `rom.000632d8` | D4 | Pot contents absorbed |
| `rom.0006355c` | B5 | Projectile fired |
| `rom.00063654` | AA | Legacy Silver arrow name |
| `rom.00063668` | A9 | Legacy Iron arrow name |
| `rom.0006367c` | A8 | Legacy Wooden arrow name |
| `rom.000638d8` | 8E | Instant-death message |
| `rom.000638e8` | 8D | Splitting message |
| `rom.0006396c` | 88 | Echoed in vain |
| `rom.00064004` | 45 | Sleep avoided |
| `rom.00064218` | 36 | Partial hunger recovery |
| `rom.00064360` | 29 | Cannot place item |
| `rom.00064500` | 1A | Old Stairs / Tactics menu |
| `rom.00064514` | 19 | Old Trap / Tactics menu |
| `rom.00064528` | 18 | Old Floor / Tactics menu |
| `rom.0006453c` | 17 | Old Items / Skills menu |
| `rom.00064888` | 7 | Old Descend / Stay choices |

## Thirty-four event fragments

The source characters remain untouched. The two previously approved contextual
repairs are separate and remain accepted; see [the event audit](EVENT_STUB_AUDIT.md).

| Source | Disposition |
|---|---|
| `event-bank-0.1041` | No selector in shipped script graph or recovered getters |
| `event-bank-0.12c3` | No selector in shipped script graph or recovered getters |
| `event-bank-0.26bd` | No selector in shipped script graph or recovered getters |
| `event-bank-1.0721` | No selector in shipped script graph or recovered getters |
| `event-bank-1.42d4` | No selector in shipped script graph or recovered getters |
| `event-bank-1.42d7` | No selector in shipped script graph or recovered getters |
| `event-bank-1.43bf` | No selector in shipped script graph or recovered getters |
| `event-bank-1.4982` | No selector in shipped script graph or recovered getters |
| `event-bank-1.513c` | No selector in shipped script graph or recovered getters |
| `event-bank-1.513f` | No selector in shipped script graph or recovered getters |
| `event-bank-1.5142` | No selector in shipped script graph or recovered getters |
| `event-bank-1.5145` | No selector in shipped script graph or recovered getters |
| `event-bank-1.5148` | No selector in shipped script graph or recovered getters |
| `event-bank-2.37e8` | No selector in shipped script graph or recovered getters |
| `event-bank-2.37eb` | No selector in shipped script graph or recovered getters |
| `event-bank-2.382a` | After unconditional END at NPC bank 2:5AE |
| `event-bank-2.382d` | After unconditional END at NPC bank 2:5AE |
| `event-bank-2.3830` | After unconditional END at NPC bank 2:5AE |
| `event-bank-3.03b3` | No selector in shipped script graph or recovered getters |
| `event-bank-3.03b6` | Inside operands at event ROM 43EB62; no entry at43EB65 |
| `event-bank-3.03b9` | No selector in shipped script graph or recovered getters |
| `event-bank-3.03bc` | No selector in shipped script graph or recovered getters |
| `event-bank-3.03f9` | No selector in shipped script graph or recovered getters |
| `event-bank-3.1c23` | No selector in shipped script graph or recovered getters |
| `event-bank-4.0d28` | No selector in shipped script graph or recovered getters |
| `event-bank-5.0e5d` | No selector in shipped script graph or recovered getters |
| `event-bank-5.0e60` | No selector in shipped script graph or recovered getters |
| `event-bank-5.131c` | No selector in shipped script graph or recovered getters |
| `event-bank-5.4c55` | No selector in shipped script graph or recovered getters |
| `event-bank-5.4c58` | No selector in shipped script graph or recovered getters |
| `event-bank-5.5254` | No selector in shipped script graph or recovered getters |
| `event-bank-6.21a8` | No selector in shipped script graph or recovered getters |
| `event-bank-6.426d` | No selector in shipped script graph or recovered getters |
| `event-bank-6.4270` | No selector in shipped script graph or recovered getters |
