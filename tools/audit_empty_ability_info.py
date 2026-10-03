"""Native Info fallback for fused sword/shield records with no property bits.

Only existing inventory/type-known fields are controlled. Ordinary Info inputs,
original category selection, copying, drawing, cancellation and reopening run.
"""
import argparse
import json
from pathlib import Path
import struct

import mgba.log
from tools.audit_dungeon_screens import AuditedSession
from tools.audit_menu_layouts import parent_image
from tools.emulator import Debugger
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.service_fixtures import dungeon
from tools.verify_items import ItemChecks


def run(source, output, allow_findings=False):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Empty-property Info ROM differs')
    fixture = dungeon(rom,build)
    results = []
    for ident, category in ((1,6),(31,3)):
        with AuditedSession(rom,output/str(ident)) as g:
            g.restore(fixture)
            g.images = []
            audit = ScreenTextAudit(g)
            g.audit = audit
            checks = ItemChecks(g,build)
            m = g.core.memory
            changes, entries, returns, copies = [], [], [], []
            def write(address, data):
                changes.append(dict(address=address,before=bytes(m[address:address+len(data)]).hex(),after=data.hex()))
                for i,value in enumerate(data): m.u8[address+i] = value
            item = bytearray(120)
            struct.pack_into('<I',item,0,0xC8200000)
            item[5],item[8] = 1,bytes(m[0x020013D0:0x020014D0]).index(ident)
            write(0x0200DF28,item)
            at = 0x02003BAC+20*ident
            write(at,struct.pack('<I',m.u32[at]|0x40000000))
            inventory = bytes(m[0x0200DF28:0x0200E888])
            def callback(event):
                a,r = event['address'],event['registers']
                audit.callback(event)
                checks.callback(event)
                if a == 0x08017A4C:
                    entries.append(event|dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
                if a == 0x0805CF54 and r[14] == 0x08017BB5:
                    require(r[0] == r[13]+8, 'Fallback copy destination differs')
                    raw = bytes(m[r[1]:r[1]+256]).split(b'\0')[0]+b'\0'
                    copies.append(dict(source=r[1],destination=r[0],raw_hex=raw.hex(),category=category,
                                       guard=bytes(m[r[0]+256:r[0]+272]).hex()))
                if a == 0x08017BB4:
                    copy = copies[-1]
                    require(bytes(m[copy['destination']:copy['destination']+len(bytes.fromhex(copy['raw_hex']))]).hex()==copy['raw_hex'] and
                            bytes(m[copy['destination']+256:copy['destination']+272]).hex()==copy['guard'],
                            'Fallback copy bytes or output guard differ')
                if a == 0x08017EEC:
                    old = entries[-1]
                    require(r[4:12]==old['registers'][4:12] and r[13]==old['registers'][13] and
                            r[0]==old['registers'][14] and bytes(m[r[13]:r[13]+32]).hex()==old['guard'],
                            'Fallback Info return ABI differs')
                    returns.append(event)
            with Debugger(g,callback,max_events=400000) as debug:
                for address in set(audit.ADDRESSES)|set(checks.ADDRESSES)|{0x08017A4C,0x08017BB4,0x08017EEC}:
                    debug.breakpoint(address)
                g.press('B',hold=8,wait=90)
                g.press('A',wait=90)
                parent = parent_image(g)
                for cycle in range(3):
                    g.press('A',wait=60)
                    actions = [m.u16[0x0200CDD0+2*i]&127 for i in range(7)]
                    require(40 in actions,'Info action unavailable')
                    for _ in range(actions.index(40)): g.press('DOWN',wait=20)
                    g.press('A',wait=90)
                    if not allow_findings:
                        require(checks.completed(f'item.category.{category}'), 'English category pixels were not checked')
                    g.capture(f'info-{cycle}')
                    g.press('B',wait=90)
                    require(parent_image(g)==parent,'Info did not restore its inventory parent')
            require(len(entries)==len(returns)==len(copies)==3 and
                    inventory==bytes(m[0x0200DF28:0x0200E888]) and
                    g.snapshot().battery==fixture.battery,'Info fallback sequence or persistence differs')
            expected = next(r for r in build['items']['entries'] if r['id']==f'item.category.{category}')
            binding = all(c['source']==expected['offset']+0x08000000 and c['raw_hex']==expected['encoded_hex'] for c in copies)
            report = dict(item=ident,category=category,inputs=g.inputs,overrides=changes,copies=copies,
                          returns=returns,images=g.images,binding=binding,audit=audit.report(),
                          reads=checks.reads,glyph_checks=checks.glyph_checks)
            report['passed'] = binding and not any(report['audit'][k] for k in
                ('unclassified_glyphs','unreadable_streams','layout_violations'))
            (g.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            results.append(report)
            print('Empty-property Info:',ident,'PASS' if report['passed'] else 'FINDING',flush=True)
    report = dict(rom_sha256=digest(rom),tool_sha256=digest(Path(__file__).read_bytes()),
                  cases=results,passed=all(r['passed'] for r in results),scope=__doc__)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    require(allow_findings or report['passed'],'Empty-property Info has native findings')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/english/empty-ability-info-validation')
    parser.add_argument('--allow-findings',action='store_true')
    args = parser.parse_args()
    run(args.source,args.output,args.allow_findings)
