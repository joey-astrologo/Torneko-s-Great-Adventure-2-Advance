'use strict';
const DATA=JSON.parse(document.getElementById('data').textContent);
const $=id=>document.getElementById(id);
const defaults=()=>({candidate:'wood-gold-v1',sampling:'area',colours:'rgb555',prompt:true,notes:'',background_context:'art',background_native:true});
let state=defaults(), custom=null, customImage=null, originalImage, candidateImage, rendered, revision=0;
const cache=new Map();
const canvas=(w=240,h=160)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
const assert=(condition,message)=>{if(!condition)throw new Error(message);};
const same=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);
function image(url){return new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(new Error('The PNG could not be read.'));im.src=url;});}
function validateImage(im){assert(im.width>=240&&im.height>=160&&im.width<=4096&&im.height<=4096,'Use a PNG between 240 × 160 and 4096 pixels per side.');assert(im.width*2===im.height*3,'Use a 3:2 PNG so the artwork will not be stretched or cropped.');}
function pixels(im){const c=canvas(im.width,im.height);c.getContext('2d').drawImage(im,0,0);return c.getContext('2d').getImageData(0,0,c.width,c.height);}
function reduce(im,method){
  const source=pixels(im);for(let i=3;i<source.data.length;i+=4)assert(source.data[i]===255,'Use an opaque full-screen PNG.');
  const out=new ImageData(240,160), sx=im.width/240, sy=im.height/160;
  // Explicit area averaging keeps exported native pixels independent of the
  // browser's image-smoothing implementation. Enlargement is nearest-neighbour.
  for(let y=0;y<160;y++)for(let x=0;x<240;x++){
    const target=(y*240+x)*4;
    if(method==='nearest'){
      const at=(Math.min(im.height-1,Math.floor((y+.5)*sy))*im.width+Math.min(im.width-1,Math.floor((x+.5)*sx)))*4;
      for(let ch=0;ch<4;ch++)out.data[target+ch]=source.data[at+ch];
    }else{
      const x0=x*sx,x1=(x+1)*sx,y0=y*sy,y1=(y+1)*sy,sum=[0,0,0,0];
      for(let yy=Math.floor(y0);yy<Math.ceil(y1);yy++)for(let xx=Math.floor(x0);xx<Math.ceil(x1);xx++){
        const weight=(Math.min(x1,xx+1)-Math.max(x0,xx))*(Math.min(y1,yy+1)-Math.max(y0,yy));
        const at=(yy*im.width+xx)*4;
        for(let ch=0;ch<4;ch++)sum[ch]+=source.data[at+ch]*weight;
      }
      for(let ch=0;ch<4;ch++)out.data[target+ch]=Math.round(sum[ch]/(sx*sy));
    }
    assert(out.data[target+3]===255,'Use an opaque full-screen PNG; transparent layers need a complete background.');
  }
  return out;
}
function render(){
  const key=state.candidate+':'+state.sampling+':'+revision;
  if(!cache.has(key))cache.set(key,reduce(state.candidate==='custom'?customImage:candidateImage,state.sampling));
  const out=new ImageData(new Uint8ClampedArray(cache.get(key).data),240,160), nearest=new Map();
  for(let i=0;i<out.data.length;i+=4){
    let rgb=[out.data[i],out.data[i+1],out.data[i+2]];
    if(state.colours==='rgb555')rgb=rgb.map(v=>(()=>{const n=Math.round(v*31/255);return (n<<3)|(n>>2);})());
    else if(state.colours==='original'){
      const k=rgb.join(',');
      if(!nearest.has(k)){
        let best=Infinity,chosen;
        for(const p of DATA.palette){const d=p.reduce((n,v,c)=>n+(v-rgb[c])**2,0);if(d<best){best=d;chosen=p;}}
        nearest.set(k,chosen);
      }
      rgb=nearest.get(k);
    }
    for(let c=0;c<3;c++)out.data[i+c]=rgb[c];
  }
  if(state.prompt)out.data.set(pixels(originalImage).data.subarray(DATA.prompt_y*240*4),DATA.prompt_y*240*4);
  rendered=canvas();rendered.getContext('2d').putImageData(out,0,0);
  return rendered;
}
function paint(target,source){const c=$(target),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);ctx.imageSmoothingEnabled=false;ctx.drawImage(source,0,0,c.width,c.height);}
function wipe(){
  const ctx=$('wipe').getContext('2d'),at=Math.round(Number($('position').value)*2.4);
  ctx.drawImage(rendered,0,0);if(at>0)ctx.drawImage(originalImage,0,0,at,160,0,0,at,160);
  if(at>0&&at<240){ctx.fillStyle='#efbc68';ctx.fillRect(at,0,1,160);}
}
function sync(){
  for(const id of ['candidate','sampling','colours','notes'])$(id).value=state[id];$('prompt').checked=state.prompt;
  $('candidate-label').textContent=state.candidate==='custom'?'IMPORTED ARTWORK · '+custom.name:'ENGLISH PROPOSAL · WOOD & GOLD';
}
function redraw(){
  render();paint('original',originalImage);paint('native-original',originalImage);paint('proposal',rendered);paint('native-proposal',rendered);wipe();
  const d=rendered.getContext('2d').getImageData(0,0,240,160).data,colors=new Set();
  for(let i=0;i<d.length;i+=4)colors.add(`${d[i]},${d[i+1]},${d[i+2]}`);
  $('metrics').textContent=`Current flattened preview: ${colors.size.toLocaleString()} distinct RGB colours. The native title allows 256 palette entries; this preview does not certify insertion.`;
  sync();redrawBackgrounds();
}
function settings(){return {schema:1,backgrounds_sha256:DATA.backgrounds.sha256,source_sha256:DATA.source_sha256,reference_sha256:DATA.reference_sha256,renderer_sha256:DATA.renderer_sha256,candidate_sha256:DATA.candidate.sha256,settings:{...state},custom:custom?{...custom}:null};}
function validateSettings(value){
  assert(value&&typeof value==='object'&&!Array.isArray(value),'Invalid audition JSON.');
  assert(value.backgrounds_sha256===DATA.backgrounds.sha256&&value.schema===1&&value.source_sha256===DATA.source_sha256&&value.reference_sha256===DATA.reference_sha256&&value.renderer_sha256===DATA.renderer_sha256&&value.candidate_sha256===DATA.candidate.sha256,'This audition uses a different source, artwork or renderer revision.');
  const s=value.settings;
  assert(s&&typeof s==='object'&&!Array.isArray(s),'Missing preview settings.');
  assert(['wood-gold-v1','custom'].includes(s.candidate)&&['area','nearest'].includes(s.sampling)&&['concept','rgb555','original'].includes(s.colours),'Unknown artwork or preview option.');
  assert(['art','menu','clean'].includes(s.background_context)&&typeof s.background_native==='boolean','Invalid background view.');
  assert(typeof s.prompt==='boolean'&&typeof s.notes==='string'&&s.notes.length<=8000,'Invalid prompt option or notes.');
  assert(Object.keys(s).sort().join(',')===Object.keys(defaults()).sort().join(','),'Unexpected preview setting.');
  if(value.custom!==null){
    assert(value.custom&&typeof value.custom.name==='string'&&value.custom.name.length<=160&&typeof value.custom.data==='string','Invalid imported artwork.');
    assert(/^data:image\/png;base64,[A-Za-z0-9+/]+={0,2}$/.test(value.custom.data)&&value.custom.data.length<=24*1024*1024,'Imported artwork must be a PNG data URL under 18 MiB.');
  }
  assert(s.candidate!=='custom'||value.custom!==null,'The imported artwork is missing.');
  return {...s};
}
function customOption(){
  const old=$('candidate').querySelector('option[value="custom"]');if(old)old.remove();
  if(custom){const opt=document.createElement('option');opt.value='custom';opt.textContent=custom.name;$('candidate').append(opt);}
}
async function loadSettings(value){
  const next=validateSettings(value);let nextImage=null;
  if(value.custom!==null){nextImage=await image(value.custom.data);validateImage(nextImage);reduce(nextImage,'nearest');}
  // All validation finishes before changing the active draft.
  state=next;custom=value.custom?{...value.custom}:null;customImage=nextImage;revision++;cache.clear();customOption();redraw();
}
async function importArt(data,name){
  const value=settings();value.custom={data,name:name.slice(0,160)};value.settings.candidate='custom';await loadSettings(value);
}
function download(name,url){const a=document.createElement('a');a.download=name;a.href=url;a.click();}
function png(scale=1){const c=canvas(240*scale,160*scale),ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;ctx.drawImage(rendered,0,0,c.width,c.height);return c.toDataURL('image/png');}
function comparison(){
  const c=canvas(960,382),ctx=c.getContext('2d');ctx.fillStyle='#101a23';ctx.fillRect(0,0,c.width,c.height);ctx.fillStyle='#f2eee5';ctx.font='15px sans-serif';
  ctx.fillText('Japanese original',12,23);ctx.fillText(state.candidate==='custom'?'Imported artwork':'English proposal · Wood & gold',492,23);
  ctx.imageSmoothingEnabled=false;ctx.drawImage(originalImage,0,34,480,320);ctx.drawImage(rendered,480,34,480,320);
  ctx.fillStyle='#b9c4c9';ctx.font='12px sans-serif';ctx.fillText('240 × 160 pixels each · Enlarged 2× · Artwork audition, not inserted',12,375);
  return c.toDataURL('image/png');
}
function notice(message){$('notice').textContent=message;$('error').textContent='';}
async function action(fn){try{await fn();}catch(e){$('error').textContent=e.message;$('notice').textContent='';}}
function bind(){
  for(const id of ['candidate','sampling','colours'])$(id).addEventListener('change',()=>action(()=>{state[id]=$(id).value;redraw();}));
  $('prompt').addEventListener('change',()=>{state.prompt=$('prompt').checked;redraw();});
  $('notes').addEventListener('input',()=>{state.notes=$('notes').value;});
  $('position').addEventListener('input',wipe);
  for(const id of ['side','split'])$(id).addEventListener('click',()=>{
    $('side-view').hidden=id!=='side';$('split-view').hidden=id!=='split';
    $('side').setAttribute('aria-pressed',String(id==='side'));$('split').setAttribute('aria-pressed',String(id==='split'));wipe();
  });
  $('reset').addEventListener('click',()=>{state={...defaults(),notes:state.notes};redraw();notice('Preview controls reset. Notes and imported artwork are retained.');});
  for(const [id,scale] of [['export-native',1],['export-large',4]])$(id).addEventListener('click',()=>{download(`torneko2-title-${state.candidate}-${scale}x.png`,png(scale));notice(`Exported ${240*scale} × ${160*scale} PNG.`);});
  $('export-comparison').addEventListener('click',()=>{download('torneko2-title-comparison.png',comparison());notice('Exported original/proposal comparison.');});
  $('save').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(settings(),null,2)+'\n'],{type:'application/json'}));download('torneko2-title-audition.json',url);setTimeout(()=>URL.revokeObjectURL(url),1000);notice('Saved settings, notes and imported artwork.');});
  $('settings-file').addEventListener('change',()=>action(async()=>{const f=$('settings-file').files[0];if(!f)return;assert(f.size<=25*1024*1024,'Audition JSON is too large.');await loadSettings(JSON.parse(await f.text()));$('settings-file').value='';notice('Audition restored.');}));
  $('art-file').addEventListener('change',()=>action(async()=>{const f=$('art-file').files[0];if(!f)return;assert(f.size<=18*1024*1024,'PNG must be under 18 MiB.');const bytes=new Uint8Array(await f.arrayBuffer());assert(same(bytes.slice(0,8),[137,80,78,71,13,10,26,10]),'Choose a PNG image.');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(f);});await importArt(data,f.name);$('art-file').value='';notice('Imported artwork. Save the audition to keep it with your notes.');}));
}
async function verify(){
  const checks=[];const test=(name,fn)=>{fn();checks.push(name);};
  const original=pixels(originalImage).data;
  test('Native original pixels preserved',()=>assert(same($('original').getContext('2d').getImageData(0,0,240,160).data,original),'Reference changed'));
  test('Original prompt strip preserved',()=>assert(same(rendered.getContext('2d').getImageData(0,DATA.prompt_y,240,160-DATA.prompt_y).data,original.slice(DATA.prompt_y*240*4)),'Prompt changed'));
  const initial=settings();
  for(const sampling of ['area','nearest'])for(const colours of ['concept','rgb555','original']){
    $('sampling').value=sampling;$('sampling').dispatchEvent(new Event('change'));$('colours').value=colours;$('colours').dispatchEvent(new Event('change'));
    test(`${sampling}/${colours} controls`,()=>assert(state.sampling===sampling&&state.colours===colours,'Controls failed'));
    const d=rendered.getContext('2d').getImageData(0,0,240,DATA.prompt_y).data;
    if(colours==='rgb555')test(`${sampling}: five-bit channels`,()=>{for(let i=0;i<d.length;i++)if(i%4!==3)assert(Array.from({length:32},(_,n)=>(n<<3)|(n>>2)).includes(d[i]),'Not RGB555');});
    if(colours==='original')test(`${sampling}: original palette membership`,()=>{const allowed=new Set(DATA.palette.map(v=>v.join(',')));for(let i=0;i<d.length;i+=4)assert(allowed.has([d[i],d[i+1],d[i+2]].join(',')),'Not original palette');});
  }
  await loadSettings(initial);
  $('notes').value='Keep the gold. Check <small> lettering & apostrophe.';$('notes').dispatchEvent(new Event('input'));
  const saved=settings();await loadSettings(JSON.parse(JSON.stringify(saved)));
  test('Settings and notes roundtrip',()=>assert(JSON.stringify(saved)===JSON.stringify(settings()),'Roundtrip differs'));
  const invalid=[{...saved,renderer_sha256:'wrong'},{...saved,settings:{...saved.settings,prompt:'yes'}},{...saved,settings:{...saved.settings,colours:'bad'}},{...saved,settings:{...saved.settings,notes:'x'.repeat(8001)}},{...saved,settings:{...saved.settings,candidate:'custom'}},{...saved,custom:{name:'bad',data:'https://invalid.example/a.png'}}];
  for(let i=0;i<invalid.length;i++){let rejected=false;try{await loadSettings(invalid[i]);}catch(e){rejected=true;}test('Invalid settings rejected '+i,()=>assert(rejected&&JSON.stringify(settings())===JSON.stringify(saved),'Invalid import changed draft'));}
  const wrong=canvas(320,160);wrong.getContext('2d').fillRect(0,0,320,160);let rejected=false;
  try{await importArt(wrong.toDataURL(),'wrong.png');}catch(e){rejected=true;}
  test('Wrong aspect ratio rejected atomically',()=>assert(rejected&&JSON.stringify(settings())===JSON.stringify(saved),'Bad aspect ratio accepted'));
  const transparent=canvas();rejected=false;try{await importArt(transparent.toDataURL(),'transparent.png');}catch(e){rejected=true;}
  test('Transparent full-screen image rejected',()=>assert(rejected&&JSON.stringify(settings())===JSON.stringify(saved),'Transparent draft accepted'));
  const sparse=canvas(480,320);sparse.getContext('2d').fillRect(0,0,480,320);sparse.getContext('2d').clearRect(0,0,1,1);rejected=false;
  try{await importArt(sparse.toDataURL(),'sparse-transparency.png');}catch(e){rejected=true;}
  test('Transparent pixel outside nearest samples rejected atomically',()=>assert(rejected&&JSON.stringify(settings())===JSON.stringify(saved),'Sparse alpha accepted'));
  await importArt(DATA.original,'artist-revision.png');state.colours='concept';state.prompt=false;redraw();
  test('Native PNG import keeps exact pixels',()=>assert(same(rendered.getContext('2d').getImageData(0,0,240,160).data,original),'Import changed pixels'));
  const imported=settings();await loadSettings(JSON.parse(JSON.stringify(imported)));
  test('Imported artwork survives settings roundtrip',()=>assert(JSON.stringify(imported)===JSON.stringify(settings()),'Imported art lost'));
  $('reset').click();test('Reset preserves notes and imported artwork',()=>assert(state.candidate==='wood-gold-v1'&&state.notes===saved.settings.notes&&custom.name==='artist-revision.png','Reset discarded notes or artwork'));
  $('split').click();$('position').value=0;$('position').dispatchEvent(new Event('input'));
  test('Slider zero shows proposal',()=>assert(!$('split-view').hidden&&same($('wipe').getContext('2d').getImageData(0,0,240,160).data,rendered.getContext('2d').getImageData(0,0,240,160).data),'Slider zero differs'));
  $('position').value=100;$('position').dispatchEvent(new Event('input'));
  test('Slider hundred shows original',()=>assert(same($('wipe').getContext('2d').getImageData(0,0,240,160).data,original),'Slider hundred differs'));
  $('side').click();await loadSettings(initial);$('position').value=50;wipe();notice('');
  const pngs={'title-english-native.png':png(1),'title-english-4x.png':png(4),'title-comparison.png':comparison()};
  for(const [name,url] of Object.entries(pngs)){const im=await image(url),expected=name.includes('native')?[240,160]:name.includes('4x')?[960,640]:[960,382];test(name+' dimensions',()=>assert(im.width===expected[0]&&im.height===expected[1],'Export size differs'));}
  const backgrounds=await verifyBackgrounds();checks.push(...backgrounds.checks);Object.assign(pngs,backgrounds.pngs);
  return {status:'passed',checks,pngs,settings:settings()};
}
async function start(){
  [originalImage,candidateImage]=await Promise.all([image(DATA.original),image(DATA.candidate.image)]);
  validateImage(candidateImage);bind();redraw();await initBackgrounds();window.TITLE_AUDITION={ready:true,verify};
  if(new URLSearchParams(location.search).get('verify')==='1'){
    let result;try{result=await verify();}catch(e){result={status:'failed',error:e.message,stack:e.stack};}
    const pre=document.createElement('pre');pre.id='verification-result';pre.hidden=true;pre.textContent=JSON.stringify(result);document.body.append(pre);
  }
}
start().catch(e=>{$('error').textContent=e.message;const pre=document.createElement('pre');pre.id='verification-result';pre.hidden=true;pre.textContent=JSON.stringify({status:'failed',error:e.message});document.body.append(pre);});
