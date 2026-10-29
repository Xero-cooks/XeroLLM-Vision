"""Exact tile hashes; safe crop reuse only, NOT skipping global detection at tile seams.
No 4–9ms claim. Full unchanged frames hit an exact byte cache. Partial reuse requires
exact tile contents, bbox and crop digest; boundary-crossing boxes are never reused.
"""
from collections import OrderedDict
import hashlib
class UIDeltaCache:
    def __init__(self,max_entries:int=64,max_bytes:int=64_000_000): self.items=OrderedDict();self.max_entries=max_entries;self.max_bytes=max_bytes;self.bytes=0
    def get(self,key:str):
        if key not in self.items:return None
        v,n=self.items.pop(key);self.items[key]=(v,n);return v
    def put(self,key:str,value,size:int=1024)->None:
        if key in self.items:self.bytes-=self.items.pop(key)[1]
        if size>self.max_bytes:return
        self.items[key]=(value,size);self.bytes+=size
        while len(self.items)>self.max_entries or self.bytes>self.max_bytes:
            _,(_,n)=self.items.popitem(last=False);self.bytes-=n
    @staticmethod
    def tile_hashes(frame)->list[str]:
        # Frame is CHW uint8 torch tensor or HWC numpy array. GPU path uses SIMD
        # reductions then verifies crop bytes with SHA256 before cache reuse.
        import numpy as np
        h,w=frame.shape[:2];th,tw=(h+3)//4,(w+3)//4;return [hashlib.sha256(np.ascontiguousarray(frame[y*th:min(h,(y+1)*th),x*tw:min(w,(x+1)*tw)]).tobytes()).hexdigest() for y in range(4) for x in range(4)]
    @staticmethod
    def tile_for(box,w:int,h:int)->int|None:
        x0,y0,x1,y1=box
        tw,th=(w+3)//4,(h+3)//4
        a=(int(x0//tw),int(y0//th));b=(min(3,int(max(x0,x1-1)//tw)),min(3,int(max(y0,y1-1)//th)))
        return a[1]*4+a[0] if a==b and 0<=a[0]<4 and 0<=a[1]<4 else None
