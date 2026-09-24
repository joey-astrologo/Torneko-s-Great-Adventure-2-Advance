"""Bounded prose formats for separately audited town-service buffers."""
import re
from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
from tools.rom import require

MARKER = re.compile(r'(\{[^{}]+\})')


def compile_format(text, raw, fields, capacity):
    """fields maps ordered argument markers to (native bytes, pixels, content bytes).

    A field's native bytes may include its original paired colour controls.
    Other native controls are independently checked by the ordinary compiler.
    """
    markers = MARKER.findall(text)
    require(markers == list(fields), 'Service argument roles/order differ')
    original = re.findall(b'%[sd]', raw)
    expected = [re.search(b'%[sd]', value[0]).group() for value in fields.values()]
    require(original == expected, 'Service native printf arguments differ')
    clean = raw
    for native, _, _ in fields.values():
        require(native in clean, 'Service field colour/control bytes differ')
        clean = clean.replace(native, b'', 1)
    compile_dialogue(MARKER.sub('', text), tokenize(clean)[0])

    def width(line):
        return measure(MARKER.sub('', line)) + sum(fields[m][1] for m in MARKER.findall(line))

    pages = []
    for paragraph in text.split('\n\n'):
        lines, line = [], ''
        for word in paragraph.split():
            require(width(word) <= 216, 'Service word exceeds216px')
            candidate = line + (' ' if line else '') + word
            if width(candidate) > 216:
                lines.append(line); line = word
            else:
                line = candidate
        require(line, 'Empty service paragraph')
        lines.append(line)
        pages.extend(lines[i:i + 2] for i in range(0, len(lines), 2))
    stream = ''
    for i, page in enumerate(pages):
        stream += '\n'.join(page)
        if i + 1 < len(pages):
            stream += '\n' * (3 - len(page))
    payload = b''.join(fields[p][0] if p in fields else encode(p)[:-1] for p in MARKER.split(stream)) + b'\0'
    # printf replaces the two-byte conversion, retaining any colour controls.
    maximum = len(payload) + sum(value[2] - 2 for value in fields.values())
    require(maximum <= capacity, 'Service output exceeds native byte capacity')
    return payload, {'pages': pages, 'line_widths': [[width(line) for line in page] for page in pages],
                     'native_width': 224, 'capacity': capacity, 'maximum_formatted_bytes': maximum,
                     'direct_rom_stream': False}
