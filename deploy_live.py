"""Prepare a PRIVATE, bounded Kaggle service. Never embeds provider or gateway keys.
Only a scoped, one-use, expiring bootstrap ticket is put in generated private code.
Do not publish generated deployment folders or their bootstrap capability.
"""
from __future__ import annotations
import argparse,base64,hashlib,io,json,pathlib,zipfile
from urllib.parse import urlsplit
from deploy_kaggle import FILES
ROOT=pathlib.Path(__file__).parent

def prepare_live(owner:str,out:pathlib.Path,broker_url:str,ticket:str,cloudflared:dict,session_seconds:int=3600)->dict:
    u=urlsplit(broker_url)
    if u.scheme!='https' or not (u.hostname or '').endswith('.trycloudflare.com') or u.username or u.password or u.path not in ('','/'):raise ValueError('use the authenticated HTTPS enrollment broker')
    if not 32<=len(ticket)<=256:raise ValueError('invalid bootstrap ticket')
    out.mkdir(parents=True,exist_ok=True);buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:z.write(ROOT/name,name)
        for p in (ROOT/'tests').glob('*.py'):z.write(p,str(p.relative_to(ROOT)))
    data=buf.getvalue()
    # Only this generated PRIVATE artifact contains the expiring one-use capability.
    script='''import base64,hashlib,io,json,os,pathlib,sys,urllib.request,zipfile
root=pathlib.Path('/kaggle/working/mercury3_vision_gateway');root.mkdir(parents=True,exist_ok=True)
blob=base64.b64decode(PAYLOAD)
assert hashlib.sha256(blob).hexdigest()==SHA
with zipfile.ZipFile(io.BytesIO(blob)) as z:z.extractall(root)
os.chdir(root);sys.path.insert(0,str(root))
request=urllib.request.Request(BROKER+'/enroll',data=b'{}',headers={'Authorization':'Bearer '+TICKET,'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=30) as response:runtime=json.loads(response.read())
from live_session import run
run(runtime,BROKER,DURATION,CLOUDFLARED)
'''
    values={'PAYLOAD':repr(base64.b64encode(data).decode()),'SHA':repr(hashlib.sha256(data).hexdigest()),'BROKER':repr(broker_url.rstrip('/')),'TICKET':repr(ticket),'DURATION':str(max(300,min(session_seconds,3600))),'CLOUDFLARED':repr(cloudflared)}
    import re
    script=re.sub(r'\b(PAYLOAD|SHA|BROKER|TICKET|DURATION|CLOUDFLARED)\b',lambda m:values[m[0]],script)
    p=out/'live_bootstrap.py';p.write_text(script);p.chmod(0o600)
    meta={'id':owner+'/mercury3-vision-gateway-live-session','title':'Mercury3 Vision Gateway Live Session','code_file':'live_bootstrap.py','language':'python','kernel_type':'script','is_private':True,'enable_gpu':True,'enable_internet':True,'machine_shape':'NvidiaTeslaT4','dataset_sources':[],'competition_sources':[],'kernel_sources':[]}
    (out/'kernel-metadata.json').write_text(json.dumps(meta,indent=2));return meta

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owner',required=True);p.add_argument('--out',required=True);p.add_argument('--broker-url',required=True);p.add_argument('--ticket-file',required=True);p.add_argument('--cloudflared-manifest',required=True);p.add_argument('--session-seconds',type=int,default=3600);a=p.parse_args()
    print(json.dumps(prepare_live(a.owner,pathlib.Path(a.out),a.broker_url,pathlib.Path(a.ticket_file).read_text().strip(),json.loads(pathlib.Path(a.cloudflared_manifest).read_text()),a.session_seconds)))
