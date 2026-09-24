"""Result UI location/stat fields at native bounds with final-screen glyph checks."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require
from tools.verify_service_ui import cstring


def native_format(template, args, memory):
    """Independently model the observed native decimal/string conversion."""
    result=bytearray();cursor=0;argument=0
    while cursor<len(template):
        if template[cursor]!=37:
            result.append(template[cursor]);cursor+=1;continue
        kind=template[cursor+1];value=args[argument];argument+=1;cursor+=2
        if kind==115:result.extend(cstring(memory,value))
        elif kind==100:
            # CPU08000FB8 tests signed value>9 before its digit loop. A
            # negative input bypasses the loop and emits its low byte+'0'.
            # Negative fields are invalid-game-state probes, not signed support.
            result.extend(bytes([(value+48)&255]) if value>=0x80000000 else str(value).encode())
        else:raise ValueError('Unexpected result format conversion')
    return bytes(result)


def run(source=ROOT/'build/results-ui-prototype', only=None, history=False):
    out=source/(('history-' if history else '')+('ui-probes' if only else 'ui-validation'));mgba.log.silence()
    entry,ready_pc,end_pc=(0x08056E04,0x08057164,0x0805734A) if history else (0x0801CA84,0x0801CEEE,0x0801CF5A)
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale result UI ROM')
    from tools import verify_player_status_prototype as status
    prior=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    rows={r['offset']+0x08000000:r for r in build['results']['ui_entries']}
    if history and 'history' in build: rows.update({r['offset']+0x08000000:r for r in build['history']['entries']})
    configs=[(f'dungeon-{i}-reason-{reason}',i,reason,None,None) for i in range(13) for reason in (21,32,33)]
    configs += [('bounds-'+name,7,21,values,None) for name,values in (
        ('zero',(0,0,0,0)),('maximum',(32767,2147483647,32767,50)),('signed-minimum',(-32768,-2147483648,-32768,1)))]
    if not history and any(r['table_offset']==0x97C for r in rows.values()):
        from tools.extract_items import extract
        named={int(r['id'].split('.')[-1]) for r in build['items']['entries'] if r['id'].startswith('item.name.')}
        equipment=[r for r in extract()['items'] if r['category'] in (1,3,6) and r['id'] in named]
        configs += [(f'equipment-{r["id"]}-{state}',0,21,None,(r['id'],r['category'],state))
                    for r in equipment for state in ('identified','unidentified','cursed','maximum-fields','priced','priced-maximum','priced-cursed-maximum','ability-present')]
    if any(r.get('table_offset')==0x6D8 for r in rows.values()):
        configs += [(f'exit-{reason}-kind-{kind}',7,reason,None,{'exit_kind':kind}) for reason,kind in ((32,0),(32,1),(32,2),(34,0),(35,0),(36,0))]
    if history and 'history' in build:
        configs += [('history-'+profile,7,21,None,{'profile':profile}) for profile in ('minimum','maximum','time-59','rank-50','empty','navigate')]
    if only: configs=[c for c in configs if c[0] in only]
    results=[]
    for case,dungeon,reason,bounds,item_config in configs:
        profile=item_config.get('profile') if isinstance(item_config,dict) else None
        exit_kind=item_config.get('exit_kind',1) if isinstance(item_config,dict) else 1
        if isinstance(item_config,dict):item_config=None
        print('History UI:' if history else 'Result UI:',case,flush=True)
        with Session(rom,out/case) as g:
            g.restore(fixture);m=g.core.memory;check=TextChecks(g,{})
            from tools.verify_items import ItemChecks
            item_check=ItemChecks(g,build)
            initial=[];returns=[];ready=[];formats=[];pending={};draws=[];overrides=[];index_override=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    write(0x020056B3,b'\0');write(0x020037CC,struct.pack('<hh',reason,exit_kind));write(0x02003B6C,struct.pack('<I',dungeon))
                    if history:
                        write(0x02011BDC,struct.pack('<I',0))
                        write(0x02004EFC,struct.pack('<IIIIhhhBBBBBB',10120,8,120,3600,3,15,6,dungeon,reason,8,0,exit_kind,0))
                        if profile:
                            record=bytearray(struct.pack('<IIIIhhhBBBBBB',10120,8,120,3600,15,2,6,dungeon,reason,8,5,exit_kind,0))
                            if profile=='minimum':record=bytearray(struct.pack('<IIIIhhhBBBBBB',1,0,0,0,0,0,1,dungeon,reason,0,0,exit_kind,0))
                            if profile=='maximum':record=bytearray(struct.pack('<IIIIhhhBBBBBB',2147483647,2147483647,2147483647,2147483647,32767,32767,32767,dungeon,reason,255,255,exit_kind,2))
                            if profile=='time-59':struct.pack_into('<I',record,12,215999)
                            if profile=='empty':record=bytearray(28)
                            write(0x02004EFC,bytes(record)*(50 if profile in ('rank-50','navigate') else 1))
                        g.core.cpu.gprs[0]=0x02002C44
                    if item_config:
                        ident,category,state=item_config
                        record=bytearray(120);flags=0xC8800000
                        if state=='unidentified':flags=0x80800000
                        if 'cursed' in state:flags|=0x04000000
                        if 'priced' in state:flags|=0x100000
                        if state=='ability-present':flags|=0x20
                        struct.pack_into('<I',record,0,flags);record[4]=99 if 'maximum' in state else 1;record[5]=1
                        record[8]=bytes(m[0x020013D0:0x020014D0]).index(ident)
                        write(0x0200DF28,bytes(record)+bytes(2280))
                        address=0x02003BAC+ident*20
                        known=m.u32[address]&~0x40000000 if state=='unidentified' else m.u32[address]|0x40000000
                        write(address,struct.pack('<I',known))
                    overrides.append({'event':e,'pc_after':entry,'r0_after':0x02002C44 if history else r[0]})
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',entry)),'Result UI redirect failed')
                if not initial or returns:return
                if history and profile=='rank-50' and a==0x08056EF0 and not index_override:
                    write(0x02011BDC,struct.pack('<I',49));index_override.append(e)
                if a==0x08001750:
                    draws[:]=[d for d in draws if d['key'][0]!=r[0]]
                if bounds and a==0x0801CD16:
                    number,score,strength,rank=bounds
                    overrides.append({'event':e,'r0_after':rank});g.core.cpu.gprs[0]=rank
                    write(r[13]+0x190,struct.pack('<I',score&0xFFFFFFFF))
                if a in (0x08000FB8,0x0805CF54) and r[1] in rows:
                    row=rows[r[1]];regs=list(r);slot=row.get('table_offset')
                    if bounds and a==0x08000FB8:
                        number,score,strength,rank=bounds
                        changes=({2:number} if slot==0x940 else {3:number} if slot in (0x650,0x6E0) else
                                 {2:score,3:strength} if slot==0x93C else {})
                        for index,value in changes.items():
                            overrides.append({'event':e,'register':index,'after':value&0xFFFFFFFF})
                            regs[index]=value&0xFFFFFFFF;g.core.cpu.gprs[index]=value
                    args=regs[2:4]+[m.u32[regs[13]+i*4] for i in range(4)]
                    payload=native_format(bytes.fromhex(row['encoded_hex']),args,m) if a==0x08000FB8 else bytes.fromhex(row['encoded_hex'])
                    row=row|{'capacity':min(row['capacity'],128) if history else row['capacity']}
                    require(len(payload)<=row['maximum_bytes']<=row['capacity'],'Result UI format capacity exceeded')
                    ret=regs[14]&~1;require(ret not in pending,'Nested same UI format')
                    pending[ret]=(regs,row,payload,bytes(m[regs[0]+len(payload):regs[0]+row['capacity']+16]))
                    debug.breakpoint(ret)
                if a in pending:
                    before,row,payload,guard=pending.pop(a);dest=before[0]
                    (g.output/'last-format.json').write_text(json.dumps({'id':row['id'],'expected':payload.hex(),'actual':bytes(m[dest:dest+len(payload)+8]).hex(),'expected_guard':guard.hex(),'actual_guard':bytes(m[dest+len(payload):dest+row['capacity']+16]).hex(),'before':before,'after':r},indent=2)+'\n')
                    require(r[4:12]==before[4:12] and r[13]==before[13] and bytes(m[dest:dest+len(payload)])==payload and
                            bytes(m[dest+len(payload):dest+row['capacity']+16])==guard,'Result UI bytes/tail/guard/ABI differ')
                    check.resources[dest]={'id':row['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[row['id']]]}}
                    formats.append({'id':row['id'],'table_offset':row.get('table_offset'),'literal':row.get('literal'),'payload':payload.hex(),'arguments':before[2:4],
                                    'capacity':row['capacity'],'guard_tail_abi_match':True})
                if a==0x080021B4 and r[1] in rows and not rows[r[1]]['printf_kinds']:
                    row=rows[r[1]]
                    check.resources[r[1]]={'id':row['id'],'encoded_hex':row['encoded_hex'],'layout':{'pages':[[row['id']]]}}
                if a==0x080021B4 and not check.active and r[1] in check.resources:
                    payload=bytes.fromhex(check.resources[r[1]]['encoded_hex'])
                    if bytes(m[r[1]:r[1]+len(payload)])!=payload:check.resources.pop(r[1])
                if a==0x08001BC4 and check.active:
                    w=r[0];key=(r[0],r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:
                        draws.append({'key':key,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],
                                      'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'id':check.active['id'],'palette_bank':m.u16[m.u32[w+12]]>>12})
                if a in set(ItemChecks.ADDRESSES)-set(TextChecks.ADDRESSES):item_check.callback(e)
                check.callback(e)
                if a==ready_pc or history and profile=='empty' and a==0x08056E36:ready.append(e)
                if a==end_pc:
                    before=initial[0]['registers']
                    require(r[4:12]==before[4:12] and r[13]==before[13] and r[0]==before[14] and
                            bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Result UI caller ABI/guard changed')
                    returns.append(e)
            with Debugger(g,callback,max_events=40000) as debug:
                for a in set(ItemChecks.ADDRESSES+(0x08008F4C,0x08000FB8,0x0801CD16,ready_pc,end_pc,0x08056EF0,0x08056E36,0x08001750)):debug.breakpoint(a)
                g.press('A',hold=1,wait=0)
                for _ in range(600):
                    g.frames(1)
                    if ready:break
                require(ready and not pending and not check.active and draws,'Result UI panel incomplete')
                if profile=='navigate':
                    for key,index in [('DOWN',1),('UP',0)]:
                        before_reads,before_ready=len(check.reads),len(ready)
                        g.press(key,hold=1,wait=0)
                        for _ in range(120):
                            g.frames(1)
                            if len(check.reads)>before_reads and len(ready)>before_ready and not check.active and not pending:break
                        require(m.u32[0x02011BDC]==index,'History navigation failed')
                        require(len(check.reads)>before_reads and not check.active and not pending,'History redraw incomplete')
                        g.frames(3)
                        g.capture('navigate-'+key.lower())
                g.frames(3);picture=g.capture('panel');pixels=0
                (g.output/'palette.json').write_text(json.dumps({'palette':[m.u16[0x05000000+2*i] for i in range(256)],'window':bytes(m[0x02000000:0x02000018]).hex(),'map':[m.u16[0x0600B8C0+2*i] for i in range(32)]},indent=2)+'\n')
                for draw in draws:
                    glyph,_=check.glyph_record(draw['code']);color=m.u16[0x05000000+2*(16*draw['palette_bank']+draw['foreground'])]
                    foreground=tuple(((color>>shift)&31)*255//31 for shift in (0,5,10))
                    for y,bits in enumerate(glyph['rows']):
                        for x,bit in enumerate(bits):
                            px=draw['origin'][0]+draw['x']+x;py=draw['origin'][1]+draw['y']*16+y
                            require(0<=px<240 and 0<=py<160 and (picture.getpixel((px,py))==foreground)==(bit=='#'),
                                    'Result UI final glyph differs: '+repr((case,draw['id'],px,py,bit,foreground,picture.getpixel((px,py)))))
                            pixels+=1
                if item_config:
                    ident,category,state=item_config
                    require(item_check.formats and all(f['bytes']<=64 and f['guard_preserved'] for f in item_check.formats), 'Result item field not verified')
                    label={6:0x97C,3:0x980,1:0x984}[category]
                    require(any(f['table_offset']==label for f in formats),'Expected equipment row missing')
                    # Each priced row uses an absolute native column. English
                    # label/name ink must stop before its inverse price cells.
                    selected=[d for d in draws if d['id']==f'results.ui-{label:03x}']
                    price=[d['x'] for d in selected if d['foreground']==12]
                    if price:
                        ink=[]
                        for d in selected:
                            if d['foreground']==12:continue
                            glyph,_=check.glyph_record(d['code'])
                            ink.extend(d['x']+x+1 for line in glyph['rows'] for x,bit in enumerate(line) if bit=='#')
                        require(max(ink,default=0)<=min(price),'Result equipment overlaps price column')
                g.press('B',hold=1,wait=0)
                for _ in range(120):
                    if returns:break
                    g.frames(1)
                require(len(returns)==1 and g.snapshot().battery==fixture.battery,'Result UI close/save failed')
            results.append({'case':case,'dungeon':dungeon,'reason':reason,'bounds':bounds,'history':history,'history_profile':profile,'exit_kind':exit_kind,'item_config':item_config,'item_formats':item_check.formats,'formats':formats,
                            'reads':check.reads,'draws':draws,'overrides':overrides,'inputs':g.inputs,
                            'return':returns[0],'visible_pixels_checked':pixels,'images':{path.name:digest(path.read_bytes()) for path in g.output.glob('*.png')}})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Controlled results entry,13 dungeon IDs and21/32/33 result reasons, plus nonnegative numeric limits, rank0/1/50 and an explicitly invalid negative-input probe preserving the original native low-byte decimal behavior. Original windows, native formatting/tails/guards/ABI, colours and final-screen pixels pass. All75 reviewed equipment identities pass eight states when the equipment cohort is present. All eight exit sources pass their native branches. History adds HP/level/strength, EXP/gold, trip/time, empty/rank50 and next/previous selection when its owned literals are present. Ordinary progression, record persistence, custom names and inscriptions remain separate.'},indent=2)+'\n')
    print('Result UI:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/results-ui-prototype')
    p.add_argument('--case',action='append');p.add_argument('--history',action='store_true');a=p.parse_args();run(a.source,a.case,a.history)
