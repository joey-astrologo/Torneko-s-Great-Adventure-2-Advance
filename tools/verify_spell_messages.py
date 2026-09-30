"""Native cast gates, spell learning/forgetting, queue/panel text and state checks."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.compact_font import encode
from tools.dialogue_checks import TextChecks,rendered_codes,player_layout_cases
from tools.name_entry import HERO
from tools.inventory_action_text import CONTROL
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_result_ui import native_format
from tools.verify_service_ui import cstring

class SpellQueue(ActionCheck):
    def width(self,data):
        m=self.game.core.memory
        return sum(self.glyph_record(c)[0]['advance'] for c in rendered_codes(data+b'\0',bytes(m[HERO:HERO+16])))
    def callback(self,e):
        a,r=e['address'],e['registers'];m=self.game.core.memory
        if a==0x080158CE and self.queue_abi and self.queued is None:
            require(m.u32[r[13]+12]==self.queue_return,'Spell queue owner differs')
            raw=cstring(m,r[6]);require(raw==self.expected_payload and len(raw)+1<=256 and bytes(m[r[6]+256:r[6]+272])==self.guard,'Spell queue payload/guard differs')
            widths=[self.width(p) for p in raw.split(CONTROL)];require(len(widths)<=2 and max(widths)<=216,'Spell queue line overflow')
            if sum(widths)<=215:widths=[sum(widths)]
            self.queued={'hex':raw.hex(),'line_widths':widths,'one_line':len(widths)==1,'bytes':len(raw)+1}
            self.expected=rendered_codes(raw.replace(CONTROL,b'')+b'\0',bytes(m[HERO:HERO+16]));self.window=0x02000000
        super().callback(e)


def run(source,only=None):
    out=source/'spell-messages-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale spell message ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['table_offset']:r for r in build['spell_messages']['entries']};names={r['spell_id']:r for r in build['spell_info']['entries'] if r['kind']=='name'};definitions=build['spell_info']['definitions']
    handler_base=struct.unpack_from('<I',rom,0x411E8)[0]-0x08000000
    handlers={i:struct.unpack_from('<I',rom,handler_base+8*i)[0] for i in range(61)}
    weights=[bytes.fromhex(r['record_hex'])[7] for r in definitions];configs=[]
    for i in range(1,61):
        configs.extend((f'{kind}-{i}',kind,i,None) for kind in ('unlearned','cast'))
        if handlers[i] and definitions[i]['hp_cost']>0:configs.append((f'low-hp-{i}','low-hp',i,None))
        if weights[i]:configs.extend((f'learn-{i}-{label}','learn',i,player) for label,player in player_layout_cases())
        if i not in (1,22):configs.append((f'forget-{i}','forget',i,None))
    results=[]
    for case,kind,ident,player in configs:
        if only and not (case==only or kind==only):continue
        print('Spell message:',case,flush=True)
        with Session(rom,out/case) as g:
            g.restore(fixture);m=g.core.memory;hero=m.u32[0x02001624];overrides=[];initial=[];returns=[];formats=[];pending={};queues=[];images={};draws=[];colours=[];pixels=0;skips=[];panel=TextChecks(g,{})
            entry=0x3EDF8 if kind=='learn' else 0x41A58 if kind=='forget' else 0x40FD0
            end=0x3EF28 if kind=='learn' else 0x41B74 if kind=='forget' else 0x41A40
            hp=definitions[ident]['hp_cost'] if kind=='low-hp' else 500
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def register(e,index,value):
                overrides.append({'event':e,'register':index,'after':value});g.core.cpu.gprs[index]=value
            def jump(e,pc,reason):
                skips.append({'event':e,'pc_after':pc,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',pc)),'Spell controlled dispatch failed')
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            format_owners={0x4105C:(0x920,0x41065,8),0x4118A:(0x860,0x41193,8),0x411CE:(0x86C,0x411D7,8),0x3EEE8:(0x848,0x3EEF1,0),0x41B32:(0x91C,None,4)}
            def callback(e):
                nonlocal pending
                a,r=e['address'],e['registers']
                if a==0x08015848 and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    write(hero+0x90,b'\2');write(hero+0x9E,b'\0');write(hero+0xA7,b'\1');write(hero+0x84,struct.pack('<HHH',hp,500,2));write(0x0200883A,b'\0')
                    learned=bytes(int(i==ident and kind not in ('unlearned','learn')) for i in range(61));write(0x02004D80,learned);write(0x02004DBD,bytes(61))
                    if player:write(HERO,player.ljust(16,b'\0'))
                    for i,v in enumerate((ident,0,0,0)):register(e,i,v)
                    jump(e,entry+0x08000000,'Controlled dispatch from native Drink with its original return address.');return
                if not initial or returns:return
                if a==0x08041092:register(e,0,98)
                if kind=='learn' and a==0x0803EE1A:register(e,0,1)
                if kind=='learn' and a==0x0803EE96:register(e,0,sum(weights[:ident])+1)
                if kind=='forget' and a==0x08041A90:register(e,0,998)
                if kind=='forget' and a==0x08041AD6:register(e,0,0)
                if a==0x0804120A:
                    require(kind=='cast' and m.u16[hero+0x84]==hp-definitions[ident]['hp_cost'],'Native spell HP payment differs')
                    jump(e,0x08041A2C,'After native cast announcement and HP payment; spell-specific targeting/effects are outside this text check.')
                if a==0x08000FB8 and (r[14]&~1)-0x08000000 in format_owners:
                    ret=(r[14]&~1)-0x08000000;slot,queue,offset=format_owners[ret];row=rows[slot]
                    require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+offset,'Spell message source/buffer differs')
                    if slot!=0x86C:require(r[2]==names[ident]['offset']+0x08000000,'Native spell name selector differs')
                    raw=native_format(bytes.fromhex(row['encoded_hex']),[r[2]],m);require(len(raw)<=row['maximum_bytes']<=256,'Spell message expansion overflow')
                    pending={'regs':r,'row':row,'raw':raw,'ret':ret+0x08000000,'guard':bytes(m[r[0]+256:r[0]+272])}
                    if queue:
                        require(not queues or queues[-1].complete and queues[-1].returned,'Prior spell message incomplete');queues.append(SpellQueue(g,raw[:-1],queue+0x08000000,256,pending['guard']));colours.append([])
                if pending and a==pending['ret']:
                    old=pending['regs'];raw=pending['raw'];p=old[0];require(bytes(m[p:p+len(raw)])==raw and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Spell formatter output/guard/ABI differs');formats.append({'id':pending['row']['id'],'hex':raw.hex(),'bytes':len(raw),'capacity':256,'guard_abi_preserved':True})
                    if kind=='forget':panel.resources[p]={'id':pending['row']['id'],'encoded_hex':raw.hex(),'layout':{'pages':[[pending['row']['id']]]}}
                    pending={}
                if queues and not (queues[-1].complete and queues[-1].returned):
                    c=queues[-1];duplicate=False
                    if a==0x08001C14 and c.pending_glyph:
                        bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10));key=(r[0],r[4],r[5],r[13],r[14],rgb);d=c.pending_glyph;duplicate='preparation' in d
                        if duplicate:require(d['preparation']==key,'Repeated spell glyph preparation differs')
                        else:d['preparation']=key;colours[-1].append(rgb)
                    if not duplicate:c.callback(e)
                if kind=='forget':
                    if a==0x08001BC4 and panel.active:
                        w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                        if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                    if a in panel.ADDRESSES:panel.callback(e)
                if a==end+0x08000000:
                    old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0 if kind in ('learn','forget') else 1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Spell caller ABI/guard differs');returns.append(e)
            with Debugger(g,callback,max_events=150000) as debug:
                addresses={0x08015848,0x08000FB8,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08041092,0x0804120A,0x0803EE1A,0x0803EE96,0x08041A90,0x08041AD6,end+0x08000000}|set(panel.ADDRESSES)|{0x08000000+a for a in format_owners}|{0x08000000+(q&~1) for _,q,_ in format_owners.values() if q}
                for a in addresses:debug.breakpoint(a)
                g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
                for i in range(7):
                    n=m.u16[0x0200CDD0+i*2]
                    if not n:break
                    actions.append(n)
                require(13 in actions,'Spell test Drink trigger absent')
                for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                g.capture('menu');images['menu.png']=digest((g.output/'menu.png').read_bytes());g.press('A',wait=0)
                panel_captured=False
                for _ in range(1200):
                    g.frames(1)
                    if kind=='forget' and panel.reads and not panel.active and not panel_captured:
                        g.frames(3);pic=g.capture('message');images['message.png']=digest((g.output/'message.png').read_bytes())
                        for d in draws:
                            glyph,_=panel.glyph_record(d['code']);require(d['x']+glyph['advance']<=m.u8[d['window']+4]*8,'Forget spell panel clips');colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                            for y,line in enumerate(glyph['rows']):
                                for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+d['y']*16+y))==rgb)==(bit=='#'),'Forget spell final pixels differ');pixels+=1
                        panel_captured=True;g.press('A',wait=0)
                    if returns:break
                expected_slots=[0x848] if kind=='learn' else [0x91C] if kind=='forget' else [0x920] if kind=='unlearned' else [0x860,0x86C] if kind=='low-hp' else [0x860]
                require(len(initial)==len(returns)==1 and [r['id'] for r in formats]==[rows[s]['id'] for s in expected_slots] and not pending and all(c.complete and c.returned for c in queues),'Spell message route incomplete: '+repr((case,[r['id'] for r in formats],len(returns),[hex(x) for x in g.core.cpu.gprs])))
                if kind!='forget':
                    g.frames(3);pic=g.capture('message');images['message.png']=digest((g.output/'message.png').read_bytes());c=queues[-1];require(len(c.draws)==len(colours[-1]),'Spell queue colour coverage differs');visible=[]
                    for d,rgb in zip(c.draws,colours[-1]):
                        if d['native_scroll']:
                            shift=d['key'][-1]-d['y']
                            for old in visible:old['final_y']-=shift
                        visible.append(d|{'final_y':d['y'],'colour':rgb})
                    for d in visible:
                        require(d['final_y']>=0,'Spell text scrolled out of view');glyph,_=c.glyph_record(d['code'])
                        for y,line in enumerate(glyph['rows']):
                            for x,bit in enumerate(line):require((pic.getpixel((m.u8[c.window]+d['x']+x,m.u8[c.window+1]+d['final_y']*16+y))==d['colour'])==(bit=='#'),'Spell message final pixels differ');pixels+=1
                else:require(panel_captured and not panel.active,'Forget spell panel did not render/close')
                expected_hp=hp-definitions[ident]['hp_cost'] if kind=='cast' and handlers[ident] else hp;require(m.u16[hero+0x84]==expected_hp,'Spell HP outcome differs')
                learned=bytes(int(i==ident and kind not in ('unlearned','forget')) for i in range(61));require(bytes(m[0x02004D80:0x02004D80+61])==learned,'Spell learned state differs')
                require(bytes(m[0x02004DBD:0x02004DBD+61])==bytes(int(i==ident and kind=='learn') for i in range(61)),'Spell learned-history state differs')
            require(g.snapshot().battery==fixture.battery,'Spell message wrote battery')
            results.append({'case':case,'kind':kind,'spell_id':ident,'inputs':g.inputs,'overrides':overrides,'skips':skips,'formats':formats,'queues':[c.queued for c in queues],'reads':panel.reads,'native_state_checked':True,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled original spell routines with real selectors, full names, HP gates/payment, learning and forgetting state. Cast checks stop after HP payment before spell-specific targeting/effects; those effects are explicitly not gameplay acceptance. RNG selections, actor state and player names are recorded. Original256-byte buffers, ABI, queues/panel, compact glyphs, final pixels and battery checked.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Spell messages:',len(results),'passed',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/spell-messages-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
