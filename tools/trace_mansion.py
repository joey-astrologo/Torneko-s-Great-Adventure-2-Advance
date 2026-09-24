"""Reproduce the mansion quest and both family choices with ordinary inputs."""

import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.name_entry_playtest import ACTORS, position as dungeon_position
from tools.research_mansion import Discovery
from tools.rom import ROOT, digest, load_base, require
from tools.town_playtest import position

OUTPUT = ROOT / 'build/mansion/native'
FIXTURE = ROOT / 'build/english/books-validation/japanese/mansion-departure'
RECIPE = ROOT / 'config/routes/mansion-japanese.json'


class SourceTrace(Discovery):
    ADDRESSES = Discovery.ADDRESSES + (0x08002284, 0x08015CE8, 0x08015E28)

    def __init__(self, game, route='mansion'):
        super().__init__(game, verbose=False)
        self.route = route
        self.active = None
        self.depth = 0
        self.reads, self.completed, self.choices = [], [], []
        self.choice_active = False

    def callback(self, event):
        a, r = event['address'], event['registers']
        if a == 0x08015CE8:
            self.choice_active = True
        elif a == 0x08015E28:
            self.choice_active = False
            self.choices.append(r[0])
        elif a == 0x080021B4:
            if self.active is not None:
                self.depth += 1
                return
            row = super().callback(event)
            self.active = {'id': row['id'], 'source': r[1], 'start_frame': event['frame']}
        elif a == 0x08002284 and self.active is not None:
            if self.depth:
                self.depth -= 1
            else:
                self.reads.append(self.active | {'end_frame': event['frame']})
                self.completed.append(self.active['id'])
                self.active = None
        elif a == 0x0801588C:
            super().callback(event)


def advance(game, observer, predicate, label, limit=100):
    for i in range(limit):
        game.capture(f'{label}-{i:03}')
        if predicate():
            return
        game.press('A', wait=240)
    raise ValueError('Mansion dialogue exceeded page budget: ' + label)


def finish(game, observer, ident, label):
    advance(game, observer, lambda: ident in observer.completed and observer.active is None, label)


def complete_quest(game, observer):
    game.capture('quest-room-entrance')
    game.snapshot().save(game.output / 'quest-room-entrance')
    game.press('UP', wait=240)
    finish(game, observer, 'rom.00061a08', 'imp-introduction')
    game.press('A', wait=120)
    game.snapshot().save(game.output / 'battle-start')
    combat = []
    for turn in range(20):
        m = game.core.memory
        player, imp = m.u32[ACTORS], m.u32[ACTORS+4]
        if not (m.u32[imp+8] & 0x80000000) or m.u16[imp+0x84] == 0:
            break
        before = m.u16[player+0x84], m.u16[imp+0x84]
        game.press('A', wait=240)
        combat.append({'turn':turn, 'before_hp':before,
                       'after_hp':[m.u16[player+0x84],m.u16[imp+0x84]]})
        require(m.u16[player+0x84] > 0, 'Player defeated in quest battle')
        game.capture(f'imp-battle-{turn:02}')
    else:
        raise ValueError('Imp battle did not finish')
    game.capture('safe-dropped')
    game.snapshot().save(game.output / 'safe-dropped')
    game.press('UP', wait=240)
    finish(game, observer, 'rom.00061978', 'safe-recovered')
    game.snapshot().save(game.output / 'safe-recovered')
    game.press('A', wait=600)
    finish(game, observer, 'event-bank-1.47b9', 'banker-thanks')
    game.press('A', wait=600)
    advance(game, observer, lambda: observer.choice_active, 'family-question')
    require('event-bank-1.1745' in observer.completed, 'Family question not reached')
    game.snapshot().save(game.output / 'family-question')
    return combat


def family_branch(game, observer, answers):
    for i, answer in enumerate(answers):
        require(observer.choice_active or i == 0, 'Family choice is not active')
        if not answer:
            game.press('RIGHT', wait=30)
        game.press('A', wait=240)
        if i == 0:
            advance(game, observer, lambda: observer.choice_active, 'old-man-question')
    finish(game, observer, 'event-bank-1.1803', 'family-supper')
    game.press('A', wait=600)
    advance(game, observer, lambda: observer.choice_active, 'bank-permission')
    require('event-bank-1.1e97' in observer.completed, 'Bank opening request missing')
    if answers == (1,1):
        game.press('RIGHT',wait=30)
        game.press('A',wait=240)
        finish(game,observer,'event-bank-1.202d','bank-refusal')
        advance(game,observer,lambda:observer.choice_active,'bank-request-again')
    game.press('A',wait=240)
    finish(game,observer,'event-bank-1.2081','bank-opening')
    game.press('A',wait=240)
    finish(game,observer,'town-common.04b0','bank-greeting')
    game.press('A',wait=120)
    game.capture('bank-service-menu-deferred')
    game.press('B',wait=240)
    finish(game,observer,'town-common.0527','bank-farewell')
    game.press('A',wait=240)
    finish(game,observer,'event-bank-1.1249','tipper-leaves')
    game.press('A',wait=240)
    before = position(game)
    for key in ('DOWN','LEFT','RIGHT','UP'):
        game.press(key, hold=8, wait=30)
        if position(game) != before:
            break
    require(position(game) != before, 'Town controls did not resume after quest')
    game.capture('morning-controls')
    game.snapshot().save(game.output / 'morning')
    require(observer.choices[:2] == list(answers), 'Family branch result changed')
    require(observer.choices[2:] == ([0,1] if answers == (1,1) else [1]),
            'Bank refusal/reconsideration result changed')


def run(output=OUTPUT):
    mgba.log.silence()
    original = load_base()
    recipe = json.loads(RECIPE.read_text())
    require(recipe['source_rom_sha256'] == digest(original), 'Mansion recipe base differs')
    all_entries, routes = [], []
    with Session(original, output) as game:
        game.restore(Snapshot.load(FIXTURE))
        observer = SourceTrace(game)
        with Debugger(game, observer.callback, max_events=100000) as debug:
            for address in observer.ADDRESSES:
                debug.breakpoint(address)
            for i, action in enumerate(recipe['inputs']):
                if 'frames' in action:
                    game.frames(action['frames'])
                else:
                    game.press(action.get('keys',action.get('key')),hold=action['hold'],wait=action['released'])
                if i + 1 == recipe.get('floor_five_checkpoint'):
                    game.snapshot().save(output / 'floor-five-stairs')
            require(game.core.memory.u16[0x02005674] == 6 and dungeon_position(game) == (6,7),
                    'Recorded mansion route did not reach quest room')
            combat = complete_quest(game, observer)
        all_entries += observer.entries
        routes.append({'route':'recovery', 'reads':observer.reads,'unknown':observer.unknown,
                       'combat':combat, 'inputs':list(game.inputs)})
        family = Snapshot.load(output / 'family-question')
        for first, second in ((1,1),(1,0),(0,1),(0,0)):
            name = f'family-{first}-{second}'
            game.output = output / name
            game.output.mkdir(parents=True,exist_ok=True)
            game.restore(family)
            start = len(game.inputs)-1
            observer = SourceTrace(game,name)
            observer.choice_active = True
            with Debugger(game,observer.callback,max_events=30000) as debug:
                for address in observer.ADDRESSES:
                    debug.breakpoint(address)
                family_branch(game,observer,(first,second))
            all_entries += observer.entries
            routes.append({'route':name,'reads':observer.reads,'choices':observer.choices,
                           'inputs':game.inputs[start:],'town_position':position(game)})
        game.output = output
        floor_five = Snapshot.load(output/'floor-five-stairs')
        game.restore(floor_five)
        start = len(game.inputs)-1
        save_calls = []
        with Debugger(game, lambda event: save_calls.append(event['frame'])) as debug:
            debug.breakpoint(0x08015354)
            game.press('DOWN',wait=90)
            game.press('DOWN',wait=90)
            game.press('A',wait=300)
            # This save already has an Adventure Log: accept overwrite, then
            # close completion/farewell pages before exporting the battery.
            for _ in range(3):
                game.press('A', wait=300)
        game.capture('suspended-on-five')
        battery = game.snapshot().battery
        require(save_calls and battery != floor_five.battery, 'Native dungeon suspend was not written')
        (output/'floor-five-native.sav').write_bytes(battery)
        suspend = {'save_sha256':digest(battery),'native_save_frames':save_calls,'inputs':game.inputs[start:]}
    require(game.disk_save == battery, 'Native suspend disk save differs')
    entries = list({e['id']:e for e in all_entries if e['japanese']}.values())
    report = {'passed':True,'source_rom_sha256':digest(original),'recipe_sha256':digest(RECIPE.read_bytes()),
              'entries':entries,'routes':routes,'suspend':suspend,
              'scope':'Original ROM, uninterrupted ordinary-input prefix and safe recovery; four family branch checkpoint replays. Native floor-five suspend retained for English continuation. No game-state writes.'}
    (output/'trace.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Japanese mansion:',len(entries),'sources;',len(routes),'routes')
    return report


if __name__ == '__main__':
    run()
