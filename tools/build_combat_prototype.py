"""Build an isolated combat research ROM without changing cumulative output."""
import json
from tools.rom import ROOT,load_base
from tools.rom_build import RomBuild
from tools.build_compact_font import add_font
from tools.monster_text import add_monsters
from tools.combat_text import add_combat
OUT=ROOT/'build/combat-prototype'
def run():
 b=RomBuild(load_base());add_font(b,compact_numbers=True);mon=add_monsters(b);combat=add_combat(b);rom,report=b.finish();OUT.mkdir(exist_ok=True)
 (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(report|{'monsters':mon,'combat':combat},indent=2)+'\n');print(report['output_sha256'])
if __name__=='__main__':run()
