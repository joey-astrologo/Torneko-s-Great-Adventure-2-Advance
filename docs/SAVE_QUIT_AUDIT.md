# Save-and-quit report — October 7, 2026

The user reports that **Save and quit** at the house freezes their Analogue
Pocket and produces abnormal sound, while a power cycle appears to reload the
save. The user subsequently identified an **EverDrive GBA Pro**, with a **white
screen and static noise** at failure. This is the Pocket's cartridge path, not
an openFPGA ROM launch. Stair suspension may have the same problem. **The Pocket
failure remains unresolved; it has not been reproduced in the project emulator.**
EverDrive/Pocket firmware versions, launch mode, save-state use and the user's
ROM/save identity are not yet established.

The current English ROM and original Japanese ROM both pass four targeted
ordinary-input routes in native mGBA 0.10.5 with its built-in BIOS: house quit
and stair suspension in each ROM. All four write a native save, execute the
original BIOS reset sequence, restart the cartridge and reach a responsive
Continue menu. All four saves cold-load and resume movement; both house cases
also resume directly after the in-game reset. This is not Pocket, external-BIOS,
flashcart or audio acceptance, and does not establish the integrity of the user's
particular save.

## What quitting actually does

Quitting is supposed to restart the game, not remain on a power-off screen.
Both routes use save mode 2 at `08015374`, which writes the record before
displaying the save-success/farewell text. After acknowledgement:

- House caller `0801FB90` finishes its fade loop and calls `0800140C` from
  `0801FBE2`.
- The dungeon exit block calls that same routine from `0800551A`.
- `0800140C` prepares the display, waits 60 frames, then calls `0805B4AC`
  with reset mask `FF`.
- The reset wrapper disables interrupts, writes zero to the BIOS cartridge-reset
  flag at `03007FFA`, sets SP to `03007F00`, and issues `RegisterRamReset`
  (`SWI 01`) followed by `SoftReset` (`SWI 00`).

The five verified ROM ranges covering the two exit blocks, native save/display
function and reset functions are identical in Japanese and English. The report
retains their exact original bytes. Both native traces reach the cartridge
startup again at `08000354`. This narrows the reported symptom to a stage after
the save write, but unchanged reset code and successful mGBA execution do not
rule out a platform-specific localization regression or another runtime fault.

The earlier home-book acceptance checked save contents and cold reloads, but did
not assert this final reset/startup/menu sequence. The new check explicitly does.

## Reproduction and evidence

```sh
.venv/bin/python -m tools.verify_save_quit
```

[Native report](../build/save-quit/validation/report.json) ·
[English house after reset](../build/save-quit/validation/english-house/after-soft-reset.png) ·
[English stairs after reset](../build/save-quit/validation/english-stairs/after-soft-reset.png)

The house cases cold-load hash-checked batteries from the retained ordinary
home-book routes, then select the four-row book menu's quit option normally.
The dungeon cases replay the retained fresh-adventure input schedules through
the first-floor stairs. These are input replays on the current ROM, not restores
of older English core states. There are no RAM, register, ROM, save-data or
gameplay overrides. Every input and save/reset event is retained, along with
before/after snapshots and native battery files. Historical input/battery
provenance is separate from the ROM tested now.

The report pins original ROM `79986287…` and current English ROM `588dc92c…`.
The supplied ROM/save, research fixtures and current English ROM are unchanged.
No ROM repair or replacement release is warranted by these results alone;
the accepted October 7 checkpoint remains available. Only the relevant native
checks ran; the full cumulative suite was not repeated.

## EverDrive Pro follow-up

Krikzz's [official manual](https://krikzz.com/pub/support/everdrive-gba/pro-series/ed-gba-pro-manual.pdf)
(April 20, 2026, pages 4, 6 and 13) describes IRQ patches for its in-game handler
and recommends **Start Safe** for crashes. That launch mode disables cheats and
the in-game menu. In the ROM's file menu, use left/right on the launch entry to
select it. Safe mode is distinct from Mode-B, whose Pocket incompatibility
statement does not describe the entire cartridge.

The first proposed comparison is a fresh Start Safe launch of the same English
ROM, loading the ordinary in-game Continue save, then repeating house Save and
quit. Avoid restoring a save state for this comparison so the run starts under
the selected launch mode. **This user-side comparison has not yet been run.**
A successful result would implicate the normal launch's added features; it would
not by itself identify the exact hook or rule out every translation interaction.

As checked October 7, the [official firmware directory](https://krikzz.com/pub/support/everdrive-gba/pro-series/firmware/)
lists `26.0719` as its newest version. The
[changelog](https://krikzz.com/pub/support/everdrive-gba/pro-series/firmware/changelog.txt)
dates Start Safe's introduction to `26.0421`; later entries include save/menu
database updates, but do not claim a Torneko quit fix. Record the installed
version before interpreting a missing Safe option or proposing an update.

A [firsthand Shining Soul report](https://www.reddit.com/r/everdrive/comments/1u13z1i/everdrive_gba_pro_crashing_to_white_screen/)
describes white video, abnormal audio and a forced power cycle after saving and
quitting on an EverDrive GBA Pro. This is a similar symptom in another game,
not independent reproduction of Torneko or confirmation of a common cause.

Remaining evidence is the Safe-mode result, EverDrive/Pocket firmware versions,
and a matching pre-quit battery save if progression matters. If Safe mode still
fails, a separate Japanese-ROM test using its own disposable save would help
distinguish original-game compatibility from an English-only failure. Do not
load an English save into the Japanese game as a compatibility test; its added
English glyph IDs are not supported by the original renderer. No new native
suite run or ROM change was needed for this hardware-report clarification.
