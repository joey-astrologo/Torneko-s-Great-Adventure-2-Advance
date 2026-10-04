# Dungeon-menu location banner correction

On 2026-09-30 the user reported Japanese `ちょっと不思議の草原` in the
dungeon menu. **All 13 names in that banner still used the Japanese table.**
English names existed in the results/history table and arrival artwork, but
this reader had never been redirected. This was a missed display path for
reviewed text.

Earlier checks selected command/status resources and tested geometry, buffer
bounds and restoration. They did not require every visible field to be English.
The banner appeared in screenshots, but its Japanese glyphs were outside those
checks. Passing those tests did not establish a fully localized menu, and the
visual review missed the remaining Japanese.

## Correction and visual confirmation

- [Native screenshots for all 13 locations](../build/location-banner/index.html)
- [Mysterious Meadow menu](../build/location-banner/native/11-mode-0/open.png)
- [Native coverage and previous-build rejection](../build/location-banner/report.json)
- [Acceptance and exact byte delta](../build/location-banner/acceptance.json)
- [Latest ROM](../build/torneko-2-english.gba) · [BPS patch](../build/torneko-2-english.bps)

`tools.location_banner` redirects one four-byte reader literal to the existing
English table. No other ROM byte changes. Existing text/graphics allocations,
instructions, geometry and save fields are preserved. ROM SHA-256:
`7716f8c51c452499a1bb651acd24ccd20d3833531188fa66f0732cf3bb8307c8`.
BPS SHA-256:
`ea883740d8099fa6e5d2bbc7cebba2d2f8b1de6662fa1cbab5811cb84a61f203`.

The banner has **168 usable pixels**, one row, normal proportional spacing
and no cursor or dynamic fields. Names are read directly from ROM, with no
new formatter buffer. The longest encoded name is 37 bytes including NUL.

| Selector | English name | Width / 168px |
|---|---|---:|
| 0 | Banker's Mansion | 89 |
| 1 | Cemetery Dungeon | 90 |
| 2 | Castle Dungeon | 76 |
| 3 | Lost Forest | 58 |
| 4 | Mt. Fiery | 45 |
| 5 | Toro Ruins | 53 |
| 6 | Magic Dungeon | 72 |
| 7 | More Magic Dungeon | 98 |
| 8 | Ordeal Mansion | 74 |
| 9 | Sword Dungeon | 74 |
| 10 | Mage Dungeon | 69 |
| 11 | Mysterious Meadow | 93 |
| 12 | Well | 18 |

## Coverage added

The new check covers all 13 names in each of three command modes: **39 cases
and 117 openings**, with cancellation and two reopenings per case. It requires
all five reader calls: three status rows, the command list and the banner.
Every drawn glyph must be English or an explicitly supported native numeric
or space glyph. Unexpected fields, Japanese fallback, incorrect pointers,
wrapping and changed geometry fail.

Native glyph bytes, colours, cursor advances, reader ABI and row bounds are
checked. Banner pixels must match after reopening, and the original eight-pixel
border gap must remain intact. The old ROM is replayed and rejected at the
missing English pointer: the new check catches the reported bug.

Mysterious Meadow with the normal command mode uses ordinary fresh-game inputs.
Other locations use a temporary selector-register override at the banner
reader; the real dungeon ID remains unchanged. The two extra command modes
temporarily change the existing character-mode field. These are controlled
display checks, not natural late-game access or class-unlock evidence.
Runs use disposable sessions, retain input schedules and preserve the supplied
ROM/save. Both opening branches, six ordinary Option routes and 135 unit tests
also pass.

This historical correction kept **3,770 text resources and 20 graphics**; existing
names were not counted twice. Its catalog then had 113 unresolved sources;
[the current matrix](COVERAGE_AUDIT.md) supersedes that count. This
fix covers the identified dungeon-menu banner family; other readers and
whole-game discovery retain their separate validation scope.

## Reproduction

```sh
.venv/bin/python -m tools.build_english
.venv/bin/python -m tools.verify_location_banner
.venv/bin/python -m tools.accept_location_banner
```

These commands run in `./build.sh`. For the historical negative control and
byte-delta check, add `--reject-old` to verification and
`--baseline build/location-banner/pre-fix` to acceptance. That archive retains
the previous ROM, BPS and ledger. The fresh fixture comes from ordinary opening
inputs; no old-ROM raw state is relabelled for reuse.
