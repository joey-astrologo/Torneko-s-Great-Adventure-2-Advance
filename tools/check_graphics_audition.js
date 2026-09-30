(() => {
 const a=window.AUDITION,assert=(v,m)=>{if(!v)throw Error(m);};
 assert(a&&a.ready,'Studio did not finish loading');
 const initial=a.settings(),checks=[];
 assert(a.entries.length===(a.mode==='credits'?15:13),'Entry coverage differs');
 assert(a.candidates.length===8,'Expected eight bitmap candidates');
 let originalCreditsSections=0;
 if(a.mode==='credits'){
  assert(initial.state.creditsStyle==='original','Credits must open on approved original artwork');
  for(let i=0;i<a.entries.length;i++){a.select(i);const v=a.current(),o=v.original.getContext('2d').getImageData(0,0,240,160).data,p=v.candidate.getContext('2d').getImageData(0,0,240,160).data;
   assert(o.every((n,j)=>n===p[j]),'Approved credit pixels changed');originalCreditsSections++;}
  assert(a.metrics.every(m=>m.font==='original-gba-artwork'),'Credits were redrawn with a font');
  const style=document.getElementById('creditsStyle'),face=document.getElementById('face');
  assert(face.disabled,'Original credits typography controls should be inactive');
  style.value='experiment';style.onchange();assert(!face.disabled,'Historical experiment controls stayed inactive');
  style.value='original';style.onchange();assert(face.disabled&&a.metrics.every(m=>m.font==='original-gba-artwork'),'Original view was not restored');
 }else{
  assert(initial.state.face==='shiren-source','Expected directly recovered Shiren starting candidate');
  assert(a.metrics.every(m=>!m.missing.length),'Current arrival names lack source glyphs');
  assert(a.metrics.every(m=>m.fit),'Approved arrival geometry has an overflow');
  const ordeal=a.metrics.find(m=>m.id==='arrival-08-line-0');assert(ordeal.advance===130&&ordeal.budget===136,'Approved Ordeal Mansion width differs');
  assert(a.metrics.every(m=>m.supplements.every(c=>c==='.')),'Unexpected substitute in source font');
  assert(a.measure('AEHKQXYZjqx0123456789','shiren-source',17).missing.length===21,'Absent source glyphs silently replaced');
 }
 for(const face of a.candidates){const s=structuredClone(initial.state);s.creditsStyle='experiment';s.face=face;s.nameFace=face;a.set(s);
  assert(a.metrics.length>0&&a.metrics.every(m=>Number.isFinite(m.advance)&&m.budget>0),'Invalid metrics');
  checks.push({font:face,lines:a.metrics.length,overflows:a.metrics.filter(m=>!m.fit).length,missing:a.metrics.filter(m=>m.missing.length).map(m=>m.id)});
 }
 a.set(initial.state);
 const roundtrip=JSON.parse(JSON.stringify(a.settings()));assert(JSON.stringify(a.validate(roundtrip))===JSON.stringify(initial.state),'Settings roundtrip differs');
 for(const mutate of [v=>v.source_sha256='bad',v=>v.mode='foreign',v=>v.state.height=0,v=>v.state.floor=1000,v=>v.state.face='missing',v=>v.state.wording={'unknown':'Hi'}]){
  const bad=structuredClone(roundtrip);mutate(bad);let rejected=false;try{a.validate(bad);}catch{rejected=true;}assert(rejected,'Invalid settings accepted');assert(JSON.stringify(a.settings())===JSON.stringify(roundtrip),'Rejected settings changed state');
 }
 const huge=structuredClone(initial.state);huge.creditsStyle='experiment';huge.height=24;huge.nameHeight=20;huge.tracking=3;a.set(huge);assert(a.metrics.some(m=>!m.fit),'Overflow was not reported');
 if(a.mode==='arrivals'){
  for(const floor of [1,10,99,999])for(const floorStyle of ['original','candidate']){a.set({...structuredClone(initial.state),floor,floorStyle});a.select(12);const v=a.current();assert(Boolean(v.suppressed)===(floor>10),'Well suppression differs');a.select(11);assert(a.current().candidate.width===240,'Arrival canvas size differs');}
  const altered=structuredClone(initial.state);altered.wording={'arrival-00':'A\nB'};a.set(altered);assert(a.metrics.filter(m=>m.id.startsWith('arrival-00-line')).length===2,'Explicit line breaks ignored');
 }
 a.set(initial.state);a.select(0);
 for(const e of ['png','png3','compare','sheet','save','load','metrics','allMetrics','rollPNG'])assert(typeof document.getElementById(e).onclick==='function','Export not bound: '+e);
 assert(a.csv().includes('width_budget_px')&&a.csv().includes('"fits"'),'CSV missing budget columns');
 const sheet=a.sheet();assert(sheet.width>240&&sheet.height>160,'Sheet export is empty');
 const c=a.current().candidate,data=c.getContext('2d').getImageData(0,0,240,160).data;assert(data.some((v,i)=>i%4!==3&&v!==0),'Candidate pixels are blank');
 const allFonts=a.allFontMetrics();assert(new Set(allFonts.map(m=>m.font)).size===8,'All-font budgets incomplete');assert(JSON.stringify(a.settings())===JSON.stringify(roundtrip),'All-font export changed current settings');
 return {passed:true,mode:a.mode,entries:a.entries.length,candidates:checks,original_credit_sections_compared:originalCreditsSections,source_only_shiren_checked:a.mode==='arrivals',settings_roundtrip:true,invalid_imports_rejected:6,overflow_detected:true,original_settings_restored:true,sheet_dimensions:[sheet.width,sheet.height],default_overflows:a.metrics.filter(m=>!m.fit).map(m=>m.id),all_font_budgets:allFonts,all_font_budgets_csv:a.csv(allFonts)};
})()
