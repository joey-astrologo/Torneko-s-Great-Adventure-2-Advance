"""Read the verified first-floor map and walk to its stairs using normal buttons."""

from collections import deque
import json

from tools.rom import require

MAP = 0x020229A8
ACTORS = 0x02001624


def nearby_monsters(game, distance=1):
    """First-dungeon actors only: live enemy slots, observed position/HP fields."""
    memory = game.core.memory
    x, y = position(game)
    nearby = []
    for slot in range(1, 56):
        actor = memory.u32[ACTORS + slot * 4]
        if 0x02000000 <= actor < 0x02040000 - 0x88:
            hp = memory.u16[actor + 0x84]
            point = memory.u16[actor + 0x66], memory.u16[actor + 0x68]
            if hp and memory.u32[actor + 8] & 0x80000000 and max(abs(point[0] - x), abs(point[1] - y)) <= distance:
                nearby.append({'slot': slot, 'position': point, 'hp': hp})
    return nearby


def narrow_passage(game):
    x, y = position(game)
    open_neighbours = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < 56 and 0 <= y + dy < 32:
                flags = game.core.memory.u32[MAP + ((x + dx) * 32 + y + dy) * 28 + 20]
                open_neighbours += bool(flags & 0x4000)
    return open_neighbours <= 2


def position(game):
    memory = game.core.memory
    actor = memory.u32[ACTORS]
    require(0x02000000 <= actor < 0x02040000 - 0x88, 'Invalid player actor')
    return memory.u16[actor + 0x66], memory.u16[actor + 0x68]


def stairs_path(game):
    memory = game.core.memory
    flags = {(x, y): memory.u32[MAP + (x * 32 + y) * 28 + 20]
             for x in range(56) for y in range(32)}
    stairs = [point for point, value in flags.items() if value & 0x20]
    require(len(stairs) == 1, 'Expected one first-floor stair')
    goal, start = stairs[0], position(game)
    queue, previous = deque([start]), {start: None}
    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            point = x + dx, y + dy
            if point not in previous and flags.get(point, 0) & 0x4000:
                previous[point] = x, y
                queue.append(point)
    require(goal in previous, 'No ordinary-ground route to the stair')
    path, point = [], goal
    while point != start:
        path.append(point)
        point = previous[point]
    return path[::-1]


def walk_to_stairs(game):
    steps = []
    for _ in range(350):
        path = stairs_path(game)
        if not path:
            return steps
        before, target = position(game), path[0]
        actor = game.core.memory.u32[ACTORS]
        hp_before = game.core.memory.u16[actor + 0x84]
        adjacent = nearby_monsters(game)
        # The native A action automatically faces an adjacent enemy. Finish a
        # fight before walking away; the old route ignored flank/rear attacks.
        if adjacent:
            key = 'A'
        elif nearby_monsters(game, 5) and narrow_passage(game):
            # Let a nearby group enter a narrow passage one at a time instead
            # of walking out into simultaneous attacks from several directions.
            key = 'A'
        elif hp_before < game.core.memory.u16[actor + 0x86] - 2 and not nearby_monsters(game, 3):
            # An empty attack advances one ordinary turn and allows native HP
            # regeneration. Re-evaluate approaching monsters after each turn.
            key = 'A'
        else:
            key = {(-1, 0): 'LEFT', (1, 0): 'RIGHT', (0, -1): 'UP', (0, 1): 'DOWN'}[
                target[0] - before[0], target[1] - before[1]]
        game.press(key, wait=90)
        blocked = position(game) == before
        if blocked and key != 'A':
            # The direction input faces a blocking monster. A attacks or
            # acknowledges an intervening tutorial/message; no state is injected.
            game.press('A', wait=90)
        actor = game.core.memory.u32[ACTORS]
        steps.append({'from': before, 'target': target, 'key': key,
                      'attack_or_acknowledge': blocked, 'after': position(game),
                      'adjacent_monsters': adjacent,
                      'hp_before': hp_before, 'hp_after': game.core.memory.u16[actor + 0x84],
                      'frame': game.core.frame_counter})
        if game.core.memory.u16[actor + 0x84] == 0:
            game.capture('walk-failure')
            game.snapshot().save(game.output / 'walk-failure')
            (game.output / 'walk-failure-report.json').write_text(json.dumps({
                'rom_sha256': game.rom_sha256, 'steps': steps, 'inputs': game.inputs}, indent=2) + '\n')
            raise ValueError('Player defeated on save route; native failure evidence retained')
    raise ValueError('First-floor route exceeded its movement budget')


def save_at_stairs(game):
    game.capture('stairs-menu')
    game.press('DOWN', wait=90)
    game.press('DOWN', wait=90)
    game.capture('save-option')
    game.press('A', wait=300)
    game.capture('save-complete')
