# Title-screen artwork audition

The user requested this audition on 2026-09-30, reopening title artwork after
the arrival-card insertion. Open the [standalone studio](../build/title-audition/index.html)
or [original/proposal comparison](../build/title-audition/title-comparison.png).
The user approved the **Wood & gold** main-title artwork on 2026-09-30, then
requested matching background-logo auditions. The studio now includes those
[five linked proposals](../build/title-audition/index.html#backgrounds), with an
[all-background comparison PNG](../build/title-audition/background-comparison.png).
The user subsequently approved all six images and requested insertion. They
are now included in the root English ROM/BPS. See the
[actual native gallery](../build/title-insertion/index.html) and
[insertion evidence](TITLE_INSERTION.md). This studio retains editable artwork
previews; the gallery shows the final native palette conversion.

## Artwork and wording

The draft follows the original wooden sign, mountain scenery, blue slime,
gold lettering and red Advance accent. The proposed English wording follows
the structure used in the Torneko 3 project:

> Dragon Quest Characters · Torneko's Great Adventure 2 · Advance · Mystery Dungeon

The main logo and scenery are an AI redraw, not preserved original pixels.
The original `Push START!` footer is composed back into the native preview by
default: the exact rectangle is `[0,136,240,160)`, or the bottom 24 rows.
Turning that option off shows the complete generated artwork instead.

- [Generated source PNG](../assets/title-screen/wood-gold-v1.png): 1536×1024.
- [Exact generation prompt](../assets/title-screen/wood-gold-v1-prompt.txt).
- [Candidate metadata and hashes](../assets/title-screen/candidate.json).
- [Native default export](../build/title-audition/title-english-native.png): 240×160.
- [4× export](../build/title-audition/title-english-4x.png): 960×640, nearest-neighbour enlargement.

Generation used the **built-in image_gen** tool, with the original T2 title as
the edit target and T3's approved title as an English lettering reference.
The T3 stone scroll, ocean and number 3 were not used as T2 artwork. The prompt,
reference hashes, source asset hash and generation dimensions are recorded.
One candidate was generated for the main-title audition. The later corner-logo
pass uses a separate miniature adaptation of that approved design.

## Five linked corner logos

| Record | Original scene | Proposed rectangle (exclusive coordinates) | Native START delay after frame 600 |
|---|---|---|---|
| 13 | Family | `[164,124,240,160)` — bottom right | 4 frames |
| 18 | Monsters and slime | `[164,0,240,36)` — top right | 7 frames |
| 19 | Monster collage | `[164,0,240,36)` — top right | 0 frames |
| 20 | Treasure chest | `[164,0,240,36)` — top right | 2 frames |
| 21 | Village | `[164,0,240,36)` — top right | 1 frame |

The user rejected the wooden backing for these five backgrounds. Revision 2
uses shared **76×36 floating RGBA lettering**, with transparent gaps and letter
holes. Gold Torneko's/Great Adventure/2 and red Advance follow the approved main
title. There is no wood, rectangular backing or filled sign. The main title's
wooden sign remains approved and unchanged. The tiny original corner logos
also omit Dragon Quest Characters, Mystery Dungeon and the start prompt.

The [transparent source PNG](../assets/title-screen/corner-logo-v2.png) is
1821×864; [its exact prompt](../assets/title-screen/corner-logo-v2-prompt.txt)
used built-in image_gen to remove the wood from the earlier lettering. The
[background candidate metadata](../assets/title-screen/background-candidate.json)
pins it to the parent title artwork SHA256. All five original logos are baked
into their scenes. Separate image_gen repairs reconstruct the scenery they
covered, with the generated output used **only inside the original 76×36
audition rectangles**. The rest of every generated scene is discarded; native
ROM pixels outside the rectangle stay exact. These hidden areas are inferred
artwork, not recovered original background pixels.

The repair assets and exact prompts are saved as
`assets/title-screen/background-{13,18,19,20,21}-clean-v2.png` and matching
`-prompt.txt` files; the metadata records all hashes and native references.
The rejected plaque and its metadata remain archived as `corner-logo-v1.png`
and `background-candidate-v1.json`. Browser area reduction uses premultiplied
alpha to retain clean letter edges. Colour preview conversion applies after
compositing, so antialiased edges also obey the selected palette/depth preview.

The added section provides original/English pairs, native/enlarged viewing,
background-only/start-menu contexts, a **Corner repair only** view, individual
PNG exports and one comparison sheet covering all five. The transparent native
logo is also exported to `build/title-audition/corner-logo-native.png`.
The main colour/reduction controls also affect the
corner logo. Notes and saved settings include the background view and pin the
linked asset/reference set. A custom full-screen import does not regenerate
the miniature logo. The main title and all five composites are approved and
inserted; the frozen approved rasters are separate from these editable controls.

## Studio controls

The standalone HTML embeds its images and script; it works offline without a
server. It includes side-by-side and slider comparisons, fixed 240×160 previews,
area-average/nearest reduction, three colour previews, the original footer
toggle, native/4×/comparison PNG exports, notes and saved audition JSON.
An opaque 3:2 replacement PNG can be imported. Saved settings pin the source,
reference, artwork and renderer hashes; invalid imports leave the draft intact.
Nothing is silently saved in browser storage.

The tools adapt `../torneko-3-gba/tools/title_audition/` to T2. They use T2's
native palette expansion, `(channel5 << 3) | (channel5 >> 2)`, and T2's own
footer bounds. The browser checks also reject isolated transparent source
pixels that nearest-neighbour sampling would otherwise skip.

## Native references and separate menu logos

`tools.capture_title_audition` uses disposable `Session` cartridges with fresh
saves. Both Japanese and pre-insertion English ROMs cold-boot to frame 600 without
inputs. Their full title pixels, tiles and palettes match exactly. Each title
also matches a full reconstruction from native VRAM and palette; all 600 visible
tile-map entries match the loader's synthesized layout. No state/register
overrides are used.

The Japanese reference then uses START held for 3 frames plus 180 released
frames, followed by A held for 3 plus 180 released frames. Menu and name editor
at frames 783/966 share record 19, distinct from title record 16. Inputs,
loader/copy traces and source hashes are retained under
[`build/title-audition/reference/`](../build/title-audition/reference/provenance.json).

The first pass decoded five menu resources (13, 18, 19, 20, 21) with stored
palettes. The linked-logo follow-up now reaches **all five through ordinary
inputs on the pre-insertion English ROM**, using the START delays in the table above,
then A for name entry. No selector/RAM/register patches are used. Each run
checks the resource against the Japanese base, all background tile bytes,
all 600 visible map entries and native calibrated palette. Name entry retains
the selected background tiles and its first 240 palette entries.

Fresh evidence is under
[`backgrounds/reference.json`](../build/title-audition/backgrounds/reference.json),
with per-case inputs, menu/name captures and native copy traces. The current
audition uses these calibrated references. Its corner rectangle is clear of
the start-menu panel on every case. The name-entry panel naturally obscures
some of the original logo; per-case overlap counts are recorded, not treated
as a new layout defect. The studio offers the unobstructed start-menu view.

Replacing the main title still will not replace these five separate resources.
This is the confirmed random-menu family, not proof that every later logo
occurrence has been found throughout the game.

## Audition validation and palette conversion

[Browser verification](../build/title-audition/verification.json) passes 85
checks: rendering controls, native reference/footer pixels, five-bit colour
channels, original-palette membership, notes/settings round trips, invalid
imports, transparent images, imported artwork retention, slider endpoints and
export dimensions, the five background contexts and linked-asset checks.
The WebKit screenshots were inspected alongside the native and comparison
exports. For all fifteen background/menu/repair views, browser and Python checks
independently verify every pixel outside the corner rectangle. Browser checks
verify every composited corner pixel against the shared lettering alpha and
per-scene repair. Python also checks that fully transparent logo pixels reveal
the repaired scene. The native alpha has transparent corners and gaps and
near-opaque lettering; resampled antialiasing need not reach alpha 255.
Exported footer pixels and protected file hashes are checked independently.

The default GBA-colour-depth preview contains **3,783 distinct colours**. The
native title resource permits **256 palette entries**, while the five menu
backgrounds permit **240**, reserving 16 for UI. The editable studio's five-bit
preview is therefore distinct from the final inserted palette.

Insertion now performs native-calibrated palette fitting while locking all
original colours and indices outside the edit regions. It preserves the title
footer and surrounding scenes exactly. Ownership, allocator checks, full native
uploads, palette calibration, startup transitions and UI restoration all pass.
See [TITLE_INSERTION.md](TITLE_INSERTION.md) for the verified ROM and native
screenshots; browser checks alone do not establish native acceptance.

Original ROM SHA256:
`79986287eef366bba987393de8247141973d5564fa72fe2f3f6dd28684cd18aa`.
The supplied save is unchanged. The **historical reference** English ROM is
`c6cf871bcb20060b91ca226d203bdf78713d89aa8cb1643170286e0b011f96c5`,
with BPS hash
`e631253711678a5334fcffbcac3299f11a749b69005973e2bacb1f7c69fc173a`.
These are archived in `build/title-insertion/pre-insertion/`. Audition tools now
read that archive. Historical provenance retains the path/hash from capture
time; verification resolves its old root-release paths to the archived copies,
while checking the original ROM/save at their actual paths.

## Reproduction

```bash
.venv/bin/python -m tools.capture_title_audition
.venv/bin/python -m tools.capture_title_backgrounds
.venv/bin/python -m tools.build_title_audition
bash tools/verify_title_audition.sh
```

The last command uses the shared macOS Cocoa/WebKit installation and the local
Python environment. The browser helper may require execution outside the
filesystem sandbox so WebKit's rendering services can start. It loads the local
page, verifies it, exports PNG/settings files and captures the studio window.
It does not launch or modify the ROM. Generation is not rerun by these commands;
the saved candidate PNG and prompt reproduce the audition deterministically.
