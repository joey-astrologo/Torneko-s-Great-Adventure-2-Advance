"""Save a natively renamed village at the house book, then cold-load it."""
import argparse
import json
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.verify_mayor import OUT
from tools.name_entry import STORED,HERO,indexed
from tools.town_playtest import position
from tools.verify_name_entry import save_fields


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/mayor-validation'
    mgba.log.silence();rom=(ROOT/'build/english/torneko-2-english.gba' if cumulative else OUT/'game.gba').read_bytes();build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text());results=[]
    require(digest(rom)==build['output_sha256'],'Mayor persistence ROM differs')
    for case,name in (('required','Torneko'),('maximum','WWWWWWW'),('redo','Newtown')):
        print('Mayor persistence:',case,flush=True)
        fixture=Snapshot.load(OUT/'native'/('renamed-'+case));expected=indexed(name)
        with Session(rom,OUT/('save-'+case)) as game:
            game.restore(fixture);m=game.core.memory;hero=bytes(m[HERO:HERO+17]);frames=[];fields=[]
            require(bytes(m[STORED:STORED+16])==expected,'Renamed checkpoint differs')
            def cb(e):
                if e['address']==0x08015354:frames.append(e['frame'])
                if e['address']==0x08006C60:fields.append({'record':e['registers'][0]})
            with Debugger(game,cb,max_events=10000) as d:
                for a in (0x08015354,0x08006C60):d.breakpoint(a)
                for key,hold in [('DOWN',8),('LEFT',72),('UP',24),('UP',56),('RIGHT',32),('UP',24),('RIGHT',32),('UP',32),('LEFT',16),('UP',3)]:game.press(key,hold=hold,wait=120)
                require(position(game)==(288,224),'Mayor return route did not reach book: '+repr(position(game)))
                game.capture('book');game.press('A',wait=150)
                for _ in range(3):game.press('DOWN',wait=30)
                game.press('A',wait=180);game.press('A',wait=300)
                require(frames and fields,'Mayor native book save missing')
                battery=game.snapshot().battery;require(battery!=fixture.battery,'Mayor book save did not change battery');game.capture('saved')
                require(bytes(m[STORED:STORED+16])==expected and bytes(m[HERO:HERO+17])==hero,'Mayor save changed names')
            (OUT/(case+'-renamed.sav')).write_bytes(battery);save_inputs=game.inputs
        with Session(rom,OUT/('cold-'+case),initial_save=battery) as game:
            game.frames(600);game.press('START',wait=180);game.capture('preview');game.press('A',wait=300);m=game.core.memory
            require(position(game)==(288,224),'Renamed save did not cold resume at book')
            require(bytes(m[STORED:STORED+16])==expected and bytes(m[HERO:HERO+17])==hero,'Renamed/player names did not persist')
            game.capture('resumed');game.press('RIGHT',hold=16,wait=120);require(position(game)!=(288,224),'Renamed cold save did not allow movement');game.capture('moved')
            results.append({'case':case,'name':name,'indexed_hex':expected.hex(),'unchanged_player_hex':hero.hex(),'source_fixture':str(OUT/'native'/('renamed-'+case)),'source_battery_sha256':digest(fixture.battery),'saved_battery_sha256':digest(battery),'save_frames':frames,'record_entries':fields,'save_inputs':save_inputs,'cold_inputs':game.inputs,'images':{folder+'/'+p.name:digest(p.read_bytes()) for folder in ('save-'+case,'cold-'+case) for p in (OUT/folder).glob('*.png')}})
    (OUT/'persistence.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Starts after controlled mayor invocation plus normal-button name entry; follows ordinary movement to the house book, native save, fresh emulator cold reload and movement. Required/widest/revised English village names persist; separate player name remains intact. Ordinary mayor unlocking remains separate.'},indent=2)+'\n');print('Mayor persistence:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

