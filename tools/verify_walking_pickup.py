"""Actual directional walking into a natively dropped item, including final pixels."""
import json
import struct
import mgba.log
from tools.emulator import Session, Debugger
from tools.name_entry_playtest import position, MAP
from tools.numeric_font import ALIASES
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_pickup_prototype import QUEUES
from tools.verify_service_ui import materialize


def run():
    out=ROOT/'build/english/walking-pickup-validation';mgba.log.silence()
    rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes();build=json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Walking pickup ROM differs')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['offset']+0x08000000:r for r in build['pickup']['entries']};results=[]
    for kind in ('native-item','gold','arrows','full','standing-option'):
        print('Walking pickup:',kind,flush=True)
        with Session(rom,out/kind) as g:
            g.restore(fixture);m=g.core.memory;overrides=[];drops=[];walks=[];central=[];checks=[];formats=[];pending={};colours=[]
            returning=False;steps=[];slot=0x0200DF28;actor=m.u32[0x02001624]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def count():return sum(bool(m.u32[slot+i*120]&0x80000000) for i in range(20))
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08024F12:drops.append(m.u32[r[0]+16])
                if not returning:return
                if a==0x080249DC:
                    walks.append(e)
                    # Movement refreshes this transient field from controls.
                    # Set it at the real walk callback, without redirecting PC.
                    if kind=='standing-option':write(0x0200567D,b'\1')
                if a==0x08024AD8:central.append(e)
                if a==0x08000FB8 and r[1] in rows:
                    row=rows[r[1]];ret=r[14]&~1;capacity=256 if kind=='standing-option' else 192
                    expected_slot=0x37C if kind=='standing-option' else 0xA0 if kind=='full' else 0x9C
                    require(row['table_offset']==expected_slot and ret-0x08000000 in QUEUES and not pending and not formats,'Unowned walking pickup format')
                    require(r[0]==r[13] and r[2]==r[13]+capacity,'Walking pickup buffer ownership differs')
                    payload=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                    require(len(payload)<=row['maximum_bytes']<=capacity,'Walking pickup exceeds output')
                    pending.update(regs=r,payload=payload,row=row,capacity=capacity,guard=bytes(m[r[0]+capacity:r[0]+capacity+64]),ret=ret)
                    checks.append(ActionCheck(g,payload[:-1],0x08000000+QUEUES[ret-0x08000000],capacity,pending['guard'][:16]))
                if pending and a==pending['ret']:
                    old=pending['regs'];p=old[0];payload=pending['payload'];capacity=pending['capacity']
                    require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+capacity:p+capacity+64])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Walking pickup bytes/field guard/ABI differ')
                    formats.append({'id':pending['row']['id'],'hex':payload.hex(),'capacity':capacity,'bytes':len(payload),'guard_abi_match':True});pending.clear()
                if checks and not (checks[0].complete and checks[0].returned):
                    if a==0x08001C14 and checks[0].pending_glyph:
                        bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])]
                        colours.append(tuple(((colour>>s)&31)*255//31 for s in (0,5,10)))
                    checks[0].callback(e)
            with Debugger(g,callback,max_events=100000) as debug:
                addresses={0x08024F12,0x080249DC,0x08024AD8,0x08000FB8,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68}
                addresses|={0x08000000+n for n in QUEUES}|{(0x08000000+n)&~1 for n in QUEUES.values()}
                for a in addresses:debug.breakpoint(a)
                g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                actions=[]
                for i in range(7):
                    n=m.u16[0x0200CDD0+i*2]
                    if not n:break
                    actions.append(n)
                require(7 in actions,'Native Drop unavailable')
                for _ in range(actions.index(7)):g.press('DOWN',wait=20)
                g.press('A',wait=180);require(len(drops)==1,'Native Drop did not establish one floor item')
                g.capture('dropped');floor=drops[0];data=bytearray(m[floor:floor+120]);mapping=bytes(m[0x020013D0:0x020014D0])
                if kind=='gold':data[8]=mapping.index(212);struct.pack_into('<h',data,4,123);write(floor,data)
                if kind=='arrows':
                    data[8]=mapping.index(78);data[4]=5;write(floor,data)
                    carried=bytearray(data);carried[4]=10;write(slot,carried)
                if kind=='full':
                    for i in range(20):write(slot+i*120,data)
                g.press('B',hold=8,wait=30);g.press('B',hold=8,wait=30);start=position(g)
                before_count=count();before_gold=m.u32[actor+0x60];before_inventory=bytes(m[slot:slot+2400])
                for key,back,dx,dy in (('LEFT','RIGHT',-1,0),('RIGHT','LEFT',1,0),('UP','DOWN',0,-1),('DOWN','UP',0,1)):
                    flags=m.u32[MAP+((start[0]+dx)*32+start[1]+dy)*28+20]
                    if not flags&0x4000:continue
                    g.press(key,wait=90);steps.append({'key':key,'position':position(g)})
                    if position(g)!=start:
                        g.capture('step-off');returning=True;g.press(back,wait=0)
                        for _ in range(300):
                            g.frames(1)
                            if checks and checks[0].complete and checks[0].returned:break
                        steps.append({'key':back,'position':position(g)});break
                require(position(g)==start and len(walks)==1 and walks[0]['registers'][14]==0x080324C7,'Directional movement did not reach native automatic pickup')
                require(len(central)==(kind!='standing-option') and (not central or central[0]['registers'][14]==0x08024AD1),'Walking pickup dispatch differs')
                require(len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and not pending,'Walking pickup incomplete')
                g.frames(3);picture=g.capture('picked-up');c=checks[0];visible=[];pixels=0
                require(len(c.draws)==len(colours),'Walking pickup glyph colours incomplete')
                for draw,colour in zip(c.draws,colours):
                    if draw['native_scroll']:
                        shift=draw['key'][-1]-draw['y'];require(shift>0,'Unexpected pickup scroll direction')
                        for previous_draw in visible:previous_draw['final_y']-=shift
                    visible.append(draw|{'final_y':draw['y'],'colour':colour})
                for draw in visible:
                    require(draw['final_y']>=0 and (0xF020<=draw['code']<=0xF07E or draw['code'] in ALIASES or draw['code']==0x20),'Pickup retained Japanese glyphs or scrolled out of view')
                    glyph,_=c.glyph_record(draw['code'])
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=m.u8[0x02000000]+draw['x']+x;py=m.u8[0x02000001]+draw['final_y']*16+y
                            require((picture.getpixel((px,py))==draw['colour'])==(bit=='#'),'Walking pickup final pixels differ');pixels+=1
                require(count()==before_count+(kind=='native-item'),'Walking inventory count differs')
                require(m.u32[actor+0x60]==before_gold+(123 if kind=='gold' else 0),'Walking gold differs')
                if kind=='arrows':require(m.u8[slot+4]==15,'Walking arrow merge differs')
                if kind in ('full','standing-option'):require(bytes(m[slot:slot+2400])==before_inventory,'Refused walking pickup changed inventory')
            require(g.snapshot().battery==fixture.battery,'Walking pickup changed battery')
            results.append({'case':kind,'overrides':overrides,'inputs':g.inputs,'steps':steps,'formats':formats,'queue':checks[0].queued,'walk_entries':walks,'central_entries':central,'visible_pixels_checked':pixels,'inventory_count_before':before_count,'inventory_count_after':count(),'gold_before':before_gold,'gold_after':m.u32[actor+0x60],'images':{p:digest((g.output/p).read_bytes()) for p in ('dropped.png','step-off.png','picked-up.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'fixture_state_sha256':digest(fixture.state),'cases':results,'scope':'Ordinary Drop and directional step-away/return reach automatic walking pickup without PC/register redirects. Native-item case has no state overrides. Explicit floor/inventory/option substitutions cover gold, merged arrows, full inventory and standing option. Actual final coloured glyph pixels, English glyphs, message/item guards and inventory/gold outcomes pass; does not establish every dungeon/item or remaining combat text.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Walking pickup:',len(results),'passed',flush=True)
    return report


if __name__=='__main__':run()
