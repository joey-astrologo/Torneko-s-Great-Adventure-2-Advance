"""Build a frame viewer and replay routes for the retained Japanese arrival captures."""

import json
from pathlib import Path

from tools.rom import ROOT, digest, load_base, require

OUTPUT = ROOT / 'build/arrival-research'
CASES = [
    ('first-dungeon', 'First dungeon entrance and arrival card', 'build/arrival-research/first-dungeon/departure', 1, 4, 603, None),
    ('first-castle', 'First castle arrival', 'build/arrival-research/first-castle/stairs', 1, 4, 303, None),
    ('castle-exit', 'Castle exit destination menu', 'build/castle-arrival/research/castle', 10, 10, 600, 'DOWN'),
    ('home-return', 'Return home', 'build/arrival-research/castle-exit/final', 5, 5, 600, None),
]

PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 arrival captures</title><style>
:root{color-scheme:dark;font:16px/1.5 system-ui;background:#101a2b;color:#eef3fa}body{max-width:1000px;margin:32px auto;padding:0 24px}
select,button{font:inherit;background:#263b57;color:inherit;border:1px solid #73849c;border-radius:5px;padding:8px 12px;margin:6px 6px 6px 0}
img{display:block;image-rendering:pixelated;width:720px;max-width:100%;margin:18px 0;background:black}input{width:min(100%,720px)}a{color:#91d8bd}p{max-width:850px}
</style><h1>Torneko 2 arrival captures</h1>
<p>Native Japanese gameplay: the first dungeon entrance and arrival card, first castle arrival, its exit menu, and the return home. Inspect individual frames or play each sequence.</p>
<select id="scene" aria-label="Transition"></select><br><button id="prev">Previous frame</button><button id="play">Play</button><button id="next">Next frame</button>
<p id="label" aria-live="polite"></p><input id="frame" type="range" min="0" value="0" aria-label="Captured frame"><img id="screen" alt="Captured Torneko 2 transition frame">
<p><a id="receipt">Capture receipt</a> · <a id="route">Replay route</a> · <a href="../../docs/GRAPHICS_INVENTORY.md">Graphics inventory and scope</a></p>
<p>The first dungeon uses a separate title/floor card. The first castle and home transitions fade into their scenes. Other entries and later story states remain to be checked.</p>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent),scene=document.getElementById('scene'),frame=document.getElementById('frame');let timer=null;
for(const [i,c] of data.entries()){const o=document.createElement('option');o.value=i;o.textContent=c.title;scene.append(o);}
function stop(){clearTimeout(timer);timer=null;document.getElementById('play').textContent='Play';}
function render(){const c=data[scene.value],i=Number(frame.value);frame.max=c.frames.length-1;document.getElementById('screen').src=c.id+'/'+c.frames[i];document.getElementById('label').textContent=c.title+' — capture '+(i+1)+' of '+c.frames.length+' ('+c.frames[i]+')';document.getElementById('receipt').href=c.id+'/report.json';document.getElementById('route').href=c.id+'/route.json';document.getElementById('prev').disabled=i===0;document.getElementById('next').disabled=i===c.frames.length-1;}
function tick(){const c=data[scene.value];if(Number(frame.value)>=c.frames.length-1){stop();return;}frame.value=Number(frame.value)+1;render();timer=setTimeout(tick,1000*c.step/60);}
scene.onchange=()=>{stop();frame.value=0;render();};frame.oninput=()=>{stop();render();};
document.getElementById('prev').onclick=()=>{stop();frame.value=Number(frame.value)-1;render();};document.getElementById('next').onclick=()=>{stop();frame.value=Number(frame.value)+1;render();};
document.getElementById('play').onclick=()=>{if(timer!==null){stop();return;}if(Number(frame.value)>=data[scene.value].frames.length-1)frame.value=0;document.getElementById('play').textContent='Pause';timer=setTimeout(tick,0);};render();
</script></html>'''


def run():
    original_hash = digest(load_base())
    cases = []
    for ident, title, fixture, step, first, last, held in CASES:
        folder = OUTPUT / ident
        report = json.loads((folder / 'report.json').read_text())
        require(report['source_rom_sha256'] == original_hash, 'Arrival capture base differs')
        steps = [] if held else [{'press': 'A', 'hold': 3, 'wait': 0}]
        frames = []
        for number in range(first, last + 1, step):
            name = f'frame-{number:03}'
            require((folder / (name + '.png')).exists(), 'Missing arrival capture')
            steps.append({'press': held, 'hold': step, 'wait': 0} if held else {'frames': step})
            steps.append({'capture': name})
            frames.append(name + '.png')
        route = {'id': ident, 'description': title + '; native Japanese normal-input replay from the documented fixture.',
                 'source_rom_sha256': original_hash, 'fixture_prefix': fixture, 'steps': steps}
        (folder / 'route.json').write_text(json.dumps(route, indent=2) + '\n')
        cases.append({'id': ident, 'title': title, 'step': step, 'frames': frames, 'fixture': fixture})
    (OUTPUT / 'index.html').write_text(PAGE.replace('__DATA__', json.dumps(cases).replace('<', '\\u003c')))
    print(OUTPUT / 'index.html')


if __name__ == '__main__':
    run()
