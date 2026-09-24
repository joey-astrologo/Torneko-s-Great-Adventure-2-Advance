"""Read-only navigation decisions, executed with ordinary dungeon buttons."""

import json
from collections import deque

from tools.name_entry_playtest import ACTORS, MAP, nearby_monsters, position, stairs_path
from tools.rom import require


def direction(dx, dy):
    return tuple((['LEFT'] if dx < 0 else ['RIGHT'] if dx > 0 else []) +
                 (['UP'] if dy < 0 else ['DOWN'] if dy > 0 else []))


def path_to(game, goal):
    start = position(game)
    queue, previous = deque([start]), {start: None}
    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            break
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            p = x+dx,y+dy
            if p not in previous and 0 <= p[0] < 56 and 0 <= p[1] < 32 and game.core.memory.u32[MAP+(p[0]*32+p[1])*28+20] & 0x4000:
                previous[p] = x,y
                queue.append(p)
    require(goal in previous, 'No ordinary-ground route to target')
    path, p = [], goal
    while p != start:
        path.append(p)
        p = previous[p]
    return path[::-1]


def walk_to_stairs(game, goal=None):
    steps = []
    for _ in range(900):
        path = stairs_path(game) if goal is None else path_to(game, goal)
        if not path:
            return steps
        before, target = position(game), path[0]
        actor = game.core.memory.u32[ACTORS]
        hp = game.core.memory.u16[actor + 0x84]
        enemies = nearby_monsters(game)
        keys = []
        if enemies:
            enemy = min(enemies, key=lambda e: e['hp'])
            dx, dy = enemy['position'][0] - before[0], enemy['position'][1] - before[1]
            face = direction(dx, dy)
            game.press(face, wait=30)
            keys.append(face)
            game.press('A', wait=90)
            keys.append(('A',))
        elif hp < game.core.memory.u16[actor+0x86] - 1 and not nearby_monsters(game, 3):
            game.press('A', wait=90)
            keys.append(('A',))
        else:
            move = direction(target[0]-before[0], target[1]-before[1])
            game.press(move, wait=90)
            keys.append(move)
            if position(game) == before:
                game.press('A', wait=90)
                keys.append(('A',))
        hp_after = game.core.memory.u16[actor+0x84]
        steps.append({'from': before, 'target': target, 'keys': keys, 'after': position(game),
                      'enemies': enemies, 'hp_before': hp, 'hp_after': hp_after,
                      'frame': game.core.frame_counter})
        if not hp_after:
            game.snapshot().save(game.output/'walk-failure')
            game.capture('walk-failure')
            (game.output/'walk-failure-steps.json').write_text(json.dumps(steps, indent=2)+'\n')
        require(hp_after, 'Player defeated on mansion route')
    raise ValueError('Mansion walk exceeded ordinary-input budget')
