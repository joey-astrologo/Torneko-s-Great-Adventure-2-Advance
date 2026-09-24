"""Normal-button village renaming after a controlled owned-service entry."""
import argparse
import json
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.verify_mayor import OUT
from tools.dialogue_checks import TextChecks
from tools.verify_name_entry import EditorChecks
from tools.name_entry_route import NameEntryRoute,SELECTION
from tools.name_entry import STORED,HERO,indexed
from tools.verify_service_ui import materialize


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/mayor-validation'
    mgba.log.silence();rom=(ROOT/'build/english/torneko-2-english.gba' if cumulative else OUT/'game.gba').read_bytes();build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Mayor editor ROM differs')
    fixture=Snapshot.load(OUT/'native/entry');rows=build['mayor']['entries'];by_pointer={r['offset']+0x08000000:r for r in rows}
    results=[]
    for case in ('decline','cancel-editor','required','maximum','redo'):
        print('Mayor editor:',case,flush=True)
        with Session(rom,OUT/('editor-'+case)) as game:
            game.restore(fixture);m=game.core.memory;initial=[int(v)&0xffffffff for v in game.core.cpu.gprs]
            guard=bytes(m[initial[13]:initial[13]+32]);stored=bytes(m[STORED:STORED+16]);hero=bytes(m[HERO:HERO+17])
            adjacent=(bytes(m[STORED-2:STORED]),bytes(m[STORED+16:HERO]))
            ga=m.u32[0x02001624]+0x60;gold=m.u32[ga];inventory=bytes(m[0x0200DF28:0x0200DF28+2400])
            resources={p:r for p,r in by_pointer.items() if r['layout']['direct_rom_stream']}
            choice=next(r for r in build['dialogue']['entries'] if r['id']=='rom.0006309c');resources[choice['rom_offset']+0x08000000]=choice
            check=TextChecks(game,resources);editor=EditorChecks(game,rom,build);route=NameEntryRoute(game,build['name_entry']['keyboard_pages'])
            editor_addresses=(0x08019F68,0x08019F72,0x08001C14,0x0801567C,0x08015680)
            opened=[];returned=[];formats=[];pending=[];images=[]
            def capture(name):game.capture(name);images.append(name+'.png')
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x0801545C:
                    require(r[0]==4 and r[2]==7 and r[3]==11,'Mayor editor arguments differ');opened.append(e)
                if a==0x08000FB8 and r[1] in by_pointer:
                    row=by_pointer[r[1]];require(row['index'] in (206,210) and r[0]==r[13] and r[2]==r[13]+0x100,'Mayor native format fields differ')
                    expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                    require(len(expected)<=row['layout']['maximum_formatted_bytes']<=256,'Mayor native format exceeds bound')
                    pending.append((r[14]&~1,r,expected,bytes(m[r[13]+256:r[13]+276]),row))
                if a in (0x08020642,0x08020674):
                    require(len(pending)==1,'Unpaired mayor formatter');end,before,expected,g,row=pending.pop()
                    require(a==end and r[13]==before[13] and r[4:12]==before[4:12],'Mayor formatter ABI differs')
                    dest=before[0];require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+256:dest+276])==g,'Mayor formatter output/guard differs')
                    check.resources[dest]=row|{'encoded_hex':expected.hex()}
                    formats.append({'id':row['id'],'expected_hex':expected.hex(),'bytes':len(expected),'capacity':256})
                if a==0x0802068A:
                    require(r[13]==initial[13] and r[4:12]==initial[4:12] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Mayor editor caller ABI/guard differs');returned.append(e)
                if a in check.ADDRESSES:check.callback(e)
                if a in editor_addresses:editor.callback(e)
            def count(ident):return sum(r['id']==ident for r in check.reads)
            def reach(predicate,label):
                for _ in range(30):
                    game.frames(90)
                    if predicate() and not check.active:return
                    game.press('A',wait=0)
                raise ValueError('Mayor failed to reach '+label)
            with Debugger(game,cb,max_events=350000) as d:
                for a in set(check.ADDRESSES+editor_addresses+(0x0801545C,0x08000FB8,0x08020642,0x08020674,0x0802068A)):d.breakpoint(a)
                reach(lambda:count('mayor-099')==1,'greeting');capture('greeting')
                game.press('B' if case=='decline' else 'A',wait=90)
                if case!='decline':
                    reach(lambda:len(opened)==1,'editor');capture('editor-initial')
                    if case=='cancel-editor':
                        route.clear();capture('empty');game.press('B',wait=90)
                    else:
                        name='W'*7 if case=='maximum' else 'Torneko'
                        route.clear();route.enter(name);capture('entered');route.confirm()
                        reach(lambda:count('mayor-206')==1,'name confirmation');capture('confirmation')
                        game.press('B' if case=='redo' else 'A',wait=90)
                        if case=='redo':
                            reach(lambda:len(opened)==2,'reopened editor');capture('editor-reopened')
                            route.clear();route.enter('Newtown');capture('replacement');route.confirm()
                            reach(lambda:count('mayor-206')==2,'replacement confirmation');capture('replacement-confirmation');game.press('A',wait=90)
                for page in range(24):
                    game.frames(90);capture(f'final-{page}')
                    if returned:break
                    game.press('A',wait=0)
            expected=stored if case in ('decline','cancel-editor') else indexed('W'*7 if case=='maximum' else 'Newtown' if case=='redo' else 'Torneko')
            require(len(returned)==1 and not check.active and not pending and bytes(m[STORED:STORED+16])==expected,'Mayor editor result incomplete/different: '+repr((case,len(returned),check.active,len(pending),bytes(m[STORED:STORED+16]).hex(),expected.hex(),opened,[r['id'] for r in check.reads])))
            require(bytes(m[HERO:HERO+17])==hero and adjacent==(bytes(m[STORED-2:STORED]),bytes(m[STORED+16:HERO])),'Mayor editor changed adjacent/player name fields')
            require(bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and m.u32[ga]==gold and game.snapshot().battery==fixture.battery,'Mayor editor changed items/gold/battery')
            expected_copies=2 if case=='redo' else 0 if case in ('decline','cancel-editor') else 1
            require(editor.copy_checks==expected_copies and len(opened)==(0 if case=='decline' else 2 if case=='redo' else 1),'Mayor editor path coverage differs')
            require(check.completed('mayor-210' if expected_copies else 'mayor-207'),'Mayor outcome text missing')
            if case=='redo':require(check.completed('mayor-209'),'Mayor correction text missing')
            if expected_copies:game.snapshot().save(OUT/'native'/('renamed-'+case))
            results.append({'case':case,'name_before_hex':stored.hex(),'name_after_hex':expected.hex(),'editor_calls':opened,'formats':formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'editor_glyphs':sorted(editor.glyphs),'cursor_checks':editor.cursor_checks,'confirmation_guard_checks':editor.copy_checks,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'editor.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled mayor entry; native dialogue answers and keyboard buttons through consumer return. Decline, B on empty entry, Torneko, seven widest English letters, rejection/re-entry. Actual indexed name changes, complete wording, cursor/glyph pixels and copy/caller guards checked. Existing live player name, inventory/gold/battery preserved. Ordinary service availability and subsequent native save/cold reload remain separate.'},indent=2)+'\n')
    print('Mayor editor:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

