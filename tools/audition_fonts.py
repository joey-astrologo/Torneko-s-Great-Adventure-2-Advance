"""Offline pixel-exact font comparison and per-context menu budget inventory."""

import csv
import json

from tools.compact_font import load_font, measure, encode
from tools.rom import ROOT, digest, require

OUTPUT = ROOT/'build/font-audition'
CONFIG = ROOT/'config/font-audition.json'
NATIVE = ROOT/'build/menu-layout-audit/native/report.json'


def metrics(font,text,budget):
    advance,ink_right = 0,0
    for char in text:
        require(char in font['glyphs'],'Unsupported audition character: '+repr(char))
        glyph = font['glyphs'][char]
        for row in glyph['rows']:
            if '#' in row:ink_right=max(ink_right,advance+row.rfind('#')+1)
        advance += glyph['advance']
    return {'advance':advance,'ink_right':ink_right,'budget':budget,
            'remaining':budget-max(advance,ink_right),'fits':max(advance,ink_right)<=budget}


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 — font audition and menu budgets</title>
<style>
:root{color-scheme:dark;font:16px/1.5 system-ui;background:#101a2b;color:#edf3fa}body{max-width:1280px;margin:30px auto;padding:0 22px 50px}h1{font-size:30px}h2{font-size:21px}p{max-width:1000px;color:#c8d4e5}a{color:#95dfc4}select,input,textarea,button{font:inherit;color:inherit;background:#17283d;border:1px solid #748397;border-radius:5px;padding:8px}textarea{display:block;width:95%;min-height:110px;margin:12px 0}label{display:block;margin:12px 0 5px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}.card{background:#142338;border:1px solid #354961;padding:16px;border-radius:8px;overflow:auto}canvas,img{image-rendering:pixelated;max-width:none}.good{color:#9ee7bc}.bad{color:#ffab99}.note{font-size:14px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:8px;text-align:left;border-bottom:1px solid #354961}th{position:sticky;top:0;background:#182a42}.tablewrap{max-height:520px;overflow:auto}button{cursor:pointer}.native{width:480px;max-width:100%}#error{color:#ffab99}summary{cursor:pointer}
</style>
<h1>Font audition and menu budgets</h1>
<p><strong>Selected for English builds: Torneko 2 compact English.</strong> The readable original compact glyphs and matching lowercase are restored. Torneko 3 remains available for comparison. Compare original and current contexts below.</p>
<p id="summary"></p>
<p>Pixel width is a window constraint, shared by both fonts. Each font uses a different amount of it. Original-window candidates are research wording; current-build labels are reviewed and inserted. Edits here are previews only. Pixel fit alone does not establish buffer safety or whole-game coverage.</p>
<label for="context">Measured context</label><select id="context"></select>
<p id="geometry"></p><p id="contextnote" class="note"></p>
<label for="sample">Audition labels — one per line</label><textarea id="sample" spellcheck="false"></textarea>
<label for="scale">Pixel scale <select id="scale"><option value="1">1×</option><option value="2">2×</option><option value="3" selected>3×</option><option value="4">4×</option></select></label>
<p id="error" role="status"></p><div id="previews" class="grid"></div>
<p class="note">These are simulated panels drawn from exact glyph pixels. Grey marks reserved cursor space; the red line marks the text boundary. Overflow stays visible for diagnosis. Native captures below are separate evidence.</p>
<h2>Every recorded budget, for both fonts</h2>
<p><a href="budgets.csv" download>Label measurements CSV</a> · <a href="contexts.csv" download>Every context / font budget CSV</a> · <a href="dynamic-budgets.csv" download>Dynamic name budgets CSV</a> · <a href="report.json">Evidence and full metrics</a> · <a href="../../docs/FONT_AUDITION.md">Scope and decisions</a></p>
<label for="filter">Filter contexts, labels or fonts</label><input id="filter" type="search" placeholder="e.g. Exchange or bank">
<label><input id="failures" type="checkbox"> Show only overflow</label>
<div class="tablewrap"><table><thead><tr><th>Context</th><th>Font</th><th>Label</th><th>Budget</th><th>Advance</th><th>Ink edge</th><th>Remaining</th><th>Role</th></tr></thead><tbody id="matrix"></tbody></table></div>
<h2>Native evidence</h2><div class="grid"><div class="card"><h3>Selected font in Torneko 2</h3><img class="native" src="native/mixed-case/menu.png" alt="Native Torneko 2 menu with imported font"><p><a href="native/validation.json">All 95 native glyph checks</a></p></div><div class="card"><h3 id="native-title">Menu being measured</h3><img id="native" class="native" alt="Original menu geometry"><p id="native-note"></p></div></div>
<details><summary>Coverage still required before menu layout sign-off</summary><ul id="unresolved"></ul></details>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),contexts=data.contexts;
const selectedFailures=data.measurements.filter(r=>r.font===data.selected_font&&r.role==='candidate'&&r.stage==='current'&&!r.fits);
$('summary').textContent=`${data.fonts.length} fonts · ${contexts.length} contexts · ${selectedFailures.length} failing labels in the current contexts. Early menus are validated; whole-game layout coverage remains open.`;
contexts.forEach(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=`${c.name} — ${c.end-c.start} px`; $('context').append(o)});
function metric(font,text,budget){let advance=0,ink=0;for(const char of text){const g=font.glyphs[char];if(!g)throw Error('Unsupported character: '+JSON.stringify(char));g.rows.forEach(row=>{const end=row.lastIndexOf('#');if(end>=0)ink=Math.max(ink,advance+end+1)});advance+=g.advance}return {advance,ink,remaining:budget-Math.max(advance,ink)}}
function render(){const c=contexts.find(c=>c.id===$('context').value),lines=$('sample').value.split('\n'),scale=Number($('scale').value);$('previews').replaceChildren();$('error').textContent='';
try{if(lines.length>32||$('sample').value.length>1500)throw Error('Preview limit: 32 lines / 1,500 characters.');
for(const f of data.fonts){const values=lines.map(t=>metric(f,t,c.end-c.start));const card=document.createElement('div');card.className='card';const title=document.createElement('h3');title.textContent=f.name;card.append(title);
const canvas=document.createElement('canvas'),w=Math.max(c.window,...values.map(v=>c.start+Math.max(v.advance,v.ink)))+8,h=lines.length*16+8;canvas.width=w*scale;canvas.height=h*scale;const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=false;ctx.fillStyle='#000039';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#263148';ctx.fillRect(4*scale,0,c.start*scale,canvas.height);ctx.fillStyle='#b45459';ctx.fillRect((4+c.end)*scale,0,scale,canvas.height);
lines.forEach((text,i)=>{let x=4+c.start;for(const ch of text){const g=f.glyphs[ch];g.rows.forEach((row,y)=>[...row].forEach((bit,px)=>{if(bit==='#'){ctx.fillStyle=x+px>=4+c.end?'#ff9b88':'white';ctx.fillRect((x+px)*scale,(4+i*16+y)*scale,scale,scale)}}));x+=g.advance}});card.append(canvas);
const table=document.createElement('table');values.forEach((v,i)=>{const tr=document.createElement('tr');[lines[i]||'(empty)',`${v.advance} px`,v.remaining>=0?`${v.remaining} px left`:`${-v.remaining} px over`].forEach(t=>{const td=document.createElement('td');td.textContent=t;tr.append(td)});tr.lastChild.className=v.remaining<0?'bad':'good';table.append(tr)});card.append(table);
const button=document.createElement('button');button.textContent='Download pixel preview';button.onclick=()=>{const a=document.createElement('a');a.download=`${c.id}-${f.id}.png`;a.href=canvas.toDataURL('image/png');a.click()};card.append(button);$('previews').append(card)}}catch(e){$('error').textContent=e.message;$('previews').replaceChildren()}}
function choose(){const c=contexts.find(c=>c.id===$('context').value);$('sample').value=c.labels.length?c.labels.join('\n'):(c.id==='bank-amount'?'99999999G':'Leather shield +1');$('geometry').textContent=`Window ${c.window} px; text starts at ${c.start}; boundary ${c.end}; usable ${c.end-c.start} px. ${c.rows} audited rows for this context.`;$('contextnote').textContent=c.note+(c.alternatives.length?' Alternatives to audition: '+c.alternatives.join(', '):'');$('native').hidden=!c.capture;if(c.capture)$('native').src='../../'+c.capture;$('native-note').textContent=c.capture?'Native capture for this context; see its evidence and scope.':'See the existing cumulative native acceptance for this context.';render()}
function matrix(){const q=$('filter').value.toLowerCase();$('matrix').replaceChildren();data.measurements.filter(r=>(!$('failures').checked||!r.fits)&&JSON.stringify(r).toLowerCase().includes(q)).forEach(r=>{const tr=document.createElement('tr');[r.context_name,r.font_name,r.label,r.budget,r.advance,r.ink_right,r.remaining,r.role].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});tr.children[6].className=r.fits?'good':'bad';$('matrix').append(tr)})}
data.unresolved.forEach(t=>{const li=document.createElement('li');li.textContent=t;$('unresolved').append(li)});$('context').value='item-equipped-current';$('context').onchange=choose;$('sample').oninput=render;$('scale').onchange=render;$('filter').oninput=matrix;$('failures').onchange=matrix;choose();matrix();
</script></html>'''


def run():
    config = json.loads(CONFIG.read_text());native = json.loads(NATIVE.read_text())
    require(native['passed'],'Native menu audit required')
    routes = {r['id']:r for r in native['routes']}
    compiled_path=ROOT/'build/english/menu-validation/report.json'
    compiled=json.loads(compiled_path.read_text());require(compiled['passed'],'Current native menu checks required')
    ledger=json.loads((ROOT/'build/english/build.json').read_text())
    require(compiled['rom_sha256']==ledger['output_sha256'],'Current evidence is stale')
    built_routes={r['id']:r for r in compiled['routes']}
    fonts = [{**f,**load_font(ROOT/f['asset']),'id':f['id'],'name':f['name'],
              'asset_sha256':digest((ROOT/f['asset']).read_bytes())} for f in config['fonts']]
    contexts,measurements = [],[]
    for c in config['contexts']:
        require(0 <= c['start'] < c['end'] <= c['window'],'Invalid menu budget')
        if 'build_route' in c:
            route=built_routes[c['build_route']]
            matches=[r for r in route['reads'][:route['menu_read_count']] if r['window_width']==c['window'] and ((not c['labels'] and r['initial_x']==c['start']) or (c['labels'] and encode(c['labels'][0])[:-1].hex() in r['raw_hex']))]
            require(matches and all(r['initial_x']==c['start'] for r in matches),'Current native region changed: '+c['id'])
            c=c | {'capture':route['capture'],'native_reads':matches}
        if 'route' in c:
            route = routes[c['route']]
            matches = [r for r in route['reads'][:route['menu_read_count']]
                       if c['match'] in r['text'] and r['window_width'] == c['window']]
            require(matches,'Missing native menu geometry: '+c['id'])
            require(all(r['fixed_advance'] == r['spacing'] == 0 for r in matches),'Menu width override requires separate metrics')
            if c['id'] != 'bank-verbs':
                require(all(r['initial_x'] == c['start'] for r in matches),'Native text inset changed')
            if c['id'] in ('bank-verbs','tactics-labels'):
                require(all(any(g['x'] == c['end'] for g in r['glyph_positions']) for r in matches),'Native field boundary changed')
            c = c | {'capture':route['capture'],'native_reads':matches}
        contexts.append(c)
        for font in fonts:
            for role,labels in [('candidate',c['labels']),('alternative',c['alternatives'])]:
                for label in labels:
                    measurements.append({'context':c['id'],'context_name':c['name'],
                        'stage':c.get('stage','original'),'font':font['id'],'font_name':font['name'],'label':label,'role':role,
                        **metrics(font,label,c['end']-c['start'])})
    require(all(r['fits'] for r in measurements if r['font']==config['selected_font'] and r['stage']=='current'),'Current label does not fit')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    dynamic=[]
    for font in fonts:
        for label,reserve in [('seven widest original Japanese name glyphs',98),
                              ('seven widest English name glyphs',7*max(g['advance'] for g in font['glyphs'].values()))]:
            suffix=measure("'s home",font);total=reserve+suffix
            dynamic.append({'context':'travel','font':font['id'],'case':label,'dynamic_reserve_px':reserve,
                            'literal_px':suffix,'total_px':total,'budget_px':140,'remaining_px':140-total,
                            'fits':total<=140,'byte_reserve':14,'scope':'Name expansion is read dynamically; seven stored name characters.'})
    require(all(r['fits'] for r in dynamic),'Dynamic travel name exceeds budget')
    with (OUTPUT/'dynamic-budgets.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(dynamic[0]));writer.writeheader();writer.writerows(dynamic)
    report = {'passed':True,'selected_font':config['selected_font'],'dynamic_measurements':dynamic,
        'config_sha256':digest(CONFIG.read_bytes()),'native_menu_report_sha256':digest(NATIVE.read_bytes()),
        'compiled_menu_report_sha256':digest(compiled_path.read_bytes()),
        'fonts':fonts,'contexts':contexts,'measurements':measurements,'unresolved':config['unresolved'],
        'layout_signoff':False,'scope':'Passing report means exact budget computation and pinned native geometry, not that every label fits. Candidates and alternatives are not new reviewed translations; no menu insertion or layout fix is implied.'}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (OUTPUT/'budgets.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(measurements[0]));writer.writeheader();writer.writerows(measurements)
    geometry = [{'context':c['id'],'name':c['name'],'font':f['id'],'window_px':c['window'],
                 'text_start_px':c['start'],'text_boundary_px':c['end'],'usable_px':c['end']-c['start'],
                 'rows':c['rows'],'stage':c.get('stage','original'),'widest_ascii_advance':max(g['advance'] for g in f['glyphs'].values()),
                 'notes':c['note']} for c in contexts for f in fonts]
    with (OUTPUT/'contexts.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(geometry[0]));writer.writeheader();writer.writerows(geometry)
    (OUTPUT/'index.html').write_text(PAGE.replace('__DATA__',json.dumps(report,ensure_ascii=True).replace('<','\\u003c')))
    print(OUTPUT/'index.html')
    print('Current selected-font overflows:',[(r['context'],r['label'],-r['remaining']) for r in measurements
                                     if r['font']==config['selected_font'] and r['stage']=='current' and r['role']=='candidate' and not r['fits']])
    return report


if __name__ == '__main__':
    run()
