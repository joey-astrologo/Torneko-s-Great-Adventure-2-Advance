"""Explicit controlled item-state probes, separate from natural route acceptance."""
import json,struct
import mgba.log
from tools.audit_menu_layouts import Observer,parent_image
from tools.emulator import Session,Snapshot,Debugger
from tools.menu_text import prototype
from tools.menu_checks import MenuChecks
from tools.compact_font import load_font,COMPACT_ASSET
from tools.review_fonts import extract
from tools.numeric_font import ALIASES,glyph as numeric_glyph
from tools.rom import ROOT,load_base,require,digest
OUT=ROOT/'build/menu-resize/variants'

def run(english=False):
    global OUT
    mgba.log.silence();original=load_base();font=load_font(COMPACT_ASSET)
    if english:
        from tools.build_english import build_rom
        rom,build=build_rom();menus=build['menus'];OUT=ROOT/'build/english/menu-variant-validation'
        fixture=Snapshot.load(ROOT/'build/english/mansion-validation/quest-room-entrance')
    else:
        rom,menus=prototype();fixture=Snapshot.load(ROOT/'build/menu-resize/prototype/quest-room')
    require(fixture.rom_sha256==digest(rom),'Refresh matching native fixture')
    definitions=0x141b9c;rows=[];cached={}
    # The 221 bounded item definitions. Adjacent disguise data is not an item definition.
    with Session(rom,OUT) as game:
        for item_id in range(221):
            category=original[definitions+item_id*24+20]
            for state in (['identified'] if item_id not in [0,30,48,78,87,116,154,169,203,212,214,218,220] else ['identified','equipped','cursed','unidentified','priced','maximum-fields']):
                game.restore(fixture);m=game.core.memory
                mapping=bytes(m[0x020013d0:0x020014d0])
                require(item_id in mapping,'Item ID absent from native mapping')
                slot=0x0200df28;original_item=bytes(m[slot:slot+120]);item=bytearray(original_item)
                flags=0xc8000000
                if state=='equipped':flags|=0x800000
                if state=='cursed':flags|=0xC000000|0x800000
                if state=='unidentified':flags=0x80000000
                if state=='priced':flags|=0x100000
                struct.pack_into('<I',item,0,flags);item[8]=mapping.index(item_id)
                item[4]=99 if state=='maximum-fields' else 0;item[5]=99 if state=='maximum-fields' else 1
                # Empty all pot-content records; never claim naturally acquired items.
                item[24:]=bytes(96)
                for i,b in enumerate(item):m.u8[slot+i]=b
                type_flags=m.u32[0x02003bac+item_id*20]
                m.u32[0x02003bac+item_id*20]=(type_flags&~0x40000000) if state=='unidentified' else (type_flags|0x40000000)
                observer=Observer(game);checks=MenuChecks(game,menus,font);widths=[];glyphs=[];actions=[];stack=[]
                def cb(e):
                    observer.callback(e);checks.callback(e);a,r=e['address'],e['registers']
                    if a==0x08019184:stack.append((r[13],r[4:12],bytes(m[r[13]:r[13]+32])))
                    if a==0x080194aa:
                        sp,regs,guard=stack.pop();require(r[13]==sp and r[4:12]==regs and bytes(m[sp:sp+32])==guard,'Variant stack corruption')
                    if a==0x0801948a:
                        actions.extend(m.u16[0x0200cdd0+i*2] for i in range(7))
                with Debugger(game,cb,max_events=12000) as debug:
                    for a in set(observer.ADDRESSES+checks.ADDRESSES+(0x0801948a,)):debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30)
                    before=parent_image(game);game.press('A',wait=30)
                    for read in observer.reads:
                        if read['window_width']!=168:continue
                        edge=0
                        for g in read['glyph_positions']:
                            code=g['code']
                            if code not in cached:
                                if 0xf020<=code<=0xf07e or (english and code in ALIASES):
                                    glyph=font['glyphs'][chr(code&255)] if 0xf020<=code<=0xf07e else numeric_glyph(font,code)
                                    cached[code]=max((x+1 for row in glyph['rows'] for x,p in enumerate(row) if p=='#'),default=0)
                                else:
                                    v=extract(original,code);cached[code]=max((x+1 for row in v['pixels'] for x,p in enumerate(row) if p),default=0)
                            edge=max(edge,g['x']+cached[code])
                        widths.append(edge)
                    game.press('B',wait=30);preserved=before==parent_image(game)
                    require(preserved,'Variant parent did not restore')
                menu=[r for r in observer.reads if r['window_width']==40 and r['screen_x']==192 and r['initial_x']==4]
                if not menu:
                    print('No action panel:',item_id,state,'category',category,flush=True)
                    rows.append({'item_id':item_id,'category':category,'state':state,'excluded':'No action panel in this synthetic state','max_item_ink_edge':max(widths,default=0),'menu_bytes':0});continue
                row={'item_id':item_id,'category':category,'state':state,'controlled_item_hex':item.hex(),
                     'actions':actions,'glyph_checks':checks.glyph_checks,'max_item_ink_edge':max(widths,default=0),'menu_hex':menu[-1]['raw_hex'],
                     'menu_bytes':len(bytes.fromhex(menu[-1]['raw_hex'])),'rows':menu[-1]['rows'],
                     'parent_preserved':preserved,'stack_preserved':not stack}
                rows.append(row)
                require(row['max_item_ink_edge']<=168,'Item ink exceeds parent window')
                require(row['menu_bytes']<=256 and row['rows']<=7,'Action buffer/row capacity exceeded')
                if state!='identified' or item_id in [0,30,48,78,87,116,154,169,203,212,214,218,220]:
                    game.press('A',wait=30);game.capture(f'item-{item_id:03}-{state}')
            if item_id%40==0:print('Item variants through',item_id,flush=True)
    report={'passed':True,'rom_sha256':digest(rom),'probes':rows,'count':len(rows),
            'maximum_item_ink_edge':max(r['max_item_ink_edge'] for r in rows),
            'maximum_menu_bytes':max(r['menu_bytes'] for r in rows),
            'scope':'Controlled replacement of one disposable inventory record. Not naturally acquired items; synthetic flags need gameplay validation. Eight reviewed item names are included; other names remain Japanese. Numeric glyphs and English row spacing use the cumulative typography fixes. Explicit known-name flags replace the earlier mistaken inscription-bit probe. Item ink remains inside the original 168 px parent; the action border begins at parent-local x=180.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['count'],report['maximum_item_ink_edge'],report['maximum_menu_bytes']);return report
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--english',action='store_true');run(p.parse_args().english)
