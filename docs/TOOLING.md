# Toolchain and reproduction

Originally validated on this Mac on 2026-09-13; the October 3 accepted build also
passes the pinned toolchain checks (see [the coverage matrix](COVERAGE_AUDIT.md)).
No pins changed in the documentation reconciliation. The setup adapts Torneko 3's pinned tools;
the installed runtime and research helpers belong to this project.

| Tool | Version / source |
|---|---|
| Python | Homebrew 3.11.15, native arm64, local `.venv` |
| mGBA Python/native | 0.10.5; `26b7884bc25a5933960f3cdcd98bac1ae14d42e2` |
| mGBA desktop | 0.10.5; `/Applications/mGBA.app` |
| Ghidra | Homebrew 12.1.3; `/opt/homebrew/opt/ghidra/libexec` |
| GBA loader | pudii; `9bfb2d1fe891aa78bab7093a328feb3a52318ab7`, extension built for 12.1.3 |
| Java / Gradle | OpenJDK 21.0.12.1 / Gradle 9.7.1 |
| armips | 0.11.0; `156f78f6bccfc07498578ac491ce7fe2a1e807a6` |
| Floating IPS | `ff216a75df0987047a67d7923567dc4482ce07ac` |
| Python packages | Exact pins in `python-toolchain.lock.txt`; includes Pillow 12.3.0, CFFI 1.17.1, CMake 3.31.10 |

`build/toolchain-validation/toolchain.json` records the installed package
versions, native binary hashes, source revisions/diffs and compatibility-patch
hashes. `docs/validation.json` is the retained acceptance receipt from this setup.

## Reproduce on this Mac

```bash
./setup.sh ../torneko-3-gba
./validate.sh
```

The optional reference argument supports an offline bootstrap. Source trees are
copied independently and their commits checked. Pinned wheels are recovered from
the reference venv where absent locally: payloads are verified against installed
RECORD hashes and executable modes are retained. Pip regenerates launchers for
this project. Recovered wheel archives are not claimed to match upstream archive
bytes; provenance is in `.tools/wheels/recovered-wheels.json`. The initial setup
used eight cached upstream wheels plus recovered CMake/pip wheels.

Running `./setup.sh` without a reference instead installs the package pins with
pip and fetches source commits from their upstream repositories; this route
requires network access and availability of the pinned distributions. It has
not been tested here. The offline reference bootstrap has been exercised.

System prerequisites are the same native Homebrew dependencies already installed
for Torneko 3: Python 3.11, pkgconf, libpng, libzip, libedit, libffi, Ghidra,
OpenJDK 21 and Gradle, plus Xcode Command Line Tools and desktop mGBA. Setup
builds local mGBA, armips and Flips. It does not upgrade system tools or install
applications globally. It uses the existing system GBA loader.

To build a replacement loader ZIP explicitly:

```bash
bash tools/build_gba_loader.sh
```

Install the generated ZIP under `.tools/src/gba-ghidra-loader/dist/` via
Ghidra's File > Install Extensions, then restart Ghidra. The current shared
extension is in Ghidra's application directory, making it available to the
isolated headless home. A future Ghidra upgrade requires rebuilding/reinstalling
the extension and updating/revalidating the pins.

## Local build details

`tools/build_mgba.sh` enables Python/shared libraries, debugger/GDB support and
scripting, disables GUI frontends, FFmpeg and Lua, and sets arm64 plus
`CMP0148=OLD` for CMake's legacy Python discovery. The e-Reader declaration patch
in `tools/patches/` makes the FFmpeg-disabled CFFI extension import correctly.
The loader patch removes one unused Jython import. See `tools/patches/README.md`.

`.venv/lib/python3.11/site-packages/torneko-mgba.pth` points into **this** project's
`.tools/build/mgba/python/`; the extension's library search path likewise points
into this project's native build. No runtime path points into Torneko 3. Moving
the project requires recreating the venv and rebuilding native tools. Local
sources, caches and build products live under ignored `.tools/` and `.venv/`.

Flips source payloads are verified against `tools/flips-toolchain.json` before
building. Its binary reproduced the Torneko 3 executable hash. During setup,
the pinned linear encoder produced an invalid BPS for an append-only synthetic
buffer. `tools/bps.py` handles this observed edge case by trying the upstream
delta encoder if linear output fails complete apply verification. Both the
append-only fallback and an edited/expanded linear patch pass; wrong source
bytes are rejected. These are packaging probes, not ROM expansion validation.

## Acceptance and limits

The 8 MiB base passes hash/header validation. mGBA boots to the title and initial
menu, using its built-in BIOS. The native entry breakpoint at `080000C0`, a
controlled EWRAM CPU-read watchpoint and 8/16/32-bit memory accesses pass. At frame
600, a 397,312-byte core state and 65,536-byte battery save are captured. Replaying
Start for 3 frames plus 180 released frames gives identical pixels, EWRAM,
IWRAM, battery bytes and frame counter through both raw and desktop-format
state restores. Native temporary saves persist and cold-reload identically.
The same checks pass seeded from a copy of the supplied save.

Eight focused tests cover corrupted headers/base images, wrong or corrupt
fixtures, callback failure/detachment, invalid inputs and traced boot timing.
Ghidra's import/ARM entry check passes, and generic Thumb function/range exports
were tested at the independently observed startup entry `08000354`.
armips emits the expected ARM/Thumb instruction bytes.

This establishes research tooling and initial runtime observations. Text
encoding, fonts, translated insertion, ROM expansion, full gameplay routes and
save-record fields were outside that initial acceptance. The subsequent
[font investigation](FONTS.md) verifies existing Latin glyphs and the initial
menu's encoding path. The source `.gba` and `.sav`
hashes were unchanged after validation. `./validate.sh` reruns the fresh-save
acceptance; repeat the supplied-save check explicitly with
`python -m tools.verify_mgba --save 'path/to/save.sav' --output build/toolchain-validation/mgba-supplied-save`.
