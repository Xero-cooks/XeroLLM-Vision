"""Narrow authenticated public ingress. Admin endpoints never reach the tunnel."""
from __future__ import annotations
import asyncio,os,secrets
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,StreamingResponse

def create_edge(token:str|None=None,transport=None)->FastAPI:
    token=token if token is not None else os.getenv('GATEWAY_TOKEN','')
    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=httpx.Timeout(120,connect=5),trust_env=False,transport=transport) as client:
            app.state.client=client;app.state.limit=asyncio.Semaphore(2);yield
    app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    @app.api_route('/{path:path}',methods=['GET','POST','PUT','DELETE','PATCH','OPTIONS'])
    async def proxy(path:str,request:Request):
        allowed=(request.method=='GET' and path in ('health','v1/models')) or (request.method=='POST' and path in ('v1/ocr','v1/chat/completions'))
        if not allowed:return JSONResponse({'error':{'message':'route not exposed'}},status_code=404)
        if not token:return JSONResponse({'error':{'message':'ingress authentication not configured'}},status_code=503)
        if not secrets.compare_digest(request.headers.get('authorization',''),'Bearer '+token):return JSONResponse({'error':{'message':'invalid gateway credentials'}},status_code=401)
        body=bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk)>24_000_000:return JSONResponse({'error':{'message':'request too large'}},status_code=413)
            body.extend(chunk)
        try:await asyncio.wait_for(app.state.limit.acquire(),timeout=5)
        except TimeoutError:return JSONResponse({'error':{'message':'gateway busy'}},status_code=429,headers={'Retry-After':'5'})
        headers={k:v for k,v in request.headers.items() if k.lower() in ('authorization','content-type','x-ui-resolution','x-session-id','x-gateway-metrics','x-dry-run')}
        try:response=await app.state.client.send(app.state.client.build_request(request.method,'/'+path,content=bytes(body),headers=headers),stream=True)
        except httpx.HTTPError:
            app.state.limit.release();return JSONResponse({'error':{'message':'gateway origin unavailable'}},status_code=502)
        outgoing={k:v for k,v in response.headers.items() if k.lower().startswith('x-') or k.lower() in ('content-type','retry-after','cache-control')}
        outgoing['Cache-Control']='no-store';outgoing['X-Accel-Buffering']='no'
        async def relay():
            try:
                async for chunk in response.aiter_bytes():yield chunk
            finally:
                await response.aclose();app.state.limit.release()
        return StreamingResponse(relay(),status_code=response.status_code,headers=outgoing)
    return app
app=create_edge()
