"""Operand widths verified against the original native NPC dispatch handlers."""
from tools.rom import require


def operand_lengths(rom):
    lengths = list(rom[0x14CEBC:0x14CEE0])
    # Dispatch increments past the opcode at 4EF58. Handler 33 then consumes
    # two bytes at 50A94, despite the historical size table claiming one.
    require(len(lengths) == 36 and lengths[33] == 1 and
            rom[0x4EF54:0x4EF5C] == bytes.fromhex('2068017801302060'),
            'Reinspect NPC size table')
    require(rom[0x50A94:0x50A98] == bytes.fromhex('02300860'),
            'Reinspect opcode 33 native operand advance')
    lengths[33] = 2
    return lengths
