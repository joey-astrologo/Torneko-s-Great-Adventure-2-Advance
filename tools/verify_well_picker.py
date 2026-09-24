"""Well difficulty prompt and native bounded number selection through return."""
import argparse
import json
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,Snapshot,ffi
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks
from tools.audit_menu_layouts import Observer
from tools.verify_service_ui import materialize
from tools.well_picker_text import add_well_picker

OUT=ROOT/'build/well-picker-prototype'


def candidate():
    from tools.build_english import build_rom
    rom,build=build_rom(include_story=False)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build


def entry(rom):
    ready=service_ready(rom,OUT);path=OUT/'native/entry'
    with Session(rom,OUT/'context') as game:
        game.restore(ready);events=[]
        def cb(e):
            if e['address']==0x0801DFAC:
                require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08051290)),'Well picker redirect failed')
                events.append(e|{'pc_after':0x08051290});game.snapshot().save(path)
        with Debugger(game,cb,max_events=10000) as d:
            d.breakpoint(0x0801DFAC);game.press('A',wait=120)
        require(len(events)==1,'Well entry missing')
        (game.output/'provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'controlled_events':events,'inputs':game.inputs},indent=2)+'\n')
    return Snapshot.load(path)


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/well-picker-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative well-picker ROM')
    else:rom,build=candidate()
    fixture=entry(rom);prompt,template=build['well_picker']['entries'];results=[]
    require(prompt['id']=='well-picker.prompt' and template['id']=='well-picker.level','Well row order differs')
    for progress in (1,2,9,10,255):
        maximum=min(progress,10)
        for action in ('cancel','initial','minimum','maximum'):
            case=f'progress-{progress}-{action}';print('Well picker:',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);game.core._core.setKeys(game.core._core,0);game.inputs.append({'release_snapshot_keys':fixture.keys,'frame':game.core.frame_counter});m=game.core.memory;initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32])
                old_level=m.u16[0x02005674];m.u16[0x02005674]=77
                ga=m.u32[0x02001624]+0x60;gold=m.u32[ga];inventory=bytes(m[0x0200DF28:0x0200DF28+2400])
                check=TextChecks(game,{prompt['offset']+0x08000000:prompt});observer=Observer(game)
                getter=[];formats=[];pending=[];returned=[];picker_results=[];images=[]
                def capture(name):game.capture(name);images.append(name+'.png')
                def cb(e):
                    a,r=e['address'],e['registers']
                    if a==0x0805129E:
                        getter.append(e|{'r0_after':progress});game.core.cpu.gprs[0]=progress
                    if a==0x08000FB8 and r[1]==template['offset']+0x08000000:
                        require(r[0]==r[13] and r[2]==r[13]+0x80,'Well native picker output/number fields differ')
                        expected=materialize(bytes.fromhex(template['encoded_hex']),[r[2]],m)
                        require(len(expected)<=template['layout']['maximum_formatted_bytes']<=128,'Well picker capacity differs')
                        pending.append((r,expected,bytes(m[r[13]+128:r[13]+160])))
                    if a==0x080164E8 and pending:
                        before,expected,g=pending.pop();dest=before[0]
                        require(r[13]==before[13] and r[4:12]==before[4:12] and bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+128:dest+160])==g,'Well formatter/ABI/guard differs')
                        check.resources[dest]=template|{'encoded_hex':expected.hex()};formats.append({'expected_hex':expected.hex(),'bytes':len(expected),'capacity':128})
                    if a==0x080512C6:picker_results.append(r[0])
                    if a==0x080512EE:
                        require(r[13]==initial[13] and r[4:12]==initial[4:12] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Well consumer ABI/guard differs');returned.append(e)
                    if a in check.ADDRESSES:check.callback(e)
                    observer.callback(e)
                with Debugger(game,cb,max_events=180000) as d:
                    for a in set(check.ADDRESSES+observer.ADDRESSES+(0x0805129E,0x08000FB8,0x080164E8,0x080512C6,0x080512EE)):d.breakpoint(a)
                    for _ in range(12):
                        game.frames(90)
                        if check.completed(template['id']) and not check.active:break
                        game.press('A',wait=0)
                    require(check.completed(prompt['id']) and check.completed(template['id']),'Well prompt/picker missing');capture('initial')
                    if action in ('minimum','maximum'):
                        for _ in range(12):game.press('DOWN',wait=25)
                        capture('minimum')
                        if action=='maximum':
                            for _ in range(12):game.press('UP',wait=25)
                            capture('maximum')
                    game.press('B' if action=='cancel' else 'A',wait=90)
                selected=1 if action=='minimum' else maximum
                require(picker_results==[0xffffffff if action=='cancel' else selected] and len(returned)==1 and not check.active and not pending,'Well bounds/result differ: '+repr((progress,action,picker_results)))
                require(m.u16[0x02005674]==(77 if action=='cancel' else selected) and m.u32[0x0201017C]==(0 if action=='cancel' else 1),'Well native output level/flag differs')
                native=[r for r in observer.reads if r['raw_hex'] in {f['expected_hex'] for f in formats}]
                require(native and all((r['screen_x'],r['screen_y'],r['window_width'],r['rows'])==(144,88,88,1) for r in native),'Well picker original geometry differs')
                require(all(r['glyph_positions'][1]['x']==6 for r in native),'Well picker is not using compact proportional spacing')
                require(game.snapshot().battery==fixture.battery and m.u32[ga]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==inventory,'Well probe changed battery/items/gold')
                results.append({'case':case,'overrides':[{'address':0x02005674,'before':old_level,'after':77}],'progress_getter':getter,'selected':picker_results,'level_after':m.u16[0x02005674],'completion_flag':m.u32[0x0201017C],'formats':formats,'reads':check.reads,'native_picker_reads':native,'glyph_checks':check.glyph_checks,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native well entry and progress-getter return; original number picker/level output/flag, cancellation and both bounds through ordinary buttons. Five progress values include10 and255 clamp; original88px geometry, proportional font,128-byte formatter/guards/ABI and unchanged items/gold/save. Ordinary unlocking and actual dungeon entry remain separate.'},indent=2)+'\n');print('Well picker:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

