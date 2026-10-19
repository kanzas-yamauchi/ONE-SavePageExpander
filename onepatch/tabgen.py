"""Builds page-tab images for pages 16+ by recomposing the digit glyphs
found in the user's own page tabs 1..10 (no game art is shipped)."""
import numpy as np
from PIL import Image

Y0, Y1 = 19, 39  # rows that contain the number glyph
TAB_BASE = 100   # block id of tab "1" in state 0; state s / page p -> 100+20*s+(p-1)


class TabGen:
    def __init__(self, atx):
        self.a = atx
        self.cache = {}

    def state_data(self, st):
        T = np.stack([np.asarray(self.a.block(TAB_BASE + st * 20 + i)).astype(float) for i in range(16)])
        lum = T[..., :3].mean(-1)
        idx = lum.argmax(0) if st == 0 else lum.argmin(0)
        bg = np.take_along_axis(T, idx[None, ..., None].repeat(4, -1), 0)[0]
        return T, bg

    def glyphs(self, st):
        T, bg = self.state_data(st)
        bl = bg[..., :3].mean(-1)
        G = {}

        def alpha(t):
            pl = T[t][..., :3].mean(-1)
            if st == 0:
                gl = pl[Y0:Y1].min(); a_ = (bl - pl) / np.maximum(bl - gl, 1)
            else:
                gl = pl[Y0:Y1].max(); a_ = (pl - bl) / np.maximum(gl - bl, 1)
            a_ = np.clip(a_, 0, 1); a_[:Y0] = 0; a_[Y1:] = 0
            return a_

        t = 5; pl = T[t][..., :3].mean(-1)
        sub = T[t][Y0:Y1]
        k = np.unravel_index((pl[Y0:Y1].argmin() if st == 0 else pl[Y0:Y1].argmax()), pl[Y0:Y1].shape)
        col = sub[k][:3]

        def crop(am, x0, x1):
            return am[:, x0:x1 + 1]

        for d in range(1, 10):
            am = alpha(d - 1); cols = np.nonzero(am.max(0) > 0.15)[0]
            G[str(d)] = crop(am, cols.min(), cols.max())
        am = alpha(9); cols = np.nonzero(am.max(0) > 0.15)[0]  # tab "10": take the "0"
        xs = [x for x in range(cols.min(), cols.max() + 1) if am[:, x].max() <= 0.15]
        mid = xs[len(xs) // 2] if xs else 30
        c0 = [c for c in cols if c > mid]
        G['0'] = crop(am, min(c0), max(c0))
        return bg, col, G

    def make(self, text, st):
        if st not in self.cache:
            self.cache[st] = self.glyphs(st)
        bg, col, G = self.cache[st]
        gap = 2
        parts = [G[c] for c in text]
        w = sum(p.shape[1] for p in parts) + gap * (len(parts) - 1)
        x = int(round(33.5 + 0.5 - w / 2))
        A = np.zeros(bg.shape[:2])
        for p in parts:
            A[:, x:x + p.shape[1]] = np.maximum(A[:, x:x + p.shape[1]], p); x += p.shape[1] + gap
        out = bg.copy()
        out[..., :3] = bg[..., :3] * (1 - A[..., None]) + col * A[..., None]
        return Image.fromarray(np.clip(out, 0, 255).astype('uint8'), 'RGBA')
