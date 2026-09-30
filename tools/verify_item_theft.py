"""Native item-theft transfers/refusals and compact conditional message layout."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.compact_font import encode
from tools.dialogue_checks import rendered_codes,player_layout_cases
from tools.emulator import Session,Debugger,ffi
from tools.inventory_action_text import CONTROL
from tools.name_entry import HERO
from tools.rom import ROOT,digest,load_base,require
from tools.verify_combat_prototype import CombatCheck
from tools.verify_service_ui import materialize,cstring


class TheftCheck(CombatCheck):
    def __init__(self,*args):
        super().__init__(*args);self.breaks=[]
    def callback(self,e):
        a,r=e['address'],e['registers'];m=self.game.core.memory
        if a==0x080158CE and self.queue_abi and self.queued is None:
            require(m.u32[r[13]+12]==self.queue_return,'Item theft queue owner differs')
            raw=cstring(m,r[6]);require(raw==self.expected_payload and len(raw)+1<=self.capacity and bytes(m[r[6]+self.capacity:r[6]+self.capacity+16])==self.guard,'Item theft queue bytes/guard differ')
            parts=raw.split(CONTROL);require(1<=len(parts)<=3,'Item theft conditional vocabulary differs')
            require(all(self.width(p)<=216 for p in parts),'Item theft fallback segment exceeds budget')
            self.queued={'hex':raw.hex(),'bytes':len(raw)+1,'fallback_widths':[self.width(p) for p in parts]}
            self.expected=rendered_codes(raw.replace(CONTROL,b'')+b'\0');self.window=0x02000000
        if a==0x080020F4 and self.queued and not self.complete:
            require(r[0]==224,'Item theft native window threshold changed')
            self.breaks.append({'glyph_index':len(self.draws),'current_x':m.u8[self.window+2],'native_width':r[0],'measured':r[1],'wraps':r[1]>r[0]})
        super().callback(e)
        if self.draws:require(self.draws[-1]['x']+self.draws[-1]['advance']<=216,'Item theft actual glyph exceeds budget')


def run(source=ROOT/'build/item-theft-prototype',only=None):
    out=source/'item-theft-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale item-theft ROM')
    from tools import verify_player_status_prototype as status
    prior=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    rows={r['table_offset']:r for r in build['item_theft']['entries']};direct={r['offset']+0x08000000:r for r in rows.values()}
    stolen_base=struct.unpack_from('<I',load_base(),0x2C0E0)[0]
    configs=[(branch,'native') for branch in ('success','empty','full','protected','ability','transformed','wait')]
    configs += [(branch,field) for branch in ('success','empty','full','protected','wait') for field in ('maximum-width','maximum-bytes','coloured')]
    configs += [('success','player-'+label) for label,_ in player_layout_cases()]
    results=[]
    for branch,field in configs:
        name=branch+'-'+field
        if only and name!=only:continue
        slot=0x2B0 if branch=='success' else 0x2AC if branch in ('empty','wait') else 0x2B8 if branch=='full' else 0x710
        row=rows[slot];print('Item theft:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;hero=m.u32[0x02001624];initial=[];returns=[];overrides=[];formats=[];pending={};checks=[];colours=[];images={};skips=[];actor=None;before_inventory=None
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def jump(e,target):
                overrides.append({'event':e,'pc_after':target});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',target)),'Item theft controlled dispatch failed')
            trigger=bytearray(120);struct.pack_into('<I',trigger,0,0xC8000000);trigger[4:6]=b'\1\1';trigger[8]=bytes(m[0x020013D0:0x020014D0]).index(177)
            write(0x0200DF28,trigger);at=0x02003BAC+177*20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            def callback(e):
                nonlocal actor,before_inventory
                a,r=e['address'],e['registers']
                if a==0x08015848 and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    actor=next(m.u32[0x02001624+4*i] for i in range(1,56) if 0x02000000<=m.u32[0x02001624+4*i]<0x0203FF00 and m.u32[m.u32[0x02001624+4*i]+8]&0x80000000)
                    write(hero+0xBF,bytes((int(branch=='transformed'),)))
                    write(0x0200DF28,bytes(2400));item=bytearray(120)
                    if branch!='empty':
                        struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item)
                        at=0x02003BAC+177*20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
                    before_inventory=bytes(m[0x0200DF28:0x0200E888]);write(stolen_base,bytes(16*120))
                    if branch=='full':
                        for i in range(16):write(stolen_base+120*i,struct.pack('<I',0x80000000))
                    if field.startswith('player-'):write(HERO,dict(player_layout_cases())[field[7:]].ljust(16,b'\0'))
                    if field=='maximum-width':write(HERO,dict(player_layout_cases())['widest-Japanese'].ljust(16,b'\0'))
                    if branch=='wait':
                        write(actor+0x76,bytes(2));write(actor+0xAA,b'\0');write(actor+0x91,b'\1')
                    g.core.cpu.gprs[0]=actor;g.core.cpu.gprs[1]=0;overrides.append({'event':e,'r0_after':actor,'r1_after':0});jump(e,0x0802A72C if branch=='wait' else 0x0802BE5C)
                if not initial or returns:return
                if a==0x0802A756 and branch=='wait':
                    overrides.append({'event':e,'r0_after':1,'reason':'Controlled visible-room predicate for the separate wait announcement.'});g.core.cpu.gprs[0]=1
                if a in (0x0802BE70,0x0802BEAC):
                    value=int(branch==('protected' if a==0x0802BE70 else 'ability'));overrides.append({'event':e,'r0_after':value});g.core.cpu.gprs[0]=value
                if a in (0x0803B8A8,0x0803B47C) and r[14] in (0x0802BEF7,0x0802BEA3):
                    skips.append(e|{'reason':'Controlled Drink entry lacks monster special-animation setup; inventory selection and transfer run natively.'});jump(e,r[14]&~1)
                if a==0x08012220 and r[14]==0x0802C0DD:
                    skips.append(e|{'reason':'Teleport redraw closes the message before final-pixel verification. Native transfer and actor flags are already complete; destination/movement are separate.'});jump(e,r[14]&~1)
                if a==0x08000FB8 and r[1] in direct:
                    require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+(8 if branch=='wait' else 4),'Item theft source/output owner differs')
                    regs=list(r);args=regs[2:4]+[m.u32[r[13]]]
                    if field in ('maximum-width','maximum-bytes','coloured'):
                        raw=encode('W'*31 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Monster')
                        if field=='coloured':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
                        write(0x02008D08,raw.ljust(64,b'\0'));args[0]=0x02008D08;g.core.cpu.gprs[2]=args[0];regs[2]=args[0]
                        overrides.append({'event':e,'r2_after':args[0]})
                        if branch=='success':
                            item=encode('W'*27 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Item')
                            if field=='coloured':item=b'\x03\x06'+item[:-1]+b'\x05\0'
                            write(args[2],item.ljust(64,b'\0'))
                    if slot==0x710:require(args[1]==rows[0x718]['offset']+0x08000000,'Item theft kind pointer differs')
                    if slot==0x2B0:require(args[2]==r[13]+0x104,'Item theft64-byte item field differs')
                    payload=materialize(bytes.fromhex(row['encoded_hex']),args,m)
                    require(len(payload)<=row['maximum_bytes']<=256,'Item theft expanded output too large')
                    pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]))
                if pending and a==(pending['regs'][14]&~1):
                    old=pending['regs'];payload=pending['payload'];dest=old[0];guard=pending['guard']
                    require(bytes(m[dest:dest+len(payload)])==payload and bytes(m[dest+256:dest+272])==guard and r[4:12]==old[4:12] and r[13]==old[13],'Item theft formatter bytes/guard/ABI differ')
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'guard_abi_match':True});pending.clear()
                    queue_return=0x0802A823 if branch=='wait' else 0x0802C0BB if branch=='success' else 0x0802BE9F if branch=='protected' else 0x0802C137
                    checks.append(TheftCheck(g,payload[:-1],queue_return,256,guard))
                if checks and not (checks[0].complete and checks[0].returned):
                    if a==0x08001C14 and checks[0].pending_glyph:
                        bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(16*bank+m.u8[0x020000C2])]
                        colours.append(tuple(((colour>>s)&31)*255//31 for s in (0,5,10)))
                    checks[0].callback(e)
                if a==(0x0802A994 if branch=='wait' else 0x0802C144):
                    old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Item theft caller ABI/guard differs');returns.append(e)
            with Debugger(g,callback,max_events=150000) as debug:
                for a in (0x08015848,0x0802A756,0x0802A81A,0x0802A822,0x0802A994,0x0802BE70,0x0802BEAC,0x0803B8A8,0x0803B47C,0x08012220,0x08000FB8,0x0802BE96,0x0802BED2,0x0802C0B2,0x0802C10E,0x0802C12E,0x0801588C,0x080158CE,0x0802BE9E,0x0802C0BA,0x0802C136,0x0802C144,0x08001BC4,0x08001C14,0x08001C68,0x080020F4):debug.breakpoint(a)
                g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                actions=[]
                for i in range(7):
                    action=m.u16[0x0200CDD0+i*2]
                    if not action:break
                    actions.append(action)
                require(13 in actions,'Item theft test Drink unavailable')
                for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                g.press('A',wait=0)
                for _ in range(1500):
                    g.frames(1)
                    if returns:break
                require(len(initial)==len(returns)==len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and not pending,'Item theft native route incomplete: '+repr((name,len(initial),len(returns),len(checks),len(formats),[hex(v) for v in g.core.cpu.gprs])))
                c=checks[0];require(len(c.breaks)==row['english'].count('{fit}'),'Item theft native break count differs')
                if field=='native':require(not any(b['wraps'] for b in c.breaks),'Ordinary theft should fit one line')
                if branch=='success':
                    require(not m.u32[0x0200DF28]&0x80000000 and m.u32[actor+0x50]==stolen_base and bytes(m[stolen_base+4:stolen_base+120])==before_inventory[4:120],'Native item transfer/identity differs')
                else:require(bytes(m[0x0200DF28:0x0200E888])==before_inventory,'Refused item theft changed inventory')
                g.frames(3);pic=g.capture('message');pixels=0;visible=[]
                require(len(colours)==len(c.draws),'Item theft colours incomplete')
                for draw,colour in zip(c.draws,colours):
                    if draw['native_scroll']:
                        shift=draw['key'][-1]-draw['y']
                        for old in visible:old['final_y']-=shift
                    visible.append(draw|{'final_y':draw['y'],'colour':colour})
                for draw in visible:
                    # The native log shows two rows and scrolls a third. Every
                    # glyph was checked at the native bitmap preparation above;
                    # final framebuffer checks cover only rows still visible.
                    if draw['final_y']<0:continue
                    glyph,_=c.glyph_record(draw['code'])
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=m.u8[c.window]+draw['x']+x;py=m.u8[c.window+1]+draw['final_y']*16+y
                            require((pic.getpixel((px,py))==draw['colour'])==(bit=='#'),'Item theft final pixels differ');pixels+=1
            require(g.snapshot().battery==fixture.battery,'Item theft wrote battery')
            results.append({'case':name,'id':row['id'],'branch':branch,'field':field,'formats':formats,'queue':c.queued,'breaks':c.breaks,'overrides':overrides,'animation_skips':skips,'inputs':g.inputs,'return':returns,'visible_pixels_checked':pixels,'glyphs_checked':len(c.draws),'glyphs_scrolled_above_final_view':sum(d['final_y']<0 for d in visible),'caller_guard_abi_preserved':True,'native_transfer_checked':branch=='success','images':{'message.png':digest((g.output/'message.png').read_bytes())}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native item-theft handler and separate wait branch, invoked from Drink with recorded resistance/visibility arguments. Native inventory eligibility, selection,120-byte stolen-record transfer, removal and refusal paths execute. Sprite-animation setup and post-transfer teleport are explicitly skipped. Complete actor/player/item fields, up to two native conditional breaks, original256/64-byte outputs, native glyph bitmaps, final visible coloured pixels, caller guards and unchanged battery are checked. Ordinary messages fit one line. Maximum fields may use three lines in the native two-row scrolling log; glyphs above the final view are counted explicitly. Ordinary AI encounters, teleport destination and recovery of stolen items remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Item theft:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/item-theft-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
