"""Private central pickup reads and the audited automatic-walk standing message."""
from tools.rom import ROOT
from tools.inventory_action_text import add_reviewed_actions

CATALOG=ROOT/'translations/pickup-review.json'
OWNERS={0x24B40:(0x150,),0x24B88:(0x1EC,0x37C),0x24C0C:(0x9C,),0x24CE8:(0x9C,),
        0x24D24:(0xA0,),0x24D38:(0x98,),0x24DE4:(0x9C,),0x24AC0:(0x37C,)}

def add_pickup(build):
    return add_reviewed_actions(build,CATALOG,OWNERS,'pickup-text')
