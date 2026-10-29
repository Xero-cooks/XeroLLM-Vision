"""Discover pip-installed NVIDIA libraries without hard-coded Python minor versions."""
from __future__ import annotations
import os,pathlib,site

def gpu_library_paths()->list[str]:
    paths=[]
    for root in site.getsitepackages()+[site.getusersitepackages()]:
        base=pathlib.Path(root)
        candidates=[base/'torch/lib',*base.glob('nvidia/*/lib'),*base.glob('tensorrt*')]
        for p in candidates:
            if p.is_dir() and any(p.glob('*.so*')) and str(p) not in paths:paths.append(str(p))
    return paths

def child_library_path()->str:
    return ':'.join(gpu_library_paths()+[p for p in os.getenv('LD_LIBRARY_PATH','').split(':') if p])

def preload_tensorrt()->dict:
    """Best-effort loading; caller must verify actual session providers separately."""
    import ctypes
    loaded=[];errors=[]
    for name in ('libnvinfer.so.10','libnvonnxparser.so.10','libnvinfer_plugin.so.10'):
        matches=[pathlib.Path(d)/name for d in gpu_library_paths() if (pathlib.Path(d)/name).exists()]
        if matches:
            try:ctypes.CDLL(str(matches[0]),mode=ctypes.RTLD_GLOBAL);loaded.append(name)
            except OSError as e:errors.append({'library':name,'error':str(e)[:300]})
    return {'loaded':loaded,'errors':errors}

if __name__=='__main__':print(child_library_path())
