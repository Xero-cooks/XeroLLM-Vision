import os,time
from test_gateway import client,A,url,payload

def test_health_and_unauthorized_requests_do_not_keep_runtime_alive(tmp_path,monkeypatch):
 p=tmp_path/'activity';monkeypatch.setenv('GATEWAY_ACTIVITY_FILE',str(p))
 with client() as c:
  assert c.get('/health',headers=A).status_code==200
  assert c.post('/v1/ocr',json={'image_url':url()}).status_code==401
  assert not p.exists()

def test_real_ocr_workload_updates_private_activity(tmp_path,monkeypatch):
 p=tmp_path/'activity';monkeypatch.setenv('GATEWAY_ACTIVITY_FILE',str(p))
 with client() as c:
  assert c.post('/v1/ocr',headers=A,json={'image_url':url()}).status_code==200
  assert p.exists() and p.stat().st_mtime>time.time()-10

def test_stream_completion_marks_activity(tmp_path,monkeypatch):
 p=tmp_path/'activity';monkeypatch.setenv('GATEWAY_ACTIVITY_FILE',str(p))
 with client() as c:
  r=c.post('/v1/chat/completions',headers={**A,'X-Dry-Run':'true'},json=payload(True))
  assert '[DONE]' in r.text and p.exists()
