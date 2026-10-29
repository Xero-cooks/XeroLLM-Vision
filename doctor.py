import importlib.metadata,json,platform
import onnxruntime as ort
j={'python':platform.python_version(),'ort':ort.__version__,'providers':ort.get_available_providers(),'gpus':[]}
try:
 import torch
 j['torch']=torch.__version__;j['cuda']=torch.version.cuda
 for i in range(torch.cuda.device_count()):j['gpus'].append({'id':i,'name':torch.cuda.get_device_name(i),'capability':torch.cuda.get_device_capability(i),'vram':torch.cuda.get_device_properties(i).total_memory})
except ImportError:j['torch']='not installed (CPU staging only)'
from runtime_env import gpu_library_paths
j['gpu_library_paths']=gpu_library_paths()
try:j['tensorrt_package']=importlib.metadata.version('tensorrt-cu12')
except importlib.metadata.PackageNotFoundError:j['tensorrt_package']='not installed'
print(json.dumps(j,indent=2))
