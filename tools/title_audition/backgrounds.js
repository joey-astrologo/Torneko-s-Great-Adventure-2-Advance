// One shared compact mark paired with the approved full-screen title.
let backgroundReady=false, badgeImage, backgroundImages=[], backgroundCanvases=[];
const badgeCache=new Map();
function reduceBadge(method){
  if(badgeCache.has(method))return badgeCache.get(method);
  const source=pixels(badgeImage), out=new ImageData(76,36), sx=source.width/76, sy=source.height/36;
  assert(source.data.some((v,i)=>i%4===3&&v===0),'Floating logo needs transparency.');
  for(let y=0;y<36;y++)for(let x=0;x<76;x++){
    const target=(y*76+x)*4;
    if(method==='nearest'){
      const at=(Math.floor((y+.5)*sy)*source.width+Math.floor((x+.5)*sx))*4;
      out.data.set(source.data.subarray(at,at+4),target);
    }else{
      const x0=x*sx,x1=Math.min(source.width,(x+1)*sx),y0=y*sy,y1=Math.min(source.height,(y+1)*sy);
      const sum=[0,0,0,0];
      for(let yy=Math.floor(y0);yy<Math.ceil(y1);yy++)for(let xx=Math.floor(x0);xx<Math.ceil(x1);xx++){
        const weight=(Math.min(x1,xx+1)-Math.max(x0,xx))*(Math.min(y1,yy+1)-Math.max(y0,yy));
        const at=(yy*source.width+xx)*4,alpha=source.data[at+3]/255;
        for(let c=0;c<3;c++)sum[c]+=source.data[at+c]*alpha*weight;
        sum[3]+=alpha*weight;
      }
      for(let c=0;c<3;c++)out.data[target+c]=sum[3]?Math.round(sum[c]/sum[3]):0;
      out.data[target+3]=Math.round(255*sum[3]/((x1-x0)*(y1-y0)));
    }
  }
  badgeCache.set(method,out);return out;
}
function colourPixels(raw,palette){
  const out=new ImageData(new Uint8ClampedArray(raw.data),raw.width,raw.height), nearest=new Map();
  for(let i=0;i<out.data.length;i+=4){
    let rgb=Array.from(out.data.subarray(i,i+3));
    if(state.colours==='rgb555')rgb=rgb.map(v=>{const n=Math.round(v*31/255);return(n<<3)|(n>>2);});
    if(state.colours==='original'){
      const key=rgb.join(',');
      if(!nearest.has(key)){
        let best=Infinity, chosen;
        for(const p of palette){const d=p.reduce((sum,v,c)=>sum+(v-rgb[c])**2,0);if(d<best){best=d;chosen=p;}}
        nearest.set(key,chosen);
      }
      rgb=nearest.get(key);
    }
    out.data.set(rgb,i);
  }
  return out;
}
function cornerPixels(palette){return colourPixels(reduceBadge(state.sampling),palette);}
function backgroundSource(i){return state.background_context==='menu'?backgroundImages[i].menu:backgroundImages[i].original;}
function composeBackground(i){
  const row=DATA.backgrounds.cases[i], out=canvas(), ctx=out.getContext('2d');
  ctx.drawImage(backgroundSource(i),0,0);
  const [x,y,w,h]=row.rectangle, clean=backgroundImages[i].clean,logo=reduceBadge(state.sampling),patch=new ImageData(w,h);
  for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++){
    const at=(yy*w+xx)*4,from=((y+yy)*240+x+xx)*4,alpha=state.background_context==='clean'?0:logo.data[at+3]/255;
    for(let c=0;c<3;c++)patch.data[at+c]=Math.round(logo.data[at+c]*alpha+clean.data[from+c]*(1-alpha));
    patch.data[at+3]=255;
  }
  ctx.putImageData(colourPixels(patch,row.palette),x,y);
  return out;
}
function redrawBackgrounds(){
  if(!backgroundReady)return;
  $('background-context').value=state.background_context;$('background-native').checked=state.background_native;
  $('background-grid').classList.toggle('actual-size',state.background_native);
  backgroundCanvases=DATA.backgrounds.cases.map((row,i)=>{
    const out=composeBackground(i);paint(`bg-original-${row.index}`,backgroundSource(i));paint(`bg-english-${row.index}`,out);return out;
  });
  const small=canvas(76,36);small.getContext('2d').putImageData(cornerPixels(DATA.backgrounds.cases[0].palette),0,0);
  paint('corner-native',small);paint('corner-large',small);
}
function backgroundSheet(){
  const sheet=canvas(960,1780),ctx=sheet.getContext('2d');ctx.fillStyle='#101a23';ctx.fillRect(0,0,960,1780);
  ctx.fillStyle='#f2eee5';ctx.font='16px sans-serif';ctx.fillText('Original backgrounds / English corner-logo audition · 2× native size',12,25);
  ctx.imageSmoothingEnabled=false;
  DATA.backgrounds.cases.forEach((row,i)=>{const y=40+i*346;ctx.fillStyle='#efbc68';ctx.fillText(`${row.name} · ${row.index} · ${row.index===13?'bottom right':'top right'}`,12,y+16);ctx.drawImage(backgroundSource(i),0,y+22,480,320);ctx.drawImage(backgroundCanvases[i],480,y+22,480,320);});
  return sheet.toDataURL('image/png');
}
async function initBackgrounds(){
  badgeImage=await image(DATA.backgrounds.badge);
  backgroundImages=await Promise.all(DATA.backgrounds.cases.map(async row=>({original:await image(row.original),menu:await image(row.menu),clean:reduce(await image(row.clean),'area')})));
  const grid=$('background-grid');
  DATA.backgrounds.cases.forEach(row=>{
    const card=document.createElement('article');card.className='background-card';
    const heading=document.createElement('h3');heading.textContent=`${row.name} · ${row.index===13?'bottom right':'top right'}`;card.append(heading);
    const pair=document.createElement('div');pair.className='background-pair';
    for(const side of ['original','english']){
      const figure=document.createElement('figure'),label=document.createElement('figcaption'),c=canvas();
      label.textContent=side==='original'?'ORIGINAL ARTWORK':'ENGLISH COMPOSITE';c.id=`bg-${side}-${row.index}`;c.className='screen';figure.append(label,c);pair.append(figure);
    }
    card.append(pair);
    const button=document.createElement('button');button.className='subtle';button.textContent='Export this English PNG';button.addEventListener('click',()=>download(`torneko2-background-${row.index}-${state.background_context}.png`,backgroundCanvases[DATA.backgrounds.cases.indexOf(row)].toDataURL('image/png')));card.append(button);grid.append(card);
  });
  $('background-context').addEventListener('change',()=>{state.background_context=$('background-context').value;redrawBackgrounds();});
  $('background-native').addEventListener('change',()=>{state.background_native=$('background-native').checked;redrawBackgrounds();});
  $('export-backgrounds').addEventListener('click',()=>download('torneko2-background-comparison.png',backgroundSheet()));
  backgroundReady=true;redrawBackgrounds();
}
async function verifyBackgrounds(){
  const checks=[],pngs={},test=(name,fn)=>{fn();checks.push(name);},initial=settings();
  test('All five menu backgrounds present',()=>assert(DATA.backgrounds.cases.map(r=>r.index).join(',')==='13,18,19,20,21','Wrong background family'));
  for(const context of ['art','menu','clean']){
    $('background-context').value=context;$('background-context').dispatchEvent(new Event('change'));
    test(`${context}: background context control`,()=>assert(state.background_context===context,'Context control failed'));

    DATA.backgrounds.cases.forEach((row,i)=>{
      const d=pixels(backgroundCanvases[i]).data,o=pixels(backgroundSource(i)).data,[x,y,w,h]=row.rectangle;
      test(`${context}/${row.index}: every pixel outside logo unchanged`,()=>{for(let yy=0;yy<160;yy++)for(let xx=0;xx<240;xx++)if(xx<x||xx>=x+w||yy<y||yy>=y+h){const at=(yy*240+xx)*4;for(let c=0;c<4;c++)assert(d[at+c]===o[at+c],'Scene or UI changed');}});
      const patch=backgroundCanvases[i].getContext('2d').getImageData(x,y,w,h).data;
      test(`${context}/${row.index}: alpha composite uses shared lettering`,()=>{
        const logo=reduceBadge(state.sampling).data,clean=backgroundImages[i].clean.data;
        for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++){
          const at=(yy*w+xx)*4,from=((y+yy)*240+x+xx)*4,alpha=context==='clean'?0:logo[at+3]/255;
          for(let c=0;c<3;c++){const v=Math.round(logo[at+c]*alpha+clean[from+c]*(1-alpha)),n=Math.round(v*31/255);assert(patch[at+c]===((n<<3)|(n>>2)),'Unexpected colour or opaque backing');}
        }
      });
      const name=`background-${row.index}-${context}.png`;pngs[name]=backgroundCanvases[i].toDataURL('image/png');
    });
  }
  const changed=settings();changed.settings.background_context='art';changed.settings.background_native=false;
  await loadSettings(changed);
  test('Background controls survive settings import',()=>assert(state.background_context==='art'&&!state.background_native&&!$('background-grid').classList.contains('actual-size'),'Background settings failed'));
  $('background-native').click();test('Native background size control',()=>assert(state.background_native&&$('background-grid').classList.contains('actual-size'),'Native size toggle failed'));
  const bad=settings();bad.backgrounds_sha256='wrong';let rejected=false;try{await loadSettings(bad);}catch(e){rejected=true;}
  test('Mismatched linked artwork rejected',()=>assert(rejected,'Wrong background set accepted'));
  await loadSettings(initial);
  pngs['background-comparison.png']=backgroundSheet();
  const logo=cornerPixels(DATA.backgrounds.cases[0].palette),logoCanvas=canvas(76,36);logoCanvas.getContext('2d').putImageData(logo,0,0);
  test('Floating logo has transparent edges and gaps',()=>{const alpha=Array.from(logo.data).filter((v,i)=>i%4===3);assert(alpha.filter(v=>v===0).length>alpha.length*.15&&alpha.some(v=>v>=240),'Logo lacks transparent gaps or solid lettering');assert([0,75,35*76,36*76-1].every(i=>alpha[i]===0),'Logo corners opaque');});
  pngs['corner-logo-native.png']=logoCanvas.toDataURL('image/png');
  for(const [name,url] of Object.entries(pngs)){const im=await image(url);test(`${name}: export dimensions`,()=>assert(im.width===(name==='background-comparison.png'?960:name==='corner-logo-native.png'?76:240)&&im.height===(name==='background-comparison.png'?1780:name==='corner-logo-native.png'?36:160),'Background export dimensions differ'));}
  return {checks,pngs};
}
