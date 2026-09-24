"""Native rendering preflight for reviewed event prose, without event insertion.

Candidate strings are appended through RomBuild, but event tables stay unchanged.
Controlled source arguments use an ordinarily reached two-row reader. Event
commands and special format consumers are explicitly excluded from this pass.
"""
import argparse, json
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Snapshot, Debugger
from tools.dialogue_layout import compile_dialogue
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.text_codec import tokenize
from tools.name_entry import HERO

OUT = ROOT / 'build/prose-preflight'

def candidate():
    import tools.build_english as english
    original = english.add_combat
    rows, exclusions, catalogs = [], [], {}
    def add(build):
        combat = original(build)
        for path in sorted((ROOT/'translations').glob('*-draft.json')):
            selected = [r for r in json.loads(path.read_text()).get('entries', [])
                        if str(r.get('id', '')).startswith('event-bank-') and r.get('english_draft')]
            if not selected: continue
            catalogs[str(path.relative_to(ROOT))] = digest(path.read_bytes())
            for row in selected:
                require(row.get('prose_review'), 'Event prose lacks its bilingual review: '+row['id'])
                if row.get('layout_blocker') or any(command in row['english_draft'] for command in ('@A@','@B@','@C@')):
                    exclusions.append({'id':row['id'], 'reason':row.get('layout_blocker') or 'Event side-effect command requires its actual story context'})
                    continue
                raw=bytes.fromhex(row['raw_hex'])
                require(digest(raw)==row['source_sha256'], 'Prose source digest differs')
                payload, layout=compile_dialogue(row['english_draft'], tokenize(raw)[0])
                offset=build.allocate('preflight-'+row['id'],payload,'prose-rendering-preflight')
                rows.append({'id':row['id'],'rom_offset':offset,'encoded_hex':payload.hex(),
                             'layout':layout,'english':row['english_draft'],'source_sha256':row['source_sha256'],
                             'catalog':str(path.relative_to(ROOT))})
        return combat
    try:
        english.add_combat=add;rom,build=english.build_rom()
    finally:
        english.add_combat=original
    build['preflight']={'entries':rows,'excluded':exclusions,'catalogs':catalogs}
    build['scope']='Rendering-only candidate strings. Event tables and source controls are not redirected. No new story insertion, natural branch coverage or final terminology acceptance is claimed.'
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def inserted_candidate():
    from tools.rom import load_base
    from tools.rom_build import RomBuild
    from tools.build_compact_font import add_font
    from tools.name_entry import add_name_entry
    from tools.event_prose_text import add_prototype, CATALOG
    build=RomBuild(load_base());add_font(build,compact_numbers=True);add_name_entry(build)
    prose=add_prototype(build);rom,report=build.finish()
    report['preflight']={'entries':prose['entries'],'excluded':json.loads(CATALOG.read_text())['excluded']}
    report['event_prose']=prose
    # This direct original resume message supplies the real two-row context.
    report['dialogue']={'entries':[{'id':'rom.0006afe0','rom_offset':0x6AFE0}]}
    report['scope']=f"{len(prose['entries'])} reviewed ordinary event sources are bound through owned offset slots in seven ROM banks. No decoded RAM growth. Controlled reader checks do not establish ordinary story progression or branch outcomes; special format/command consumers are excluded."
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    return rom,report

def context(rom,build):
    path=OUT/'native/reader-entry'
    if path.with_suffix('.json').exists():
        snapshot=Snapshot.load(path)
        if snapshot.rom_sha256==digest(rom):return snapshot
    battery=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
    target=next(r['rom_offset']+0x08000000 for r in build['dialogue']['entries'] if r['id']=='rom.0006afe0')
    reached=[]
    with Session(rom,OUT/'native',initial_save=battery) as game:
        def callback(event):
            if event['registers'][1]==target and not reached:
                game.snapshot().save(path);reached.append(event)
        with Debugger(game,callback,max_events=2000) as debug:
            debug.breakpoint(0x08002298)
            game.frames(600);game.press('START',wait=180);game.frames(204)
            for _ in range(12):
                if reached: break
                game.press('A', wait=120)
        require(reached,'Ordinary resume did not reach the expected story reader')
        (OUT/'native/provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'save_sha256':digest(battery),
                                                           'events':reached,'inputs':game.inputs,'controlled_overrides':[]},indent=2)+'\n')
    return Snapshot.load(path)

def run(inserted=False,cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        from tools.build_english import build_rom
        from tools.event_prose_text import CATALOG
        OUT=ROOT/'build/english/event-prose-validation';rom,build=build_rom()
        build['preflight']={'entries':[r for r in build['dialogue']['entries'] if r['batch']=='event-prose'],
                            'excluded':json.loads(CATALOG.read_text())['excluded']}
        build['scope']='Current cumulative ROM with original and newly reviewed text sharing seven checked event banks. These cases validate the ordinary event-prose family through controlled reader arguments; special consumers have separate native calls and actual ROM bindings have a separate getter report.'
    elif inserted:
        OUT=ROOT/'build/event-prose-insertion';rom,build=inserted_candidate()
    else:rom,build=candidate()
    fixture=context(rom,build)
    revision=digest((ROOT/'tools/verify_prose_preflight.py').read_bytes()
                    +(ROOT/'tools/dialogue_checks.py').read_bytes()
                    +(ROOT/'tools/emulator.py').read_bytes())
    results=[]
    for row in build['preflight']['entries']:
        payload=bytes.fromhex(row['encoded_hex'])
        cases=player_layout_cases() if any(c in row['layout']['commands'] for c in ('{player}','{initial}')) else [('native',None)]
        for label,name in cases:
            output=OUT/(row['id']+'-'+label);path=output/'report.json'
            key={'rom_sha256':digest(rom),'fixture_sha256':digest(fixture.state),'verifier_sha256':revision,'id':row['id'],'case':label}
            if path.exists():
                cached=json.loads(path.read_text())
                if cached.get('cache_key')==key and cached.get('passed') and all((output/p).exists() and digest((output/p).read_bytes())==sha for p,sha in cached['images'].items()):
                    results.append(cached);continue
            print('Prose',row['id'],label,flush=True)
            with Session(rom,output) as game:
                game.restore(fixture);before=int(game.core.cpu.gprs[1]);target=row['rom_offset']+0x08000000
                game.core.cpu.gprs[1]=target
                if name:
                    for i,value in enumerate(name.ljust(16,b'\0')):game.core.memory.u8[HERO+i]=value
                check=TextChecks(game,{target:row});images=[]
                with Debugger(game,check.callback,max_events=100000) as debug:
                    for address in check.ADDRESSES:debug.breakpoint(address)
                    game.frames(120);game.capture('page-0');images.append('page-0.png')
                    for page in range(1,len(row['layout']['pages'])+4):
                        if check.completed(row['id']) and check.active is None:break
                        game.press('A',wait=120);image='page-'+str(page);game.capture(image);images.append(image+'.png')
                    require(check.completed(row['id']) and check.active is None,'Prose reader did not finish: '+row['id'])
                require(len(check.reads)==1,'Unexpected extra prose read')
                require(game.snapshot().battery==fixture.battery,'Controlled prose preflight wrote the save')
                result={'passed':True,'cache_key':key,'source_sha256':row['source_sha256'],
                        'controlled_source':{'r1_before':before,'r1_after':target},'controlled_player_hex':name.hex() if name else None,
                        'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                        'images':{p:digest((output/p).read_bytes()) for p in images}}
                path.write_text(json.dumps(result,indent=2)+'\n');results.append(result)
    report={'passed':True,'rom_sha256':digest(rom),'sources':len(build['preflight']['entries']),
            'cases':len(results),'glyph_checks':sum(r['glyph_checks'] for r in results),'excluded':build['preflight']['excluded'],
            'case_reports':[str((OUT/(r['cache_key']['id']+'-'+r['cache_key']['case'])/'report.json').relative_to(ROOT)) for r in results],
            'scope':build['scope']+' Native reader pixels, rows, paging, player-name extremes and return ABI checked. Source references are supplied as controlled reader arguments. Event-table binding status is specified above and checked separately by the relocation verifier.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Prose preflight',report['sources'],'sources;',report['cases'],'cases')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--inserted',action='store_true');mode.add_argument('--cumulative',action='store_true')
    args=parser.parse_args();run(args.inserted,args.cumulative)
