"""Owned acid and rust consumers, using the shared item-format layout compiler."""
from tools.rom import ROOT
from tools.inventory_action_text import add_reviewed_actions
CATALOG=ROOT/'translations/rust-review.json'
OWNERS={0x279C8:(0x2F4,0x2EC,0x300),0x10F68:(0x288,),0x10FAC:(0x8E4,),
        0x10FFC:(0x43C,),0x11018:(0x304,),0x11038:(0x27C,),0x1106C:(0x280,),
        0x11080:(0x8E8,),0x110A8:(0x304,),0x110C8:(0x27C,),0x110F8:(0x284,)}


def add_rust(build):
    result=add_reviewed_actions(build,CATALOG,OWNERS,'rust-text')
    # The reusable compiler's 192-byte cap is stricter than this actual native
    # 256-byte output. Preserve both facts instead of misreporting its frame.
    for row in result['entries']:
        row['compile_budget_bytes']=row['capacity']
        row['capacity']=256 if row['table_offset']==0x43C else None
        row['direct_rom_stream']=row['table_offset']!=0x43C
    result.update(output_capacity=256,item_capacity=64,shield_frame_bytes=320)
    return result
