import io
from types import SimpleNamespace
from PIL import Image
import pytest
from gpu_ocr_engine import DualT4UltrafastOCREncoder

def test_cmyk_gpu_rejected_before_torchvision_decode():
 encoder=DualT4UltrafastOCREncoder.__new__(DualT4UltrafastOCREncoder)
 encoder.torch=object();encoder.cfg=SimpleNamespace(max_pixels=12000000)
 b=io.BytesIO();Image.new('CMYK',(200,200)).save(b,format='JPEG')
 with pytest.raises(ValueError,match='CMYK'):encoder._decode(b.getvalue())

def test_cmyk_cpu_staging_is_explicit_and_supported():
 encoder=DualT4UltrafastOCREncoder.__new__(DualT4UltrafastOCREncoder)
 encoder.torch=None;encoder.cfg=SimpleNamespace(max_pixels=12000000)
 b=io.BytesIO();Image.new('CMYK',(200,200)).save(b,format='JPEG')
 frame,w,h=encoder._decode(b.getvalue());assert frame.shape==(200,200,3) and (w,h)==(200,200)
