import json,time,httpx
from fastapi.testclient import TestClient
from deployment_broker import create_broker
from public_edge import create_edge

def test_public_edge_blocks_admin_and_requires_auth():
    seen=[]
    def origin(r):seen.append(r);return httpx.Response(200,json={'object':'list','data':[]})
    with TestClient(create_edge('client-secret',httpx.MockTransport(origin))) as c:
        assert c.get('/admin/keys/status',headers={'Authorization':'Bearer client-secret'}).status_code==404
        assert c.get('/v1/models').status_code==401
        assert not seen
        assert c.get('/v1/models',headers={'Authorization':'Bearer client-secret'}).status_code==200
    assert len(seen)==1

def test_enrollment_is_authenticated_one_use_and_reporting_filters_secrets(tmp_path):
    pool=tmp_path/'pool.json';pool.write_text(json.dumps({'keys':['fake-provider-secret']}));out=tmp_path/'reports.json';config=tmp_path/'broker.json'
    config.write_text(json.dumps({'bootstrap_token':'enroll-secret','report_token':'report-secret','gateway_token':'client-secret','admin_token':'admin-secret','expires_unix':time.time()+300,'provider_pool_file':str(pool),'report_file':str(out)}))
    with TestClient(create_broker(str(config))) as c:
        assert c.post('/enroll',json={}).status_code==401
        auth={'Authorization':'Bearer enroll-secret'}
        assert c.post('/enroll',headers=auth,json={}).json()['keys']==['fake-provider-secret']
        assert c.post('/enroll',headers=auth,json={}).status_code==410
        r=c.post('/report',headers={'Authorization':'Bearer report-secret'},json={'phase':'ready','keys':'MUST_NOT_PERSIST','public_url':'https://unit-test.trycloudflare.com'})
        assert r.status_code==200 and 'MUST_NOT_PERSIST' not in out.read_text()
        assert c.post('/report',headers={'Authorization':'Bearer report-secret'},json={'public_url':'http://127.0.0.1'}).status_code==400

def test_private_deployment_does_not_embed_runtime_keys(tmp_path):
    import ast
    from deploy_live import prepare_live
    metadata=prepare_live('testowner',tmp_path,'https://unit-broker.trycloudflare.com','x'*40,{'url':'https://github.com/cloudflare/cloudflared/releases/download/v-test/cloudflared-linux-amd64','sha256':'0'*64},300)
    assert metadata['is_private'] and metadata['id'].endswith('-live-session')
    text=(tmp_path/'live_bootstrap.py').read_text();ast.parse(text)
    assert 'GATEWAY_TOKEN=' not in text and 'INCEPTION_API_KEYS=' not in text
    assert "'/enroll'" in text and 'x'*40 in text

def test_key_dataclass_repr_does_not_reveal_secrets():
    from api_pool import KeyState
    from config import Settings
    assert 'hidden-provider-secret' not in repr(KeyState('hidden-provider-secret'))
    assert 'hidden-provider-secret' not in repr(Settings(keys=['hidden-provider-secret'],gateway_token='private-client-token',admin_token='private-admin-token'))

def test_quick_tunnel_transport_pins_public_ip_and_preserves_tls_hostname(monkeypatch):
    from cloudflare_transport import CloudflareDNSTransport
    seen=[]
    monkeypatch.setattr('cloudflare_transport.public_ipv4',lambda host:['104.16.230.132'])
    def handle(self,request):seen.append(request);return httpx.Response(200,content=b'ok')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',handle)
    with httpx.Client(transport=CloudflareDNSTransport()) as c:assert c.get('https://unit-session.trycloudflare.com/health').status_code==200
    assert seen[0].url.host=='104.16.230.132' and seen[0].headers['host']=='unit-session.trycloudflare.com'
    assert seen[0].extensions['sni_hostname']=='unit-session.trycloudflare.com'

def test_private_live_metadata_can_use_validated_kernel_cache(tmp_path):
    from deploy_live import prepare_live
    j=prepare_live('testowner',tmp_path,'https://unit-broker.trycloudflare.com','x'*40,{'url':'https://example.com/client','sha256':'0'*64},300,'testowner/validation-cache')
    assert j['kernel_sources']==['testowner/validation-cache'] and j['is_private']
