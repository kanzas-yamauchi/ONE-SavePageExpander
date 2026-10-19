"""Protobuf encoder for the atlas LayoutInfo (atlas.pb) read by the engine."""
import struct
def varint(n):
    if n<0: n+=1<<64
    o=bytearray()
    while True:
        b=n&0x7f;n>>=7
        if n: o.append(b|0x80)
        else: o.append(b); return bytes(o)
def key(f,w): return varint((f<<3)|w)
def f_int(f,v): return b'' if not v else key(f,0)+varint(int(v))
def f_float(f,v): return b'' if not v else key(f,5)+struct.pack('<f',float(v))
def f_str(f,v):
    if v is None: return b''
    b=v.encode('utf-8'); return key(f,2)+varint(len(b))+b
def f_msg(f,b): return key(f,2)+varint(len(b))+b
MESH=['texNo','offsetX','offsetY','srcOffsetX','srcOffsetY','texU1','texV1','texU2','texV2','viewX','viewY','width','height']
def mesh(m):
    return f_int(1,m['texNo'])+b''.join(f_float(i+2,m[k]) for i,k in enumerate(MESH[1:]))
def attr(a):
    return b''.join(f_int(i+1,a[k]) for i,k in enumerate(['id','x','y','width','height','color']))
BF=[('filename',1,'s'),('filenameOld',2,'s'),('id',3,'i'),('anchorX',4,'f'),('anchorY',5,'f'),('width',6,'f'),('height',7,'f'),('offsetX',8,'f'),('offsetY',9,'f'),('priority',10,'i')]
def block(b):
    o=b''
    for k,f,t in BF:
        v=b.get(k)
        o+= f_str(f,v) if t=='s' else f_int(f,v) if t=='i' else f_float(f,v)
    for m in b.get('Mesh') or []: o+=f_msg(11,mesh(m))
    for a in b.get('Attribute') or []: o+=f_msg(12,attr(a))
    if b.get('blend') is not None: o+=f_str(13,b['blend'])
    return o
def layout(j):
    c=j['Canvas']; o=f_msg(1,f_int(1,c['Width'])+f_int(2,c['Height']))
    for b in j['Block']: o+=f_msg(2,block(b))
    return o
