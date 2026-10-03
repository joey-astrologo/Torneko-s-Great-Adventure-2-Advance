"""Ordinary later quest inputs with an independent, unfiltered glyph audit."""
import json

import mgba.log

from tools.audit_dungeon_screens import AuditedSession
from tools.emulator import Debugger
from tools.holy_flame_playtest import items, use
from tools.mansion_playtest import direction, path_to, walk_to_stairs
from tools.name_entry_playtest import ACTORS, MAP, nearby_monsters, narrow_passage, position, stairs_path
from tools.research_mansion import status
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit
from tools.trace_mansion import complete_quest, family_branch, finish
from tools.verify_mansion import QuestTrace

OUT = ROOT/'build/localization-closure/later-quest-retry'


def walk_castle(g, goal=None):
    """Fight, heal and use naturally acquired items through ordinary menus."""
    turns = []
    for turn in range(900):
        path = stairs_path(g) if goal is None else path_to(g, goal)
        if not path:
            return turns
        m = g.core.memory
        player = m.u32[ACTORS]
        hp, maximum = m.u16[player+0x84], m.u16[player+0x86]
        enemies, before = nearby_monsters(g), position(g)
        if hp < maximum//2 and any(i == 169 for _,i,_ in items(g)):
            use(g, 169, 13);action = 'drink-Medicinal-herb'
        elif enemies:
            enemy = min(enemies, key=lambda e:e['hp'])
            if (enemy['hp'] >= 10 and (len(enemies) > 1 or hp < 15)
                    and any(i == 51 and charge > 0 for _,i,charge in items(g))):
                g.press(direction(enemy['position'][0]-before[0], enemy['position'][1]-before[1]), wait=30)
                use(g, 51, 10);action = 'swing-Lightning-Staff'
            else:
                g.press('A', wait=90);action = 'attack'
        elif (hp < maximum-1 and not nearby_monsters(g,3)) or (nearby_monsters(g,5) and narrow_passage(g)):
            g.press('A', wait=90);action = 'wait-heal-or-lure'
        else:
            target = path[0]
            action = direction(target[0]-before[0], target[1]-before[1])
            g.press(action, wait=90)
            if position(g) == before:
                g.press('A', wait=90)
        turns.append(dict(turn=turn, before=before, after=position(g), action=action, hp_before=hp,
                          hp_after=m.u16[player+0x84], enemies=enemies, inventory=items(g)))
        if not m.u16[player+0x84]:
            (g.output/'failed-walk.json').write_text(json.dumps(turns,indent=2)+'\n')
            raise ValueError('Castle route defeated')
    raise ValueError('Castle route turn limit')


def run():
    mgba.log.silence()
    rom = (ROOT/'build/english/torneko-2-english.gba').read_bytes()
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Later quest build identity differs')
    original_hash = digest(load_base())
    save_path = default_rom().with_suffix('.sav')
    save_hash = digest(save_path.read_bytes())
    battery = (ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
    recipe = json.loads((ROOT/'config/routes/storage-japanese.json').read_text())
    routes, error = [], None
    with AuditedSession(rom, OUT, initial_save=battery) as g:
        g.images = []
        audit = ScreenTextAudit(g)

        def observe(c):
            def callback(event):
                audit.callback(event)
                if event['address'] in c.ADDRESSES:
                    c.callback(event)
            return callback

        def attach(d, c):
            for address in sorted(set(audit.ADDRESSES+c.ADDRESSES)):
                d.breakpoint(address)

        try:
            c = QuestTrace(g, 'mansion-completion', build, save_fixture=False)
            with Debugger(g, observe(c), max_events=500000) as d:
                attach(d, c)
                g.frames(600)
                g.audit = audit
                g.capture('cold-start')
                g.press('START', wait=180)
                g.frames(204)
                finish(g, c, 'rom.0006afe0', 'floor-six-voice')
                g.press('A', wait=120)
                require(g.core.memory.u16[0x02005674] == 6, 'Mansion did not resume on 6F')
                targets = [(x,y+1) for x in range(56) for y in range(31)
                           if g.core.memory.u32[MAP+(x*32+y)*28+20] & 0x800000]
                require(len(targets) == 1, 'Mansion room marker differs')
                walk_to_stairs(g, targets[0])
                complete_quest(g, c)
            routes.append({'phase':c.route, 'completed':c.completed, 'input_end':len(g.inputs)})
            c = QuestTrace(g, 'family-and-bank-opening', build, save_fixture=False)
            c.choice_active = True
            with Debugger(g, observe(c), max_events=500000) as d:
                attach(d, c)
                family_branch(g, c, (1,1))
            routes.append({'phase':c.route, 'completed':c.completed, 'input_end':len(g.inputs)})
            c = QuestTrace(g, 'holy-flame-quest', build, save_fixture=False)
            with Debugger(g, observe(c), max_events=1500000) as d:
                attach(d, c)
                for action in recipe['inputs'][:22]:
                    g.press(action['key'], hold=action['hold'], wait=action['released'])
                finish(g, c, 'event-bank-1.6a74', 'accepted')
                g.press('A', wait=120)
                g.snapshot().save(OUT/'accepted')
                for action in recipe['inputs'][42:60]:
                    g.press(action['key'], hold=action['hold'], wait=action['released'])
                require(g.core.memory.u16[0x02005674] == 1, 'Castle dungeon entry missing')
                for floor in range(1,7):
                    g.snapshot().save(OUT/f'castle-floor-{floor}')
                    print('Castle floor', floor, status(g), flush=True)
                    turns = walk_castle(g)
                    (OUT/f'castle-floor-{floor}-turns.json').write_text(json.dumps(turns,indent=2)+'\n')
                    g.press('A', wait=600)
                finish(g, c, 'rom.00061998', 'flame')
                g.snapshot().save(OUT/'holy-flame')
            routes.append({'phase':c.route, 'completed':c.completed, 'input_end':len(g.inputs)})
        except Exception as exc:
            error = repr(exc)
            if exc.__cause__:
                error += ': '+repr(exc.__cause__)
            print('Quest audit interrupted:', error, flush=True)
        g.capture('end')
        g.snapshot().save(OUT/'end')
        require(digest(load_base()) == original_hash and digest(save_path.read_bytes()) == save_hash,
                'Original ROM/save changed')
        try:
            final_status = status(g)
        except ValueError:
            final_status = {'player_actor_unavailable': True, 'frame': g.core.frame_counter}
        report = dict(rom_sha256=digest(rom), source_rom_sha256=original_hash,
                      source_save_sha256=save_hash, initial_battery_sha256=digest(battery),
                      routes=routes, inputs=g.inputs, images=g.images, error=error, status=final_status,
                      controlled_overrides=[], audit=audit.report(), original_files_unchanged=True,
                      scope='Ordinary input continuation from the earned Japanese mansion suspend on the current English ROM. '
                            'Navigation reads RAM but never writes it. Every observed shared glyph/reader is retained. '
                            'Coverage is bounded by the completed phases, not whole-game acceptance.')
        report['passed'] = not (error or audit.unclassified or audit.unreadable or audit.layout_violations)
        (OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print('Later quest:', report['passed'], error, 'unclassified',len(audit.unclassified),
              'layout',len(audit.layout_violations), flush=True)
    require(report['passed'], 'Later quest needs investigation; see report.json')
    return report


if __name__ == '__main__':
    run()
