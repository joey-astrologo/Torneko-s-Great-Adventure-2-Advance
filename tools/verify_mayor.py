"""Controlled native rendering/format tests for the village-renaming consumer."""
import argparse
import json
import struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,Snapshot,ffi
from tools.mayor_text import add_mayor
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks
from tools.compact_font import encode
from tools.verify_service_ui import materialize

OUT=ROOT/'build/mayor-prototype'


def candidate():
    from tools import build_english as english
    prior=english.add_combat;resource=None
    def add(build):
        nonlocal resource
        result=prior(build);resource=add_mayor(build);return result
    try:
        english.add_combat=add
        rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['mayor']=resource;build['reviewed_resource_counts']['mayor']=len(resource['entries'])
    build['total_reviewed_inserted_resources']+=len(resource['entries'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build


def contexts(rom):
    fixture=service_ready(rom,OUT);paths={n:OUT/'native'/n for n in ('entry','farewell')}
    revision=digest((ROOT/'tools/verify_mayor.py').read_bytes());rp=OUT/'native/context-revision.txt'
    if rp.exists() and rp.read_text()==revision and all(p.with_suffix('.json').exists() and Snapshot.load(p).rom_sha256==digest(rom) for p in paths.values()):
        return {n:Snapshot.load(p) for n,p in paths.items()}
    with Session(rom,OUT/'context') as game:
        game.restore(fixture);events=[];saved=set()
        def cb(e):
            a,r=e['address'],e['registers']
            if a==0x0801DFAC:
                game.core.cpu.gprs[1]=0
                require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08020564)),'Mayor redirect failed')
                game.snapshot().save(paths['entry']);saved.add('entry')
                events.append(e|{'redirected_pc':0x08020564,'r1_after':0})
            if a==0x0801D0A0 and r[14]==0x080205A3 and 'farewell' not in saved:
                game.snapshot().save(paths['farewell']);saved.add('farewell');events.append(e)
        with Debugger(game,cb,max_events=10000) as d:
            for a in (0x0801DFAC,0x0801D0A0):d.breakpoint(a)
            game.press('A',wait=120)
            for _ in range(30):
                if 'farewell' in saved:break
                game.press('B',wait=120)
        require(saved==set(paths),'Mayor contexts incomplete')
        (game.output/'provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'events':events,'inputs':game.inputs},indent=2)+'\n')
    rp.write_text(revision)
    return {n:Snapshot.load(p) for n,p in paths.items()}


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/mayor-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative mayor ROM')
    else:rom,build=candidate()
    fixtures=contexts(rom);rows=build['mayor']['entries']
    with Session(rom,OUT/'entry-inspection') as game:
        game.restore(fixtures['entry']);initial=[int(v)&0xffffffff for v in game.core.cpu.gprs]
        caller_guard=bytes(game.core.memory[initial[13]:initial[13]+32])
    results=[]
    for row in rows:
        formatted=not row['layout']['direct_rom_stream']
        names=[('required',encode('Torneko')),('eight-English',encode('W'*8)),('eight-Japanese',b'\x82\xb0'*8+b'\0'),('empty',b'\0')] if formatted else [('plain',None)]
        for label,name in names:
            case=row['id']+'-'+label;print('Mayor:',case,flush=True)
            with Session(rom,OUT/case) as game:
                fixture=fixtures['farewell'];game.restore(fixture);m=game.core.memory
                sp=int(game.core.cpu.gprs[13]);target=row['offset']+0x08000000;overrides=[]
                def reg(i,v):
                    overrides.append({'register':i,'before':int(game.core.cpu.gprs[i])&0xffffffff,'after':v});game.core.cpu.gprs[i]=v
                expected=bytes.fromhex(row['encoded_hex']);dest=target
                require(sp+0x114+32==initial[13],'Mayor frame differs')
                if formatted:
                    dest=sp;address=sp+0x100
                    overrides.append({'address':address,'before':bytes(m[address:address+20]).hex(),'after':name.ljust(20,b'\0').hex()})
                    for i,v in enumerate(name.ljust(20,b'\0')):m.u8[address+i]=v
                    reg(0,dest);reg(1,target);reg(2,address)
                    overrides.append({'pc_after':0x08020670,'reason':'Owned native final-message formatter call; existing name field and output frame.'})
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08020670)),'Mayor formatter redirect failed')
                    expected=materialize(expected,[address],m)
                    require(len(expected)<=row['layout']['maximum_formatted_bytes']<=256,'Mayor format capacity differs')
                else:reg(0,target)
                guard=bytes(m[sp+256:sp+276]);saved=[int(game.core.cpu.gprs[i])&0xffffffff for i in range(4,12)]
                resources={r['offset']+0x08000000:r for r in rows if r['layout']['direct_rom_stream']}
                resources[dest]=row|{'encoded_hex':expected.hex()};check=TextChecks(game,resources)
                returned=[];formats=[];images=[]
                inventory=bytes(m[0x0200DF28:0x0200DF28+2400]);ga=m.u32[0x02001624]+0x60;gold=m.u32[ga]
                names_before=bytes(m[0x02003B36:0x02003B69])
                def cb(e):
                    a,r=e['address'],e['registers']
                    if a==0x08020674 and formatted:
                        require(bytes(m[sp:sp+len(expected)])==expected and bytes(m[sp+256:sp+276])==guard,'Mayor formatted bytes/guard differ')
                        require(r[13]==sp and r[4:12]==saved,'Mayor formatter ABI differs');formats.append(e)
                    if a==0x0802068A:
                        require(r[13]==initial[13] and r[4:12]==initial[4:12] and r[0]==initial[14],'Mayor return ABI differs')
                        require(bytes(m[r[13]:r[13]+32])==caller_guard,'Mayor caller guard differs');returned.append(e)
                    if a in check.ADDRESSES:check.callback(e)
                with Debugger(game,cb,max_events=120000) as d:
                    for a in set(check.ADDRESSES+(0x08020674,0x0802068A)):d.breakpoint(a)
                    for page in range(24):
                        game.frames(90);image=f'page-{page:02}';game.capture(image);images.append(image+'.png')
                        if returned:break
                        game.press('B',wait=0)
                require(len(returned)==1 and (len(formats)==1 if formatted else not formats) and check.completed(row['id']) and not check.active,'Mayor rendering incomplete')
                require(bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and m.u32[ga]==gold and game.snapshot().battery==fixture.battery,'Mayor render probe changed items/gold/save')
                require(bytes(m[0x02003B36:0x02003B69])==names_before,'Mayor render probe changed live name records')
                results.append({'case':case,'id':row['id'],'controlled_overrides':overrides,'formats':formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'sources':len(rows),'cases':results,'scope':'Controlled native consumer rendering and256-byte formatting, existing20-byte village field, eight-cell legacy width, paging/pixels/ABI/guards and unchanged items/gold/live names/battery. Plain sources replace farewell; formats use the native final-message call. Actual editor confirmation/cancellation, ordinary unlocking and persistence are separate.'},indent=2)+'\n')
    print('Mayor:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

