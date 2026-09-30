'use strict';
const $ = id => document.getElementById(id);
const MODE = DATA.mode, FACES = Object.fromEntries(DATA.fonts.map(f => [f.id, f]));
const isCredits = MODE === 'credits', images = {}, controls = ['creditsStyle','face','nameFace','height','nameHeight','tracking','align','edges','colour','nameColour','floor','floorStyle','guides'];
const defaults = () => ({creditsStyle:'original',face:isCredits?'credits':'shiren-source',nameFace:'t2-compact',height:isCredits?12:17,nameHeight:10,tracking:0,align:'original',edges:'soft',colour:isCredits?'#7bf7f7':'#ffffff',nameColour:'#ffffff',floor:1,floorStyle:'original',guides:false,wording:{}});
let state = defaults(), selected = 0, offset = 150, playing = false, lastTime = 0, scrollRemainder = 0, roll, allMetrics = [], ready = false;
const entries = isCredits ? DATA.credits.sections : DATA.arrivals.entries;
const canvas = (w=240,h=160) => Object.assign(document.createElement('canvas'),{width:w,height:h});
function ctx(c) {const x=c.getContext('2d',{willReadFrequently:true});x.imageSmoothingEnabled=false;return x;}
function blank(c) {const x=ctx(c);x.fillStyle='#000';x.fillRect(0,0,c.width,c.height);return x;}
function rgb(hex) {return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16));}
function quantize(v) {const n=Math.round(v*31/255);return (n<<3)|(n>>2);}
function colour(hex,level) {return 'rgb('+rgb(hex).map(v=>quantize(v*level/3)).join(',')+')';}
function glyph(face,ch,height) {
 const g=face.glyphs[ch];if(!g)return null;
 const ratio=height/face.cap_height;
 return {source:g,width:g.width?Math.max(1,Math.round(g.width*ratio)):0,height:g.height?Math.max(1,Math.round(g.height*ratio)):0,top:Math.round(g.top*ratio),advance:Math.max(1,Math.round(g.advance*ratio))};
}
function measure(text,faceId,height) {
 const f=FACES[faceId], missing=[], supplements=new Set();let width=0;
 for(const ch of text){const g=glyph(f,ch,height);if(!g){missing.push(ch);width+=height;continue;}width+=g.advance+state.tracking;
 if(/supplement/.test(g.source.origin||''))supplements.add(ch);}
 return {width:Math.max(0,width-(text.length?state.tracking:0)),missing:[...new Set(missing)],supplements:[...supplements]};
}
function drawText(c,text,x,baseline,faceId,height,hex) {
 const context=ctx(c),f=FACES[faceId];let cursor=x;
 for(const ch of text){const g=glyph(f,ch,height);
  if(!g){context.strokeStyle='#ff6655';context.strokeRect(cursor,baseline-height,height-1,height);cursor+=height;continue;}
  for(let y=0;y<g.height;y++)for(let xx=0;xx<g.width;xx++){
   let value=Number(g.source.rows[Math.min(g.source.height-1,Math.floor(y*g.source.height/g.height))][Math.min(g.source.width-1,Math.floor(xx*g.source.width/g.width))]);
   if(state.edges==='crisp')value=value>=2?3:0;
   if(value){context.fillStyle=colour(hex,value);context.fillRect(cursor+xx,baseline+g.top+y,1,1);}
  }
  cursor+=g.advance+state.tracking;
 }
}
function inkBounds(c) {
 const p=ctx(c).getImageData(0,0,c.width,c.height).data;let x1=c.width,y1=c.height,x2=-1,y2=-1;
 for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){const at=(y*c.width+x)*4;if(p[at]||p[at+1]||p[at+2]){x1=Math.min(x1,x);x2=Math.max(x2,x);y1=Math.min(y1,y);y2=Math.max(y2,y);}}
 return x2<0?null:[x1,y1,x2+1,y2+1];
}
function metric(id,text,face,height,region,baseline,x) {
 const m=measure(text,face,height),probe=canvas(2048,160);blank(probe);
 drawText(probe,text,32,60,face,height,'#ffffff');const ink=inkBounds(probe);
 const box=ink?[x+ink[0]-32,baseline+ink[1]-60,x+ink[2]-32,baseline+ink[3]-60]:null;
 const fit=!m.missing.length&&m.width<=region[2]&&(!box||(box[0]>=region[0]&&box[1]>=region[1]&&box[2]<=region[0]+region[2]&&box[3]<=region[1]+region[3]));
 return {id,text,font:face,height,advance:m.width,budget:region[2],region,ink:box,fit,missing:m.missing,supplements:m.supplements};
}
function titleText(e) {return state.wording[e.id]??e.english;}
function creditsRoll() {
 const c=canvas(240,DATA.credits.dimensions[1]);blank(c);const metrics=[];
 if(state.creditsStyle==='original'){
  ctx(c).drawImage(images.roll,0,0);
  for(const line of DATA.credits.lines){const b=line.bounds;
   metrics.push({id:line.id,text:line.text,font:'original-gba-artwork',height:b[3]-b[1],advance:b[2]-b[0],budget:240-b[0],region:[b[0],b[1],240-b[0],b[3]-b[1]],ink:b,fit:true,missing:[],supplements:[]});}
  return {canvas:c,metrics};
 }
 for(const line of DATA.credits.lines){const heading=line.role==='heading',face=heading?state.face:state.nameFace,height=heading?state.height:state.nameHeight;
  const m=measure(line.text,face,height),x=state.align==='center'?Math.floor((240-m.width)/2):line.x;
  const region=state.align==='center'?[8,line.y,224,19]:[line.x,line.y,240-line.x,19];
  const baseline=line.y+height;
  metrics.push(metric(line.id,line.text,face,height,region,baseline,x));
  drawText(c,line.text,x,baseline,face,height,heading?state.colour:state.nameColour);
 }
 return {canvas:c,metrics};
}
function nativeFloor(c,e,floor) {
 if(e.selector===12&&floor>10)return;
 const x=ctx(c),s=String(floor).padStart(3,' ');
 if(e.selector===12)x.drawImage(images['glyph-level'],64,80);
 for(let i=e.selector===12?1:0;i<3;i++)if(s[i]!==' ')x.drawImage(images['glyph-'+s[i]],128+i*16,80);
 if(e.selector!==12)x.drawImage(images['glyph-F'],176,80);
}
function arrivalOriginal(e,floor) {
 const c=canvas();blank(c);
 if(e.selector===12&&floor>10)return c;
 ctx(c).drawImage(images[e.id],0,0);nativeFloor(c,e,floor);return c;
}
function arrival(e,floor=state.floor) {
 const c=canvas();blank(c);const metrics=[];
 if(e.selector===12&&floor>10)return {canvas:c,metrics,suppressed:true};
 const lines=titleText(e).split('\n'),region=e.text_region;
 const gap=2,total=lines.length*state.height+(lines.length-1)*gap;
 const top=region[1]+Math.floor((region[3]-total)/2);
 lines.forEach((text,i)=>{const m=measure(text,state.face,state.height),x=Math.floor((240-m.width)/2),baseline=top+state.height+i*(state.height+gap);
  metrics.push(metric(e.id+'-line-'+i,text,state.face,state.height,region,baseline,x));
  drawText(c,text,x,baseline,state.face,state.height,state.colour);
 });
 const ordinary=e.selector!==12;
 if(state.floorStyle==='original'){
  const p=ctx(c),s=String(floor).padStart(3,' ');
  if(!ordinary){const region=[64,80,64,24],height=Math.min(state.height,18),text='Level',baseline=80+height;
   metrics.push(metric(e.id+'-level',text,state.face,height,region,baseline,64));drawText(c,text,64,baseline,state.face,height,state.nameColour);}
  for(let i=ordinary?0:1;i<3;i++)if(s[i]!==' ')p.drawImage(images['glyph-'+s[i]],128+16*i,80);
  if(ordinary)p.drawImage(images['glyph-F'],176,80);
 }else{
  const text=ordinary?floor+'F':'Level '+floor,region=ordinary?[128,80,64,24]:[64,80,112,24],height=Math.min(state.height,20);
  const m=measure(text,state.face,height),x=region[0]+region[2]-m.width,baseline=80+height;
  metrics.push(metric(e.id+'-floor',text,state.face,height,region,baseline,x));drawText(c,text,x,baseline,state.face,height,state.nameColour);
 }
 return {canvas:c,metrics,suppressed:false};
}
function showToast(message) {$('toast').textContent=message;$('toast').classList.remove('hidden');clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>$('toast').classList.add('hidden'),7000);}
function syncControls() {for(const key of controls){const e=$(key);if(e.type==='checkbox')e.checked=state[key];else e.value=state[key];}if(!isCredits)$('wording').value=titleText(entries[selected]);
 for(const key of ['face','nameFace','height','nameHeight','tracking','align','edges','colour','nameColour'])$(key).disabled=isCredits&&state.creditsStyle==='original';}
function guides(c) {
 if(!state.guides)return;const x=ctx(c);x.strokeStyle='#dc8567';x.setLineDash([2,2]);
 if(isCredits){x.strokeRect(.5,0,239,159);x.beginPath();x.moveTo(64.5,0);x.lineTo(64.5,160);x.stroke();}
 else{const r=entries[selected].text_region;x.strokeRect(r[0]+.5,r[1]+.5,r[2]-1,r[3]-1);x.strokeRect(64.5,80.5,127,23);}x.setLineDash([]);
}
function current() {
 if(isCredits){const original=canvas(),candidate=canvas();blank(original);blank(candidate);ctx(original).drawImage(images.roll,0,-offset);ctx(candidate).drawImage(roll,0,-offset);
  const section=entries[selected];return {original,candidate,metrics:allMetrics.slice(section.first_line,section.end_line_exclusive)};}
 const e=entries[selected],r=arrival(e);return {original:arrivalOriginal(e,state.floor),candidate:r.canvas,metrics:r.metrics,suppressed:r.suppressed};
}
function renderView() {
 const view=current();for(const [id,c] of [['original',view.original],['preview',view.candidate],['native',view.candidate]]){const x=blank($(id));x.drawImage(c,0,0);if(id==='preview')guides($(id));}
 const bad=view.metrics.filter(m=>!m.fit),missing=[...new Set(view.metrics.flatMap(m=>m.missing))],supplements=[...new Set(view.metrics.flatMap(m=>m.supplements))];
 $('fit').className=bad.length?'bad':'good';
 $('fit').textContent=view.suppressed?'The original suppresses this card above level 10.':bad.length?bad.map(m=>m.text+': '+m.advance+'px / '+m.budget+'px'+(m.missing.length?' · missing glyphs '+m.missing.join(''): ' · check width and height')).join(' | '):view.metrics.map(m=>m.advance+' / '+m.budget+'px').join(' · ')+' — fits the measured regions';
 const preserved=isCredits&&state.creditsStyle==='original';
 $('previewLabel').textContent=preserved?'Approved artwork · unchanged':isCredits?'Historical experiment · not selected':'Candidate';
 $('fontNote').textContent=preserved?'Original English GBA credit artwork, approved unchanged on 2026-09-30. No replacement font is used.':FACES[state.face].name+'. '+(FACES[state.face].scope||'')+(supplements.length?' This preview uses marked supplement glyphs: '+supplements.join(' '):'');
 $('scope').textContent=isCredits?'Keep the original English artwork. Replacement experiments are retained for reference only.':'Insertion name region: '+entries[selected].text_region[2]+' × '+entries[selected].text_region[3]+'px. Original Japanese width: '+entries[selected].original_text_region[2]+'px. Floor artwork has its own region. Separate town cards have not been established.';
 $('transcript').textContent=isCredits?DATA.credits.lines.slice(entries[selected].first_line,entries[selected].end_line_exclusive).map(l=>l.text).join('\n')+'\n\nSource: compressed GBA bitmap at ROM 0x585304.':entries[selected].japanese+'\n'+entries[selected].english+'\nDescriptor: 0x'+entries[selected].descriptor_offset.toString(16)+'\n'+entries[selected].native_reachability;
 $('scroll').value=offset;$('scrollLabel').value=Math.floor(offset)+'px';$('entry').value=selected;
 return {bad,missing};
}
function rebuild() {
 if(!ready)return;
 if(isCredits){const r=creditsRoll();roll=r.canvas;allMetrics=r.metrics;}else allMetrics=entries.flatMap(e=>arrival(e).metrics);
 const gallery=$('gallery');gallery.replaceChildren();
 entries.forEach((e,i)=>{
  const tile=document.createElement('div');tile.className='tile';const label=document.createElement('h3');label.textContent=isCredits?e.label:e.english;
  let c,metrics;
  if(isCredits){c=canvas(240,e.bottom-e.top);blank(c);ctx(c).drawImage(roll,0,-e.top);metrics=allMetrics.slice(e.first_line,e.end_line_exclusive);}else{const r=arrival(e);c=r.canvas;metrics=r.metrics;}
  const note=document.createElement('p'),bad=metrics.filter(m=>!m.fit);note.className=bad.length?'bad':'good';note.textContent=bad.length?bad.length+' line(s) exceed the region or lack glyphs':'Fits';
  const button=document.createElement('button');button.textContent='Inspect';button.onclick=()=>select(i);tile.append(label,c,note,button);gallery.append(tile);
 });
 const bad=allMetrics.filter(m=>!m.fit);$('galleryStatus').textContent=isCredits&&state.creditsStyle==='original'?'67 English lines in the approved original artwork. Exports preserve the source pixels.':allMetrics.length+' measured lines · '+bad.length+' flagged. Exports preserve overflow warnings; fit is not ROM insertion approval.';
 renderView();
}
function select(i) {selected=(i+entries.length)%entries.length;if(isCredits)offset=Math.max(0,Math.min(1920,entries[selected].top));syncControls();renderView();}
function settings() {return {schema:1,kind:'torneko2-graphics-audition',mode:MODE,source_sha256:DATA.source_sha256,font_sha256:DATA.font_sha256,renderer_sha256:DATA.renderer_sha256,state:structuredClone(state)};}
function validatedSettings(value) {
 if(!value||value.schema!==1||value.kind!=='torneko2-graphics-audition'||value.mode!==MODE)throw Error('This settings file belongs to another studio.');
 for(const k of ['source_sha256','font_sha256','renderer_sha256'])if(value[k]!==DATA[k])throw Error('Settings use different '+k.replace('_sha256','')+' data.');
 const s=value.state;if(!s||Object.keys(s).sort().join()!==Object.keys(defaults()).sort().join())throw Error('Settings fields are incomplete or unknown.');
 for(const k of ['face','nameFace'])if(!Object.hasOwn(FACES,s[k]))throw Error('Unknown bitmap font.');
 for(const [k,min,max] of [['height',7,24],['nameHeight',7,20],['tracking',0,3],['floor',1,999]])if(!Number.isInteger(s[k])||s[k]<min||s[k]>max)throw Error('Invalid '+k+'.');
 if(!['original','center'].includes(s.align)||!['soft','crisp'].includes(s.edges)||!['original','candidate'].includes(s.floorStyle)||typeof s.guides!=='boolean')throw Error('Invalid rendering settings.');
 if(!['original','experiment'].includes(s.creditsStyle))throw Error('Invalid credits view.');
 for(const k of ['colour','nameColour'])if(!/^#[0-9a-fA-F]{6}$/.test(s[k]))throw Error('Invalid colour.');
 if(!s.wording||typeof s.wording!=='object'||Array.isArray(s.wording))throw Error('Invalid wording.');
 const ids=new Set(DATA.arrivals.entries.map(e=>e.id));for(const [id,text] of Object.entries(s.wording))if(!ids.has(id)||typeof text!=='string'||text.length>160||!/^[\x20-\x7e\n]*$/.test(text)||!text.trim())throw Error('Invalid location wording.');
 if(isCredits&&Object.keys(s.wording).length)throw Error('Credits wording must be preserved.');
 return structuredClone(s);
}
function download(blob,name) {const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exportPNG(c,name,scale=1) {const out=canvas(c.width*scale,c.height*scale);ctx(out).drawImage(c,0,0,out.width,out.height);out.toBlob(b=>{if(b)download(b,name);else showToast('PNG export failed.');},'image/png');}
function sheet(comparison=false) {
 const panels=entries.map((e,i)=>{
  if(isCredits){const o=canvas(240,e.bottom-e.top),p=canvas(240,e.bottom-e.top);blank(o);blank(p);ctx(o).drawImage(images.roll,0,-e.top);ctx(p).drawImage(roll,0,-e.top);return {o,p,label:e.label};}
  return {o:arrivalOriginal(e,state.floor),p:arrival(e).canvas,label:e.english};
 });
 const columns=comparison?2:3,cw=comparison?500:260,heights=[];
 for(let i=0;i<panels.length;i+=columns)heights.push(Math.max(...panels.slice(i,i+columns).map(p=>p.p.height))+45);
 const c=canvas(columns*cw,heights.reduce((a,b)=>a+b,35)),x=blank(c);x.fillStyle='#e7edf5';x.font='14px system-ui';x.fillText('Torneko 2 · '+MODE+(isCredits&&state.creditsStyle==='original'?' · approved original artwork':' · audition candidates'),10,22);
 let y=35;panels.forEach((p,i)=>{if(i&&i%columns===0)y+=heights[Math.floor(i/columns)-1];const xx=(i%columns)*cw+10;x.fillStyle='#e7edf5';x.fillText(p.label,xx,y+17);if(comparison){x.drawImage(p.o,xx,y+25);x.drawImage(p.p,xx+244,y+25);}else x.drawImage(p.p,xx,y+25);});
 return c;
}
function tick(time) {if(!playing)return;if(lastTime){scrollRemainder+=(time-lastTime)*30/1000;const delta=Math.floor(scrollRemainder);scrollRemainder-=delta;offset=Math.min(1920,offset+delta);renderView();}lastTime=time;if(offset>=1920){playing=false;$('play').textContent='Play scroll';}else requestAnimationFrame(tick);}
function csv(metrics=allMetrics) {const rows=[['id','text','font','height_px','advance_px','width_budget_px','region_x','region_y','region_width','region_height','fits','missing','supplements']];for(const m of metrics)rows.push([m.id,m.text,m.font,m.height,m.advance,m.budget,...m.region,m.fit,m.missing.join(''),m.supplements.join('')]);return rows.map(r=>r.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n');}
function allFontMetrics() {const previous=state,rows=[];try{for(const f of DATA.fonts){state={...previous,creditsStyle:'experiment',face:f.id,nameFace:f.id};rows.push(...(isCredits?creditsRoll().metrics:entries.flatMap(e=>arrival(e).metrics)));}}finally{state=previous;}return rows;}
function updateControl(key) {const e=$(key);let value=e.type==='checkbox'?e.checked:e.type==='number'?Number(e.value):e.value;
 const candidate=settings();candidate.state[key]=value;try{state=validatedSettings(candidate);syncControls();rebuild();}catch(error){showToast(error.message);syncControls();}}
async function boot() {
 await Promise.all(Object.entries(DATA.images).map(([key,url])=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{images[key]=im;resolve();};im.onerror=()=>reject(Error('An embedded original image did not load.'));im.src=url;})));
 document.querySelectorAll('[data-mode]').forEach(e=>{e.hidden=e.dataset.mode!==MODE;});
 $('title').textContent=isCredits?'Ending credits · original artwork':'Arrival and dungeon card studio';document.title='Torneko 2 · '+$('title').textContent;
 $('intro').textContent=isCredits?'Approved: keep the original English GBA credits unchanged.':'The approved Shiren arrival cards are inserted. Compare their lettering and measured insertion regions.';
 $('candidateNote').textContent=isCredits?'Original artwork is selected. Earlier typography experiments remain available for reference.':'Approved defaults: Shiren source lettering and original floor digits. Ordeal Mansion now has a 136px region. Other settings remain experiments.';
 $('galleryTitle').textContent=isCredits?'All 15 credit sections':'All 13 location cards';
 for(const id of ['face','nameFace'])for(const f of DATA.fonts){const o=document.createElement('option');o.value=f.id;o.textContent=f.name;$(id).append(o);}
 entries.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=isCredits?e.label:String(e.selector).padStart(2,'0')+' · '+e.english;$('entry').append(o);});
 for(const key of controls)$(key).onchange=()=>updateControl(key);
 $('wording').onchange=()=>{const candidate=settings();candidate.state.wording[entries[selected].id]=$('wording').value;try{state=validatedSettings(candidate);rebuild();}catch(error){showToast(error.message);syncControls();}};
 $('entry').onchange=()=>select(Number($('entry').value));$('prev').onclick=()=>select(selected-1);$('next').onclick=()=>select(selected+1);
 $('scroll').oninput=()=>{offset=Number($('scroll').value);renderView();};
 $('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Pause scroll':'Play scroll';lastTime=0;scrollRemainder=0;if(playing){if(offset>=1920)offset=0;requestAnimationFrame(tick);}};
 $('reset').onclick=()=>{state=defaults();syncControls();rebuild();};
 $('save').onclick=()=>download(new Blob([JSON.stringify(settings(),null,2)+'\n'],{type:'application/json'}),'torneko2-'+MODE+'-settings.json');
 $('load').onclick=()=>$('file').click();$('file').onchange=async()=>{try{if(!$('file').files[0])return;const value=JSON.parse(await $('file').files[0].text()),next=validatedSettings(value);state=next;syncControls();rebuild();showToast('Settings restored.');}catch(error){showToast('Could not load settings: '+error.message);}finally{$('file').value='';}};
 $('png').onclick=()=>exportPNG(current().candidate,'torneko2-'+MODE+'-'+entries[selected].id+'.png');$('png3').onclick=()=>exportPNG(current().candidate,'torneko2-'+MODE+'-'+entries[selected].id+'-3x.png',3);
 $('sheet').onclick=()=>exportPNG(sheet(),'torneko2-'+MODE+'-all.png');$('compare').onclick=()=>{const v=current(),c=canvas(488,160);blank(c);ctx(c).drawImage(v.original,0,0);ctx(c).drawImage(v.candidate,248,0);exportPNG(c,'torneko2-'+MODE+'-comparison.png');};
 $('metrics').onclick=()=>download(new Blob([csv()],{type:'text/csv'}),'torneko2-'+MODE+'-budgets.csv');
 $('allMetrics').onclick=()=>download(new Blob([csv(allFontMetrics())],{type:'text/csv'}),'torneko2-'+MODE+'-all-font-budgets.csv');
 $('rollPNG').onclick=()=>exportPNG(roll,'torneko2-credits-full-roll.png');
 ready=true;syncControls();rebuild();
 window.AUDITION={get mode(){return MODE;},get state(){return structuredClone(state);},get metrics(){return structuredClone(allMetrics);},settings,validate:validatedSettings,
  set(s){state=validatedSettings({...settings(),state:s});syncControls();rebuild();},select,measure,current,sheet,csv,allFontMetrics,
  get candidates(){return DATA.fonts.map(f=>f.id);},get entries(){return entries;},get ready(){return ready;}};
}
boot().catch(error=>{$('intro').textContent=error.message;$('intro').className='bad';});
