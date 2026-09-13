"""Checked original-ROM patches and one ledger for appended resources."""

from tools.rom import digest, load_base, require


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
