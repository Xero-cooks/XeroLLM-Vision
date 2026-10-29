"""Download a pinned wheel as data, verify PyPI SHA256, extract only model assets.
No package import/install, no unsafe archive paths; CPU ORT is not installed over GPU ORT.
"""
import pathlib,json,urllib.request,hashlib,zipfile,io
VERSION='1.4.4'
def acquire(directory:str='models')->dict:
    root=pathlib.Path(directory);root.mkdir(parents=True,exist_ok=True)
    receipt=root/'assets.json'
    if receipt.exists():
        j=json.loads(receipt.read_text())
        if all((root/name).exists() and hashlib.sha256((root/name).read_bytes()).hexdigest()==info['sha256'] for name,info in j['files'].items()):return j
    req=urllib.request.Request(f'https://pypi.org/pypi/rapidocr-onnxruntime/{VERSION}/json')
    with urllib.request.urlopen(req,timeout=30) as r:meta=json.load(r)
    wheel=next(x for x in meta['urls'] if x['filename'].endswith('.whl'))
    with urllib.request.urlopen(wheel['url'],timeout=60) as r:blob=r.read(40_000_001)
    if len(blob)>40_000_000 or hashlib.sha256(blob).hexdigest()!=wheel['digests']['sha256']:raise RuntimeError('model wheel integrity failure')
    files={}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if name.endswith('.onnx') or ('dict' in name.lower() and name.endswith('.txt')):
                data=z.read(name);out=root/pathlib.PurePosixPath(name).name;out.write_bytes(data);files[out.name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    j={'package':f'rapidocr-onnxruntime=={VERSION}','wheel_sha256':wheel['digests']['sha256'],'files':files};receipt.write_text(json.dumps(j,indent=2));return j
if __name__=='__main__':print(json.dumps(acquire(),indent=2))
