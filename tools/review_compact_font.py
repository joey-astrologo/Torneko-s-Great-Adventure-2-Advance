"""Create a pixel-exact atlas and an offline, editable compact English preview."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.build_compact_font import OUTPUT
from tools.compact_font import ASSET, load_font, measure
from tools.rom import digest, require


def draw_text(picture, text, position, font, color=(255, 255, 255), scale=1):
    x, y = position
    draw = ImageDraw.Draw(picture)
    for char in text:
        glyph = font["glyphs"][char]
        for py, row in enumerate(glyph["rows"]):
            for px, bit in enumerate(row):
                if bit == "#":
                    left, top = x + px * scale, y + py * scale
                    draw.rectangle((left, top, left + scale - 1, top + scale - 1), fill=color)
        x += glyph["advance"] * scale


def atlas(font, output):
    sheet = Image.new("RGB", (960, 792), "#142136")
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 20), "TORNEKO 2 / COMPACT ENGLISH", fill="white", font_size=22)
    draw.text((24, 54), "95 printable characters. White: 63 original glyphs. Mint: 32 additions. Labels show pixel advance.",
              fill="#becbdc", font_size=14)
    for i, (char, glyph) in enumerate(font["glyphs"].items()):
        x, y = 24 + (i % 16) * 57, 94 + (i // 16) * 78
        color = (151, 237, 200) if glyph["origin"] == "new" else (255, 255, 255)
        label = "space" if char == " " else char
        draw.text((x, y), f"{label} / {glyph['advance']}", fill="#becbdc")
        draw.line((x, y + 19 + 12 * 3 + 2, x + 28, y + 19 + 12 * 3 + 2), fill="#34465e")
        draw_text(sheet, char, (x, y + 19), font, color, scale=3)
    for i, text in enumerate(("Start adventure", "The quick brown fox jumps over the lazy dog.", "0123456789  Il1  rn m  g j p q y")):
        y = 596 + i * 58
        draw_text(sheet, text, (24, y), font, scale=3)
        draw.text((800, y + 24), f"{measure(text, font)} px", fill="#becbdc", font_size=14)
    draw.text((24, 776), "Glyph artwork comes from ROM rows and the editable font asset; annotation text uses a host font.", fill="#becbdc")
    sheet.save(output / "compact-english.png")


PAGE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Torneko 2 — Compact English font</title>
<style>
:root {color-scheme:dark;font:16px/1.55 system-ui,sans-serif;background:#101a2b;color:#edf3fa}
body {max-width:1040px;margin:40px auto;padding:0 24px 60px} h1 {font-size:32px;line-height:1.2}
h2 {font-size:21px;margin-top:32px} p {max-width:850px;color:#c9d5e6} a {color:#98dec5}
.card {padding:22px;border:1px solid #35435b;border-radius:12px;background:#162238;margin:24px 0}
label {display:block;margin:12px 0 6px} textarea,input,select {font:inherit;color:inherit;background:#101a2b;border:1px solid #65738c;border-radius:6px;padding:9px}
textarea {box-sizing:border-box;width:100%;min-height:120px} input {width:90px} .controls {display:flex;gap:24px;flex-wrap:wrap}
.canvas-wrap {overflow:auto;padding:16px 0} canvas {display:block;image-rendering:pixelated}
img {max-width:100%;height:auto;image-rendering:pixelated} .native {width:480px}
.good {color:#98dec5} .bad {color:#ffb4a3} .note {font-size:14px;color:#b4c3d8}
table {border-collapse:collapse;width:100%;margin-top:12px} td,th {text-align:left;border-bottom:1px solid #35435b;padding:8px}
code {font:14px ui-monospace,monospace} button {font:inherit;padding:8px 12px;border:1px solid #65738c;border-radius:6px;background:#283951;color:inherit;cursor:pointer}
</style>
<h1>Compact English, completed</h1>
<p>The original compact capitals and digits, with a matching lowercase alphabet.
All 95 printable ASCII characters are covered: 63 original glyphs and 32 additions.
New lowercase advances are 3–6 pixels. Ascenders share the capital height; descenders fit the native 14-row bitmap.</p>
<p class="good">Native mGBA verification: all 95 glyphs, final screen pixels, cursor advances and string measurements passed.</p>
<div class="card">
<h2 style="margin-top:0">Try a line</h2>
<p class="note">This preview uses the actual font rows and advances. The 96-pixel default is the observed initial-menu width.
The test ROM includes a leading space; include it here to reproduce that label's 88-pixel total.
Lines keep your explicit breaks. No automatic wrapping or translation storage budget is implied.</p>
<label for="sample">Text</label>
<textarea id="sample" spellcheck="false"> Start adventure
The quick brown fox
jumps over the lazy dog.</textarea>
<div class="controls"><label for="budget">Line budget (pixels)<br><input id="budget" type="number" min="1" max="1024" value="96"></label>
<label for="zoom">Pixel scale<br><select id="zoom"><option value="2">2×</option><option value="3" selected>3×</option><option value="4">4×</option><option value="6">6×</option></select></label></div>
<p id="errors" class="bad" role="status"></p><div class="canvas-wrap"><canvas id="preview" aria-label="Pixel font preview"></canvas></div>
<table><thead><tr><th>Line</th><th>Width</th><th>Budget remaining</th></tr></thead><tbody id="widths"></tbody></table>
<p><button id="download">Save preview PNG</button></p>
</div>
<h2>In the game</h2>
<p>The cartridge itself selects the new font. These captures use normal menu input with no glyph-code register overrides.</p>
<img class="native" src="mixed-case/menu.png" alt="Native title menu reading Start adventure">
<p><a href="torneko-2-compact-font.gba">Test ROM</a> · <a href="torneko-2-compact-font.bps">BPS patch</a> ·
<a href="validation.json">Native verification report</a> · <a href="build.json">Checked allocation and patch ledger</a></p>
<p class="note">The test changes the first menu label to “Start adventure”. The rest of the game remains Japanese.
This is a font specimen, not a complete translation. Open the generated ROM in mGBA and press Start.</p>
<h2>Every character</h2>
<p>Mint glyphs are new: a–z, backslash, backtick, braces, vertical bar and tilde. The original compact backslash position contains a yen sign;
the new English table has a backslash while preserving the original Japanese font.</p>
<a href="compact-english.png"><img src="compact-english.png" alt="Complete English glyph atlas with original glyphs in white and additions in mint"></a>
<p class="note">Printable ASCII covers the English alphabet, digits and basic punctuation. Curly quotes, em dashes, accented letters and other Unicode characters need explicit handling.</p>
<p><a href="../../assets/fonts/compact-english.json">Editable font asset</a> · <a href="../../docs/COMPACT_FONT.md">Encoding, building and validation notes</a></p>
<script id="font-data" type="application/json">__FONT__</script>
<script>
const font = JSON.parse(document.getElementById('font-data').textContent).glyphs;
const sample = document.getElementById('sample'), budgetInput = document.getElementById('budget');
const zoom = document.getElementById('zoom'), canvas = document.getElementById('preview');
function render() {
  const lines = sample.value.split('\n');
  const unknown = [...new Set([...sample.value].filter(c => c !== '\n' && !Object.hasOwn(font,c)))];
  const error = document.getElementById('errors');
  if (unknown.length || lines.length > 40 || sample.value.length > 2000) {
    error.textContent = unknown.length ? 'Unsupported characters: ' + unknown.map(c => JSON.stringify(c)).join(', ') : 'Preview limit: 40 lines and 2,000 characters.';
    canvas.width = canvas.height = 0; document.getElementById('widths').replaceChildren();
    document.getElementById('download').disabled = true; return;
  }
  error.textContent = ''; document.getElementById('download').disabled = false;
  const budget = Math.max(1, Math.min(1024, Number(budgetInput.value) || 96));
  const scale = Number(zoom.value), widths = lines.map(line => [...line].reduce((x,c) => x + font[c].advance,0));
  const width = Math.max(budget, ...widths) + 8, height = lines.length * 18 + 8;
  canvas.width = width * scale; canvas.height = height * scale;
  const ctx = canvas.getContext('2d'); ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#000039'; ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.fillStyle = '#34546a'; ctx.fillRect((budget + 4)*scale,0,scale,canvas.height);
  lines.forEach((line,i) => {
    let x = 4; const y = 4 + i * 18; ctx.fillStyle = '#ffffff';
    for (const c of line) {
      const g = font[c]; g.rows.forEach((row,py) => [...row].forEach((bit,px) => {
        if (bit === '#') ctx.fillRect((x+px)*scale,(y+py)*scale,scale,scale);
      })); x += g.advance;
    }
  });
  const rows = document.getElementById('widths'); rows.replaceChildren();
  widths.forEach((width,i) => {
    const tr = document.createElement('tr');
    for (const value of [i+1, width + ' px', budget >= width ? (budget-width) + ' px left' : (width-budget) + ' px over']) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    tr.lastElementChild.className = width <= budget ? 'good' : 'bad'; rows.append(tr);
  });
}
[sample,budgetInput,zoom].forEach(element => element.addEventListener('input',render));
document.getElementById('download').addEventListener('click',() => {
  const link = document.createElement('a'); link.download = 'torneko-2-english-preview.png'; link.href = canvas.toDataURL('image/png'); link.click();
});
render();
</script></html>
'''


def review(output=OUTPUT):
    font = load_font()
    validation = json.loads((output / "validation.json").read_text())
    require(validation["passed"], "Run native font validation before generating the review")
    require(all(s["build"]["font_asset_sha256"] == digest(ASSET.read_bytes()) for s in validation["samples"]),
            "Native validation is for an older font asset")
    atlas(font, output)
    payload = json.dumps(font, ensure_ascii=True).replace("<", "\\u003c")
    (output / "index.html").write_text(PAGE.replace("__FONT__", payload))
    print(output / "index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    review(parser.parse_args().output.resolve())
