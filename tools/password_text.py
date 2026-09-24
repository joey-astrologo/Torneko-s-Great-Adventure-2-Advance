"""Translate the owned password notice without changing its generated kana code."""
import json,re,struct
from tools.compact_font import encode,load_font
from tools.dialogue_layout import width
from tools.extract_items import source
from tools.rom import ROOT,digest,require

CATALOG=ROOT/'translations/password-review.json'


def compile_notice(text,rows,budget):
    font=load_font();pages=[]
    for paragraph in text.split('\n\n'):
        lines=[]
        for authored in paragraph.split('\n'):
            line=''
            for word in authored.split():
                require(width(word,font)<=budget,'Password word exceeds width')
                candidate=(line+' '+word).strip()
                if width(candidate,font)>budget:lines.append(line);line=word
                else:line=candidate
            require(line,'Empty password line');lines.append(line)
        pages.extend(lines[i:i+rows] for i in range(0,len(lines),rows))
    stream=''.join('\n'.join(page)+('\n'*(rows+1-len(page)) if i<len(pages)-1 else '') for i,page in enumerate(pages))
    payload=bytearray()
    for part in re.split(r'(\{color:6\}|\{/color\})',stream):
        if part=='{color:6}':payload.extend(b'\x03\x06')
        elif part=='{/color}':payload.append(5)
        else:
            require(not any(c in part for c in '{}%'),'Unexpected password control')
            payload.extend(encode(part)[:-1])
    payload.append(0)
    return bytes(payload),{'pages':pages,'line_widths':[[width(line,font) for line in p] for p in pages],
                           'maximum_width':budget,'native_rows':rows,'encoded_bytes':len(payload)}


def add_password(build):
    catalog=json.loads(CATALOG.read_text());entries=[]
    require(catalog['base_rom_sha256']==digest(build.original) and {r['literal'] for r in catalog['entries']}=={0x57A44,0x57A48},'Password source/owners differ')
    for row in catalog['entries']:
        pointer=struct.unpack_from('<I',build.original,row['literal'])[0]
        require(row['status']=='reviewed' and row['source']==source(build.original,pointer),'Password review source differs')
        notice=row['literal']==0x57A48
        require(re.findall(r'\{[^}]+\}',row['english'])==(['{color:6}','{/color}'] if notice else []),'Password colour controls differ')
        payload,layout=compile_notice(row['english'],4 if notice else 1,216 if notice else 58)
        offset=build.allocate(row['id'],payload,'password-text')
        build.patch(row['id']+'-literal',row['literal'],struct.pack('<I',pointer),struct.pack('<I',offset+0x08000000),'password-text')
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout})
    return {'entries':entries,'review_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope'],
            'retained_protocol':'Nine generated kana in original order; format literal57A3C, alphabet literal57A40 and generator57A94 unchanged.'}
