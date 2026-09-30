"""Quantize approved rasters while locking original pixels outside edited regions."""
from collections import Counter
import json
import math
import struct
from PIL import Image
from tools.rom import ROOT, load_base, digest, require
from tools.extract_graphics_audition import save_json
from tools.title_art import APPROVAL, PACKED, SOURCES, RECORDS, TABLE, rgb, calibrate, linear_tiles, tiled_pixels, edited
from tools.trace_graphics_sources import tiled_image


def pack_entry(original, entry):
    index=entry['index'];start=SOURCES[index];count=256 if index==16 else 240;gamma=-2 if index==16 else -1
    original_resource=original[start:start+38912]
    require(original[TABLE+index*20:TABLE+index*20+20]==bytes.fromhex(RECORDS[index]),'Descriptor differs')
    palette=list(struct.unpack('<256H',original_resource[:512]));pixels=bytearray(linear_tiles(original_resource[512:]))
    native_palette=b''.join(struct.pack('<H',calibrate(c,original,gamma)) for c in palette)
    reference_path=(ROOT/'build/title-audition/reference/japanese/title.palette' if index==16 else ROOT/f'build/title-audition/backgrounds/reference/{index}/native.palette')
    require(native_palette[:count*2]==reference_path.read_bytes()[:count*2],'Palette model does not match native capture')
    wanted=Image.open(ROOT/entry['raster']).convert('RGB');require(wanted.size==(240,160),'Approved dimensions differ')
    require(digest((ROOT/entry['raster']).read_bytes())==entry['raster_sha256'],'Approved raster changed')
    target=list(wanted.get_flattened_data());area=[p for p in range(38400) if edited(index,p%240,p//240)]
    locked={pixels[p] for p in range(38400) if not edited(index,p%240,p//240)}
    require(max(pixels)<count,'Background uses UI palette entries')
    free=[i for i in range(count) if i not in locked];require(free,'No palette capacity')
    weights=Counter(target[p] for p in area);unique=sorted(weights)
    sample=Image.new('RGB',(len(area),1));sample.putdata([target[p] for p in area])
    quant=sample.quantize(colors=len(free),method=Image.Quantize.MEDIANCUT,kmeans=3)
    qp=quant.getpalette();colors=[tuple(qp[i*3:i*3+3]) for _,i in sorted(quant.getcolors(),key=lambda x:x[1])]
    native_channels=[rgb(calibrate(c,original,gamma))[0] for c in range(32)]
    def encode(color):
        return sum(min(range(32),key=lambda n:(native_channels[n]-c)**2)<<shift for c,shift in zip(color,(0,5,10)))
    for slot,color in zip(free,colors):palette[slot]=encode(color)
    history=[];best=None
    for iteration in range(7):
        shown=[rgb(calibrate(c,original,gamma)) for c in palette[:count]]
        distances={c:[sum((a-b)**2 for a,b in zip(c,p)) for p in shown] for c in unique}
        lookup={c:min(range(count),key=distances[c].__getitem__) for c in unique}
        error=sum(weights[c]*distances[c][lookup[c]] for c in unique)
        history.append(error)
        if best is None or error<best[0]:best=(error,palette[:],lookup.copy())
        means={slot:[0,0,0,0] for slot in free}
        for c,n in weights.items():
            slot=lookup[c]
            if slot in means:
                for k in range(3):means[slot][k]+=c[k]*n
                means[slot][3]+=n
        previous=palette[:]
        for slot,total in means.items():
            if total[3]:palette[slot]=encode([v/total[3] for v in total[:3]])
        if palette==previous:break
    error,palette,lookup=best
    for p in area:pixels[p]=lookup[target[p]]
    payload=struct.pack('<256H',*palette)+tiled_pixels(pixels)
    shown_palette=b''.join(struct.pack('<H',calibrate(c,original,gamma)) for c in palette)
    preview=tiled_image(payload[512:],shown_palette,240,160,8)
    original_picture=tiled_image(original_resource[512:],native_palette,240,160,8)
    for p in range(38400):
        if not edited(index,p%240,p//240):require(preview.getpixel((p%240,p//240))==original_picture.getpixel((p%240,p//240))==target[p],'Preserved pixel changed')
    require(payload[480:512]==original_resource[480:512] if index!=16 else True,'UI tail changed')
    errors=[math.sqrt(sum((a-b)**2 for a,b in zip(target[p],preview.getpixel((p%240,p//240))))/3) for p in area]
    PACKED.mkdir(parents=True,exist_ok=True);(PACKED/f'{index}.bin').write_bytes(payload)
    preview.save(PACKED/f'{index}-preview.png')
    row={**entry,'packed_sha256':digest(payload),'original_resource_sha256':digest(original_resource),
         'palette_count':count,'gamma':gamma,'calibration_level':4,'locked_palette_indices':sorted(locked),'available_edited_palette_entries':len(free),
         'all_unedited_palette_entries_and_indices_preserved':True,'edited_pixels':len(area),
         'edited_rgb_rmse':math.sqrt(error/(len(area)*3)),'edited_max_channel_rmse':max(errors),'iteration_squared_errors':history,
         'preview_sha256':digest((PACKED/f'{index}-preview.png').read_bytes())}
    print(f'Packed {index}: {len(free)} available palette entries, edited RGB RMSE {row["edited_rgb_rmse"]:.2f}',flush=True)
    return row


def run():
    original=load_base();approval=json.loads(APPROVAL.read_text());require(approval['status']=='approved-for-insertion','Approval missing')
    require(approval['source_sha256']==digest(original),'Approval source differs')
    entries=[pack_entry(original,row) for row in approval['entries']]
    inputs=[APPROVAL,ROOT/'tools/pack_title_art.py',ROOT/'tools/title_art.py']+[ROOT/e['raster'] for e in entries]
    save_json(PACKED/'manifest.json',{'schema':1,'source_sha256':digest(original),'approval_sha256':digest(APPROVAL.read_bytes()),
              'entries':entries,'input_hashes':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in inputs},
              'scope':'Native-calibrated palette fitting with all indices/palette entries outside each edited area locked. All six original resources remain untouched; packed resources require appended allocation.'})


if __name__=='__main__':run()
