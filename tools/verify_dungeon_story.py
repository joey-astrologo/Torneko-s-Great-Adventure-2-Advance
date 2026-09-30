"""Original dungeon story message blocks, full frames and native Yes/No branches."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO

# Source index -> original message-block entry and continuation.
BLOCKS={0:(0x1BCEC,0x1BD10),1:(0x1BD30,0x1BD5A),2:(0x1BD5A,0x1BD76),3:(0x1BD88,0x1BDA4),4:(0x1BDCE,0x1BDEA),5:(0x1C042,0x1C06E),6:(0x1C06E,0x1C08E),7:(0x1C09C,0x1C0BC),8:(0x1C0C4,0x1C0D2),10:(0x1C0F0,0x1C116),11:(0x1C13E,0x1C1E4),14:(0x1C1C0,0x1C1E4),15:(0x1C394,0x1C3C0),16:(0x1C3C6,0x1C3E2),17:(0x1C3F4,0x1C410),18:(0x1C41A,0x1C428),20:(0x1C43C,0x1C460),21:(0x1C4A0,0x1C4C4),22:(0x1C4F6,0x1C51A)}

def run(source,only=None):
 out=source/'dungeon-story-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale dungeon-story ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 by_index={r['index']:r for r in build['dungeon_story']['entries']};resources={r['offset']+0x08000000:r for r in by_index.values()};results=[]
 for index,(start,stop) in BLOCKS.items():
  if only is not None and index!=only:continue
  for profile,player in (player_layout_cases() if index in (8,11,18,21) else [('ordinary',None)]):
   for choice in (('yes','no','cancel') if index==11 else ('continue',)):
    case=f'{index}-{profile}-{choice}';print('Dungeon story:',case,flush=True)
    entry,prologue,epilogue,end=(0x1BC24,0x1BC30,0x1BE00,0x1BE0E) if index<5 else (0x1BFBC,0x1BFC8,0x1C268,0x1C276) if index<15 else (0x1C2E8,0x1C2F4,0x1C520,0x1C52E)
    with Session(rom,out/case) as g:
     g.restore(fixture);m=g.core.memory;initial=[];returns=[];overrides=[];draws=[];images={};pixels=0;modals=[];modal_returns=[];choice_results=[];helpers=[];panel=TextChecks(g,resources);modal_pending=[]
     def write(a,data):
      overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
      for i,v in enumerate(data):m.u8[a+i]=v
     def reg(e,i,v):overrides.append({'event':e,'register':i,'after':v});g.core.cpu.gprs[i]=v
     def jump(e,at,why):
      overrides.append({'event':e,'pc_after':at+0x08000000,'reason':why});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Dungeon story redirect failed')
     item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000))
     hero=m.u32[0x02001624];gold=m.u32[hero+0x60];inventory=bytes(m[0x0200DF28:0x0200E888])
     def callback(e):
      a,r=e['address'],e['registers']
      if a==0x08015848 and not initial:
       initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'inventory':bytes(m[0x0200DF28:0x0200E888]).hex()});jump(e,entry,'Controlled native Drink dispatch into complete cutscene prologue.');return
      if not initial or returns:return
      if a==prologue+0x08000000:
       if player:write(HERO,player.ljust(16,b'\0'))
       # Establish the original live register state required by the selected
       # basic block, without substituting any string pointer at the modal.
       if index<5:values={4:0,5:512,6:0x020015EC,8:0x020015EE,9:m.u32[0x0801BE10]}
       elif index<15:values={4:0,5:0,7:hero,8:0x020015EC,9:0x020015EE,10:512}
       else:values={4:0,5:512,6:0x020015EC,7:hero,8:0x020015EE,9:m.u32[0x0801C530]}
       for i,v in values.items():reg(e,i,v)
       jump(e,start,'Execute original immutable-ROM table load and native modal block; cutscene staging/movement excluded.')
      if a==0x0801C958:helpers.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
      if a==0x0801C962:
       reg(e,4,0);jump(e,0x1C9FC,'Relic helper retains its original frame/source but animation and item effects are excluded.')
      if a==0x0801CA1E:jump(e,0x1CA34,'Return through original relic-helper epilogue after its complete native text.')
      if a==0x0801CA3A:
       old=helpers[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==helpers[-1]['guard'],'Relic helper caller ABI differs')
      if a==0x08015A18:
       require(r[0] in resources,'Dungeon story selected an unowned source');row=resources[r[0]];expected_choice=row['index']==11
       require(r[2]==int(expected_choice),'Dungeon story native choice mode differs');modals.append(e|{'id':row['id']});modal_pending.append(e)
      if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
      if a==0x08001BC4 and panel.active:
       w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
       if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
      if a in panel.ADDRESSES:panel.callback(e)
      if modal_pending and a==(modal_pending[-1]['registers'][14]&~1):
       old=modal_pending.pop()['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Dungeon story modal ABI differs');modal_returns.append(e|{'inventory':bytes(m[0x0200DF28:0x0200E888]).hex()})
      if a==0x0801C168:
       require(r[0]==(1 if choice=='yes' else 0),'Old man native Yes/No result differs');choice_results.append(e)
      if a==stop+0x08000000:jump(e,epilogue,'Native message/choice branch completed; subsequent quest effects excluded.')
      if a==end+0x08000000:
       old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Dungeon story caller ABI/guard differs');returns.append(e|{'inventory':bytes(m[0x0200DF28:0x0200E888]).hex()})
     def capture(tag):
      nonlocal pixels
      g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Dungeon story no visible text')
      for d in draws:
       glyph,_=panel.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
       for y,line in enumerate(glyph['rows']):
        for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Dungeon story final pixels differ: '+repr((case,tag,hex(d['code']))));pixels+=1
     addresses={0x08015848,prologue+0x08000000,end+0x08000000,stop+0x08000000,0x08015A18,0x08001750,0x0801C958,0x0801C962,0x0801CA1E,0x0801CA3A,0x0801C168,0x0801C18C,0x0801C1C0,0x0801C1E4}
     with Debugger(g,callback,max_events=220000) as debug:
      for a in addresses|set(panel.ADDRESSES):debug.breakpoint(a)
      g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
      for i in range(7):
       n=m.u16[0x0200CDD0+2*i]
       if not n:break
       actions.append(n)
      require(13 in actions,'Dungeon story Drink trigger absent')
      for _ in range(actions.index(13)):g.press('DOWN',wait=20)
      g.press('A',hold=1,wait=0);handled=set()
      for tick in range(3600):
       if returns:break
       waiting=panel.active and panel.active['page_waits']
       state=(len(panel.reads),panel.active['page_waits'] if panel.active else -1)
       if (waiting or (panel.reads and not panel.active)) and state not in handled:
        capture('page-'+str(len(images)));handled.add(state)
        if not panel.active and panel.reads[-1]['id']=='dungeon-story.11':
         if choice=='no':g.press('RIGHT',hold=1,wait=15)
         g.press('B' if choice=='cancel' else 'A',hold=1,wait=0)
        else:g.press('A',hold=1,wait=0)
       else:g.frames(1)
      require(len(initial)==len(returns)==1 and panel.reads and not panel.active and not modal_pending,'Dungeon story route incomplete: '+repr((case,len(modals),len(modal_returns),len(panel.reads),len(returns))))
     expected=[11,12 if choice=='yes' else 13,14] if index==11 else [index]
     require([int(r['id'].split('.')[-1]) for r in panel.reads]==expected and len(modals)==len(modal_returns)==len(expected),'Dungeon story selected sources/branches differ')
     require(len(images)==sum(len(by_index[i]['layout']['pages']) for i in expected),'Dungeon story pages missing')
     require(m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200E888]).hex()==initial[0]['inventory']==returns[0]['inventory'] and g.snapshot().battery==fixture.battery,'Dungeon story text probe changed items/gold/save')
     results.append({'case':case,'index':index,'profile':profile,'choice':choice,'inputs':g.inputs,'overrides':overrides,'reads':panel.reads,'modals':modals,'modal_returns':modal_returns,'choice_results':choice_results,'helpers':helpers,'caller_guard_abi_preserved':True,'inventory_stable_during_message_block':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native Drink dispatch, complete original cutscene frames, original table-load/message blocks and complete native modals, pages, colours, player/initial bounds and exact pixels. The old-man identity question follows all original Yes/No/cancel response branches. Relic helper source handoff and complete frame execute with animation/item effects excluded. Full helper/modal/caller ABI and unchanged gold/battery. Inventory is unchanged across the controlled message block; native Drink consumes the test herb before that entry, so no claim is made of unchanged inventory across the trigger action. Natural cutscene triggering, movement, story flags and relic acquisition effects remain unverified. Unread farewell slots9/19 are excluded.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Dungeon story:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
