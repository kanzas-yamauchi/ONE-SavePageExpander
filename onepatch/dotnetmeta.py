"""Minimal ECMA-335 metadata reader.

Used to read the value of a string constant field (e.g. the package password)
from the game's own Assembly-CSharp.dll at runtime, so that this repository does
not need to ship it.
"""
import struct

# table ids used for coded index sizes
T_Module, T_TypeRef, T_TypeDef, T_FieldPtr, T_Field, T_MethodPtr, T_MethodDef = 0, 1, 2, 3, 4, 5, 6
T_ParamPtr, T_Param, T_InterfaceImpl, T_MemberRef, T_Constant = 7, 8, 9, 10, 11
T_Property, T_ModuleRef, T_TypeSpec, T_AssemblyRef = 0x17, 0x1A, 0x1B, 0x23


class Meta:
    def __init__(self, data: bytes):
        self.d = d = data
        pe = struct.unpack_from('<I', d, 0x3C)[0]
        if d[pe:pe + 4] != b'PE\0\0':
            raise ValueError('not a PE file')
        nsec, = struct.unpack_from('<H', d, pe + 6)
        optsz, = struct.unpack_from('<H', d, pe + 20)
        opt = pe + 24
        magic, = struct.unpack_from('<H', d, opt)
        ddir = opt + (96 if magic == 0x10B else 112)
        cli_rva, _ = struct.unpack_from('<II', d, ddir + 14 * 8)
        self.secs = []
        so = opt + optsz
        for i in range(nsec):
            vsz, va, rsz, rptr = struct.unpack_from('<IIII', d, so + i * 40 + 8)
            self.secs.append((va, max(vsz, rsz), rptr))
        cli = self.off(cli_rva)
        md_rva, _ = struct.unpack_from('<II', d, cli + 8)
        md = self.off(md_rva)
        if struct.unpack_from('<I', d, md)[0] != 0x424A5342:
            raise ValueError('no CLI metadata')
        vlen, = struct.unpack_from('<I', d, md + 12)
        p = md + 16 + vlen + 2
        nstreams, = struct.unpack_from('<H', d, p); p += 2
        self.streams = {}
        for _ in range(nstreams):
            o, sz = struct.unpack_from('<II', d, p); p += 8
            e = d.index(b'\0', p); name = d[p:e].decode('ascii')
            p = (e + 4) & ~3
            self.streams[name] = (md + o, sz)
        self._tables()

    def off(self, rva):
        for va, sz, rptr in self.secs:
            if va <= rva < va + sz:
                return rva - va + rptr
        raise ValueError('rva not mapped')

    def string(self, i):
        o, _ = self.streams['#Strings']
        e = self.d.index(b'\0', o + i)
        return self.d[o + i:e].decode('utf-8', 'replace')

    def blob(self, i):
        o, _ = self.streams['#Blob']
        p = o + i; b = self.d[p]
        if b & 0x80 == 0:
            n = b; p += 1
        elif b & 0xC0 == 0x80:
            n = ((b & 0x3F) << 8) | self.d[p + 1]; p += 2
        else:
            n = ((b & 0x1F) << 24) | (self.d[p + 1] << 16) | (self.d[p + 2] << 8) | self.d[p + 3]; p += 4
        return self.d[p:p + n]

    def _tables(self):
        d = self.d
        o, _ = self.streams.get('#~') or self.streams['#-']
        heap = d[o + 6]
        valid, = struct.unpack_from('<Q', d, o + 8)
        p = o + 24
        self.rows = [0] * 64
        for t in range(64):
            if valid >> t & 1:
                self.rows[t], = struct.unpack_from('<I', d, p); p += 4
        S = 4 if heap & 1 else 2
        G = 4 if heap & 2 else 2
        B = 4 if heap & 4 else 2
        def idx(t): return 4 if self.rows[t] >= 0x10000 else 2
        def coded(ts, bits): return 4 if max(self.rows[t] for t in ts) >= (1 << (16 - bits)) else 2
        RS = coded([T_Module, T_ModuleRef, T_AssemblyRef, T_TypeRef], 2)
        TDR = coded([T_TypeDef, T_TypeRef, T_TypeSpec], 2)
        MRP = coded([T_TypeDef, T_TypeRef, T_ModuleRef, T_MethodDef, T_TypeSpec], 3)
        HC = coded([T_Field, T_Param, T_Property], 2)
        # column layouts of tables 0..11 (enough to reach Constant)
        self.layout = {
            T_Module: [2, S, G, G, G],
            T_TypeRef: [RS, S, S],
            T_TypeDef: [4, S, S, TDR, idx(T_Field), idx(T_MethodDef)],
            T_FieldPtr: [idx(T_Field)],
            T_Field: [2, S, B],
            T_MethodPtr: [idx(T_MethodDef)],
            T_MethodDef: [4, 2, 2, S, B, idx(T_Param)],
            T_ParamPtr: [idx(T_Param)],
            T_Param: [2, 2, S],
            T_InterfaceImpl: [idx(T_TypeDef), TDR],
            T_MemberRef: [MRP, S, B],
            T_Constant: [1, 1, HC, B],
        }
        self.tstart = {}
        for t in range(T_Constant + 1):
            self.tstart[t] = p
            p += self.rows[t] * sum(self.layout[t])

    def row(self, t, i):  # i: 0-based
        cols = self.layout[t]
        p = self.tstart[t] + i * sum(cols)
        out = []
        for c in cols:
            out.append(int.from_bytes(self.d[p:p + c], 'little')); p += c
        return out

    def string_constants(self, field_name):
        """Return the values of all string-constant fields called field_name."""
        rids = [i + 1 for i in range(self.rows[T_Field])
                if self.string(self.row(T_Field, i)[1]) == field_name]
        want = {(r << 2) | 0 for r in rids}
        vals = []
        for i in range(self.rows[T_Constant]):
            typ, _, parent, val = self.row(T_Constant, i)
            if typ == 0x0E and parent in want:
                vals.append(self.blob(val).decode('utf-16-le'))
        return vals
