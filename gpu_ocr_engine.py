"""Real PP-OCRv4 ONNX execution. CPU staging and GPU paths are explicitly labeled.
GPU JPEG decode only: torchvision PNG decode is CPU, so strict GPU rejects PNG.
FP16 is TensorRT compute precision; ONNX input dtype is honored (usually float32).
"""
from __future__ import annotations
import concurrent.futures,hashlib,io,json,math,pathlib,threading,time,datetime,logging
from dataclasses import dataclass
import numpy as np
from PIL import Image
from config import Settings
from model_assets import acquire
from spatial_serializer import UIElement,serialize
from ui_delta_cache import UIDeltaCache
@dataclass
class EncodedFrame:
    markdown:str; elements:list[UIElement]; width:int; height:int; latency_ms:float; frame_id:str; captured_at:str; cache_hit_ratio:float; backend:str
    def public(self)->dict:
        entries=[]
        for i,e in enumerate(self.elements):
            x0,y0,x1,y1=e.box
            entries.append({'id':f'e{i}',**e.public(),'center_normalized':[round(500*(x0+x1)/self.width),round(500*(y0+y1)/self.height)]})
        # Geometric relationships only; not inferred semantic widget roles.
        relations=[]
        order=sorted(range(len(entries)),key=lambda i:(self.elements[i].box[1],self.elements[i].box[0]))
        for a,b in zip(order,order[1:]):relations.append({'from':f'e{a}','to':f'e{b}','relation':'precedes_in_geometric_reading_order'})
        return {'markdown':self.markdown,'elements':entries,'relationships':relations,'width':self.width,'height':self.height,'ocr_latency_ms':self.latency_ms,'frame_id':self.frame_id,'captured_at':self.captured_at,'cache_hit_ratio':self.cache_hit_ratio,'backend':self.backend}
class DualT4UltrafastOCREncoder:
    def __init__(self,settings:Settings):
        import onnxruntime as ort
        self.cfg=settings;self.ort=ort;self.lock=threading.Lock();self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=2);self.cache=UIDeltaCache(settings.max_cache_entries,settings.max_cache_bytes);self.crop_cache=UIDeltaCache(2048,16_000_000);self.previous_frames=UIDeltaCache(4,settings.max_cache_bytes);self.tile_generation=0
        self.torch=None;self.gpus=0
        if settings.backend!='cpu':
            try:
                import torch
                if torch.cuda.is_available():self.torch=torch;self.gpus=torch.cuda.device_count()
            except ImportError:pass
        if settings.backend=='gpu' and not self.gpus:raise RuntimeError('GPU mode requires CUDA; CPU fallback not hidden')
        if self.gpus and 'CUDAExecutionProvider' not in ort.get_available_providers():raise RuntimeError('CUDA torch found but ONNX CUDA provider missing')
        self.runtime_libraries={}
        if self.gpus:
            from runtime_env import preload_tensorrt
            self.runtime_libraries=preload_tensorrt()
        self.backend='dual_cuda' if self.gpus>=2 else ('single_cuda' if self.gpus else 'cpu_staging')
        acquire(settings.model_dir);root=pathlib.Path(settings.model_dir)
        det=next(root.glob('*OCRv4*det*.onnx'));rec=next(root.glob('*OCRv4*rec*.onnx'))
        if self.gpus:
            from ctc_graph import reduced_ctc_model
            rec=reduced_ctc_model(rec)
        logging.getLogger(__name__).warning('Initializing detector on device 0')
        self.det_session_gpu0=self._session(det,0)
        logging.getLogger(__name__).warning('Initializing recognition sessions on %s device(s)',min(self.gpus,2))
        if self.gpus>=2:
            a=self.pool.submit(self._session,rec,0);b=self.pool.submit(self._session,rec,1)
            self.rec_session_gpu0=a.result();self.rec_session_gpu1=b.result()
        else:self.rec_session_gpu0=self._session(rec,0);self.rec_session_gpu1=self.rec_session_gpu0
        metadata=self.rec_session_gpu0.get_modelmeta().custom_metadata_map
        chars=metadata.get('character','')
        if chars:self.characters=['blank']+chars.splitlines()+[' ']
        else:
            paths=list(root.glob('*dict*.txt'))
            if not paths:raise RuntimeError('recognition character dictionary unavailable')
            self.characters=['blank']+paths[0].read_text().splitlines()+[' ']
        self.warmed=False;self.warmup()
    def _session(self,path:pathlib.Path,device:int):
        opts=self.ort.SessionOptions();opts.intra_op_num_threads=1;opts.inter_op_num_threads=1
        providers=['CPUExecutionProvider']
        if self.gpus:
            providers=[('CUDAExecutionProvider',{'device_id':device})]
            if self.cfg.enable_tensorrt and 'TensorrtExecutionProvider' in self.ort.get_available_providers():
                cache=pathlib.Path(self.cfg.model_dir)/f'trt_cache_gpu{device}'/path.stem;cache.mkdir(parents=True,exist_ok=True)
                if 'rec' in path.stem:profiles=('x:1x3x48x160','x:16x3x48x320','x:16x3x48x640')
                else:profiles=('x:1x3x384x640','x:1x3x384x640','x:1x3x448x768')
                providers.insert(0,('TensorrtExecutionProvider',{'device_id':device,'trt_fp16_enable':True,'trt_builder_optimization_level':max(0,min(5,self.cfg.trt_builder_opt_level)),'trt_engine_cache_enable':True,'trt_engine_cache_path':str(cache),'trt_max_workspace_size':1073741824,'trt_profile_min_shapes':profiles[0],'trt_profile_opt_shapes':profiles[1],'trt_profile_max_shapes':profiles[2]}))
        try:session=self.ort.InferenceSession(str(path),sess_options=opts,providers=providers)
        except Exception:
            if not self.gpus:raise
            logging.getLogger(__name__).warning('TensorRT session construction failed; explicitly retrying CUDA on device %s',device)
            session=self.ort.InferenceSession(str(path),sess_options=opts,providers=[('CUDAExecutionProvider',{'device_id':device})])
        if self.gpus and 'CUDAExecutionProvider' not in session.get_providers():
            # ORT's internal EP failure handler may retry CPU-only, ignoring requested CUDA fallback.
            logging.getLogger(__name__).warning('ORT selected CPU after provider failure; explicitly retrying CUDA on device %s',device)
            session=self.ort.InferenceSession(str(path),sess_options=opts,providers=[('CUDAExecutionProvider',{'device_id':device})])
        if self.gpus and 'CUDAExecutionProvider' not in session.get_providers():raise RuntimeError('ONNX CUDA provider failed to initialize; refusing hidden CPU fallback')
        return session
    def _run(self,session,array,device:int=0):
        name=session.get_inputs()[0].name;dtype=np.float16 if 'float16' in session.get_inputs()[0].type else np.float32
        if self.torch is None:
            outputs=session.run(None,{name:np.asarray(array,dtype=dtype)})
            return outputs if session.get_outputs()[0].name=='gateway_ctc_ids' else outputs[0]
        torch=self.torch
        with torch.cuda.device(device):
            tensor=array.to(device=f'cuda:{device}',dtype=torch.float16 if dtype==np.float16 else torch.float32).contiguous()
            torch.cuda.synchronize(device) # safe interop with ORT-owned CUDA streams; measured overhead, not hidden
            binding=session.io_binding();binding.bind_input(name,'cuda',device,dtype,tuple(tensor.shape),tensor.data_ptr())
            for out in session.get_outputs():binding.bind_output(out.name,'cuda',device)
            session.run_with_iobinding(binding);binding.synchronize_outputs()
            outputs=binding.copy_outputs_to_cpu() # CTC graph sends only IDs/scores, not large vocabulary logits.
            return outputs if session.get_outputs()[0].name=='gateway_ctc_ids' else outputs[0]
    def warmup(self):
        torch=self.torch
        def zeros(shape,d=0):return torch.zeros(shape,device=f'cuda:{d}') if torch else np.zeros(shape,np.float32)
        for h,w in (self.cfg.detector_shape,self.cfg.high_shape):self._run(self.det_session_gpu0,zeros((1,3,h,w)))
        for width in (160,320,640):
            futures=[self.pool.submit(self._run,s,zeros((16,3,48,width),d),d) for s,d in [(self.rec_session_gpu0,0),(self.rec_session_gpu1,1 if self.gpus>=2 else 0)]]
            for f in futures:f.result()
        self.warmed=True
    def health(self)->dict:
        result={'backend':self.backend,'warmed':self.warmed,'detector_providers':self.det_session_gpu0.get_providers(),'recognizer_providers':[self.rec_session_gpu0.get_providers(),self.rec_session_gpu1.get_providers()],'precision':'TensorRT FP16 requested; model I/O dtype preserved' if self.cfg.enable_tensorrt else 'CUDA/CPU graph precision; TensorRT explicitly disabled (not FP16 acceptance)','gpu_count':self.gpus,'gpu':[],'runtime_libraries':self.runtime_libraries,'ctc_reduction':'ONNX device-side ArgMax/ReduceMax' if self.gpus else 'NumPy CPU staging','partial_cache_policy':'full detection; exact unchanged tile/crop recognition reuse; GPU uses exact tiled equality, no collision risk'}
        result['engine_cache_files']=[str(p.relative_to(self.cfg.model_dir)) for p in pathlib.Path(self.cfg.model_dir).glob('trt_cache_gpu*/**/*.engine')]
        if self.torch:
            for i in range(self.gpus):result['gpu'].append({'id':i,'name':self.torch.cuda.get_device_name(i),'allocated_bytes':self.torch.cuda.memory_allocated(i),'free_total_bytes':list(self.torch.cuda.mem_get_info(i))})
        return result
    def _decode(self,blob:bytes):
        # PIL reads dimensions/header only on GPU path; no full CPU decode there.
        with Image.open(io.BytesIO(blob)) as im:
            w,h=im.size;fmt=im.format
            if w*h>self.cfg.max_pixels or min(w,h)<16:raise ValueError('image dimensions outside limits')
            if fmt not in ('JPEG','PNG','WEBP'):raise ValueError('unsupported image format')
            if not self.torch:return np.asarray(im.convert('RGB'))[:,:,::-1].copy(),w,h
        if fmt!='JPEG':raise ValueError('strict GPU decode supports JPEG only; convert PNG client-side or use explicit CPU staging')
        import torchvision.io as tv
        tensor=tv.decode_jpeg(self.torch.frombuffer(bytearray(blob),dtype=self.torch.uint8),mode=tv.ImageReadMode.RGB,device='cuda:0')
        return tensor.flip(0),w,h
    def _tile_ids(self,frame,w:int,h:int,namespace:str):
        if self.torch is None:return UIDeltaCache.tile_hashes(frame)
        import torch.nn.functional as F
        key=f'{namespace}:{w}:{h}'
        previous=self.previous_frames.get(key)
        if previous is None:same=[False]*16;ids=[0]*16
        else:
            prev,ids=previous
            eq=frame.eq(prev)
            th,tw=(h+3)//4,(w+3)//4
            eq=F.pad(eq,(0,tw*4-w,0,th*4-h),value=True)
            same=eq.reshape(3,4,th,4,tw).all(dim=0).all(dim=1).all(dim=2).reshape(-1).cpu().tolist()
        versions=[]
        for unchanged,version in zip(same,ids):
            if not unchanged:self.tile_generation+=1;version=self.tile_generation
            versions.append(version)
        self.previous_frames.put(key,(frame.clone(),versions),frame.numel()*frame.element_size())
        return versions
    def _preprocess(self,frame,h:int,w:int):
        if self.torch:
            import torch.nn.functional as F
            # Letterbox preserves aspect; the requested shapes are NOT exactly 16:9.
            _,oh,ow=frame.shape;scale=min(w/ow,h/oh);nh,nw=max(1,round(oh*scale)),max(1,round(ow*scale))
            x=F.interpolate(frame[None].float(),size=(nh,nw),mode='bilinear',align_corners=False)/255.
            x=F.pad(x,(0,w-nw,0,h-nh));mean=x.new_tensor([.485,.456,.406])[None,:,None,None];std=x.new_tensor([.229,.224,.225])[None,:,None,None]
            return (x-mean)/std,scale
        import cv2
        oh,ow=frame.shape[:2];scale=min(w/ow,h/oh);nh,nw=max(1,round(oh*scale)),max(1,round(ow*scale));x=np.zeros((h,w,3),np.float32);x[:nh,:nw]=cv2.resize(frame,(nw,nh))/255.
        return ((x-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)).transpose(2,0,1)[None],scale
    def _boxes(self,prob,scale,w,h):
        import cv2
        prob=np.squeeze(prob);mask=(prob>.3).astype(np.uint8)*255;contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE);boxes=[]
        for c in sorted(contours,key=cv2.contourArea,reverse=True)[:512]:
            x,y,bw,bh=cv2.boundingRect(c)
            if bw<3 or bh<3 or float(prob[y:y+bh,x:x+bw].mean())<.45:continue
            # Axis-aligned UI detector; rotated text unsupported and explicitly documented.
            pad=max(1,bh*.35);box=(max(0,(x-pad)/scale),max(0,(y-pad)/scale),min(w,(x+bw+pad)/scale),min(h,(y+bh+pad)/scale))
            if box[2]-box[0]>2 and box[3]-box[1]>2:boxes.append(box)
        return sorted(boxes,key=lambda b:(b[1],b[0]))[:256]
    def _crop(self,frame,box):
        x0,y0,x1,y1=[int(v) for v in box];width=min(640,max(8,round(48*(x1-x0)/max(1,y1-y0))));bucket=next(v for v in (160,320,640) if width<=v)
        if self.torch:
            import torch.nn.functional as F
            crop=F.interpolate(frame[None,:,y0:y1,x0:x1].float(),size=(48,width),mode='bilinear',align_corners=False)/127.5-1
            return F.pad(crop,(0,bucket-width),value=-1)[0],bucket
        import cv2
        crop=cv2.resize(frame[y0:y1,x0:x1],(width,48)).astype(np.float32)/127.5-1;x=np.full((48,bucket,3),-1,np.float32);x[:,:width]=crop;return x.transpose(2,0,1),bucket
    def _recognize(self,items,session,device):
        output={}
        for bucket in (160,320,640):
            group=[(i,c) for i,c,b in items if b==bucket]
            for start in range(0,len(group),16):
                chunk=group[start:start+16]
                if not chunk:continue
                batch=self.torch.stack([c for _,c in chunk]).to(f'cuda:{device}') if self.torch else np.stack([c for _,c in chunk]);logits=self._run(session,batch,device)
                reduced=isinstance(logits,list) and len(logits)==2
                rows=zip(logits[0],logits[1]) if reduced else ((row.argmax(-1),row.max(-1)) for row in logits)
                for (i,_),(ids,scores) in zip(chunk,rows):
                    text=[];conf=[];prev=-1
                    for idx,score in zip(ids,scores):
                        idx=int(idx)
                        if idx!=0 and idx!=prev and idx<len(self.characters):text.append(self.characters[idx]);conf.append(float(score))
                        prev=idx
                    output[i]=(''.join(text),float(np.mean(conf)) if conf else 0.)
        return output
    def encode(self,blob:bytes,frame_id:str|None=None,captured_at:str|None=None,high:bool=False,cache_namespace:str='local')->EncodedFrame:
        t=time.perf_counter();digest=hashlib.sha256(blob).hexdigest();fid=frame_id or digest[:16];ts=captured_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        # Serialization attributes are regenerated per request: cache cannot return stale frame IDs/timestamps.
        with self.lock:
            key=f'{cache_namespace}:{self.backend}:{high}:{digest}';cached=self.cache.get(key)
            if cached is not None:els,w,h=cached;hit=1.
            else:
                frame,w,h=self._decode(blob);dh,dw=self.cfg.high_shape if high else self.cfg.detector_shape;data,scale=self._preprocess(frame,dh,dw);boxes=self._boxes(self._run(self.det_session_gpu0,data),scale,w,h);els=[];items=[];cropkeys={};hits=0
                # GPU compares tile contents exactly in parallel and transfers 16 booleans only.
                tiles=self._tile_ids(frame,w,h,cache_namespace)
                for i,box in enumerate(boxes):
                    crop,bucket=self._crop(frame,box);tile=UIDeltaCache.tile_for(box,w,h);ck=None
                    if tiles is not None and tile is not None:
                        ck=f'{cache_namespace}:{self.backend}:{high}:{w}:{h}:{tile}:{tiles[tile]}:{tuple(box)}';old=self.crop_cache.get(ck)
                        if old is not None:
                            text,confidence=old;els.append(UIElement(text,box,confidence));hits+=1;continue
                    cropkeys[i]=ck;items.append((i,crop,bucket))
                n=(len(items)+1)//2
                if self.gpus>=2:
                    a=self.pool.submit(self._recognize,items[:n],self.rec_session_gpu0,0);b=self.pool.submit(self._recognize,items[n:],self.rec_session_gpu1,1);recognized={**a.result(),**b.result()}
                else:recognized=self._recognize(items,self.rec_session_gpu0,0)
                for i,(text,confidence) in recognized.items():
                    if text:els.append(UIElement(text,boxes[i],confidence))
                    if cropkeys.get(i):self.crop_cache.put(cropkeys[i],(text,confidence),len(text.encode())+256)
                hit=hits/max(1,len(boxes));self.cache.put(key,(els,w,h),sum(len(e.text.encode())+256 for e in els)+len(blob))
        elapsed=(time.perf_counter()-t)*1000
        return EncodedFrame(serialize(els,w,h,fid,ts,elapsed),els,w,h,elapsed,fid,ts,hit,self.backend)
    def close(self)->None:self.pool.shutdown(wait=True,cancel_futures=True)
