from __future__ import annotations
import asyncio,contextlib,json,math,secrets,time,uuid
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse,StreamingResponse
from api_pool import InceptionKeyPool,PoolUnavailable
from config import Settings
from payload_transformer import transform,image_bytes

def create_app(cfg:Settings|None=None,engine=None,upstream_transport=None)->FastAPI:
    cfg=cfg or Settings()
    if cfg.gateway_token and cfg.admin_token and secrets.compare_digest(cfg.gateway_token,cfg.admin_token):
        raise ValueError('client and admin bearer secrets must be different')
    pool=InceptionKeyPool(cfg.keys)
    @asynccontextmanager
    async def lifespan(app):
        nonlocal engine
        if engine is None:
            if cfg.encoder_factory:
                import importlib
                module,name=cfg.encoder_factory.split(':',1)
                factory=getattr(importlib.import_module(module),name)
            else:
                from gpu_ocr_engine import DualT4UltrafastOCREncoder
                factory=DualT4UltrafastOCREncoder
            engine=await asyncio.to_thread(factory,cfg)
        app.state.engine=engine;app.state.pool=pool
        async with httpx.AsyncClient(base_url=cfg.upstream,http2=True,trust_env=False,timeout=httpx.Timeout(cfg.http_timeout,connect=10),limits=httpx.Limits(max_keepalive_connections=32,max_connections=64),transport=upstream_transport) as client:
            app.state.client=client;app.state.limit=asyncio.Semaphore(cfg.max_concurrent_requests)
            yield
        if hasattr(engine,'close'):await asyncio.to_thread(engine.close)
    app=FastAPI(title='Mercury3 Vision Gateway',lifespan=lifespan)
    @app.middleware('http')
    async def boundary(request,call_next):
        request.state.start=time.perf_counter()
        if request.url.path.startswith(('/v1/','/admin/')) or request.url.path=='/health':
            try:auth(request,request.url.path.startswith('/admin/'))
            except HTTPException as e:return JSONResponse({'detail':e.detail},status_code=e.status_code)
        if request.url.path in ('/v1/chat/completions','/v1/ocr','/admin/keys'):
            try:
                declared=int(request.headers.get('content-length','0'))
                if declared>cfg.max_body_bytes:return JSONResponse({'error':{'message':'request too large'}},status_code=413)
            except ValueError:return JSONResponse({'error':{'message':'invalid content length'}},status_code=400)
            # Enforce byte cap before JSON parsing, even for chunked bodies.
            body=bytearray()
            async for chunk in request.stream():
                if len(body)+len(chunk)>cfg.max_body_bytes:return JSONResponse({'error':{'message':'request too large'}},status_code=413)
                body.extend(chunk)
            request._body=bytes(body)
        return await call_next(request)
    def auth(request:Request,admin:bool=False):
        secret=cfg.admin_token if admin else cfg.gateway_token
        if not secret:raise HTTPException(503,'authentication is not configured')
        value=request.headers.get('authorization','').removeprefix('Bearer ')
        if not secrets.compare_digest(value,secret):raise HTTPException(401,'invalid gateway credentials')
    async def body(request):
        try:j=await request.json()
        except (ValueError,UnicodeError):raise HTTPException(400,'invalid JSON')
        if not isinstance(j,dict):raise HTTPException(400,'JSON object required')
        return j
    def headers(metrics,rate=None):return {'X-Upstream-Attempts':str(metrics.get('upstream_attempts',0)),'X-OCR-Latency-Ms':f"{metrics.get('ocr_latency_ms',0):.3f}",'X-Images-Processed':str(metrics.get('images_processed',0)),'X-Cache-Hit-Ratio':f"{metrics.get('cache_hit_ratio',0):.3f}",'X-Effective-Paired-Tok-Per-Sec':str(rate) if rate is not None else 'pending','X-Gateway-OCR-Backend':','.join(metrics.get('backends',[])),'Cache-Control':'no-store'}
    @app.get('/health')
    async def health(request:Request):
        auth(request)
        return {'status':'ready','ocr':engine.health(),'pool':pool.status(),'performance_targets_verified':False}
    @app.get('/v1/models')
    async def models(request:Request):
        auth(request)
        return {'object':'list','data':[{'id':cfg.model,'object':'model','created':0,'owned_by':'inceptionlabs'}]}
    @app.get('/admin/keys/status')
    async def key_status(request:Request):auth(request,True);return pool.status()
    @app.post('/admin/keys')
    async def keys(request:Request):
        auth(request,True);j=await body(request)
        try:pool.reload(j.get('keys'),j.get('mode','replace'))
        except (ValueError,TypeError):raise HTTPException(400,'invalid key pool update')
        return pool.status()
    @app.post('/v1/ocr')
    async def ocr(request:Request):
        auth(request);j=await body(request)
        image=j.get('image_url');url=image.get('url') if isinstance(image,dict) else image
        if not isinstance(url,str):raise HTTPException(400,'image_url is required')
        async with app.state.limit:
            try:
                blob=await image_bytes(url,app.state.client,cfg)
                fid=j.get('frame_id');ts=j.get('captured_at')
                if any(v is not None and (not isinstance(v,str) or len(v)>128) for v in (fid,ts)):raise ValueError('invalid frame metadata')
                frame=await asyncio.to_thread(engine.encode,blob,fid,ts,request.headers.get('X-UI-Resolution')=='high',request.headers.get('X-Session-ID','default')[:128])
            except (ValueError,httpx.HTTPError):raise HTTPException(422,'image fetch/decode/encoding rejected; inspect local deployment health')
        metrics={'ocr_latency_ms':frame.latency_ms,'images_processed':1,'cache_hit_ratio':frame.cache_hit_ratio,'backends':[frame.backend]}
        return JSONResponse(frame.public(),headers=headers(metrics,'not_applicable'))
    @app.post('/v1/chat/completions')
    async def chat(request:Request):
        auth(request);j=await body(request)
        if not isinstance(j.get('stream',False),bool):raise HTTPException(400,'stream must be a boolean')
        dry=request.headers.get('X-Dry-Run','').lower()=='true'
        mock=dry or (cfg.allow_mock and pool.status()['real_keys']==0)
        await app.state.limit.acquire()
        held=True
        try:
            try:out,metrics=await transform(j,engine,app.state.client,cfg,high=request.headers.get('X-UI-Resolution')=='high',namespace=request.headers.get('X-Session-ID','default')[:128])
            except (ValueError,httpx.HTTPError):raise HTTPException(422,'invalid multimodal payload or image encoding failure')
            if mock:
                budget=out.get('max_completion_tokens',out.get('max_tokens',250))
                if not isinstance(budget,int) or isinstance(budget,bool) or not 1<=budget<=4096:raise HTTPException(400,'mock token budget must be 1..4096')
                metrics['simulation']=True
                if not out.get('stream'):
                    await asyncio.sleep(budget/1068)
                    result={'id':'mock-'+uuid.uuid4().hex,'object':'chat.completion','model':'mercury-3-MOCK','choices':[{'index':0,'message':{'role':'assistant','content':'mock '*budget},'finish_reason':'stop'}],'usage':{'completion_tokens':budget,'prompt_tokens':0,'total_tokens':budget},'gateway_metrics':{**metrics,'throughput_kind':'SIMULATED_LEXICAL_UNITS_NOT_PROVIDER_TOKENS'}}
                    h=headers(metrics,'simulated');h['X-Gateway-Simulation']='true';return JSONResponse(result,headers=h)
                async def simulated():
                    try:
                        ident='mock-'+uuid.uuid4().hex
                        for pos in range(0,budget,16):
                            n=min(16,budget-pos);await asyncio.sleep(n/1068)
                            yield 'data: '+json.dumps({'id':ident,'object':'chat.completion.chunk','model':'mercury-3-MOCK','choices':[{'index':0,'delta':{'content':'mock '*n},'finish_reason':None}]})+'\n\n'
                        yield 'data: '+json.dumps({'id':ident,'object':'chat.completion.chunk','model':'mercury-3-MOCK','choices':[{'index':0,'delta':{},'finish_reason':'stop'}],'usage':{'completion_tokens':budget,'total_tokens':budget,'prompt_tokens':0},'gateway_metrics':{**metrics,'throughput_kind':'SIMULATED_LEXICAL_UNITS_NOT_PROVIDER_TOKENS'}})+'\n\n'
                        yield 'data: [DONE]\n\n'
                    finally:app.state.limit.release()
                held=False;h=headers(metrics,'simulated');h['X-Gateway-Simulation']='true';return StreamingResponse(simulated(),media_type='text/event-stream',headers=h)
            attempted:set[str]=set()
            response=None
            attempt_budget=max(1,min(cfg.max_upstream_attempts,8))
            for attempt in range(attempt_budget):
                try:key=pool.acquire(attempted)
                except PoolUnavailable as e:raise HTTPException(503,str(e))
                attempted.add(key.id);metrics['upstream_attempts']=attempt+1;t=time.perf_counter()
                try:
                    response=await app.state.client.send(app.state.client.build_request('POST','/chat/completions',json=out,headers={'Authorization':'Bearer '+key.secret}),stream=True)
                except (httpx.ConnectError,httpx.ConnectTimeout,httpx.PoolTimeout):
                    pool.failed(key)
                    if attempt+1<attempt_budget:continue
                    raise HTTPException(502,'upstream connection failed; retry budget exhausted')
                except httpx.HTTPError:
                    raise HTTPException(502,'ambiguous upstream transport failure; request not replayed')
                metrics['upstream_http_version']=response.http_version
                metrics['upstream_headers_ms']=round((time.perf_counter()-t)*1000,3)
                if response.status_code<400:break
                status=response.status_code;retry=None;can_retry=False
                if status==429:
                    # Explicit account/global quota signals override per-key configuration.
                    scope=cfg.rate_limit_scope if cfg.rate_limit_scope in ('pool','key') else 'pool'
                    if response.headers.get('x-ratelimit-scope','').lower() in ('account','organization','global'):scope='pool'
                    error_bytes=bytearray()
                    async for chunk in response.aiter_bytes():
                        error_bytes.extend(chunk[:max(0,8192-len(error_bytes))])
                        if len(error_bytes)>=8192:break
                    try:
                        err=json.loads(error_bytes).get('error',{})
                        code=str(err.get('code',''))+' '+str(err.get('type','')) if isinstance(err,dict) else ''
                        if any(word in code.lower() for word in ('quota','billing','credit','account')):scope='pool'
                    except (ValueError,AttributeError):pass
                    retry=pool.limited(key,response.headers.get('retry-after'),scope=scope);can_retry=scope=='key'
                elif status in (401,403):pool.failed(key,invalid=True);can_retry=True
                elif status in (500,502,503,504):pool.failed(key);can_retry=True
                await response.aclose()
                if can_retry and attempt+1<attempt_budget:continue
                return JSONResponse({'error':{'message':'upstream rejected request; retry policy exhausted or replay unsafe','upstream_status':status}},status_code=status,headers={**headers(metrics,'unavailable'),**({'Retry-After':str(retry)} if retry else {})})
            if response is None:raise HTTPException(502,'no upstream response')
            if not out.get('stream'):
                try:
                    raw=bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(raw)+len(chunk)>8_000_000:raise HTTPException(502,'upstream response exceeds limit')
                        raw.extend(chunk)
                    try:result=json.loads(raw)
                    except ValueError:raise HTTPException(502,'upstream returned invalid JSON')
                    if not isinstance(result,dict):raise HTTPException(502,'upstream returned invalid object')
                    key.latency_ms=round((time.perf_counter()-t)*1000,2)
                    tokens=result.get('usage',{}).get('completion_tokens');rate=round(tokens/(time.perf_counter()-request.state.start),2) if isinstance(tokens,int) and tokens>=0 else 'unavailable'
                    result['gateway_metrics']={**metrics,'paired_tokens_per_second':rate,'throughput_kind':'MEASURED_USING_PROVIDER_COMPLETION_TOKEN_USAGE'}
                    return JSONResponse(result,headers=headers(metrics,rate))
                except httpx.HTTPError:raise HTTPException(502,'upstream response interrupted; ambiguous request not replayed')
                finally:await response.aclose()
            if 'text/event-stream' not in response.headers.get('content-type',''):
                await response.aclose();raise HTTPException(502,'upstream did not return SSE')
            async def relay():
                tokens=None;total=0
                try:
                    async for line in response.aiter_lines():
                        total+=len(line)
                        if len(line)>1_000_000 or total>16_000_000:raise RuntimeError('SSE size bound')
                        if line.strip()=='data: [DONE]':continue
                        if line.startswith('data: '):
                            with contextlib.suppress(ValueError,TypeError,AttributeError):tokens=json.loads(line[6:]).get('usage',{}).get('completion_tokens',tokens)
                        yield line+'\n'
                    if request.headers.get('X-Gateway-Metrics','').lower()=='true':
                        rate=round(tokens/(time.perf_counter()-request.state.start),2) if isinstance(tokens,int) and tokens>=0 else None
                        yield 'data: '+json.dumps({'object':'chat.completion.chunk','choices':[],'gateway_metrics':{**metrics,'paired_tokens_per_second':rate,'throughput_kind':'MEASURED_IF_PROVIDER_USAGE_PRESENT'}})+'\n\n'
                    yield 'data: [DONE]\n\n'
                except (httpx.HTTPError,RuntimeError):yield 'data: '+json.dumps({'error':{'message':'upstream stream interrupted; not retried'}})+'\n\ndata: [DONE]\n\n'
                finally:await response.aclose();app.state.limit.release()
            held=False;return StreamingResponse(relay(),media_type='text/event-stream',headers=headers(metrics))
        finally:
            if held:app.state.limit.release()
    return app
app=create_app()
