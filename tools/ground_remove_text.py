"""Retain the original fragment meaning in the owned floor-Remove refusal."""
from tools.rom import ROOT
from tools.inventory_action_text import add_reviewed_actions
CATALOG=ROOT/'translations/ground-remove-review.json'
def add_ground_remove(build):
 return add_reviewed_actions(build,CATALOG,{0x24930:(0x90,)},'ground-remove')
