"""Known event-text banks and native-source identities; no insertion ownership."""

from functools import lru_cache
import struct

from tools.lz77 import decompress
from tools.rom import digest, load_base

BANK_TABLE = 0x14CD84
BANK_COUNT = 7
BANK_RAM = 0x020241AC


@lru_cache(maxsize=1)
def banks():
    original = load_base()
    records = []
    for index in range(BANK_COUNT):
        pointer = BANK_TABLE + index * 4
        offset = struct.unpack_from("<I", original, pointer)[0] - 0x08000000
        decoded, end = decompress(original, offset)
        records.append({"id": f"event-bank-{index}", "index": index, "pointer_offset": pointer,
                        "rom_offset": offset, "rom_end_exclusive": end,
                        "compressed_sha256": digest(original[offset:end]),
                        "decoded_bytes": len(decoded), "decoded_sha256": digest(decoded),
                        "runtime_start": BANK_RAM, "data": decoded})
    return tuple(records)


def manifest():
    return [{k: v for k, v in bank.items() if k != "data"} for bank in banks()]
