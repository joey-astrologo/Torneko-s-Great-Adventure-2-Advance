# README screenshots

The four images in [the project README](../README.md) are unedited 240×160
mGBA framebuffer captures from one fresh English game. They are stored in
`docs/images/` so the README works without the ignored `build/` directory.
HTML display width enlarges the originals; no artwork is composited into them.

| Image | Scene | How reached |
|---|---|---|
| [Title](images/title-screen.png) | Approved English title | Cold boot, frame 600 |
| [Inventory](images/inventory.png) | Big bread, Bronze shield, Oaken club, Copper sword and Bread | Ordinary first-floor pickups, then the Items menu |
| [Dialogue](images/dialogue.png) | Tipper welcomes Torneko home | Ordinary opening with the seven-character name Torneko |
| [Arrival](images/dungeon-arrival.png) | Mysterious Meadow 1F | First dungeon entry during the opening |

The inventory route uses recorded directional inputs, attacks and tutorial
acknowledgements. It does not manufacture items. No RAM/register modifications,
raw state restores or imported saves are used for the gallery replay.

The capture ROM SHA-256 is
`bd61d3f6f2db7af8119ecc6ee757f7560808d55ddec192c670368523a2708ab3`.
[Provenance](images/provenance.json) records the emulator version, built-in BIOS,
ROM/source hashes, every actual input, capture frames and image hashes.
The screenshot route demonstrates these scenes, not complete game coverage.

Reproduce using the matching English build and installed project toolchain:

```sh
.venv/bin/python -m tools.capture_readme
```

The helper replays [the saved route](../config/routes/readme.json) through a
fresh disposable `Session`, checks all four framebuffer hashes against the
reviewed captures, then copies the PNGs into `docs/images/`. It checks that the
original ROM/save and root release files remain unchanged. Research output is
saved under `build/readme-captures/native/`.

A different ROM hash stops reproduction until the route and expected images
have been reviewed for that build. Screenshot refreshes are separate from ROM
compilation and do not update the translation or release patch.
