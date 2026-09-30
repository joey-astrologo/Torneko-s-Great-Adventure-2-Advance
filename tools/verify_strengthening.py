"""Native random-effect item/HP/strength changes and player-wrapper notices."""
import argparse, struct
from pathlib import Path
from tools.rom import ROOT, require
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_dungeon_leaves import run as check

OWNERS = {
    'items': (0x356E8, 0x15860, 0x15869, 0x35B4E, 0, 0x368),
    'strength-hp': (0x356E8, 0x15860, 0x15869, 0x35B4E, 0, 0x36C),
}


class Strengthening:
    breakpoints = (0x080357E6,)
    scope = ('Native random-effect branches0/1 selected through an explicit valid RNG-result override. '
             'Three player names in ordinary/boundary inventory and stat states. The native handler '
             'increments eligible weapon/shield/staff/pot amounts and both current/maximum HP and strength; '
             'unsupported item categories and all unrelated item bytes remain unchanged. '
             'Exact player-wrapper routing, output and guards, full caller ABI, glyphs/pixels and battery checked. '
             'Natural effect selection and acquisition remain separate.')

    def case_fields(self, owner):
        return tuple(name + '-' + state for name, _ in player_layout_cases() for state in ('normal', 'boundary'))

    def field_capacity(self, role):
        require(role == 'player', 'Unexpected strengthening field')
        return 16

    def setup(self, owner, game, hero, actor, write, overrides):
        name, self.state = self.field.rsplit('-', 1)
        write(HERO, dict(player_layout_cases())[name].ljust(16, b'\0'))
        memory = game.core.memory
        self.expected_stats = None
        self.hp_cap = None
        if owner == 'items':
            mapping = bytes(memory[0x020013D0:0x020014D0])
            items = bytearray(2400)
            # Verified ordinary weapon, shield, staff, pot and herb IDs.
            ids = (1, 25, 48, 154, 177)
            amounts = (0, 3, 3, 3, 1) if self.state == 'normal' else (98, 99, 99, 6, 1)
            for index, (ident, amount) in enumerate(zip(ids, amounts)):
                at = index * 120
                struct.pack_into('<I', items, at, 0xC8000000)
                items[at + 4] = amount
                items[at + 5] = 1
                items[at + 8] = mapping.index(ident)
            write(0x0200DF28, items)
            self.expected_items = bytearray(items)
            for index in range(4):
                self.expected_items[index * 120 + 4] = min(7 if index == 3 else 99, amounts[index] + 3)
        else:
            strengths = (2, 8) if self.state == 'normal' else (95, 96)
            hp = (10, 30) if self.state == 'normal' else (998, 999)
            write(hero + 0x76, struct.pack('<HH', *strengths))
            write(hero + 0x84, struct.pack('<HH', *hp))
            self.before_stats = (*strengths, *hp)
        return (hero, 0, 0, 0)

    def event(self, owner, event, game, hero, actor, write, overrides):
        address, registers = event['address'], event['registers']
        if address == 0x080356F8:
            value = int(owner == 'strength-hp')
            overrides.append({'event': event, 'register': 0, 'after': value,
                              'reason': 'Select valid native random-effect branch0 or1.'})
            game.core.cpu.gprs[0] = value
        if address == 0x080357E6 and owner == 'strength-hp':
            require(self.hp_cap is None and registers[0] > 0, 'Native HP cap missing/repeated')
            self.hp_cap = registers[0]

    def return_register(self, owner):
        return 0

    def returned(self, owner, game, hero, actor):
        memory = game.core.memory
        if owner == 'items':
            require(bytes(memory[0x0200DF28:0x0200DF28 + 2400]) == bytes(self.expected_items),
                    'Native item strengthening/category/cap differs')
        else:
            require(self.hp_cap is not None, 'Native HP cap was not observed')
            expected = tuple(min(96 if i < 2 else self.hp_cap, value + 3)
                             for i, value in enumerate(self.before_stats))
            actual = tuple(memory.u16[hero + offset] for offset in (0x76, 0x78, 0x84, 0x86))
            require(actual == expected, 'Native HP/strength increment/cap differs: ' + repr((actual, expected)))


def run(source, only=None):
    check(source, only, owners=OWNERS, resource_key='player_messages',
          folder='strengthening-validation', hooks=Strengthening())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/english')
    parser.add_argument('--only')
    args = parser.parse_args()
    run(args.source, args.only)
