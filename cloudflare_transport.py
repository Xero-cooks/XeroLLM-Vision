"""Resolve fresh quick-tunnel hostnames via HTTPS DNS and retain TLS SNI checks.
Some notebook resolvers briefly cache NXDOMAIN for newly issued tunnel names.
"""
from __future__ import annotations
import ipaddress,json,urllib.parse,urllib.request
import httpx

def public_ipv4(host:str)->list[str]:
    if not host.endswith('.trycloudflare.com'):raise ValueError('not a quick-tunnel hostname')
    url='https://dns.google/resolve?'+urllib.parse.urlencode({'name':host,'type':'A'})
    try:
        with urllib.request.urlopen(url,timeout=15) as response:j=json.loads(response.read(65536))
    except (OSError,ValueError) as error:raise httpx.ConnectError('HTTPS DNS lookup temporarily unavailable') from error
    ips=[entry['data'] for entry in j.get('Answer',[]) if entry.get('type')==1]
    if not ips:raise httpx.ConnectError('new tunnel DNS has not propagated yet')
    if any(not ipaddress.ip_address(ip).is_global for ip in ips):raise httpx.ConnectError('public DNS returned disallowed targets')
    return list(dict.fromkeys(ips))

class CloudflareDNSTransport(httpx.HTTPTransport):
    def __init__(self,**kwargs):
        super().__init__(retries=2,trust_env=False,**kwargs);self.addresses={}
    def handle_request(self,request:httpx.Request)->httpx.Response:
        host=request.url.host
        if request.url.scheme=='https' and host.endswith('.trycloudflare.com'):
            if host not in self.addresses:self.addresses[host]=public_ipv4(host)
            request.url=request.url.copy_with(host=self.addresses[host][0])
            request.headers['Host']=host
            request.extensions['sni_hostname']=host
        return super().handle_request(request)
