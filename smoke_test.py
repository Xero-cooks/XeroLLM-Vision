"""Exercises a running local server with real image bytes. Never prints bearer secrets."""
import base64,json,pathlib,os,httpx
r=pathlib.Path(__file__).parent;auth={'Authorization':'Bearer '+os.environ['GATEWAY_TOKEN']};admin={'Authorization':'Bearer '+os.environ['GATEWAY_ADMIN_TOKEN']};u='data:image/jpeg;base64,'+base64.b64encode((r/'evidence/fixtures/ui-0.jpg').read_bytes()).decode();checks={}
with httpx.Client(base_url=os.getenv('GATEWAY_URL','http://127.0.0.1:8000'),timeout=60) as c:
 health=c.get('/health',headers=auth);health.raise_for_status();checks['health']=health.json()
 ocr=c.post('/v1/ocr',headers=auth,json={'image_url':u,'frame_id':'smoke-frame'});ocr.raise_for_status();checks['real_ocr']={'elements':len(ocr.json()['elements']),'latency_ms':ocr.json()['ocr_latency_ms'],'backend':ocr.json()['backend']}
 p={'model':'mercury-3','max_tokens':64,'messages':[{'role':'user','content':[{'type':'text','text':'Summarize the screen'},{'type':'image_url','image_url':{'url':u}}]}]}
 for stream in (False,True):
  response=c.post('/v1/chat/completions',headers={**auth,'X-Dry-Run':'true'},json={**p,'stream':stream});response.raise_for_status();checks['mock_sse' if stream else 'mock_json']={'status':response.status_code,'simulation_label':response.headers.get('x-gateway-simulation'),'done_present':'[DONE]' in response.text if stream else None}
 x=c.post('/admin/keys',headers=admin,json={'keys':['PLACEHOLDER_RUNTIME_INJECTION'],'mode':'append'});x.raise_for_status();checks['hot_reload']=x.json();checks['unauthorized_admin_rejected']=c.get('/admin/keys/status',headers=auth).status_code==401
path=r/'evidence/http-smoke.json';path.write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
