"""Reader for CatSystem .atx atlases (zip of texN.png + atlas.json + atlas.pb)."""
import io, json, zipfile
from PIL import Image


class Atx:
    def __init__(self, data: bytes):
        self.raw = data
        self.z = z = zipfile.ZipFile(io.BytesIO(data))
        self.tex = []
        i = 0
        while f'tex{i}.png' in z.namelist():
            self.tex.append(Image.open(io.BytesIO(z.read(f'tex{i}.png'))).convert('RGBA')); i += 1
        self.j = json.loads(z.read('atlas.json').decode('utf-8-sig'))
        self.blocks = {b['id']: b for b in self.j['Block']}

    def block(self, id):
        """Render one block (sprite) to an RGBA image of the block size."""
        b = self.blocks[id]
        im = Image.new('RGBA', (int(b['width']), int(b['height'])), (0, 0, 0, 0))
        for m in b['Mesh']:
            t = self.tex[m['texNo']]
            c = t.crop((int(m['viewX']), int(m['viewY']),
                        int(m['viewX'] + m['width']), int(m['viewY'] + m['height'])))
            im.alpha_composite(c, (int(m['srcOffsetX']), int(m['srcOffsetY'])))
        return im
