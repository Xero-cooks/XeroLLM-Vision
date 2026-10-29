"""Short-lived HTTPS rendezvous for a private Kaggle job, never a public key store.
Run behind TLS. Bootstrap ticket is one-use and expires. No secret payload logging.
"""
from __future__ import annotations
import json,os,pathlib,secrets,time
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse

def create_broker(config_path:str)->FastAPI:
    cfg=json.loads(pathlib.Path(config_path).read_text());claimed=False
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    async def bounded(request:Request)->dict:
        body=bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk)>8192:raise HTTPException(413,'payload too large')
            body.extend(chunk)
        try:j=json.loads(body)
        except ValueError:raise HTTPException(400,'invalid JSON')
        if not isinstance(j,dict):raise HTTPException(400,'JSON object required')
        return j
    def auth(request:Request,token:str):
        if not secrets.compare_digest(request.headers.get('authorization',''),'Bearer '+token):raise HTTPException(401,'invalid enrollment credentials')
    @app.post('/enroll')
    async def enroll(request:Request):
        nonlocal claimed
        auth(request,cfg['bootstrap_token'])
        if claimed or time.time()>cfg['expires_unix']:raise HTTPException(410,'enrollment no longer available')
        await bounded(request)
        if claimed or time.time()>cfg['expires_unix']:raise HTTPException(410,'enrollment no longer available')
        keys=json.loads(pathlib.Path(cfg['provider_pool_file']).read_text())['keys']
        claimed=True
        return JSONResponse({'keys':keys,'gateway_token':cfg['gateway_token'],'admin_token':cfg['admin_token'],'report_token':cfg['report_token']},headers={'Cache-Control':'no-store'})
    @app.post('/report')
    async def report(request:Request):
        auth(request,cfg['report_token']);j=await bounded(request)
        allowed={'phase','public_url','backend','gpu_count','session_end_unix','error_code','provider_real_keys','upstream_attempts','completion_tokens','cached_file_count'}
        clean={k:v for k,v in j.items() if k in allowed and isinstance(v,(str,int,float,bool))}
        if any(isinstance(v,str) and len(v)>300 for v in clean.values()):raise HTTPException(400,'field too long')
        if 'public_url' in clean:
            from urllib.parse import urlsplit
            u=urlsplit(clean['public_url'])
            if u.scheme!='https' or not (u.hostname or '').endswith('.trycloudflare.com') or u.username or u.password or u.port not in (None,443) or u.path not in ('','/'):raise HTTPException(400,'unexpected public endpoint')
        p=pathlib.Path(cfg['report_file']);records=json.loads(p.read_text()) if p.exists() else []
        records.append({'received_unix':time.time(),**clean});p.write_text(json.dumps(records[-100:],indent=2));p.chmod(0o600)
        return {'accepted':True}
    return app
app=create_broker(os.environ['DEPLOYMENT_BROKER_CONFIG']) if os.getenv('DEPLOYMENT_BROKER_CONFIG') else FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
