"""Own the separate contained-item action producer and its unchanged geometry."""
import struct
from tools.rom import require

STACK=[(0x194C8,'a0b0','d0b0'),(0x19652,'10a8','40a8'),
       (0x1968E,'10a8','40a8'),(0x19696,'10a9','40a9'),(0x196E8,'20b0','50b0')]

def add_child_actions(build):
    table=next(r for r in build.allocations if r['id']=='action-label-table')
    require(table['end_exclusive']-table['start']==176,'Owned action copy size differs')
    for site,before,after in STACK:
        build.patch(f'child-action-stack-{site:x}',site,bytes.fromhex(before),bytes.fromhex(after),'child-actions')
    build.patch('child-action-table',0x19680,struct.pack('<I',0x08141904),
                struct.pack('<I',0x08000000+table['start']),'child-actions')
    for site,expected in ((0x196B2,'1820'),(0x196B6,'0522'),(0x196C2,'0421')):
        require(build.original[site:site+2]==bytes.fromhex(expected),'Child action geometry differs')
    return {'table_offset':table['start'],'consumer_entry':0x080194C0,'consumer_end':0x080196F4,
            'output_capacity':256,'scratch_capacity':64,'text_width':36,'outer_border_gap':8,
            'scope':'Separate contained-item action producer. Uses the reviewed private IDs1..43; unrelated original consumers and separate discard ID44 remain untouched.'}
