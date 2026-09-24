"""Bounded decoding of the type-10 streams consumed by the game's BIOS wrapper."""

from tools.rom import require


def pack_literals(data):
    """Deterministic type-10 stream with literal groups; no ROM-space guessing.

    Appended resources need no size-preserving compression. Keeping the packer
    simple also makes its exact BIOS output straightforward to verify.
    """
    require(0 < len(data) <= 0x40000, 'Invalid LZ77 input size')
    return b'\x10' + len(data).to_bytes(3, 'little') + b''.join(
        b'\0' + data[start:start + 8] for start in range(0, len(data), 8))


def decompress(data, offset=0, max_output=0x40000):
    require(0 <= offset and offset + 4 <= len(data), "Truncated LZ77 header")
    require(data[offset] == 0x10, "Expected type-10 LZ77 stream")
    size = int.from_bytes(data[offset + 1:offset + 4], "little")
    require(0 < size <= max_output, "Invalid LZ77 output size")
    cursor, output = offset + 4, bytearray()
    while len(output) < size:
        require(cursor < len(data), "Truncated LZ77 flags")
        flags = data[cursor]
        cursor += 1
        for bit in range(7, -1, -1):
            if len(output) == size:
                break
            if flags & (1 << bit):
                require(cursor + 2 <= len(data), "Truncated LZ77 back-reference")
                first, second = data[cursor:cursor + 2]
                cursor += 2
                count = (first >> 4) + 3
                distance = ((first & 15) << 8 | second) + 1
                require(distance <= len(output), "LZ77 back-reference before output")
                for _ in range(min(count, size - len(output))):
                    output.append(output[-distance])
            else:
                require(cursor < len(data), "Truncated LZ77 literal")
                output.append(data[cursor])
                cursor += 1
    return bytes(output), cursor
