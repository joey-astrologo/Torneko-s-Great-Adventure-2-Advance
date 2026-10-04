"""Recognize bounded ARM7 Thumb jump tables; matches are discovery candidates.

Only the complete CMP/BHI/LSL/LDR/ADD/LDR/MOV-PC pattern is accepted. Paired
code, literal and table bytes must agree. Matching data is not proof of code
reachability; callers must supply entry context and native evidence separately.
"""
import struct

BASE = 0x08000000


def switches(original, compiled, limit=0x5E000):
    result = {}
    end = min(limit, len(original), len(compiled))
    for at in range(0, end-13, 2):
        w = struct.unpack_from('<7H', original, at)
        if (w[0] & 0xF800 != 0x2800 or w[1] & 0xFF00 != 0xD800 or
                w[2] & 0xFFC0 != 0x0080 or w[3] & 0xF800 != 0x4800 or
                w[4] & 0xFE00 != 0x1800 or w[5] & 0xFFC0 != 0x6800 or
                w[6] & 0xFF87 != 0x4687):
            continue
        index, dest, table_reg = (w[0] >> 8) & 7, w[2] & 7, (w[3] >> 8) & 7
        if (index != (w[2] >> 3) & 7 or dest == table_reg or
                (w[4] & 7, (w[4] >> 3) & 7, (w[4] >> 6) & 7) != (dest, dest, table_reg) or
                (w[5] & 7, (w[5] >> 3) & 7) != (dest, dest) or
                (w[6] >> 3) & 15 != dest):
            continue
        literal = ((at+10) & ~3)+(w[3] & 255)*4
        if literal+4 > end:
            continue
        table = struct.unpack_from('<I', original, literal)[0]-BASE
        count = (w[0] & 255)+1
        if table & 3 or not 0 <= table <= end-count*4:
            continue
        targets = struct.unpack_from('<'+str(count)+'I', original, table)
        if not all(BASE <= target < BASE+end and not target & 1 for target in targets):
            continue
        if any(original[start:stop] != compiled[start:stop] for start, stop in
               ((at, at+14), (literal, literal+4), (table, table+count*4))):
            continue
        offset = w[1] & 255
        default = at+6+2*(offset-256 if offset & 128 else offset)
        if not 0 <= default < end:
            continue
        result[at] = dict(guard=BASE+at, jump=BASE+at+12, index_register=index,
                          count=count, table=BASE+table, literal=BASE+literal,
                          default=BASE+default, targets=list(targets),
                          code_hex=original[at:at+14].hex(),
                          table_hex=original[table:table+count*4].hex())
    return result
