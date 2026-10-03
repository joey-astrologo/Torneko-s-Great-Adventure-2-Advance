"""Replay a recorded ordinary quest attempt, auditing every shared text glyph."""
import argparse
import json
from pathlib import Path

import mgba.log

from tools.audit_dungeon_screens import AuditedSession
from tools.emulator import Debugger
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit


def run(schedule, output):
    mgba.log.silence()
    prior = json.loads(schedule.read_text())
    rom = (ROOT/'build/english/torneko-2-english.gba').read_bytes()
    save_path = ROOT/'build/mansion/native/floor-five-native.sav'
    battery = save_path.read_bytes()
    require(digest(battery) == prior['initial_battery_sha256'], 'Replay initial save differs')
    with AuditedSession(rom,output,initial_save=battery) as g:
        g.images = []
        audit = ScreenTextAudit(g)
        with Debugger(g,audit.callback,max_events=1500000) as d:
            for address in audit.ADDRESSES:
                d.breakpoint(address)
            for i, action in enumerate(prior['inputs']):
                require(g.core.frame_counter == action['start_frame'], 'Replay input start differs')
                if 'frames' in action:
                    g.frames(action['frames'])
                else:
                    g.press(action.get('keys',action.get('key')),hold=action['hold'],wait=action['released'])
                require(g.core.frame_counter == action['end_frame'], 'Replay input end differs')
                g.audit = audit
            g.capture('recorded-attempt-end')
            # This quest returns a defeated player to castle 1F for a retry.
            for _ in range(40):
                player = g.core.memory.u32[0x02001624]
                if g.core.memory.u16[0x02005674] == 1 and g.core.memory.u16[player+0x84] > 0:
                    break
                g.press('A',wait=240)
            returned = g.core.memory.u16[0x02005674] == 1 and g.core.memory.u16[player+0x84] > 0
        g.capture('castle-retry');g.snapshot().save(output/'castle-retry')
        report = dict(rom_sha256=digest(rom), initial_battery_sha256=digest(battery),
                      schedule_path=str(schedule.relative_to(ROOT)),schedule_sha256=digest(schedule.read_bytes()),
                      inputs=g.inputs,controlled_overrides=[],audit=audit.report(),images=g.images,
                      recorded_route_error=prior['error'],castle_retry=returned,
                      scope='Exact recorded ordinary inputs through the mansion and castle attempt, followed by native defeat/results and castle 1F retry. '
                            'The defeat is the tested outcome; this does not claim castle quest completion.')
        report['passed'] = returned and not (audit.unclassified or audit.unreadable or audit.layout_violations)
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        require(digest(save_path.read_bytes()) == digest(battery),'Original replay save changed')
        print('Quest replay:',report['passed'],'glyphs',len(audit.glyphs),'unclassified',len(audit.unclassified),
              'layout',len(audit.layout_violations),flush=True)
        require(report['passed'],'Quest replay contains unclassified text/layout findings')
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,default=ROOT/'build/localization-closure/later-quest-retry/report.json')
    parser.add_argument('--output',type=Path,default=ROOT/'build/localization-closure/quest-replay')
    args = parser.parse_args()
    run(args.schedule.resolve(),args.output.resolve())
