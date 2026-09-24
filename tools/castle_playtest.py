"""Read-only decisions for castle combat; all actions use native controls."""
from tools.name_entry_playtest import ACTORS,position,stairs_path,nearby_monsters,narrow_passage
from tools.mansion_playtest import direction
from tools.holy_flame_playtest import items,use
from tools.rom import require

def walk(game):
 turns=[];disabled=set();floor=game.core.memory.u16[0x02005674]
 for turn in range(1000):
  path=stairs_path(game)
  if not path:return turns
  m=game.core.memory;p=m.u32[ACTORS];hp=m.u16[p+0x84];before=position(game);enemies=nearby_monsters(game)
  if enemies:
   enemy=min(enemies,key=lambda e:(e['slot'] in disabled,e['hp']));game.press(direction(enemy['position'][0]-before[0],enemy['position'][1]-before[1]),wait=150)
   available=[i for _,i,charge in items(game) if charge>0 and i in (51,53,54,55)]
   if available and enemy['slot'] not in disabled:
    use(game,available[0],10);disabled.add(enemy['slot']);action='staff-'+str(available[0])
   elif enemy['slot'] in disabled and path[0] not in [e['position'] for e in enemies]:
    q=path[0];action=direction(q[0]-before[0],q[1]-before[1]);game.press(action,wait=150)
   else:game.press('A',wait=150);action='attack'
  elif hp<m.u16[p+0x86]-1 or (nearby_monsters(game,5) and narrow_passage(game)):
   game.press('A',wait=90);action='wait'
  else:
   q=path[0];action=direction(q[0]-before[0],q[1]-before[1]);game.press(action,wait=90)
  turns.append({'turn':turn,'position':before,'after':position(game),'hp':hp,'hp_after':m.u16[p+0x84],'action':action,'enemies':enemies,'items':items(game)})
  require(m.u16[p+0x84]>0 and m.u16[0x02005674]==floor,'Castle route defeated or unexpectedly changed floor')
 raise ValueError('Castle route exceeded turn bound')
