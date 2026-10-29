"""Adapter contract for the user's image-to-text encoder; not required to be OCR.
Set ENCODER_FACTORY=your_module:create_encoder. The trusted factory receives Settings.
Return EncodedFrame using frame_id/captured_at from this request, original dimensions,
measured latency, honest backend name, and observed elements (unknown roles if absent).
Never claim visual capabilities supplied only by text detection.
"""
from typing import Protocol
from gpu_ocr_engine import EncodedFrame
class ImageTextEncoder(Protocol):
    def encode(self,blob:bytes,frame_id:str|None=None,captured_at:str|None=None,high:bool=False,cache_namespace:str='default')->EncodedFrame: ...
    def health(self)->dict: ...
    def close(self)->None: ...
