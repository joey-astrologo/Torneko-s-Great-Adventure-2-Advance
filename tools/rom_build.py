"""Checked original-ROM patches and one ledger for appended resources."""

from tools.rom import digest, load_base, require


def verify_ledger(original, rom, report):
    """Independently reconstruct a finished ROM; reject gaps, overlaps and edits."""
    require(digest(original) == report['source_sha256'] and digest(rom) == report['output_sha256'],
            'Ledger ROM identity differs')
    require(len(original) == report['source_bytes'] and len(rom) == report['output_bytes'],
            'Ledger ROM size differs')
    expected = bytearray(original + b'\xFF'*(len(rom)-len(original)))
    ends, ids = [], set()
    for patch in report['patches']:
        lo, hi = patch['start'], patch['end_exclusive']
        before, after = bytes.fromhex(patch['before_hex']), bytes.fromhex(patch['after_hex'])
        require(0 <= lo < hi <= len(original) and hi-lo == len(before) == len(after)
                and original[lo:hi] == before, 'Ledger patch source differs')
        require(patch['id'] not in ids and patch['owner'] and all(hi <= a or lo >= b for a,b in ends),
                'Ledger patch overlap/identity differs')
        ends.append((lo, hi));ids.add(patch['id'])
        expected[lo:hi] = after
    cursor = len(original)
    for allocation in report['allocations']:
        lo, hi = allocation['start'], allocation['end_exclusive']
        require(cursor <= lo < hi <= len(rom) and lo-cursor == allocation['padding_before']
                and allocation['alignment'] > 0
                and allocation['alignment'] & (allocation['alignment'] - 1) == 0
                and lo % allocation['alignment'] == 0,
                'Ledger allocation range differs')
        require(allocation['id'] not in ids and allocation['owner']
                and digest(rom[lo:hi]) == allocation['sha256'], 'Ledger allocation identity/bytes differ')
        expected[lo:hi] = rom[lo:hi]
        ids.add(allocation['id']);cursor = hi
    require(bytes(expected) == rom, 'ROM has unowned bytes outside ledger')
    return True


class RomBuild:
    def __init__(self, original):
        require(original == load_base(), "Expected the pinned Japanese base")
        self.original = bytes(original)
        self.data = bytearray(original)
        self.allocations, self.patches, self.ids = [], [], set()

    def claim(self, ident, owner):
        require(ident and owner and ident not in self.ids, "Missing or duplicate resource identity")
        self.ids.add(ident)

    def allocate(self, ident, payload, owner, alignment=4):
        require(payload and alignment > 0 and alignment & (alignment - 1) == 0, "Invalid allocation")
        start = (len(self.data) + alignment - 1) & -alignment
        end = start + len(payload)
        require(end <= 0x02000000, "Allocation exceeds GBA ROM capacity")
        self.claim(ident, owner)
        padding = start - len(self.data)
        self.data.extend(b"\xFF" * padding)
        self.data.extend(payload)
        self.allocations.append({"id": ident, "owner": owner, "start": start, "end_exclusive": end,
                                 "padding_before": padding, "alignment": alignment, "sha256": digest(payload)})
        return start

    def patch(self, ident, offset, expected, replacement, owner):
        require(expected and len(expected) == len(replacement), "Patch must preserve original-region size")
        end = offset + len(expected)
        require(0 <= offset < end <= len(self.original), "Patch outside original ROM")
        require(self.original[offset:end] == expected and self.data[offset:end] == expected, "Source-byte mismatch")
        for previous in self.patches:
            require(end <= previous["start"] or offset >= previous["end_exclusive"], "Patch overlap")
        self.claim(ident, owner)
        self.data[offset:end] = replacement
        self.patches.append({"id": ident, "owner": owner, "start": offset, "end_exclusive": end,
                             "before_hex": expected.hex(), "after_hex": replacement.hex()})

    def finish(self):
        restored = bytearray(self.data[:len(self.original)])
        for patch in self.patches:
            require(self.data[patch["start"]:patch["end_exclusive"]] == bytes.fromhex(patch["after_hex"]),
                    "Checked patch was overwritten")
            restored[patch["start"]:patch["end_exclusive"]] = bytes.fromhex(patch["before_hex"])
        require(restored == self.original, "Unowned changes to original ROM")
        cursor = len(self.original)
        for allocation in self.allocations:
            require(self.data[cursor:allocation["start"]] == b"\xFF" * allocation["padding_before"],
                    "Alignment padding was overwritten")
            require(digest(self.data[allocation["start"]:allocation["end_exclusive"]]) == allocation["sha256"],
                    "Allocated resource was overwritten")
            cursor = allocation["end_exclusive"]
        require(cursor == len(self.data), "Unowned appended bytes")
        size = 1 << (len(self.data) - 1).bit_length()
        require(size <= 0x02000000, "Expanded ROM exceeds capacity")
        data = bytes(self.data) + b"\xFF" * (size - len(self.data))
        return data, {"source_sha256": digest(self.original), "output_sha256": digest(data),
                      "source_bytes": len(self.original), "output_bytes": len(data),
                      "allocations": self.allocations, "patches": self.patches,
                      "unowned_original_bytes_preserved": True}
