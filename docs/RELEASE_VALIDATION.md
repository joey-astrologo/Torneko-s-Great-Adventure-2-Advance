# November 14 release verification

The release candidate contains the Someone and False priest reader repairs and
the Magic Dungeon dialogue corrections. The game's Mystery Dungeon title and
approved artwork remain unchanged. No additional ROM changes were needed during
this verification pass: the ROM and BPS match the earlier False-priest checkpoint.

The [release ZIP](../build/releases/2026-11-14-release-candidate.zip) contains the
BPS, matching manifest, release notes, completion receipt, verification logs and
selected reports. It contains no ROM or save. The local accepted ROM and evidence
are preserved in `build/accepted/3814-release-validation/`; the previous
`3814-false-priest` checkpoint and ZIP remain intact.

| Artifact | SHA-256 |
|---|---|
| Japanese base | `79986287eef366bba987393de8247141973d5564fa72fe2f3f6dd28684cd18aa` |
| English ROM | `9f127400b8e289f6acbb96bc5658663f6ba3a9780e064c642e4579199b5af746` |
| BPS | `d652dc4038663bbfeec5058db7006709c1868abeea3afecd39e8019e4200753f` |

Apply the BPS to a clean base with the matching hash and verify the resulting ROM.
Use a separate playtest copy and retain existing saves. The save layout is
unchanged. The build has 3,814 inserted text resources and 20 approved graphics;
these counts do not measure whole-game scene coverage. No public version tag is
assigned, and the compiler's root export manifest retains `development` status.

## Verification on this release

| Check | Result and scope |
|---|---|
| Full `build.sh` | All 328 commands pass in one successful run; none skipped or resumed after failure |
| `validate.sh` | 192 unit tests, pinned toolchain, native mGBA replay and Ghidra checks pass |
| Source verification | 147 master source round trips, seven native bank decompressions and 1,046 event-table entries checked; master catalog bytes unchanged |
| Cumulative acceptance | Current service/menu family reports and their source, build and image identities pass `tools.accept_services` |
| Font verification | 315 WebKit contexts / 3,430 measurements; 95 native glyph checks; selected-font layout checks pass |
| Item rows and descriptions | All 2,006 required item/state/name cases pass |
| Repaired actor readers | 17 getter cases, 12 complete combat cases and a real hallucination-trap handler pass; the earlier negative controls remain preserved separately |
| Save and quit | Four ordinary-input original/English house/stair routes pass native save, reset, cold resume and movement under mGBA's built-in BIOS |
| Reproducibility | A clean temporary build reproduces the ROM and BPS byte for byte; ledger reconstruction and independent application of the packaged patch pass |

The full build reruns the existing approved title/arrival regressions, opening
and story checks, caller and screen audits, combat/status text, tutorials,
service transactions, menus, item rows, results/history and link-trading checks.
This does not reopen graphics discovery. The font-audition config refreshes
native evidence hashes and two preview lines for the already inserted Magic
Dungeon wording; font metrics and window geometry are unchanged. The recorded
scripts distinguish ordinary-input routes from controlled native calls and
state overrides.

The fresh entry points were:

```bash
bash -x ./build.sh
./validate.sh
bash tools/verify_font_audition.sh
.venv/bin/python -m tools.accept_services
.venv/bin/python -m tools.verify_save_quit --output build/release-validation-nov14/save-quit
```

The source extraction and event-table audits were refreshed separately, with
extraction staged against a copy and an exact-byte comparison confirming that
the master translation catalog was unchanged. Full logs and invocation metadata
are retained in `build/release-validation-nov14/`. The acceptance scripts also
check the current source reports before creating their cumulative receipts.

[Completion receipt](../build/accepted/3814-release-validation/completion.json) ·
[Archive integrity and patch-application check](../build/release-validation-nov14/package-verification.json) ·
[Cumulative receipt](english-services-validation.json) ·
[Menu receipt](english-menu-validation.json) ·
[Save/reset report](../build/release-validation-nov14/save-quit/report.json)

## Known limits

The reported Analogue Pocket/EverDrive GBA Pro white screen and static noise
after Save and quit remains unresolved. The successful mGBA routes do not
establish Pocket, flashcart or external-BIOS compatibility. See the
[save-and-quit investigation](SAVE_QUIT_AUDIT.md).

Whole-game scene/state coverage, ordinary late-game progression and broader
independent playtesting remain incomplete. Existing original gameplay bugs,
including the documented [link-fault item loss](LINK_ERROR_AUDIT.md), are
intentionally preserved. The [coverage matrix](COVERAGE_AUDIT.md) keeps these
limits separate from the passing scripted checks. Historical research and
negative-control reports retain their own ROM identities.
