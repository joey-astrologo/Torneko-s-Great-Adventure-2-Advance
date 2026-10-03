"""Cold English continuation of an ordinarily earned castle suspend save."""
import json

import mgba.log

from tools.audit_dungeon_screens import AuditedSession
from tools.audit_later_quest import walk_castle
from tools.emulator import Debugger
from tools.holy_flame_playtest import items
from tools.name_entry_playtest import MAP
from tools.research_mansion import status
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.trace_mansion import finish
from tools.town_playtest import position as town_position
from tools.verify_mansion import QuestTrace

OUT = ROOT/'build/localization-closure/castle-continuation'


def run():
    mgba.log.silence()
    source = ROOT/'build/english'
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    provenance_path = ROOT/'build/localization-closure/castle-earned-suspend/provenance.json'
    provenance = json.loads(provenance_path.read_text())
    battery = (provenance_path.parent/'suspended.sav').read_bytes()
    require(digest(rom) == build['output_sha256'] and digest(battery) == provenance['battery_sha256']
            and provenance['writes'] and not provenance['controlled_overrides'], 'Castle suspend provenance differs')
    error, walks = None, []
    with AuditedSession(rom,OUT,initial_save=battery) as g:
        g.images = []
        audit = ScreenTextAudit(g)
        c = QuestTrace(g,'castle-earned-suspend-continuation',build,save_fixture=False)

        def callback(event):
            audit.callback(event)
            if event['address'] in c.ADDRESSES:
                c.callback(event)

        try:
            with Debugger(g,callback,max_events=1500000) as d:
                for address in sorted(set(audit.ADDRESSES+c.ADDRESSES)):
                    d.breakpoint(address)
                g.frames(600);g.audit = audit
                g.press('START',wait=180);g.capture('preview')
                g.press('A',wait=600)
                for _ in range(5):
                    if any(g.core.memory.u32[MAP+i*28+20] & 0x20 for i in range(56*32)):
                        break
                    g.press('A',wait=600)
                print('Cold continuation',status(g),flush=True)
                require(g.core.memory.u16[0x02005674] == 6, 'Earned castle suspend did not resume on 6F')
                g.snapshot().save(OUT/'floor-six')
                m = g.core.memory
                floor_items = []
                for x in range(56):
                    for y in range(32):
                        pointer = m.u32[MAP+(x*32+y)*28+16]
                        if 0x02000000 <= pointer < 0x02040000-120 and m.u32[pointer] & 0x80000000:
                            ident = m.u8[0x020013D0+m.u8[pointer+8]]
                            floor_items.append(dict(position=(x,y),item_id=ident))
                print('Natural floor items',floor_items,flush=True)
                staff = next((x for x in floor_items if x['item_id'] == 51),None)
                if staff:
                    walks.append(dict(target=staff,turns=walk_castle(g,tuple(staff['position']))))
                walks.append(dict(target='stairs',turns=walk_castle(g)))
                g.press('A',wait=600)
                finish(g,c,'rom.00061998','sacred-flame')
                g.capture('sacred-flame')
                finish(g,c,'event-bank-1.6e07','blacksmith-repairs-lock')
                g.press('A',wait=240)
                g.snapshot().save(OUT/'repaired-lock')
                print('Lock repaired',status(g),flush=True)
                recipe = json.loads((ROOT/'config/routes/storage-japanese.json').read_text())
                for action in recipe['inputs'][486:491]:
                    g.press(action['key'],hold=action['hold'],wait=action['released'])
                finish(g,c,'event-bank-1.2f78','warehouse-opening')
                g.press('A',wait=600)
                finish(g,c,'event-bank-1.32ca','warehouse-directions')
                g.press('A',wait=600)
                g.capture('warehouse-opened');g.snapshot().save(OUT/'warehouse-opened')
                print('Warehouse opened',status(g),flush=True)
                require(c.choice_active,'Warehouse tips choice was not reached')
                g.press('A',wait=240)
                finish(g,c,'event-bank-1.1001','warehouse-tips')
                g.press('A',wait=240)
                if c.choice_active:
                    g.press('B',wait=240)
                for key,hold in (('RIGHT',16),('UP',56),('LEFT',16),('UP',8)):
                    g.press(key,hold=hold,wait=120)
                    print('Book approach',key,town_position(g),flush=True)
                g.press('A',wait=120);g.capture('first-storage-menu')
                require(any(r['text'].startswith('{pixel-x:060c}Store items') for r in audit.report()['reads']),
                        'First storage command menu not reached')
                before_items = items(g)
                require(before_items,'Earned inventory is empty')
                g.press('A',wait=120);g.press('R',wait=60);g.press('A',wait=120)
                require(len(items(g)) == len(before_items)-1,'First native storage deposit failed')
                g.capture('first-storage-deposit')
                g.press('A',wait=120);g.press('RIGHT',wait=30);g.press('A',wait=120);g.press('A',wait=120)
                require(sorted((i,n) for _,i,n in items(g)) == sorted((i,n) for _,i,n in before_items),
                        'First native storage withdrawal failed')
                g.capture('first-storage-withdrawal');g.snapshot().save(OUT/'first-storage-roundtrip')
        except Exception as exc:
            error = repr(exc)+((': '+repr(exc.__cause__)) if exc.__cause__ else '')
            print('Castle continuation interrupted:',error,flush=True)
        g.capture('end');g.snapshot().save(OUT/'end')
        report = dict(rom_sha256=digest(rom), initial_save_sha256=digest(battery),
                      initial_save_provenance=str(provenance_path.relative_to(ROOT)),
                      provenance_sha256=digest(provenance_path.read_bytes()),
                      inputs=g.inputs,controlled_overrides=[],completed=c.completed,
                      walks=walks,error=error,audit=audit.report(),images=g.images,
                      status=status(g),scope=__doc__+' Original Japanese gameplay earned the suspend. '
                      'The English ROM cold-loads the native battery and uses ordinary inputs, with read-only navigation decisions. '
                      'This is not an uninterrupted English quest from its beginning.')
        report['passed'] = not (error or audit.unclassified or audit.unreadable or audit.layout_violations)
        (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('Castle continuation',report['passed'],'unclassified',len(audit.unclassified),
              'layout',len(audit.layout_violations),flush=True)
    require(report['passed'],'Castle continuation needs investigation')
    return report


if __name__ == '__main__':
    run()
