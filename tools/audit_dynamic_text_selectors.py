"""Byte-checked dispositions for computed selectors missed by the local scan.

This proves the listed bindings and the direct-call damage selector domain. It
does not infer whole-game reachability or exclude unknown indirect callers.
"""
import argparse
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import BASE, direct_calls
from tools.audit_source_readers import inserted_resources
from tools.extract_monsters import RESOURCE, DEFINITIONS, COUNT
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require


def run(source, output):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'],'Selector audit ROM differs')
    english = {r['offset']+BASE:r for r in inserted_resources(build)}
    checked = []

    def code(at, raw):
        expected = bytes.fromhex(raw)
        require(original[at:at+len(expected)] == compiled[at:at+len(expected)] == expected,
                'Selector instructions differ: '+hex(at))
        checked.append(dict(start=BASE+at,end_exclusive=BASE+at+len(expected),raw_hex=raw))

    def binding(table, index):
        pointer = struct.unpack_from('<I',compiled,table-BASE+4*index)[0]
        row = english.get(pointer)
        require(row is not None,'Computed selector is not a reviewed English resource')
        raw = bytes.fromhex(row['encoded_hex'])
        require(compiled[pointer-BASE:pointer-BASE+len(raw)] == raw,'Selected English bytes differ')
        return dict(index=index,pointer=pointer,id=row['id'],english=row['english'])

    # The damage wrapper's incoming r3 is saved before calls clobber registers.
    calls = direct_calls(original,BASE+0xCD38)
    selectors = {0xCBC2:0x89,0xCCC0:0x67,0xCCE6:0,0xCD08:0,0xCD2C:0}
    require(calls == [BASE+a for a in selectors],'Damage direct-call domain changed')
    for call,index in selectors.items(): code(call-2,struct.pack('<H',0x2300|index).hex())
    code(0xCD4C,'9693')
    code(0xCEC4,'2249969da8004018016847aa07a83b1cf4f770f8')
    code(0xCEEC,'969b002b03d007a8002108f0c9fc')
    table = struct.unpack_from('<I',compiled,0xCF50)[0]
    require(struct.unpack_from('<I',original,0xCF50)[0] == BASE+0x140D68 and
            table == BASE+build['shield_reflection']['table_offset'],
            'Damage private-table literal differs')
    damage = dict(format_call=BASE+0xCED4,queue_call=BASE+0xCEF6,
        direct_call_selectors=[dict(call=BASE+c,index=i) for c,i in selectors.items()],
        bindings=[binding(table,i) for i in (0x67,0x89)],
        zero_selector='Intermediate formatting occurs, but the byte-checked branch skips the queue when saved r3 is zero.')

    code(0x25834,'2649a000401805680020e4f745f9041ce9f74cff40a9e9f751fb031c6846291c221cdbf7affb')
    use_table = struct.unpack_from('<I',compiled,0x258D0)[0]
    use = dict(format_call=BASE+0x25856,original_queue_call=BASE+0x2585E,literal=BASE+0x258D0,
               bindings=[binding(use_table,i) for i in range(5)],
               scope='Five owned item-use category formats. The original queue call has been replaced by the existing item-use helper; native item-use checks cover that hook and type decoding.')
    code(0x282D0,'3848e8235b00c018016840464a46d8f76bfe40460121')
    item_table = struct.unpack_from('<I',compiled,0x283B4)[0]
    item = dict(format_call=BASE+0x282DE,queue_call=BASE+0x282E6,literal=BASE+0x283B4,
                bindings=[binding(item_table,0x1D0//4)])

    # Equipped-item curse messages retain source pointers intentionally: the
    # queue's closed mapping translates them before drawing. Resolve that final
    # consumer instead of calling a Japanese intermediate pointer a failure.
    curse_calls = {0x2B994:0x99,0x2B9A0:0x9A,0x2B9AC:0x9B}
    require(direct_calls(original,BASE+0x2B89C) == [BASE+c for c in curse_calls],
            'Equipped curse direct-call domain changed')
    notices = {r['source']['offset']+BASE:r for r in build['combat']['queue_notices']['entries']}
    curse_table = struct.unpack_from('<I',compiled,0x2B914)[0]
    mapping_at = build['combat']['queue_notices']['mapping_offset']
    mapping = dict(struct.iter_unpack('<II',compiled[mapping_at:mapping_at+8*len(notices)]))
    curse = []
    code(0x2B8F2,'084942469000401800680021e9f7c5ff')
    for call,index in curse_calls.items():
        code(call-2,struct.pack('<H',0x2100|index).hex())
        pointer = struct.unpack_from('<I',compiled,curse_table-BASE+4*index)[0]
        row = notices[pointer]
        require(mapping[pointer] == BASE+row['offset'] and
                compiled[row['offset']:row['offset']+len(bytes.fromhex(row['encoded_hex']))].hex() == row['encoded_hex'],
                'Computed curse queue mapping differs')
        curse.append(dict(call=BASE+call,index=index,source_pointer=pointer,
                          queue_pointer=mapping[pointer],id=row['id'],english=row['english']))

    # Announcement and projectile selectors coexist in the same original record.
    data,_ = decompress(original,RESOURCE)
    projectile = []
    table = struct.unpack_from('<I',compiled,0x2AC2C)[0]
    require(table == struct.unpack_from('<I',compiled,0x2AA54)[0] ==
            BASE+build['monster_announcements']['table_offset'],'Announcement readers diverged')
    for ident in range(COUNT):
        announcement = struct.unpack_from('<h',data,DEFINITIONS+28*ident+20)[0]
        projectile_id = data[DEFINITIONS+28*ident+22]
        if projectile_id:
            projectile.append(dict(actor_id=ident,projectile_id=projectile_id,selector=announcement,
                binding=binding(table,announcement) if announcement else None,
                disposition='English announcement' if announcement else 'Native zero-selector branch skips announcement'))
    require([r['actor_id'] for r in projectile if r['selector']] == [84,85,121,122],
            'Projectile announcement actor domain differs')
    code(0x17BA6,'1448ad002d18296802a845f0d0f9206800210122eaf731fc206802a90022')
    category_table = struct.unpack_from('<I',compiled,0x17BF8)[0]
    require(category_table == struct.unpack_from('<I',compiled,0x17E68)[0],
            'Empty-ability and ordinary category Info tables diverged')
    empty_ability = dict(copy_call=BASE+0x17BB0,literal=BASE+0x17BF8,
                         bindings=[binding(category_table,i) for i in (3,6)])
    name_copies = []
    for at,raw in ((0xCE94,'fcf71afe011c201c50f05af8'),(0xCF92,'fcf79bfd011c201c4ff0dbff'),
                   (0xD706,'fcf7e1f9011c201c4ff021fc'),(0x2D51C,'dcf7d6fa011c301c2ff016fd'),
                   (0x392B0,'d0f70cfc011c281c23f04cfe'),(0x3997C,'d0f7a6f8011c381c23f0e6fa')):
        code(at,raw)
        name_copies.append(dict(getter_call=BASE+at,copy_call=BASE+at+8,
            producer=BASE+0x9ACC,scope='Copies the actor-name getter result; no independent sentence selector.'))
    # Follow the conditional queue wrapper's sole original direct caller.
    require(direct_calls(original,BASE+0x15870)==[BASE+0x97A0], 'Conditional queue caller domain changed')
    code(0x15870,'00b5021c04480078002802d1101c00f005f801bc0047')
    code(0x9786,'54ac1e488046e220400040440168201c0a22f7f70efc201c00210cf066f8')
    forwarded = dict(call=BASE+0x1587E,producer_call=BASE+0x9798,
        binding=binding(struct.unpack_from('<I',compiled,0x9804)[0],0x1C4//4))
    bypassed = []
    for at,key,interior in ((0x50BC4,'village_prose',0x50BFE),(0x50C14,'well_level',0x50C30)):
        require(compiled[at:at+4]==bytes.fromhex('004b1847') and
                struct.unpack_from('<I',compiled,at+4)[0]==BASE+build[key]['helper_offset']+1,
                'Owned entry trampoline differs')
        bypassed.append(dict(entry=BASE+at,old_interior_call=BASE+interior,
                              target=BASE+build[key]['helper_offset'],scope='Normal entry executes the owned replacement.'))
    require(compiled[0x2585A:0x25860]==bytes.fromhex('014b1847c046') and
            struct.unpack_from('<I',compiled,0x25860)[0]==BASE+build['item_use']['helper_offset']+1,
            'Item-use hook differs')
    bypassed.append(dict(entry=BASE+0x2585A,old_interior_call=BASE+0x2585E,
                         target=BASE+build['item_use']['helper_offset'],scope='Old queue instruction has been overwritten by the hook.'))
    report = dict(rom_sha256=digest(compiled),source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()),checked_code=checked,
        damage=damage,item_use=use,item_result=item,equipped_curse=curse,projectile_species=projectile,
        empty_ability_info=empty_ability,actor_name_copies=name_copies,conditional_queue=forwarded,bypassed_calls=bypassed,
        scope=__doc__,passed=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Computed text selectors: all listed bindings pass')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/english/dynamic-text-selectors.json')
    args = parser.parse_args()
    run(args.source,args.output)
