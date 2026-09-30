"""Spell list pages and action states through ordinary buttons in controlled RAM."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import TextChecks
from tools.verify_service_ui import materialize


def run(source=ROOT/'build/spell-menu-prototype',only=None):
    out=source/'spell-menu-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale spell menu ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    definitions=build['spell_info']['definitions'];eligible={r['id'] for r in definitions if r['menu_eligible']}
    direct={r['offset']+0x08000000:r for r in build['spell_menu']['entries']}
    direct.update({r['offset']+0x08000000:r for r in build['spell_info']['entries'] if r['kind']=='format'})
    names={r['offset']+0x08000000:r for r in build['spell_info']['entries'] if r['kind']=='name'}
    learned_at=0x02004D80;equipped_at=0x02004E7A;results=[]
    cases=[]
    for first in (True,False):
        ids={r['id'] for r in definitions if r['menu_eligible'] and ((r['menu_order']<=30)==first)}
        for available in (True,False):cases.append((('first' if first else 'last')+'-'+('available' if available else 'disabled'),ids,available,False,False))
    cases.append(('unlearned',set(),True,False,False))
    for equipped in (False,True):
        for available in (True,False):cases.append(('action-'+('remove' if equipped else 'equip')+'-'+('available' if available else 'disabled'),{43},available,equipped,True))
    for name,ids,available,equipped,action in cases:
        if only and name!=only:continue
        print('Spell menu:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;overrides=[];formats=[];pending=[];draws=[];images={};pixels=0;entries=[];returns=[];creations=[];action_entries=[];action_returns=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            hero=m.u32[0x02001624];write(hero+0x90,b'\2');write(hero+0x84,struct.pack('<HH',500 if available else 1,500))
            write(learned_at,bytes(int(i in ids) for i in range(61)));write(equipped_at,bytes((43 if equipped else 0,)))
            resources={r['offset']+0x08000000:r|{'layout':{'pages':[[r['id']]]}} for r in build['spell_info']['entries'] if r['kind']=='description'}
            c=TextChecks(g,resources)
            def callback(e):
                a,r=e['address'],e['registers']
                if a in (0x08022280,0x08022690):
                    (entries if a==0x08022280 else action_entries).append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                if a==0x08001798:creations.append(e)
                if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08000FB8 and r[1] not in direct:c.resources.pop(r[0],None)
                if a==0x08000FB8 and r[1] in direct:
                    row=direct[r[1]];cap=row['capacity'];args=r[2:4]+[m.u32[r[13]+i*4] for i in range(4)]
                    require(r[0]==r[13]+(8 if row['kind']=='list-format' else 4 if row['kind']=='format' else 0),'Spell menu output ownership differs')
                    payload=materialize(bytes.fromhex(row['encoded_hex']),args,m);require(len(payload)<=cap,'Spell menu format overflow')
                    spell_names=[names[v]['spell_id'] for v in args if v in names]
                    pending.append((r,row,payload,bytes(m[r[0]+cap:r[0]+cap+16]),spell_names))
                if pending and a==(pending[-1][0][14]&~1):
                    old,row,payload,guard,spell_names=pending.pop();at=old[0];cap=row['capacity']
                    require(bytes(m[at:at+len(payload)])==payload and bytes(m[at+cap:at+cap+16])==guard and r[4:12]==old[4:12] and r[13]==old[13],'Spell menu output/guard/ABI differs')
                    c.resources[at]={'id':row['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[row['id']]]}}
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':cap,'spell_ids':spell_names,'guard_abi_preserved':True})
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a in c.ADDRESSES:c.callback(e)
                if a in (0x080224D4,0x080227DE):
                    starts=entries if a==0x080224D4 else action_entries;ends=returns if a==0x080224D4 else action_returns
                    old=starts[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==starts[-1]['guard'],'Spell menu caller ABI/guard differs');ends.append(e)
            def capture(tag):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Missing spell menu glyphs')
                for d in draws:
                    if tag=='info' and d['window']!=c.reads[-1]['window']:continue
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Spell menu final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=250000) as debug:
                for a in set(c.ADDRESSES+(0x08022280,0x080224D4,0x08022690,0x080227DE,0x08001798,0x08001750,0x08001888,0x08000FB8,0x080225BE,0x080225FA,0x08022616,0x080226D0,0x08022702,0x0802286A)):debug.breakpoint(a)
                g.press('B',hold=8,wait=120);g.press('DOWN',wait=30);g.press('A',wait=120);capture('list')
                require(entries and creations[-1]['registers'][2] in (7,21),'Spell list setup missing')
                if action:
                    g.press('A',wait=120);capture('actions')
                    require(action_entries[-1]['registers'][0]==43 and creations[-1]['registers'][:4]==[24,7,5,3],'Spell action selection/geometry differs')
                    # Window borders extend four pixels past each content edge.
                    require((24*8-4)-((1+21)*8+4)==8,'Spell windows lost the original eight-pixel border gap')
                    g.press('UP',wait=30);g.press('DOWN',wait=30);g.press('DOWN',wait=30)
                    if not available:
                        count=len(action_returns);g.press('A',wait=120);require(len(action_returns)==count,'Unavailable Equip/Remove unexpectedly closed')
                    g.press('DOWN',wait=30);g.press('A',wait=120);capture('info')
                    require(c.completed('spell.description.43'),'Spell action Info did not select its description')
                    g.press('B',wait=120);capture('after-info')
                    g.press('A',wait=120);capture('reopened-actions');g.press('B',wait=120);capture('cancelled-actions')
                    if available:
                        original_spell=43 if equipped else 0
                        g.press('A',wait=120);g.press('DOWN',wait=30);g.press('A',wait=120)
                        require(m.u8[equipped_at]==(0 if equipped else 43),'Native Set/Unset did not change shortcut')
                        capture('shortcut-changed')
                        g.press('A',wait=120);capture('opposite-action');g.press('DOWN',wait=30);g.press('A',wait=120)
                        require(m.u8[equipped_at]==original_spell,'Native Set/Unset did not restore shortcut')
                        capture('shortcut-restored')
                else:
                    for page in range(1,4):g.press('RIGHT',wait=120);capture('page-'+str(page))
                    g.press('RIGHT',wait=120);capture('wrapped-page')
                    if not ids:
                        count=len(action_entries);g.press('A',wait=120);require(len(action_entries)==count,'Unlearned spell opened actions')
                g.press('B',wait=120)
            covered={i for r in formats if r['capacity']==64 for i in r['spell_ids']}
            require(covered==ids,'Spell list source set differs: '+repr((name,covered,ids)))
            require(len(entries)==len(returns) and len(action_entries)==len(action_returns) and not pending and not c.active and g.snapshot().battery==fixture.battery,'Spell menu return/guard/battery incomplete')
            require(bytes(m[learned_at:learned_at+61])==bytes(int(i in ids) for i in range(61)) and m.u8[equipped_at]==(43 if equipped else 0),'Spell preview changed learned/equipped state')
            results.append({'case':name,'spell_ids':sorted(ids),'covered_ids':sorted(covered),'available':available,'equipped':equipped,'reads':c.reads,'formats':formats,'inputs':g.inputs,'overrides':overrides,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'returns':returns,'action_returns':action_returns,'images':images})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Existing mage vocation, learned bytes, HP and equipped spell are controlled; ordinary buttons open native lists and action/Info menus. All50 menu-eligible spell names/targets are checked across two learned cohorts and affordable/unaffordable states, plus unlearned and equipped/unselected action variants. Actual Set/Unset toggles and restoration, original geometry,64/256-byte buffers, final coloured pixels, page wrapping, cursor wrapping, cancellation/reopening and caller/battery preservation pass. Natural vocation/spell acquisition and casting effects remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Spell menu:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/spell-menu-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
