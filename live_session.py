"""Bounded Kaggle serving process. Provider credentials stay in process memory/env.
No keep-alive/anti-idle tricks, no public admin routes, no indefinite uptime claim.
"""
from __future__ import annotations
import base64,contextlib,hashlib,importlib.metadata,json,os,pathlib,re,shutil,subprocess,sys,time,urllib.request

def run(runtime:dict,broker_url:str,session_seconds:int,cloudflared:dict)->None:
    def report(phase:str,**fields):
        payload=json.dumps({'phase':phase,**fields}).encode()
        req=urllib.request.Request(broker_url+'/report',data=payload,headers={'Authorization':'Bearer '+runtime['report_token'],'Content-Type':'application/json'})
        with contextlib.suppress(Exception):
            with urllib.request.urlopen(req,timeout=10) as r:r.read(1024)
    root=pathlib.Path.cwd();processes=[];logs=[]
    os.environ.update(PYTHONUNBUFFERED='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    try:
        # Optional trusted, private validation output supplies compatible model/engine caches.
        for receipt in pathlib.Path('/kaggle/input').rglob('assets.json'):
            source=receipt.parent
            if source.name!='models':continue
            candidates=[p for p in source.rglob('*') if p.is_file()]
            if len(candidates)>2000 or sum(p.stat().st_size for p in candidates)>2_000_000_000:continue
            shutil.copytree(source,root/'models',dirs_exist_ok=True)
            report('model_cache_restored',cached_file_count=len(candidates));break
        report('installing_dependencies')
        with open('install.log','w') as log:
            def pip(*args,timeout=900):subprocess.run([sys.executable,'-m','pip',*args],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout)
            subprocess.run([sys.executable,'-m','pip','uninstall','-y','onnxruntime'],stdout=log,stderr=log,check=False)
            pip('install','-q','-r','requirements.txt')
            try:matched=importlib.metadata.version('torch').split('+')[0]=='2.7.1' and importlib.metadata.version('torchvision').split('+')[0]=='0.22.1'
            except importlib.metadata.PackageNotFoundError:matched=False
            if not matched:pip('install','-q','torch==2.7.1','torchvision==0.22.1','--index-url','https://download.pytorch.org/whl/cu126')
            pip('install','-q','tensorrt-cu12==10.9.0.34')
        from runtime_env import child_library_path
        os.environ['LD_LIBRARY_PATH']=child_library_path()
        subprocess.run([sys.executable,'doctor.py'],stdout=open('doctor.json','w'),check=True)
        subprocess.run([sys.executable,'-m','pytest','-q','tests'],check=True,timeout=180)
        binary=root/'cloudflared';data=urllib.request.urlopen(cloudflared['url'],timeout=60).read()
        if hashlib.sha256(data).hexdigest()!=cloudflared['sha256']:raise RuntimeError('tunnel_binary_hash_mismatch')
        binary.write_bytes(data);binary.chmod(0o700)
        env=os.environ.copy();env.update(GATEWAY_TOKEN=runtime['gateway_token'],GATEWAY_ADMIN_TOKEN=runtime['admin_token'],INCEPTION_API_KEYS=','.join(runtime['keys']),OCR_BACKEND='gpu',ENABLE_TENSORRT='true',TRT_BUILDER_OPT_LEVEL='1',KEY_RATE_LIMIT_SCOPE='key')
        def spawn(command,filename,child_env):
            f=open(filename,'w');logs.append(f);p=subprocess.Popen(command,env=child_env,stdout=f,stderr=f);processes.append(p);return p
        report('preparing_tensorrt_engines')
        gateway=spawn([sys.executable,'-m','uvicorn','gateway_server:app','--host','127.0.0.1','--port','8000','--workers','1','--no-access-log'],'gateway.log',env)
        import httpx
        auth={'Authorization':'Bearer '+runtime['gateway_token']}
        from cloudflare_transport import CloudflareDNSTransport
        with httpx.Client(timeout=120,trust_env=False,transport=CloudflareDNSTransport()) as client:
            deadline=time.time()+1800
            while time.time()<deadline:
                if gateway.poll() is not None:raise RuntimeError('gateway_startup_failed')
                try:
                    health=client.get('http://127.0.0.1:8000/health',headers=auth,timeout=3)
                    if health.status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(5)
            else:raise RuntimeError('gateway_startup_timeout')
            state=health.json()
            if state['ocr']['gpu_count']<2:raise RuntimeError('two_gpu_target_not_allocated')
            from benchmark_700toks import fixture
            image='data:image/jpeg;base64,'+base64.b64encode(fixture(0)).decode()
            encoded=client.post('http://127.0.0.1:8000/v1/ocr',headers=auth,json={'image_url':image})
            encoded.raise_for_status()
            if len(encoded.json().get('elements',[]))<5:raise RuntimeError('real_ocr_smoke_failed')
            report('starting_public_ingress',backend=state['ocr']['backend'],gpu_count=state['ocr']['gpu_count'],provider_real_keys=state['pool']['real_keys'])
            edge_env=os.environ.copy();edge_env['GATEWAY_TOKEN']=runtime['gateway_token']
            edge=spawn([sys.executable,'-m','uvicorn','public_edge:app','--host','127.0.0.1','--port','8080','--workers','1','--no-access-log'],'edge.log',edge_env)
            for _ in range(30):
                try:
                    if client.get('http://127.0.0.1:8080/v1/models',headers=auth,timeout=3).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(1)
            else:raise RuntimeError('public_ingress_startup_failed')
            tunnel=spawn([str(binary),'tunnel','--no-autoupdate','--protocol','http2','--url','http://127.0.0.1:8080'],'tunnel.log',os.environ.copy())
            public_url=None
            for _ in range(90):
                if tunnel.poll() is not None:raise RuntimeError('tunnel_startup_failed')
                match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',(root/'tunnel.log').read_text())
                if match:
                    public_url=match.group()
                    try:
                        if client.get(public_url+'/v1/models',headers=auth,timeout=10).status_code==200:break
                    except httpx.HTTPError:pass
                time.sleep(2)
            else:raise RuntimeError('public_tunnel_not_reachable')
            report('testing_live_provider',public_url=public_url)
            payload={'model':'mercury-3','max_tokens':64,'messages':[{'role':'user','content':[{'type':'text','text':'Name three visible navigation labels.'},{'type':'image_url','image_url':{'url':image}}]}]}
            real=client.post(public_url+'/v1/chat/completions',headers=auth,json=payload);real.raise_for_status()
            if real.headers.get('x-gateway-simulation')=='true':raise RuntimeError('live_request_was_simulated')
            if not real.json().get('choices'):raise RuntimeError('live_provider_completion_missing')
            with client.stream('POST',public_url+'/v1/chat/completions',headers=auth,json={**payload,'stream':True}) as response:
                response.raise_for_status();done=False
                for line in response.iter_lines():
                    if line.strip()=='data: [DONE]':done=True;break
                if not done:raise RuntimeError('live_sse_not_completed')
            if client.get(public_url+'/admin/keys/status',headers=auth).status_code!=404:raise RuntimeError('admin_public_route_exposed')
            if client.get(public_url+'/v1/models').status_code!=401:raise RuntimeError('public_auth_not_enforced')
            end=time.time()+max(300,min(session_seconds,3600))
            report('ready',public_url=public_url,backend=state['ocr']['backend'],gpu_count=state['ocr']['gpu_count'],session_end_unix=end,provider_real_keys=state['pool']['real_keys'],completion_tokens=real.json().get('usage',{}).get('completion_tokens',0),upstream_attempts=int(real.headers.get('x-upstream-attempts','0')))
            while time.time()<end:
                if any(p.poll() is not None for p in processes):raise RuntimeError('serving_process_exited')
                time.sleep(min(20,max(0,end-time.time())))
            report('session_expired',public_url=public_url)
    except Exception as error:
        # Exception text can contain credentials/URLs, so report only class and safe runtime codes.
        safe=str(error) if isinstance(error,RuntimeError) and re.fullmatch('[a-z_]+',str(error)) else type(error).__name__
        report('failed',error_code=safe)
        pathlib.Path('LIVE_FAILURE.json').write_text(json.dumps({'error_code':safe}));raise RuntimeError(safe) from None
    finally:
        for process in reversed(processes):
            if process.poll() is None:process.terminate()
        for process in reversed(processes):
            with contextlib.suppress(subprocess.TimeoutExpired):process.wait(timeout=20)
            if process.poll() is None:process.kill()
        for log in logs:log.close()
