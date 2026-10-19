"""CatSystem compiled script container (CSTX): zlib-deflated list of text blocks."""
import struct,zlib,json,sys
def rlen(d,p):
    n=0;s=0
    while True:
        b=d[p];p+=1;n|=(b&0x7f)<<s;s+=7
        if b<128: return n,p
def wlen(n):
    o=bytearray()
    while True:
        b=n&0x7f;n>>=7
        if n: b|=0x80
        o.append(b)
        if b<128: return bytes(o)
def load(path):
    return load_bytes(open(path,'rb').read())
def load_bytes(d):
    if d[:4]!=b'CSTX': raise ValueError('not a CSTX file')
    orig,clen,mode=struct.unpack_from('<iii',d,4)
    raw=zlib.decompress(d[16:16+clen],-15); assert len(raw)==orig and mode==1
    p=0; nb=struct.unpack_from('<i',raw,0)[0]; p=4; blocks=[]
    for _ in range(nb):
        n,p=rlen(raw,p); bl=[]
        for _ in range(n):
            l,p=rlen(raw,p); bl.append(raw[p:p+l].decode('utf-8')); p+=l
        blocks.append(bl)
    assert p==len(raw)
    return blocks
def dump(blocks):
    raw=bytearray(struct.pack('<i',len(blocks)))
    for bl in blocks:
        raw+=wlen(len(bl))
        for s in bl:
            b=s.encode('utf-8'); raw+=wlen(len(b))+b
    co=zlib.compressobj(9,zlib.DEFLATED,-15); c=co.compress(bytes(raw))+co.flush()
    return b'CSTX'+struct.pack('<iii',len(raw),len(c),1)+c
