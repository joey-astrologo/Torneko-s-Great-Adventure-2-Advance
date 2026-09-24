"""All reviewed appearances through native inventory rows, with bounded state probes."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.item_alias_text import add_aliases
from tools.verify_items import ItemChecks
from tools.numeric_checks import NumericChecks
from tools.audit_menu_layouts import Observer,parent_image
from tools.compact_font import encode
from tools.verify_mansion import QuestTrace,attach
from tools.trace_mansion import finish

OUT=ROOT/'build/item-alias-prototype'
REPRESENTATIVES={0:116,1:87,2:48,5:203,7:169,9:154}

def candidate():
    import tools.build_english as english
    prior=english.add_combat;aliases=None
    def add(build):
        nonlocal aliases
        combat=prior(build);aliases=add_aliases(build);return combat
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['aliases']=aliases
    build['baseline_reviewed_inserted_resources']=build['total_reviewed_inserted_resources']
    build['reviewed_resource_counts']['item_appearances']=len(aliases['entries'])
    build['total_reviewed_inserted_resources']+=len(aliases['entries'])
    build['scope']='Separate appearance prototype on the early-text baseline, without the current story candidate. Controlled appearance tests and cumulative story acceptance are separate.'
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def context(rom,build):
    out=OUT/'native';path=out/'ready';battery=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
    provenance=out/'provenance.json'
    if path.with_suffix('.json').exists() and provenance.exists():
        snapshot=Snapshot.load(path);record=json.loads(provenance.read_text())
        if snapshot.rom_sha256==digest(rom) and record['source_save_sha256']==digest(battery):return snapshot
    out.mkdir(parents=True,exist_ok=True);(out/'source.sav').write_bytes(battery)
    with Session(rom,out,initial_save=battery) as game:
        check=QuestTrace(game,'alias-context',build,save_fixture=False)
        with Debugger(game,check.callback,max_events=30000) as debug:
            attach(debug,check);game.frames(600);game.press('START',wait=180);game.frames(204)
            finish(game,check,'rom.0006afe0','resume');game.press('A',wait=120)
            require(game.core.memory.u16[0x02005674]==6,'Alias checkpoint did not reach native 6F')
        snapshot=game.snapshot();snapshot.save(path);game.capture('ready')
        provenance.write_text(json.dumps({'rom_sha256':digest(rom),'source_save_sha256':digest(battery),
                                         'inputs':game.inputs,'controlled_overrides':[]},indent=2)+'\n')
    return snapshot

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/item-alias-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative appearance ROM differs')
    else:rom,build=candidate()
    fixture=context(rom,build);rows=build['aliases']['entries']
    widest={category:max((r for r in rows if r['category']==category),
                         key=lambda r:(r['display_width_px'],r['display_encoded_bytes'])) for category in REPRESENTATIVES}
    cases=[(r,'unknown') for r in rows]+[(r,state) for r in widest.values() for state in ('priced-maximum','identified')]
    results=[]
    for row,state in cases:
        ident=REPRESENTATIVES[row['category']];case=f"{row['id']}-{state}";print('Item appearance',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;address=0x0200DF28
            old_item=bytes(m[address:address+120]);item=bytearray(old_item);mapping=bytes(m[0x020013D0:0x020014D0])
            flags=0x80100000 if state=='priced-maximum' else 0xC8000000 if state=='identified' else 0x80000000
            struct.pack_into('<I',item,0,flags);item[8]=mapping.index(ident);item[4]=99 if state=='priced-maximum' else 1
            item[5]=1;item[24:]=bytes(96)
            for i,value in enumerate(item):m.u8[address+i]=value
            definition=0x02003BAC+ident*20;old_definition=bytes(m[definition:definition+20])
            m.u16[definition+4]=row['id']
            m.u32[definition]=(m.u32[definition]|0x40000000) if state=='identified' else (m.u32[definition]&~0x40000000)
            check=ItemChecks(game,build);observer=Observer(game);numbers=NumericChecks(game)
            def callback(event):observer.callback(event);check.callback(event);numbers.callback(event)
            with Debugger(game,callback,max_events=100000) as debug:
                for a in set(check.ADDRESSES+observer.ADDRESSES+numbers.ADDRESSES):debug.breakpoint(a)
                game.press('B',hold=8,wait=120);game.press('A',wait=120);game.capture('inventory')
                original_parent=parent_image(game)
                for attempt in range(2):
                    game.press('A',wait=90);game.capture('actions-'+str(attempt))
                    game.press('B',wait=120)
                    require(parent_image(game)==original_parent,'Alias action panel did not restore parent')
                game.press('B',wait=120);game.press('B',wait=120)
            formats=[f for f in check.formats if f['item']==ident]
            require(formats and not check.stack and check.active is None,'Alias row formatter did not complete')
            payload=encode(row['name'])[:-1]
            for formatted in formats:
                raw=bytes.fromhex(formatted['hex'])
                require(formatted['known_name']==(state=='identified'),'Alias identification state was ignored')
                require((payload in raw)==(state!='identified'),'Native alias name missing or retained after identification')
                require(b'\x1c' not in raw and b'\x1d' not in raw,'English alias row was condensed')
            require(check.glyph_checks>0 and check.reads,'Alias row was not checked by native renderer')
            require(game.snapshot().battery==fixture.battery,'Alias probe wrote battery')
            results.append({'case':case,'alias_id':row['id'],'item_id':ident,'category':row['category'],'state':state,
                            'name':row['name'],'original_item_hex':old_item.hex(),'controlled_item_hex':item.hex(),
                            'original_definition_hex':old_definition.hex(),'controlled_definition_hex':bytes(m[definition:definition+20]).hex(),
                            'formats':formats,'reads':check.reads,'glyph_checks':check.glyph_checks,
                            'numeric_checks':numbers.samples,'inputs':game.inputs,'parent_restoration_checks':2})
    require({r['alias_id'] for r in results if r['state']=='unknown'}==set(range(154)),'Missing appearance names')
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'All 154 English appearance labels plus widest priced and identified probes in each of six categories: 166 native cases. Each uses a recorded representative item, explicit appearance assignment and identification state in disposable RAM. Full native row guards, bitmap/width checks, numeric cells, unchanged spacing, repeated action-panel restoration and battery preservation pass. Random assignment code/table/sentinel stay original; ordinary discovery, custom names, inscriptions and special definitions remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Item appearances:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
