"""Read town coordinates verified after the first audience; no state overrides."""

from tools.rom import require

X = 0x0200FF0C
Y = 0x0200FF10
MOVE = 0x0804B528


def position(game):
    return game.core.memory.u32[X], game.core.memory.u32[Y]


def face_home_roamer(game):
    """Face the first village's slot-24 NPC after the ordinary eastward approach.

    Loading/page timing can leave him east or south of the player. Read his
    observed town actor coordinates, then press a direction; never move actors
    or alter event state in RAM.
    """
    actor = 0x02010A78 + 24 * 64
    x, y = position(game)
    target = game.core.memory.u32[actor + 56], game.core.memory.u32[actor + 60]
    dx, dy = target[0] - x, target[1] - y
    require((dx or dy) and abs(dx) <= 32 and abs(dy) <= 32, 'Home roamer is outside the verified approach')
    key = ('RIGHT' if dx > 0 else 'LEFT') if abs(dx) >= abs(dy) else ('DOWN' if dy > 0 else 'UP')
    game.press(key, hold=3, wait=0)
    return {'actor_slot':24, 'observed_position':target, 'player_position':(x,y), 'facing_input':key}
