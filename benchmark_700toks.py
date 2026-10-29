"""Real encoder timing. Paired rates are PROJECTIONS unless a real provider is called.
Synthetic known-text frames are test fixtures, never a screenshot-quality dataset.
"""
import argparse,io,json,pathlib,statistics,time
from PIL import Image,ImageDraw,ImageFont
from config import Settings
from gpu_ocr_engine import DualT4UltrafastOCREncoder
from ui_delta_cache import UIDeltaCache

def fixture(index:int)->bytes:
    im=Image.new('RGB',(1920,1080),'#f0f3f8');d=ImageDraw.Draw(im)
    try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',30)
    except OSError:
        try:font=ImageFont.truetype('Arial.ttf',30)
        except OSError:font=ImageFont.load_default(size=30)
    d.rectangle((0,0,1920,90),fill='#15253d');d.text((40,23),'Mercury Gateway    File    Edit    View    Search',font=font,fill='white')
    labels=['Dashboard','API Keys','Logs','Settings','Deploy Gateway']
    for n,text in enumerate(labels):d.text((35,140+n*110),text,font=font,fill='#102036')
    for n in range(8):
        y=150+n*90;d.text((420,y),f'Service {n+1}',font=font,fill='black');d.text((900,y),'Healthy',font=font,fill='#125b30');d.text((1350,y),f'Latency {20+n} ms',font=font,fill='black')
    d.text((440,950),f'Frame {index:03}    Submit    Cancel',font=font,fill='black')
    b=io.BytesIO();im.save(b,format='JPEG',quality=92);return b.getvalue()
def p95(values):return sorted(values)[max(0,int(len(values)*.95+.999)-1)]
def projected_rate(tokens,overhead_ms,baseline=1068.):return tokens/(tokens/baseline+overhead_ms/1000)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='evidence/benchmark.json');ap.add_argument('--live-url',default=None);ap.add_argument('--iterations',type=int,default=20);args=ap.parse_args()
    if not 5<=args.iterations<=100:raise SystemExit('iterations must be 5..100')
    cfg=Settings();start=time.perf_counter();engine=DualT4UltrafastOCREncoder(cfg);startup=(time.perf_counter()-start)*1000
    frames=[fixture(i) for i in range(5)];pathlib.Path('evidence/fixtures').mkdir(parents=True,exist_ok=True)
    for i,b in enumerate(frames):pathlib.Path(f'evidence/fixtures/ui-{i}.jpg').write_bytes(b)
    first=engine.encode(frames[0]);cold=first.latency_ms
    for i in range(3):engine.encode(frames[i])
    times=[];recognized=[]
    for i in range(args.iterations):
        engine.cache=UIDeltaCache();engine.crop_cache=UIDeltaCache(2048,16_000_000)
        result=engine.encode(frames[i%5]);times.append(result.latency_ms);recognized.append(len(result.elements))
    engine.cache=UIDeltaCache();sequence=[engine.encode(b) for b in frames];exact=[engine.encode(b) for b in frames]
    full=statistics.median(times);overhead_assumption=18.;projection={str(n):round(projected_rate(n,full+overhead_assumption),2) for n in (250,500,1000)}
    j={'kind':'MEASURED_REAL_OCR_WITH_PROJECTED_NOT_LIVE_PROVIDER_THROUGHPUT','backend':engine.backend,'environment':engine.health(),'startup_engine_warmup_ms':startup,'first_frame_ocr_ms':cold,'warm_uncached_ocr_ms':{'p50':full,'p95':p95(times),'samples':times},'changed_frame_sequence_ms':[x.latency_ms for x in sequence],'exact_repeat_cache_ms':{'p50':statistics.median(x.latency_ms for x in exact)},'recognized_element_counts':recognized,'sample_text':[e.text for e in first.elements[:12]],'quality_gate_minimum_5_elements':min(recognized)>=5,'assumed_http_and_other_overhead_ms':overhead_assumption,'assumed_vendor_generation_tokens_per_second':1068,'projected_paired_tokens_per_second':projection,'projected_700_target_met':all(projection[str(n)]>700 for n in (250,500)),'actual_live_provider_throughput_verified':False,'dual_T4_latency_target_verified':False}
    if args.live_url:
        import os,base64,httpx
        token=os.environ.get('GATEWAY_TOKEN')
        if not token:raise SystemExit('live benchmark requires secure GATEWAY_TOKEN env')
        live=[]
        with httpx.Client(base_url=args.live_url,timeout=120,headers={'Authorization':'Bearer '+token}) as client:
            for n in (250,500,1000):
                payload={'model':'mercury-3','max_tokens':n,'messages':[{'role':'user','content':[{'type':'text','text':'Describe every visible UI item in detail.'},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(frames[0]).decode()}}]}]}
                started=time.perf_counter();response=client.post('/v1/chat/completions',json=payload);elapsed=time.perf_counter()-started;response.raise_for_status();actual=response.json().get('usage',{}).get('completion_tokens')
                if response.headers.get('X-Gateway-Simulation')=='true':raise RuntimeError('live benchmark refuses simulated responses')
                live.append({'requested_output_tokens':n,'actual_output_tokens':actual,'wall_seconds':elapsed,'measured_paired_tok_s':actual/elapsed if isinstance(actual,int) and actual>0 else None})
        j['live_provider_samples']=live
        j['actual_live_provider_throughput_verified']=all(x['measured_paired_tok_s'] is not None for x in live)
        j['live_700_target_met']=all(x['measured_paired_tok_s'] is not None and x['measured_paired_tok_s']>700 for x in live[:2])
    out=pathlib.Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(j,indent=2))
    print('| Metric | Result |\n|---|---|');print(f'| Backend | {engine.backend} |\n| Startup/warmup ms | {startup:.2f} |\n| First OCR ms | {cold:.2f} |\n| Warm uncached OCR p50 / p95 ms | {full:.2f} / {p95(times):.2f} |\n| Exact-repeat cache p50 ms | {j["exact_repeat_cache_ms"]["p50"]:.2f} |')
    for n,v in projection.items():print(f'| PROJECTED paired rate, {n} outputs | {v} |')
    print('LIVE 700 tok/s acceptance: UNVERIFIED. Projections assume network/prefill overhead; no keys/provider call.');engine.close()
if __name__=='__main__':main()
