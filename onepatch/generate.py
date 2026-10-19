"""Generates the three override files from the user's own original files.

Input : original fes/saveload.cstx, image/sys/sys_saveload.atx,
        image/sys/sys_saveload_panel.atx (bytes, read from the user's install)
Output: dict {relative path: bytes} for the patched versions.
"""
import copy, io, json, zipfile
import numpy as np
from PIL import Image, ImageDraw

from . import cstx, atlaspb
from .atx import Atx
from .tabgen import TabGen, TAB_BASE

NPAGES = 75            # pages after patching (6 slots each -> 450 slots)
PER = 15               # tabs shown at once (same as the original layout)
NGROUP = NPAGES // PER
MAXSLOT = NPAGES * 6 - 1

# layout of the page tabs on screen (column-major 2 x 8 grid)
X0, DX, Y0, DY = 101, 98, 182, 80
TW, TH = 2048, 1024    # size of the added texture sheet
ZDATE = (2020, 1, 1, 0, 0, 0)

PATHS = ('fes/saveload.cstx', 'image/sys/sys_saveload.atx', 'image/sys/sys_saveload_panel.atx')


class PatchError(Exception):
    pass


def slotpos(i):
    return (X0 + DX * (i // 8), Y0 + DY * (i % 8))


def _zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for name, data in entries:
            zi = zipfile.ZipInfo(name, ZDATE); zi.compress_type = zipfile.ZIP_DEFLATED
            zo.writestr(zi, data)
    return buf.getvalue()


def _png(im):
    t = io.BytesIO(); im.save(t, 'PNG', optimize=True); return t.getvalue()


def _arrow(a, tg, st, left):
    """◀ / ▶ button: a tab background (number erased) with a drawn triangle."""
    T, bg = tg.state_data(st)
    arr = np.asarray(a.block(TAB_BASE + 20 * st)).astype(float).copy()
    arr[19:39, 18:50] = bg[19:39, 18:50]
    im = Image.fromarray(arr.clip(0, 255).astype('uint8'), 'RGBA')
    col = (84, 84, 84, 255) if st == 0 else (255, 255, 255, 255)
    cx, cy = 34, 28
    pts = [(cx + 6, cy - 8), (cx + 6, cy + 8), (cx - 8, cy)] if left else [(cx - 6, cy - 8), (cx - 6, cy + 8), (cx + 8, cy)]
    big = Image.new('L', (68 * 4, 70 * 4), 0)
    ImageDraw.Draw(big).polygon([(x * 4, y * 4) for x, y in pts], fill=255)
    m = big.resize((68, 70), Image.LANCZOS)
    im.paste(Image.new('RGBA', (68, 70), col), (0, 0), m)
    return im


def build_saveload_atx(src: bytes) -> bytes:
    a = Atx(src)
    for need in [TAB_BASE + 20 * s + i for s in range(4) for i in range(16)]:
        if need not in a.blocks:
            raise PatchError(f'sys_saveload.atx: block {need} not found (unknown game version)')
    if any(b['id'] in (1800, 1900) or 2000 <= b['id'] < 2400 for b in a.j['Block']):
        raise PatchError('sys_saveload.atx is already patched')
    tg = TabGen(a)
    imgs = {}
    for p in range(1, NPAGES + 1):
        i = (p - 1) % PER
        for s in range(4):
            im = a.block(TAB_BASE + 20 * s + (p - 1)) if p <= 15 else tg.make(str(p), s)
            imgs[2000 + (p - 1) * 4 + s] = (im, slotpos(i))
    for s in range(4):
        imgs[1800 + s] = (a.block(TAB_BASE + 20 * s + 15), slotpos(15))   # quick-save tab
    for k, (left, base_id) in enumerate([(True, 1900), (False, 1910)]):
        for st in range(2):
            imgs[base_id + st] = (_arrow(a, tg, st, left), (X0 + DX * k, Y0 + DY * 8))
    ntex = len(a.tex)
    tex = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    x = y = 2
    tmpl = a.blocks[TAB_BASE]
    for bid, (im, (px, py)) in sorted(imgs.items()):
        w, h = im.size
        if x + w + 2 > TW:
            x = 2; y += h + 4
        if y + h >= TH:
            raise PatchError('texture sheet overflow')
        tex.paste(im, (x, y))
        b = copy.deepcopy(tmpl); b['id'] = bid
        b['anchorX'] = b['offsetX'] = float(px); b['anchorY'] = b['offsetY'] = float(py)
        m = b['Mesh'][0]
        m.update(texNo=ntex, viewX=float(x), viewY=float(y), width=float(w), height=float(h),
                 offsetX=w / 2, offsetY=h / 2,
                 texU1=x / TW, texV1=y / TH, texU2=(x + w) / TW, texV2=(y + h) / TH)
        a.j['Block'].append(b)
        x += w + 4
    entries = [(f'tex{n}.png', a.z.read(f'tex{n}.png')) for n in range(ntex)]
    entries.append((f'tex{ntex}.png', _png(tex)))
    entries.append(('atlas.json', json.dumps(a.j, ensure_ascii=False, separators=(',', ':'))))
    entries.append(('atlas.pb', atlaspb.layout(a.j)))
    return _zip(entries)


def build_panel_atx(src: bytes) -> bytes:
    """Adds digit positions 34/35 (3rd digit) and moves the NEW mark right."""
    p = Atx(src)
    for need in (30, 32, 39):
        if need not in p.blocks:
            raise PatchError(f'sys_saveload_panel.atx: block {need} not found')
    if 34 in p.blocks or 35 in p.blocks:
        raise PatchError('sys_saveload_panel.atx is already patched')
    for new, srcid in [(34, 30), (35, 32)]:
        b = copy.deepcopy(p.blocks[srcid]); b['id'] = new
        b['offsetX'] += 14; b['anchorX'] += 14
        p.j['Block'].append(b)
    for b in p.j['Block']:
        if b['id'] == 39:
            b['offsetX'] += 14; b['anchorX'] += 14
    entries = [(n, p.z.read(n)) for n in p.z.namelist() if n.startswith('tex')]
    entries.append(('atlas.json', json.dumps(p.j, ensure_ascii=False, separators=(',', ':'))))
    entries.append(('atlas.pb', atlaspb.layout(p.j)))
    return _zip(entries)


def patch_script(L):
    """Rule-based edits of the save/load screen script (list of lines, edited in place).

    Each rule locates a short anchor line and inserts/replaces lines with new
    code. If an anchor is missing (different game version) a PatchError is raised
    and nothing is written."""
    def idx_of(s, start=0):
        try:
            return L.index(s, start)
        except ValueError:
            raise PatchError(f'saveload.cstx: anchor not found: {s!r}')

    def rep(old, new, count=None):
        idx = [i for i, s in enumerate(L) if s == old]
        if not idx or (count is not None and len(idx) != count):
            raise PatchError(f'saveload.cstx: anchor mismatch: {old!r} ({len(idx)})')
        for i in idx:
            L[i] = new

    def ins_after(anchor, lines, occ=0):
        idx = [i for i, s in enumerate(L) if s == anchor]
        if len(idx) <= occ:
            raise PatchError(f'saveload.cstx: anchor not found: {anchor!r}')
        i = idx[occ]; L[i + 1:i + 1] = lines

    if '#SETTABS' in L:
        raise PatchError('saveload.cstx is already patched')

    # object definitions: page tabs use new ids (2000+, 1800+), add the group buttons
    ins_after('\tBUTTON\t\tpage[16]', ['\tBUTTON\t\tgrp[2]'])
    for i in range(16):
        olds = [s for s in L if s.startswith(f'page[{i}]\t1')]
        if not olds:
            raise PatchError(f'saveload.cstx: page[{i}] definition not found')
        base = 2000 + i * 4 if i < 15 else 1800
        rep(olds[0], f'page[{i}]\t{base}\t\t{base + 1}\t\t{base + 2}\t\t{base + 3}', 1)
    ins_after('page[15]\t1800\t\t1801\t\t1802\t\t1803',
              ['', '#OBJECT\tFILE\tPRI\tENABLE\tPL\t\tDISP', 'grp\tsys_saveload\t250\t0\t\tpl[0]\t1', '',
               '#OBJECT\tID.0\tID.1\tID.2\tID.3', 'grp[0]\t1900\t\t1901\t\t1901\t\t1901',
               'grp[1]\t1910\t\t1911\t\t1911\t\t1911'])
    # key / gamepad navigation: one more row for the group buttons
    rep('#KEYBLOCK\t11\t', '#KEYBLOCK\t12\t', 1)
    rep('7\t2,1\t6,-1,-1,10', '7\t2,1\t6,11,-1,10', 1)
    ins_after('10\t2,1\t9,-1,5,-1', ['11\t2,1\t7,-1,-1,10'])
    ins_after('page[15]\t7,1,0', ['grp[0]\t\t11,0,0', 'grp[1]\t\t11,1,0'])
    ins_after('\tpage keypos 1 16 16', ['\tgrp keypos 1 16 16'])
    # "newest save" search range
    n = 0
    for i, s in enumerate(L):
        if s.strip() == 'newsave 850 0 100':
            L[i] = s.replace('newsave 850 0 100', f'newsave 850 0 {MAXSLOT}'); n += 1
    if not n:
        raise PatchError('saveload.cstx: newsave not found')
    # current tab group (\126) follows the current page (\125)
    i = idx_of('\t\t\\125 = \\120 / 6 + 1'); j = idx_of('\tendif', i)
    L[j + 1:j + 1] = [f'\t\\126 = (\\125-1)/{PER}']
    rep('if (\\125<=15) ', f'if (\\125<={NPAGES}) ')
    rep('if ((_PAGE_D_!=0)&&(\\125<15)) ', f'if ((_PAGE_D_!=0)&&(\\125<{NPAGES})) ', 1)
    i = idx_of('\t\t\\125--'); L[i + 1:i + 1] = [f'\t\t\\126 = (\\125-1)/{PER}']
    i = idx_of('\t\t\\125++'); L[i + 1:i + 1] = [f'\t\t\\126 = (\\125-1)/{PER}']
    # tab state handling (\127 = index of the highlighted tab, -1 if not in this group)
    i = idx_of('\tpage setid 0')
    if L[i + 1] != '\tpage[\\125-1] setid 1':
        raise PatchError('saveload.cstx: unexpected BTNINIT')
    L[i:i + 2] = ['\tcall SETTABS', '\tcall CALC127', '\tpage setid 0', 'if (\\127>=0) ',
                  '\t\tpage[\\127] setid 1', '\tendif', '\tgrp setid 0', '\tgrp disp 1', '\tgrp enable 1']
    i = idx_of('\tpage[\\125-1] enable 0')
    L[i:i + 1] = ['if (\\127>=0) ', '\t\tpage[\\127] enable 0', '\tendif']
    rep('if (\\125-1!=@) ', 'if (\\127!=@) ', 2)
    i = idx_of('\t\\125 = @+1')
    L[i:i + 1] = ['if (@==15) ', f'\t\t\\125 = {NPAGES + 1}', '\telse', f'\t\t\\125 = \\126*{PER}+@+1',
                  '\tendif', '\tgrp enable 0']
    i = idx_of('\tpage enable 0', idx_of('#DISABLE_ALLBTN')); L[i + 1:i + 1] = ['\tgrp enable 0']
    # slot number: 3 digits
    for tag, big, small, third, font in [('#SETDATA_NODATA', '33', '32', '35', 'dfont[1]'),
                                         ('#SETDATA_EXIST', '31', '30', '34', 'dfont[0]')]:
        s0 = idx_of(tag)
        i = idx_of('\tdata[\\108] dispid 0 30 31 32 33', s0)
        L[i] = '\tdata[\\108] dispid 0 30 31 32 33 34 35'
        e = idx_of('\telse', i); k = idx_of('\tendif', e)
        old = L[e + 1:k]
        L[e:k + 1] = (['\telse', 'if (\\499<100) '] + ['\t' + x for x in old] +
                      ['\t\telse',
                       f'\t\t\tdata[\\108] ptype NUM_O2 {big} {font} \\499/100',
                       f'\t\t\tdata[\\108] ptype NUM_O2 {small} {font} (\\499/10)%10',
                       f'\t\t\tdata[\\108] ptype NUM_O2 {third} {font} \\499%10',
                       f'\t\t\tdata[\\108] dispid 1 {small} {big} {third}',
                       '\t\tendif', '\tendif'])
    ins_after('\tdata ptype NUM_O 31 dfont[0] 0', ['\tdata ptype NUM_O 34 dfont[0] 0'])
    ins_after('\tdata ptype NUM_O 33 dfont[1] 0', ['\tdata ptype NUM_O 35 dfont[1] 0'])
    i = idx_of('\tdata[\\108] dispid 0 2 10 12 13 30 31')
    L[i] = '\tdata[\\108] dispid 0 2 10 12 13 30 31 34'
    # new labels
    L += ['', '#grp.FOCUS', '\t@ setid 1', '\t#814 = 105', '\tcall SYSVOICE', '',
          '#grp.UNFOCUS', '\t@ setid 0', '',
          '#grp.PUSH_L', 'if (@==0) ', f'\t\t\\126 = (\\126+{NGROUP - 1})%{NGROUP}', '\telse',
          f'\t\t\\126 = (\\126+1)%{NGROUP}', '\tendif',
          f'\t\\125 = \\126*{PER}+1', '\tpage enable 0', '\tgrp enable 0', '\tnext SETDATA', '',
          '#SETTABS']
    for i in range(PER):
        for s in range(4):
            L.append(f'\tpage[{i}] settbl {s} 2000+\\126*{PER * 4}+{i * 4 + s}')
    L += ['', '#CALC127', '\t\\127 = -1', f'if (\\125>{NPAGES}) ', '\t\t\\127 = 15', '\tendif',
          f'if (\\125<={NPAGES}) ', f'if ((\\125-1)/{PER}==\\126) ', f'\t\t\t\\127 = (\\125-1)%{PER}',
          '\t\tendif', '\tendif', '']
    return L


def build_script(src: bytes) -> bytes:
    blocks = cstx.load_bytes(src)
    if len(blocks) != 1:
        raise PatchError('saveload.cstx: unexpected structure')
    patch_script(blocks[0])
    return cstx.dump(blocks)


def generate(orig: dict) -> dict:
    """orig: {path: bytes} for PATHS -> {path: patched bytes}"""
    return {
        'fes/saveload.cstx': build_script(orig['fes/saveload.cstx']),
        'image/sys/sys_saveload.atx': build_saveload_atx(orig['image/sys/sys_saveload.atx']),
        'image/sys/sys_saveload_panel.atx': build_panel_atx(orig['image/sys/sys_saveload_panel.atx']),
    }


def is_patched(path: str, data: bytes) -> bool:
    """Recognises files written by this tool (used by uninstall)."""
    try:
        if path.endswith('.cstx'):
            return '#SETTABS' in cstx.load_bytes(data)[0]
        z = zipfile.ZipFile(io.BytesIO(data))
        j = json.loads(z.read('atlas.json').decode('utf-8-sig'))
        ids = {b['id'] for b in j['Block']}
        return (1900 in ids and 2000 in ids) if path.endswith('sys_saveload.atx') else (34 in ids and 35 in ids)
    except Exception:
        return False
