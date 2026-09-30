"""Inscribed scroll rows, complete effect names, prices, guards and restoration."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require
from tools.compact_font import encode
from tools.dialogue_checks import rendered_codes
from tools.verify_items import ItemChecks
from tools.numeric_checks import NumericChecks
from tools.audit_menu_layouts import Observer,parent_image


def run(source,only=None):
    out=source/'scroll-item-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale inscribed scroll ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    names={r['item_id']:r for r in build['scroll_item']['entries'] if r['id'].startswith('scroll-item.effect.')}
    configs=[(i,state) for i in names for state in ('normal','priced')]+[(149,state) for state in ('priced-maximum','priced-equipped','priced-cursed')]
    if only is not None:configs=[r for r in configs if r[0]==only]
    results=[]
    for ident,state in configs:
        name=f'{ident}-{state}';print('Scroll item:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8400000|(0x100000 if state.startswith('priced') else 0)|(0x800000 if state in ('priced-equipped','priced-cursed') else 0)|(0x4000000 if state=='priced-cursed' else 0));item[4]=0;item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(ident);write(0x0200DF28,item)
            at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            expected='Blank: '+names[ident]['english'];checks=ItemChecks(g,build);checks.names[ident]=checks.names[ident]|{'english':expected}
            observer=Observer(g);numbers=NumericChecks(g);lookup=[];formats=[];pending={}
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x0800F0DC and state in ('priced-maximum','priced-equipped','priced-cursed'):
                    overrides.append({'event':e,'register':0,'after':999999,'reason':'Formatter-only largest six-digit price; item definition/cost remains unchanged.'});g.core.cpu.gprs[0]=999999
                if a==0x0800F302:
                    require(r[0]==build['scroll_item']['definition_copy_offset']+0x08000000+24*ident,'Inscribed scroll name index differs');lookup.append(e)
                if a==0x08000FB8 and r[14]==0x0800F5B3:
                    require(r[1]==build['scroll_item']['entries'][-1]['offset']+0x08000000 and r[2]==build['scroll_item']['entries'][-2]['offset']+0x08000000 and r[3]==r[13]+4 and bytes(m[r[3]:r[3]+len(bytes.fromhex(names[ident]['encoded_hex']))]).hex()==names[ident]['encoded_hex'],'Inscribed scroll format/kind/name differs')
                    payload=b'\x03\x04'+encode(expected)[:-1]+b'\x05\0';pending.update(regs=r,payload=payload,guard=bytes(m[r[0]+64:r[0]+80]),effect=bytes(m[r[3]:r[3]+64]))
                if a==0x0800F5B2 and pending:
                    old=pending['regs'];p=old[0];raw=pending['payload'];require(bytes(m[p:p+len(raw)])==raw and bytes(m[p+64:p+80])==pending['guard'] and bytes(m[old[3]:old[3]+64])==pending['effect'] and r[4:12]==old[4:12] and r[13]==old[13],'Inscribed scroll output/field/guard/ABI differs');formats.append({'id':'scroll-item.format','bytes':len(raw),'guard_abi_preserved':True});pending.clear()
                observer.callback(e)
                try:checks.callback(e)
                except ValueError:
                    (g.output/'failure.json').write_text(json.dumps({'event':e,'item_events':checks.item_events,'bytes_at_outputs':{hex(int(x['regs'][1],16)):bytes(m[int(x['regs'][1],16):int(x['regs'][1],16)+96]).hex() for x in checks.item_events if x['address'] in ('0x800ef30','0x800f244')}},indent=2))
                    raise
                numbers.callback(e)
            with Debugger(g,callback,max_events=100000) as debug:
                for a in set(checks.ADDRESSES+observer.ADDRESSES+(0x0800F302,0x0800F5B2,0x0800F0DC)):debug.breakpoint(a)
                g.press('B',hold=8,wait=120);g.press('A',wait=120);pic=g.capture('inventory');parent=parent_image(g)
                g.press('A',wait=120);g.capture('actions');g.press('B',wait=120);require(parent_image(g)==parent,'Inscribed scroll action cancellation changed parent')
                g.press('A',wait=120);g.press('B',wait=120);require(parent_image(g)==parent,'Inscribed scroll action reopening changed parent')
            require(formats and lookup and not pending and not checks.active and not checks.stack,'Inscribed scroll checks incomplete')
            reads=[r for r in observer.reads if r['window_width']==168 and encode(expected)[:-1].hex() in r['raw_hex']];require(reads,'Complete inscribed scroll was not rendered')
            budgets=[];pixels=0
            for read in reads:
                colours=rendered_codes(bytes.fromhex(read['raw_hex']),foreground=15,saved=15);require(len(colours)==len(read['glyph_positions']),'Inscribed scroll glyph/budget trace differs');ink=[];price=[];price_cells=[]
                for (code,colour),glyph in zip(colours,read['glyph_positions']):
                    record,_=checks.glyph_record(code);edge=max((x+1 for line in record['rows'] for x,bit in enumerate(line) if bit=='#'),default=0)
                    is_price=code==0x8140 or 0x8740<=code<=0x8749
                    if is_price:price_cells.append(glyph['x'])
                    if edge:(price if is_price else ink).append((glyph['x'],glyph['x']+edge))
                    bank=m.u16[m.u32[read['window']+12]]>>12;native_colour=m.u16[0x05000000+2*(16*bank+colour)];rgb=tuple(((native_colour>>shift)&31)*255//31 for shift in (0,5,10))
                    for y,line in enumerate(record['rows']):
                        for x,bit in enumerate(line):
                            require((pic.getpixel((read['screen_x']+glyph['x']+x,read['screen_y']+glyph['row']*16+y))==rgb)==(bit=='#'),'Inscribed scroll final pixels differ: '+repr((name,hex(code),glyph['x']+x,glyph['row']*16+y)))
                            pixels+=1
                right=max((b for _,b in ink+price),default=0);require(right<=168,'Inscribed scroll exceeds item row')
                if price_cells:require(max((b for _,b in ink),default=0)<=min(price_cells),'Inscribed scroll overlaps price cells')
                budgets.append({'ink_right':right,'text_budget':162,'name_price_separate':True,'raw_hex':read['raw_hex']})
            require(g.snapshot().battery==fixture.battery,'Inscribed scroll wrote save')
            results.append({'case':name,'item_id':ident,'state':state,'inputs':g.inputs,'overrides':overrides,'lookups':lookup,'formats':formats,'reads':checks.reads,'glyph_checks':checks.glyph_checks,'budgets':budgets,'numeric_checks':numbers.samples,'parent_restored':True,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'images':{p:digest((g.output/p).read_bytes()) for p in ('inventory.png','actions.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'All37 non-spell category0 inscription selectors in normal/priced states plus longest priced name stress with six digits and markers. Exact English effect lookup, preserved64-byte field/output, complete row pixels, name/price separation, native compact digits, two action cancellations/reopenings and unchanged battery are checked. Special/reserved category members are explicit controlled states; ordinary writing eligibility and other categories remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Scroll item:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/scroll-item-prototype');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
