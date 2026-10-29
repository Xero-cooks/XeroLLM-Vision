"""Prepare a private, bounded Kaggle GPU verification job, using kaggle CLI auth.
No provider keys or local gateway credentials are embedded. Review outputs, not submission success.
"""
import argparse,base64,hashlib,io,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).parent
FILES=['cloudflare_transport.py','agent_client.py','deploy_live.py','live_session.py','public_edge.py','deployment_broker.py','deploy_kaggle.py','verify_quality.py','runtime_env.py','ctc_graph.py','config.py','api_pool.py','gpu_ocr_engine.py','ui_delta_cache.py','spatial_serializer.py','payload_transformer.py','gateway_server.py','model_assets.py','encoder_protocol.py','benchmark_700toks.py','doctor.py','smoke_test.py','requirements.txt','pytest.ini']
def prepare(owner:str,out:pathlib.Path):
    out.mkdir(parents=True,exist_ok=True);buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:z.write(ROOT/name,name)
        for p in (ROOT/'tests').glob('*.py'):z.write(p,str(p.relative_to(ROOT)))
    data=buffer.getvalue();sha=hashlib.sha256(data).hexdigest();payload=base64.b64encode(data).decode()
    script='''import base64,hashlib,io,json,os,pathlib,secrets,subprocess,sys,time,zipfile
root=pathlib.Path('/kaggle/working/mercury3_vision_gateway');root.mkdir(parents=True,exist_ok=True)
blob=base64.b64decode(PAYLOAD)
assert hashlib.sha256(blob).hexdigest()==EXPECTED
with zipfile.ZipFile(io.BytesIO(blob)) as z:z.extractall(root)
os.chdir(root);sys.path.insert(0,str(root))
os.environ.update(PYTHONUNBUFFERED='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
preflight={'python':sys.version,'source_sha256':EXPECTED}
try:preflight['nvidia_smi']=subprocess.run(['nvidia-smi'],capture_output=True,text=True,timeout=30).stdout
except Exception as e:preflight['nvidia_smi_error']=type(e).__name__
pathlib.Path('preflight.json').write_text(json.dumps(preflight,indent=2))
try:
 # Remove the CPU distribution to avoid two packages owning the same namespace.
 subprocess.run([sys.executable,'-m','pip','uninstall','-y','onnxruntime'],check=False,timeout=60)
 subprocess.run([sys.executable,'-m','pip','install','-q','-r','requirements.txt','pytest==8.3.4','pytest-asyncio==0.25.0'],check=True,timeout=600)
 # A matched CUDA wheel pair is required for GPU JPEG decoding and I/O binding.
 try:
  import importlib.metadata as md
  matched=md.version('torch').split('+')[0]=='2.7.1' and md.version('torchvision').split('+')[0]=='0.22.1'
 except md.PackageNotFoundError:matched=False
 if not matched:subprocess.run([sys.executable,'-m','pip','install','-q','torch==2.7.1','torchvision==0.22.1','--index-url','https://download.pytorch.org/whl/cu126'],check=True,timeout=900)
 # TensorRT is optional only in the sense that CUDA EP fallback is explicit in health.
 try:subprocess.run([sys.executable,'-m','pip','install','-q','tensorrt-cu12==10.9.0.34'],check=True,timeout=600)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired):print('TensorRT install unavailable: CUDA fallback, target not verified')
 from runtime_env import child_library_path
 os.environ['LD_LIBRARY_PATH']=child_library_path()
 os.environ['OCR_BACKEND']='gpu'
 subprocess.run([sys.executable,'doctor.py'],check=True,stdout=open('doctor.json','w'))
 subprocess.run([sys.executable,'-m','pytest','-q','tests'],check=True)
 # First preserve a real CUDA baseline and endpoint receipts before long TensorRT preparation.
 os.environ['ENABLE_TENSORRT']='false'
 subprocess.run([sys.executable,'benchmark_700toks.py','--output','evidence/benchmark-cuda.json'],check=True,timeout=300)
 subprocess.run([sys.executable,'verify_quality.py'],check=True,timeout=180)
 env=os.environ.copy();env.update(GATEWAY_TOKEN=secrets.token_urlsafe(32),GATEWAY_ADMIN_TOKEN=secrets.token_urlsafe(32))
 process=subprocess.Popen([sys.executable,'-m','uvicorn','gateway_server:app','--host','127.0.0.1','--port','8000','--workers','1','--no-access-log'],env=env)
 try:
  import httpx
  for _ in range(90):
   if process.poll() is not None:raise RuntimeError('server startup failed')
   try:
    if httpx.get('http://127.0.0.1:8000/health',headers={'Authorization':'Bearer '+env['GATEWAY_TOKEN']},timeout=2).status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(2)
  subprocess.run([sys.executable,'smoke_test.py'],env=env,check=True,timeout=120)
 finally:process.terminate();process.wait(timeout=20)
 # Separately bounded TensorRT compilation/benchmark. Failure does not erase CUDA receipts.
 trt_env=os.environ.copy();trt_env.update(ENABLE_TENSORRT='true',TRT_BUILDER_OPT_LEVEL='1')
 try:subprocess.run([sys.executable,'benchmark_700toks.py','--output','evidence/benchmark-tensorrt.json'],env=trt_env,check=True,timeout=1500)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:pathlib.Path('TRT_FAILURE.json').write_text(json.dumps({'type':type(e).__name__,'message':str(e)[:500]},indent=2))
 print('Bounded verification completed. Read stage receipts; no public tunnel or live provider keys configured.')
except Exception as e:
 pathlib.Path('REMOTE_FAILURE.json').write_text(json.dumps({'type':type(e).__name__,'message':str(e)[:500]},indent=2));raise
'''.replace('PAYLOAD',repr(payload)).replace('EXPECTED',repr(sha))
    (out/'bootstrap.py').write_text(script)
    meta={'id':owner+'/mercury3-vision-gateway-t4-validation','title':'Mercury3 Vision Gateway T4 Validation','code_file':'bootstrap.py','language':'python','kernel_type':'script','is_private':True,'enable_gpu':True,'enable_internet':True,'machine_shape':'NvidiaTeslaT4','dataset_sources':[],'competition_sources':[],'kernel_sources':[]}
    (out/'kernel-metadata.json').write_text(json.dumps(meta,indent=2));return meta
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owner',required=True);p.add_argument('--out',default='../mercury3-kaggle-run');a=p.parse_args();print(json.dumps(prepare(a.owner,pathlib.Path(a.out)),indent=2))
