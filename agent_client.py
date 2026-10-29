"""Optional agent-side adapter: convert PNG/WebP before strict GPU JPEG ingress.
Image decoding happens on the agent computer, not the Kaggle inference CPU path.
"""
from __future__ import annotations
import base64,copy,io,json,pathlib,time
from PIL import Image

def normalize_messages(messages:list[dict])->list[dict]:
    output=copy.deepcopy(messages)
    for message in output:
        content=message.get('content')
        if not isinstance(content,list):continue
        for block in content:
            if not isinstance(block,dict) or block.get('type')!='image_url':continue
            image=block.get('image_url',{});url=image.get('url','') if isinstance(image,dict) else ''
            if not url.startswith(('data:image/png;base64,','data:image/webp;base64,')):continue
            encoded=url.split(',',1)[1]
            if len(encoded)>10_666_680:raise ValueError('agent image exceeds byte limit')
            raw=base64.b64decode(encoded,validate=True)
            with Image.open(io.BytesIO(raw)) as source:
                if source.width*source.height>12_000_000:raise ValueError('agent image exceeds pixel limit')
                rgba=source.convert('RGBA');background=Image.new('RGB',source.size,'white');background.paste(rgba,mask=rgba.getchannel('A'))
                data=io.BytesIO();background.save(data,format='JPEG',quality=92)
            if data.tell()>8_000_000:raise ValueError('converted agent image exceeds byte limit')
            image['url']='data:image/jpeg;base64,'+base64.b64encode(data.getvalue()).decode()
    return output

class GatewayAgentClient:
    def __init__(self,connection_file:str):
        from openai import OpenAI
        import httpx
        from cloudflare_transport import CloudflareDNSTransport
        config=json.loads(pathlib.Path(connection_file).read_text())
        self.model=config.get('model','mercury-3');self.expiry=config.get('expires_unix')
        self.client=OpenAI(base_url=config['base_url'],api_key=config['api_key'],max_retries=0,http_client=httpx.Client(transport=CloudflareDNSTransport(),trust_env=False))
    def create(self,messages:list[dict],**kwargs):
        if self.expiry and time.time()>=self.expiry:raise RuntimeError('gateway serving session expired')
        return self.client.chat.completions.create(model=self.model,messages=normalize_messages(messages),**kwargs)
