"""One-line player-status candidate exercised by native Drink actions."""
import argparse, json, struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Snapshot, Debugger
from tools.player_status_text import add_player_status
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize
from tools.verify_combat_prototype import CombatCheck
from tools.verify_mansion import QuestTrace, attach
from tools.trace_mansion import finish
from tools.holy_flame_playtest import items

OUT = ROOT / 'build/player-status-prototype'

def candidate():
    import tools.build_english as english
    rom, build = english.build_rom()
    build['scope'] = 'Isolated player-status prototype added to current English resources; not cumulative acceptance.'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build, indent=2)+'\n')
    return rom, build

def ready(rom, build):
    path=OUT/'native/ready'
    if path.with_suffix('.json').exists():
        snapshot=Snapshot.load(path)
        if snapshot.rom_sha256==digest(rom): return snapshot
    battery=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
    # Cumulative consumers share exactly the same ordinary-input resume route.
    # On2255 its state/save/keys were byte-identical to the service fixture.
    # Keep per-family evidence, but avoid replaying that prefix for every probe.
    cumulative = ROOT / 'build/english/build.json'
    if cumulative.exists() and json.loads(cumulative.read_text())['output_sha256'] == digest(rom):
        from tools.service_fixtures import dungeon
        snapshot = dungeon(rom, build)
        provenance_path = ROOT / 'build/services/current-dungeon/inputs.json'
        provenance = json.loads(provenance_path.read_text())
        require(snapshot.rom_sha256 == provenance['rom_sha256'] == digest(rom) and
                provenance['source_battery_sha256'] == digest(battery), 'Shared native fixture provenance differs')
        snapshot.save(path)
        (OUT/'native/provenance.json').write_text(json.dumps({
            'rom_sha256': digest(rom), 'save_sha256': digest(battery),
            'inputs': provenance['inputs'], 'controlled_overrides': [],
            'shared_native_fixture': 'build/services/current-dungeon/ready',
            'shared_provenance_sha256': digest(provenance_path.read_bytes()),
            'state_sha256': digest(snapshot.state), 'battery_sha256': digest(snapshot.battery)
        }, indent=2)+'\n')
        return snapshot
    with Session(rom, OUT/'native', initial_save=battery) as game:
        check=QuestTrace(game,'player-status-checkpoint',build,save_fixture=False)
        with Debugger(game,check.callback,max_events=30000) as debug:
            attach(debug,check);game.frames(600);game.press('START',wait=180);game.frames(204)
            finish(game,check,'rom.0006afe0','resume');game.press('A',wait=120)
            require(game.core.memory.u16[0x02005674]==6,'Player-status checkpoint did not reach 6F')
        snapshot=game.snapshot();snapshot.save(path)
        (OUT/'native/provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'save_sha256':digest(battery),'inputs':game.inputs,'controlled_overrides':[]},indent=2)+'\n')
        return snapshot

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/player-status-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative player-status ROM differs')
    else:rom,build=candidate()
    fixture=ready(rom,build)
    targets={r['offset']+0x08000000:r for r in build['player_status']['entries']}
    results=[]
    for kind, ident, expected_id in [('hallucination',176,'player-status.0e4'),('blind',173,'player-status.0e8'),('blind-refusal',173,'player-status.4a0')]:
        for label,name in player_layout_cases():
            case=kind+'-'+label
            print('Player status',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory
                for i,v in enumerate(name.ljust(16,b'\0')):m.u8[HERO+i]=v
                address=0x0200DF28;old=bytes(m[address:address+120]);replacement=bytearray(old)
                mapping=bytes(m[0x020013D0:0x020014D0]);struct.pack_into('<I',replacement,0,0xC8000000)
                replacement[8]=mapping.index(ident);replacement[4]=replacement[5]=1;replacement[24:]=bytes(96)
                for i,v in enumerate(replacement):m.u8[address+i]=v
                type_address=0x02003BAC+ident*20;type_before=m.u32[type_address];m.u32[type_address]=type_before|0x40000000
                status_override=[];checks=[];formats=[];pending=None
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x0800B764 and kind=='blind-refusal':
                        actor=m.u32[0x02001624]
                        status_override.append({'address':actor+0xB2,'before':m.u8[actor+0xB2],'after':1})
                        m.u8[actor+0xB2]=1
                    if a==0x08000FB8 and r[1] in targets:
                        row=targets[r[1]];require(row['id']==expected_id,'Unexpected status branch')
                        require(r[0]==r[13] and r[14] in (0x0800B74D,0x0800B7C9,0x0800B7A1),'Unowned player-status formatter')
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                        require(len(expected)<=row['maximum_bytes'],'Player-status expansion exceeds bound')
                        pending=(r[14]&~1,r[0],expected,bytes(m[r[0]+256:r[0]+272]),r[4:12],r[13])
                        queue_return=0x0800B759 if kind=='hallucination' else 0x0800B7D1
                        checks.append(CombatCheck(game,expected[:-1],queue_return,256,pending[3]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp=pending
                        require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+256:dest+272])==guard,'Status formatter bytes/guard differ')
                        require(r[4:12]==regs and r[13]==sp,'Status formatter ABI differs')
                        formats.append({'id':expected_id,'bytes':len(expected),'expected_hex':expected.hex(),'capacity':256,'abi_and_guard_preserved':True});pending=None
                    for check in checks:check.callback(event)
                with Debugger(game,callback,max_events=50000) as debug:
                    for a in (0x0800B764,0x08000FB8,0x0800B748,0x0800B74C,0x0800B7C8,0x0800B7A0,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x0800B758,0x0800B7D0):debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                    actions=[]
                    for i in range(7):
                        action=m.u16[0x0200CDD0+i*2]
                        if not action:break
                        actions.append(action)
                    require(13 in actions,'Native Drink command absent')
                    for _ in range(actions.index(13)):game.press('DOWN',wait=20)
                    game.press('A',wait=0)
                    for _ in range(180):
                        if checks and checks[0].complete and checks[0].returned: break
                        game.frames(1)
                    game.capture('effect')
                require(len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and checks[0].queued['one_line'],'Status did not finish on one line')
                require(game.snapshot().battery==fixture.battery,'Status probe wrote save')
                results.append({'case':case,'player_hex':name.hex(),'controlled_item':{'address':address,'before':old.hex(),'after':replacement.hex()},
                                'controlled_type':{'address':type_address,'before':type_before,'after':type_before|0x40000000},'controlled_status':status_override,
                                'formats':formats,'queue':checks[0].queued,'glyphs':len(checks[0].draws),'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':('Cumulative build. ' if cumulative else 'Isolated candidate. ')+'Native Drink/effect/queue execution with explicitly controlled inventory, identification, player names and refusal status byte. Three owned player-only messages fit one line at maximum name width. Exact buffer, ABI, pixels and queue checks; no natural acquisition or blanket shared-message translation claimed.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Player statuses:',len(results),'one-line native cases')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
