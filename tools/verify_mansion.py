"""Native English continuation of the mansion quest from a Japanese suspend save."""

import json

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.emulator import Debugger, Session, Snapshot
from tools.mansion_playtest import walk_to_stairs
from tools.name_entry import HERO
from tools.name_entry_playtest import MAP, position as dungeon_position
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.trace_mansion import complete_quest, family_branch, finish
from tools.town_playtest import position
from tools.verify_home_books import EnglishTrace

OUTPUT = ROOT / 'build/english/mansion-validation'
JAPANESE = ROOT / 'build/mansion/native'


class QuestTrace(EnglishTrace):
    ADDRESSES = TextChecks.ADDRESSES + (0x08015CE8, 0x08015E28,
                                      0x08002124, 0x0800212A, 0x08002138, 0x080022C4)

    def callback(self, event):
        a, r = event['address'], event['registers']
        if a == 0x080022C4:
            if r[1] == self.targets['rom.00061978'] and self.save_fixture:
                self.game.snapshot().save(self.game.output / 'acquisition-entry')
            return
        if a == 0x080021B4:
            if r[1] not in self.resources and self.active is None:
                return  # Untranslated combat/results/service UI is outside this batch.
        if a in (0x08002124, 0x0800212A, 0x08002138) and self.active is None:
            return
        super().callback(event)


def attach(debug, observer):
    for address in observer.ADDRESSES:
        debug.breakpoint(address)


def record(observer, game, inputs, **extra):
    return {'route':observer.route, 'reads':observer.reads, 'choices':observer.choices,
            'centers':observer.centers, 'native_glyph_checks':observer.glyph_checks,
            'inputs':inputs, **extra}


def name_probes(rom, build, output):
    snapshot = Snapshot.load(output / 'acquisition-entry')
    results = []
    with Session(rom, output / 'name-probes') as game:
        for label, name in player_layout_cases():
            game.restore(snapshot)
            m = game.core.memory
            guard = bytes(m[HERO-16:HERO]), bytes(m[HERO+16:HERO+32])
            for i, value in enumerate(name.ljust(16,b'\0')):
                m.u8[HERO+i] = value
            observer = QuestTrace(game,label,build,save_fixture=False)
            start = len(game.inputs)-1
            with Debugger(game,observer.callback,max_events=10000) as debug:
                attach(debug,observer)
                game.frames(240)
            require(observer.completed == ['rom.00061978'] and len(observer.centers) == 2,
                    'Controlled acquisition name display differs')
            require(guard == (bytes(m[HERO-16:HERO]), bytes(m[HERO+16:HERO+32])) and
                    snapshot.battery == game.snapshot().battery, 'Name probe changed guards or save')
            game.capture(label)
            results.append(record(observer,game,game.inputs[start:],name_hex=name.hex(),
                fixture_state_sha256=digest(snapshot.state),name_guards_and_battery_preserved=True))
    return results


def run():
    mgba.log.silence()
    original = load_base(); rom, build = build_rom()
    save_hash = digest(default_rom().with_suffix('.sav').read_bytes())
    battery = (JAPANESE/'floor-five-native.sav').read_bytes()
    routes = []
    with Session(rom,OUTPUT,initial_save=battery) as game:
        observer = QuestTrace(game,'cold-resume-recovery',build)
        with Debugger(game,observer.callback,max_events=150000) as debug:
            attach(debug,observer)
            game.frames(600)
            game.press('START',wait=180)
            game.frames(204)  # Recorded ordinary-input wait selects this regression layout.
            game.capture('cold-save-preview')
            finish(game,observer,'rom.0006afe0','floor-six-voice')
            game.press('A',wait=120)
            require(game.core.memory.u16[0x02005674] == 6, 'Cold suspend did not resume on 6F')
            game.capture('floor-six-resumed')
            targets = [(x,y+1) for x in range(56) for y in range(31)
                       if game.core.memory.u32[MAP+(x*32+y)*28+20] & 0x800000]
            require(len(targets) == 1, 'Special-room entrance marker is ambiguous')
            walk = walk_to_stairs(game,targets[0])
            combat = complete_quest(game,observer)
        routes.append(record(observer,game,list(game.inputs),walk=walk,combat=combat,
                             cold_save_sha256=digest(battery)))
        family = Snapshot.load(OUTPUT/'family-question')
        for answers in ((1,1),(1,0),(0,1),(0,0)):
            route = 'family-' + '-'.join(map(str,answers))
            game.output = OUTPUT/route; game.output.mkdir(parents=True,exist_ok=True)
            game.restore(family)
            start = len(game.inputs)-1
            observer = QuestTrace(game,route,build)
            observer.choice_active = True
            with Debugger(game,observer.callback,max_events=100000) as debug:
                attach(debug,observer)
                family_branch(game,observer,answers)
            routes.append(record(observer,game,game.inputs[start:],town_position=position(game)))
    probes = name_probes(rom,build,OUTPUT)
    observed = {r['id'] for route in routes for r in route['reads']}
    expected = {r['id'] for r in build['dialogue']['entries'] if r['batch'] == 'mansion-quest'}
    require(expected <= observed,'Missing native mansion sources: ' + repr(sorted(expected-observed)))
    require(digest(load_base()) == digest(original) and
            digest(default_rom().with_suffix('.sav').read_bytes()) == save_hash,'Original files changed')
    report = {'passed':True,'source_rom_sha256':digest(original),'output_rom_sha256':digest(rom),
        'source_save_sha256':save_hash,'original_files_unchanged':True,
        'native_japanese_suspend_sha256':digest(battery),'routes':routes,
        'controlled_name_layouts':probes,'inserted_mansion_resources_observed':len(expected),
        'scope':'English cold continuation from an ordinary-input Japanese floor-five suspend, through 6F voice, Imp battle, safe recovery, results, banker thanks and home; four native family/bank-opening branch checkpoint replays and cancellation of service menu. Three separate controlled acquisition name displays. This is not an uninterrupted English 1F-6F run. Combat messages, item names, transaction menu and other results UI are outside this verifier\'s scope.'}
    (OUTPUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('English mansion:',len(expected),'resources;',sum(r['native_glyph_checks'] for r in routes),'glyph checks;',len(probes),'name probes')
    return report


if __name__ == '__main__':
    run()
