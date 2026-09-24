"""Lossless source tokens for the observed Torneko 2 character/control reader.

Byte preservation is separate from semantic verification. Unknown codes remain
explicit; this is not yet an insertion encoder for arbitrary game commands.
"""

from tools.rom import require

# Operand lengths follow the jump handlers reached from 08001DA8.
PARAMETERS = {3: 1, 4: 1, 6: 1, 14: 2, 18: 1, 19: 1}
NAMES = {1: "style-on", 2: "style-off", 3: "legacy-position", 4: "legacy-x",
         6: "pixel-x", 9: "tab", 13: "newline", 14: "fit-next", 18: "skip-byte",
         19: "text-mode", 28: "spacing-on", 29: "spacing-off", 31: "name-substitution"}


def tokenize(data, start=0, limit=None):
    end = min(len(data), limit if limit is not None else len(data))
    require(0 <= start < end, "Text start outside source")
    tokens, cursor = [], start
    while cursor < end:
        begin, code = cursor, data[cursor]
        cursor += 1
        if code == 0:
            tokens.append({"kind": "end", "raw_hex": "00"})
            return tokens, cursor
        if code == 0x40:
            close = data.find(b"@", cursor, end)
            require(close >= 0 and b"\0" not in data[cursor:close], "Unterminated @ command")
            cursor = close + 1
            token = {"kind": "command", "name": "at-command", "semantic_status": "unresolved"}
        elif code > 0x80:
            if not 0xA0 <= code <= 0xDF:
                cursor += 1
            require(cursor <= end, "Truncated Japanese glyph")
            raw = data[begin:cursor]
            try:
                decoded = raw.decode("cp932")
                if len(decoded) == 1:
                    token = {"kind": "text", "text": decoded}
                else:
                    token = {"kind": "glyph", "code": int.from_bytes(raw, "big"), "semantic_status": "unresolved"}
            except UnicodeDecodeError:
                token = {"kind": "glyph", "code": int.from_bytes(raw, "big"), "semantic_status": "unresolved"}
        elif 0x20 <= code <= 0x5F:
            token = {"kind": "text", "text": chr(code)}
        else:
            cursor += PARAMETERS.get(code, 0)
            require(cursor <= end, "Truncated control operands")
            token = {"kind": "command", "code": code, "name": NAMES.get(code, "unclassified-control"),
                     "semantic_status": "reader-disassembly" if code in NAMES else "unresolved"}
        token["raw_hex"] = data[begin:cursor].hex()
        if token["kind"] == "text" and tokens and tokens[-1]["kind"] == "text":
            tokens[-1]["text"] += token["text"]
            tokens[-1]["raw_hex"] += token["raw_hex"]
        else:
            tokens.append(token)
    raise ValueError("Unterminated text within source bounds")


def source_bytes(tokens):
    return b"".join(bytes.fromhex(token["raw_hex"]) for token in tokens)


def readable(tokens):
    output = []
    for token in tokens:
        kind = token["kind"]
        if kind == "text":
            output.append(token["text"])
        elif kind == "glyph":
            output.append("{glyph:" + token["raw_hex"] + "}")
        elif kind == "command":
            if token["name"] == "newline":
                output.append("\n")
            elif token["name"] == "at-command":
                output.append(bytes.fromhex(token["raw_hex"]).decode("ascii", "backslashreplace"))
            else:
                output.append("{" + token["name"] + ":" + token["raw_hex"] + "}")
    return "".join(output)
