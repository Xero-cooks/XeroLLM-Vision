"""Single-loop mutation is synchronous (no await inside), not cross-process lock-free."""
from dataclasses import dataclass
import hashlib,time,datetime,email.utils
@dataclass
class KeyState:
    secret: str
    calls: int = 0
    cooldown_until: float = 0.0
    invalid: bool = False
    latency_ms: float | None = None
    @property
    def id(self)->str: return hashlib.sha256(self.secret.encode()).hexdigest()[:12]
    @property
    def placeholder(self)->bool: return self.secret.startswith('PLACEHOLDER_')
class PoolUnavailable(Exception): pass
class InceptionKeyPool:
    def __init__(self,keys:list[str]): self.states:tuple[KeyState,...]=(); self.cursor=0; self.global_until=0.; self.reload(keys)
    def reload(self,keys:list[str],mode:str='replace')->None:
        if mode not in ('append','replace'): raise ValueError('invalid mode')
        if not keys or len(keys)>100 or any(not isinstance(k,str) or not 8<=len(k)<=512 or any(c.isspace() for c in k) for k in keys): raise ValueError('invalid keys')
        old={s.secret:s for s in self.states}; names=([s.secret for s in self.states] if mode=='append' else [])+keys
        unique=list(dict.fromkeys(names))
        if len(unique)>100: raise ValueError('pool limit')
        self.states=tuple(old.get(k) or KeyState(k) for k in unique); self.cursor%=len(self.states)
    def acquire(self)->KeyState:
        now=time.monotonic()
        if now<self.global_until: raise PoolUnavailable('provider cooldown active')
        for _ in self.states:
            s=self.states[self.cursor%len(self.states)];self.cursor=(self.cursor+1)%len(self.states)
            if not s.placeholder and not s.invalid and s.cooldown_until<=now: s.calls+=1;return s
        raise PoolUnavailable('no usable provider keys')
    def limited(self,s:KeyState,retry_after:str|None)->int:
        seconds=60.
        if retry_after:
            try: seconds=float(retry_after)
            except ValueError:
                try: seconds=email.utils.parsedate_to_datetime(retry_after).timestamp()-time.time()
                except (ValueError,TypeError,OverflowError): pass
        if not seconds>=0 or seconds==float('inf'): seconds=60.
        seconds=min(max(seconds,1.),86400.)
        s.cooldown_until=time.monotonic()+seconds
        # Fail closed across the pool: keys can share one account's quota. No retry/key hopping.
        self.global_until=max(self.global_until,s.cooldown_until);return int(seconds+0.999)
    def status(self)->dict:
        now=time.monotonic()
        return {'size':len(self.states),'real_keys':sum(not s.placeholder for s in self.states),'cooldown_seconds':max(0,round(self.global_until-now,1)), 'keys':[{'id':s.id,'placeholder':s.placeholder,'active':not s.placeholder and not s.invalid and max(s.cooldown_until,self.global_until)<=now,'requests':s.calls,'latency_ms':s.latency_ms} for s in self.states]}
