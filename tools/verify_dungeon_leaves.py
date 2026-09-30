"""Controlled native dungeon effect selectors, outcomes, buffers and visible text."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.compact_font import encode
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_result_ui import native_format

# entry, formatter return, queue return(LR), final BX, output offset, source slot
OWNERS={
 'grabbed':(0x2291C,0x22C90,0x22CCD,0x22ED0,0,0x360),
 'kerplunk-damage':(0xCD38,0xD0F4,0xD0FD,0xD692,0x1C,0x480),
 'kerplunk-magic':(0xD694,0xD934,0xD93D,0xDB82,0x1C,0x480),
 'kerplunk-revival':(0x2FBA4,0x2FBDE,0x2FBE7,0x2FCC4,0x1C,0x480),
 'upgrade-one':(0x35074,0x350D8,0x350E1,0x35186,4,0x140),
 'upgrade-three':(0x35074,0x350D8,0x350E1,0x35186,4,0x4B0),
 'uncurse':(0x35074,0x3512E,0x35137,0x35186,4,0x9C4),
 'transform':(0x352CC,0x3535A,0x35363,0x35368,0,0x160),
 'staff-one':(0x35370,0x35412,0x3541B,0x35452,0,0x164),
 'staff-three':(0x35370,0x35412,0x3541B,0x35452,0,0x4B4),
 'pot-capacity':(0x35370,0x35412,0x3541B,0x35452,0,0x168),
 'heal-pot':(0x35B50,0x35B9E,0x35BA7,0x35BD2,0,0x104),
 'speed-item':(0x3431C,0x34346,0x3434F,0x34354,0,0x1F4),
 'speed-effect':(0x37760,0x37786,0x3778F,0x37794,0,0x1F4),
 'defence':(0x37B80,0x37BB8,0x37BC1,0x37BC6,0,0x400),
 'staff-nullify':(0x37D80,0x37DD4,0x37DDD,0x38432,4,0x640),
 'kaclang-projectile':(0x36EFC,0x36F2C,0x371FD,0x374F6,8,0x48C),
 'scorching-flame':(0x36EFC,0x372BA,0x372C3,0x374F6,0x108,0x358),
 'full-recovery':(0x356E8,0x35A2A,0x35A33,0x35B4E,0,0x104),
 'kaclang-damage':(0xCD38,0xCDBC,0xCDC5,0xD692,0x1C,0x48C),
 'kaclang-magic':(0xD694,0xD72C,0xD735,0xDB82,0x1C,0x48C),
 'kaclang-attack':(0xBCBC,0xBF66,0xBF6F,0xCC94,0x1C,0x48C),
}


def run(source=ROOT/'build/dungeon-leaves-prototype',only=None,*,owners=None,resource_key='dungeon_leaves',folder='dungeon-leaves-validation',hooks=None):
    out=source/folder;mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale dungeon leaf ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['table_offset']:r for r in build[resource_key]['entries']};results=[]
    for owner,(entry,formatted,queued,end,buffer_offset,slot) in (owners or OWNERS).items():
        if only and owner!=only:continue
        row=rows[slot]
        for field in (hooks.case_fields(owner) if hooks and hasattr(hooks,'case_fields') else ('native','maximum-width','maximum-bytes','coloured')):
            if hooks:hooks.field=field;hooks.row=row
            name=owner+'-'+field;print('Dungeon leaf:',name,flush=True)
            with Session(rom,out/name) as g:
                g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];checks=[];pending={};overrides=[];colours=[];skips=[];outcomes=[]
                hero=m.u32[0x02001624];target=0x0200DF28+120
                actor=next(m.u32[0x02001624+4*i] for i in range(1,56) if 0x02000000<=m.u32[0x02001624+4*i]<0x0203FF00 and m.u32[m.u32[0x02001624+4*i]+8]&0x80000000)
                def write(a,data):
                    require(0x02000000<=a and a+len(data)<=0x04000000,'Dungeon leaf override must remain in existing RAM')
                    overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[a+i]=v
                mapping=bytes(m[0x020013D0:0x020014D0]);item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=mapping.index(177);write(0x0200DF28,item)
                item_id=48 if owner.startswith('staff-') else 154 if owner=='pot-capacity' else 157 if owner=='heal-pot' else 1
                struct.pack_into('<I',item,0,0xC8000000|(0x800000 if owner.startswith('upgrade') or owner=='uncurse' else 0)|(0x4000000 if owner=='uncurse' else 0));item[4]=99 if owner=='uncurse' else 3 if owner in ('pot-capacity','heal-pot') or owner.startswith('staff-') else 0;item[8]=mapping.index(item_id);write(target,item)
                for ident in (177,item_id,204,205):
                    at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000))
                def jump(e,address):
                    overrides.append({'event':e,'pc_after':address});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',address)),'Dungeon leaf dispatch failed')
                def callback(e):
                    a,r=e['address'],e['registers']
                    if a==0x08015848 and not initial:
                        write(target,item)
                        write(hero+0x44,b'\1');write(hero+0x84,struct.pack('<HH',10,30));write(hero+0xA1,b'\0')
                        if owner=='heal-pot':write(hero+0x43,b'\1')
                        if owner=='kerplunk-revival':write(actor+0x91,b'\x5a');write(actor+0xA7,b'\1')
                        if owner=='grabbed':write(hero+0xC0,struct.pack('<I',actor))
                        if owner=='staff-nullify':write(actor+0x91,b'\x80')
                        if owner.startswith('kaclang-'):
                            write(actor+0x9B,b'\1');write(actor+8,struct.pack('<I',m.u32[actor+8]&~1))
                        if owner=='scorching-flame':write(hero+0x9B,b'\0')
                        if owner=='full-recovery':
                            write(hero+0x76,bytes(m[hero+0x78:hero+0x7A]));write(hero+0x54,bytes(m[hero+0x58:hero+0x5C]))
                        args=(target,100 if owner=='upgrade-three' else 0,hero,0) if owner.startswith('upgrade') or owner=='uncurse' else (target,actor,0,0) if owner=='staff-nullify' else (hero,actor,0,0) if owner=='kaclang-projectile' else (hero,0,0,0)
                        if owner=='scorching-flame':args=(actor,hero,0xD6,0)
                        if owner=='kerplunk-revival':args=(actor,0,0,0)
                        if owner=='kaclang-damage':args=(1,0,actor,0)
                        if owner=='kaclang-magic':args=(1,actor,hero,0)
                        if owner=='kaclang-attack':args=(hero,actor,1,0)
                        if hooks:args=hooks.setup(owner,g,hero,actor,write,overrides)
                        initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'arguments':args,'target_before':bytes(m[target:target+120]).hex(),'hero_before':bytes(m[hero:hero+0xC0]).hex()})
                        for i,v in enumerate(args):g.core.cpu.gprs[i]=v
                        overrides.append({'event':e,'r0_r3_after':args});jump(e,entry+0x08000000)
                    if not initial or returns:return
                    if hooks:hooks.event(owner,e,g,hero,actor,write,overrides)
                    if owner=='grabbed' and a==0x08022926:
                        overrides.append({'event':e,'register':7,'after':hero,'reason':'Existing native player record owns the captor pointer at+C0.'});g.core.cpu.gprs[7]=hero
                        skips.append({'event':e,'pc_after':0x08022C6C,'reason':'Controlled grab message block after original prologue; movement dispatch excluded.'});jump(e,0x08022C6C)
                    kerplunk_blocks={'kerplunk-damage':(0xCD46,0xD0DA,0xD680),'kerplunk-magic':(0xD6A0,0xD91A,0xDB74),'kerplunk-revival':(None,None,0x2FCB6)}
                    if owner in kerplunk_blocks:
                        prologue,start,epilogue=kerplunk_blocks[owner]
                        if prologue is not None and a==prologue+0x08000000:
                            overrides.append({'event':e,'register':5,'after':actor,'reason':'Use existing actor for controlled native Kerplunk announcement block; natural damage/revival conditions excluded.'});g.core.cpu.gprs[5]=actor
                            skips.append({'event':e,'pc_after':start+0x08000000,'reason':'Original frame preserved; controlled message block entry.'});jump(e,start+0x08000000)

                    if (a==0x080356F8 and owner=='full-recovery') or (a==0x0800BF1A and owner=='kaclang-attack'):
                        value=6 if owner=='full-recovery' else 1
                        overrides.append({'event':e,'register':0,'after':value,'reason':'Select valid native recovery RNG branch6.' if owner=='full-recovery' else 'Control native visibility result for Kaclang announcement.'});g.core.cpu.gprs[0]=value
                    if a==0x080353AA and owner in ('staff-one','staff-three'):
                        chance=struct.unpack_from('<I',rom,0x353D4)[0]
                        require(struct.unpack_from('<H',rom,chance-0x08000000)[0]==6,'Native staff bonus chance differs')
                        value=0 if owner=='staff-three' else 98
                        overrides.append({'event':e,'register':0,'after':value,'reason':'Choose a valid original RNG result on either side of the unchanged6-percent threshold.'});g.core.cpu.gprs[0]=value
                    if formatted and a==0x08000FB8 and r[14]==formatted+0x08000001:
                        require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+buffer_offset,'Dungeon leaf native source/output differs: '+repr((owner,hex(r[1]),hex(r[0]),hex(r[13]))))
                        regs=list(r);args=[]
                        for i,role in enumerate(row['fields'],2):
                            at=regs[i] if i<4 else m.u32[r[13]+4*(i-4)]
                            if role=='amount':
                                if hooks and hasattr(hooks,'integer_value'):
                                    value=hooks.integer_value(owner,field,at)
                                    if value!=at:
                                        overrides.append({'event':e,'argument_index':i-2,'integer_before':at,'integer_after':value,'reason':'Formatter-only decimal boundary; original gameplay state is not changed.'})
                                        at=value
                                        if i<4:regs[i]=at;g.core.cpu.gprs[i]=at
                                        else:write(r[13]+4*(i-4),struct.pack('<I',at))
                                args.append(at);continue
                            capacity=hooks.field_capacity(role) if hooks and hasattr(hooks,'field_capacity') else 64
                            if field in ('maximum-width','maximum-bytes','coloured'):
                                raw=encode(('W'*(31 if 'actor' in role else 27)) if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Torneko' if role=='actor' else 'Oaken club')
                                if field=='coloured':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
                                if hooks and hasattr(hooks,'field_data'):raw=hooks.field_data(role,field,raw)
                                if hooks and hasattr(hooks,'field_address'):at=hooks.field_address(owner,role,i,r,g)
                                else:
                                    at=0x02008D08 if role=='actor' else at
                                    if role!='actor':require(r[13]+buffer_offset+256<=at<r[13]+buffer_offset+384,'Item field scratch ownership differs')
                                require(len(raw)<=capacity,'Dungeon leaf field probe exceeds owned capacity')
                                write(at,raw.ljust(capacity,b'\0'))
                                if i<4:regs[i]=at;g.core.cpu.gprs[i]=at;overrides.append({'event':e,'register':i,'after':at})
                                else:write(r[13]+4*(i-4),struct.pack('<I',at))
                            args.append(at)
                        payload=native_format(bytes.fromhex(row['encoded_hex']),args,m);require(len(payload)<=row['maximum_bytes']<=256,'Dungeon leaf output overflow')
                        fields=[(v,bytes(m[v:v+(hooks.field_capacity(role) if hooks and hasattr(hooks,'field_capacity') else 64)]).hex()) for v,role in zip(args,row['fields']) if role!='amount']
                        pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),fields=fields)
                        checker=getattr(hooks,'queue_checker',ActionCheck)
                        if row['english'].count('{fit}')>1:
                            from tools.verify_item_theft import TheftCheck
                            checker=TheftCheck
                        checks.append(checker(g,payload[:-1],queued+0x08000000,256,pending['guard']))
                    if formatted and a==formatted+0x08000000 and pending:
                        old=pending['regs'];p=old[0];payload=pending['payload']
                        require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13] and all(bytes(m[v:v+len(bytes.fromhex(raw))]).hex()==raw for v,raw in pending['fields']),'Dungeon leaf output/field/guard/ABI differs')
                        if owner.startswith('upgrade'):require(m.u8[target+4]==(3 if owner=='upgrade-three' else 1),'Native upgrade amount differs: '+repr((bytes.fromhex(initial[0]['target_before'])[:12].hex(),bytes(m[target:target+12]).hex())))
                        if owner=='uncurse':require(m.u8[target+4]==99 and not m.u32[target]&0x4000000,'Native curse removal changed bonus or retained curse')
                        if owner=='transform':require(mapping[m.u8[target+8]]==204 and m.u8[target+4]==0,'Native transformation result differs')
                        if owner in ('staff-one','staff-three','pot-capacity'):require(m.u8[target+4]==(6 if owner=='staff-three' else 4),'Native use/capacity increment differs')
                        if owner in ('heal-pot','full-recovery'):require(m.u16[hero+0x84]==30,'Native healing differs')
                        if owner=='defence':require(m.u8[hero+0xA1]==1,'Native defence penalty differs')
                        outcomes.append({'target_after':bytes(m[target:target+120]).hex(),'hero_after':bytes(m[hero:hero+0xC0]).hex()})
                        formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':256,'guard_abi_match':True});pending.clear()
                    if not formatted and a==0x0801588C and r[14]==queued+0x08000000:
                        require(not row['fields'] and not checks,'Unexpected static leaf queue/fields')
                        payload=bytes.fromhex(row['encoded_hex']);capacity=0 if buffer_offset is None else 256
                        expected=row['offset']+0x08000000 if buffer_offset is None else r[13]+buffer_offset
                        require(r[0]==expected and bytes(m[r[0]:r[0]+len(payload)])==payload,'Static leaf queue source/bytes differ')
                        guard=bytes(m[r[0]+capacity:r[0]+capacity+16]) if capacity else b''
                        checker=getattr(hooks,'queue_checker',ActionCheck)
                        checks.append(checker(g,payload[:-1],queued+0x08000000,capacity,guard))
                        formats.append({'id':row['id'],'kind':'ROM-stream' if not capacity else 'native-static-copy','hex':payload.hex(),'bytes':len(payload),'capacity':capacity or 'immutable-ROM','guard_abi_match':True})
                    if checks and not (checks[0].complete and checks[0].returned):
                        duplicate=False
                        if a==0x08001C14 and checks[0].pending_glyph:
                            bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                            glyph=checks[0].pending_glyph;key=(r[0],r[4],r[5],r[13],r[14],rgb)
                            duplicate='probe_preparation' in glyph
                            if duplicate:require(glyph['probe_preparation']==key,'Repeated glyph preparation differs')
                            else:glyph['probe_preparation']=key;colours.append(rgb)
                        if not duplicate:checks[0].callback(e)
                    if owner=='grabbed' and a in (0x08022C90,0x08022CCC):
                        target_pc=0x08022CC4 if a==0x08022C90 else 0x08022EC4
                        skips.append({'event':e,'pc_after':target_pc,'reason':'Skip grab animation/gameplay; native format, queue and original epilogue still execute.'});jump(e,target_pc)
                    if owner in kerplunk_blocks and a==(queued&~1)+0x08000000:
                        require(checks and checks[0].complete and checks[0].returned,'Kerplunk text incomplete before effect exclusion')
                        epilogue=kerplunk_blocks[owner][2]
                        skips.append({'event':e,'pc_after':epilogue+0x08000000,'reason':'Original epilogue preserves caller; revival/death/map effects excluded from render preflight.'});jump(e,epilogue+0x08000000)
                    if owner=='scorching-flame' and a==0x080372C2:
                        require(checks[0].complete and checks[0].returned,'Flame announcement not finished before controlled damage skip')
                        skips.append({'event':e,'pc_after':0x080374E8,'reason':'Keep announcement visible; subsequent damage and its messages are outside this rendering check.'});jump(e,0x080374E8)
                    if a==end+0x08000000:
                        bx=hooks.return_register(owner) if hooks else 1 if owner in ('kaclang-attack','grabbed') else 0
                        old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[bx]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Dungeon leaf caller ABI/guard differs')
                        if hooks:hooks.returned(owner,g,hero,actor)
                        returns.append(e)
                with Debugger(g,callback,max_events=150000) as debug:
                    for a in (0x08015848,0x08022926,0x0800CD46,0x0800D6A0,0x080353AA,0x080356F8,0x0800BF1A,0x08000FB8,formatted+0x08000000,0x0801588C,0x080158CE,(queued&~1)+0x08000000,end+0x08000000,0x08001BC4,0x08001C14,0x08001C68,0x080020F4):debug.breakpoint(a)
                    if hooks:
                        for a in hooks.breakpoints:debug.breakpoint(a)
                    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                    actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+i*2]
                        if not n:break
                        actions.append(n)
                    require(13 in actions,'Dungeon leaf Drink trigger unavailable')
                    for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                    g.capture('menu');g.press('A',wait=0)
                    for _ in range(1200):
                        g.frames(1)
                        if returns:break
                    require(len(initial)==len(returns)==len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and not pending,'Dungeon leaf route incomplete: '+repr((name,len(initial),len(returns),len(checks),len(formats),[hex(x) for x in g.core.cpu.gprs])))
                    if hooks and hasattr(hooks,'verify_draws'):hooks.verify_draws(owner,field,checks[0])
                    g.frames(3);pic=g.capture('message');c=checks[0];visible=[];pixels=0;require(len(c.draws)==len(colours),'Dungeon leaf colours incomplete')
                    for draw,colour in zip(c.draws,colours):
                        if draw['native_scroll']:
                            shift=draw['key'][-1]-draw['y'];require(shift>0,'Unexpected dungeon leaf scroll')
                            for old in visible:old['final_y']-=shift
                        visible.append(draw|{'final_y':draw['y'],'colour':colour})
                    for d in visible:
                        if d['final_y']<0:
                            require(hooks and getattr(hooks,'allow_scrolled',False),'Dungeon leaf scrolled out of view');continue
                        glyph,_=c.glyph_record(d['code'])
                        for y,line in enumerate(glyph['rows']):
                            for x,bit in enumerate(line):
                                px=m.u8[c.window]+d['x']+x;py=m.u8[c.window+1]+d['final_y']*16+y
                                require((pic.getpixel((px,py))==d['colour'])==(bit=='#'),'Dungeon leaf final pixels differ: '+repr((name,px,py,hex(d['code']))));pixels+=1
                require(g.snapshot().battery==fixture.battery,'Dungeon leaf wrote battery')
                results.append({'case':name,'id':row['id'],'owner':owner,'field':field,'overrides':overrides,'inputs':g.inputs,'formats':formats,'queue':checks[0].queued,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'outcomes':outcomes,'initial':initial,'visual_effect_skips':skips,'glyphs_scrolled_above_final_view':sum(d['final_y']<0 for d in visible),'native_breaks':getattr(c,'breaks',[]),'images':{p:digest((g.output/p).read_bytes()) for p in ('menu.png','message.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':hooks.scope if hooks else 'Controlled native effect dispatch from Drink, with existing item/actor/selection fields recorded. Each report records exact original formatter selection,256-byte output, field bounds, native conditional breaks, final coloured pixels and full caller/battery preservation. Natural item acquisition and ordinary combat encounters remain separate. This report does not cover omitted source consumers.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Dungeon leaves:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/dungeon-leaves-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
