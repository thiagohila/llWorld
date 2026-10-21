"""Count exact RGBA colours in RGBA 8-bit PNGs (stdlib only)."""
import sys, zlib, struct, collections
def read(path):
    data = open(path, 'rb').read(); pos = 8; idat = b''
    while pos < len(data):
        n, = struct.unpack('>I', data[pos:pos+4]); typ = data[pos+4:pos+8]; body = data[pos+8:pos+8+n]; pos += 12 + n
        if typ == b'IHDR': w, h, bd, ct = struct.unpack('>IIBB', body[:10])
        elif typ == b'IDAT': idat += body
    assert bd == 8 and ct == 6, (bd, ct)
    raw = zlib.decompress(idat); bpp = 4; stride = w * bpp; out = []; prev = bytearray(stride); i = 0
    for _ in range(h):
        f = raw[i]; line = bytearray(raw[i+1:i+1+stride]); i += 1 + stride
        for x in range(stride):
            a = line[x-bpp] if x >= bpp else 0; b = prev[x]; c = prev[x-bpp] if x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c; pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out.append(bytes(line)); prev = line
    return w, h, out
for path in sys.argv[1:]:
    w, h, rows = read(path); cnt = collections.Counter()
    for r in rows:
        for x in range(w): cnt['#%02x%02x%02x/%d' % tuple(r[x*4:x*4+4])] += 1
    semi = sum(v for k, v in cnt.items() if not (k.endswith('/0') or k.endswith('/255')))
    keys = {k: v for k, v in cnt.items() if k.split('/')[0] in ('#ff00ff', '#ff80ff', '#a000a0', '#5a3e2b', '#e0aa80', '#b9825a', '#16110d')}
    print(f"{path.split('/')[-1]}: {w}x{h}, {len(cnt)} cores, pixels semitransparentes={semi}, chaves={keys}")
