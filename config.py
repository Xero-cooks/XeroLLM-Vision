"""No secrets in source. One event loop / one Uvicorn worker owns the GPU sessions."""
from dataclasses import dataclass, field
import os
INCEPTION_API_KEY_POOL: list[str] = [f'PLACEHOLDER_INCEPTION_API_KEY_{i:02}' for i in range(1,5)]
@dataclass
class Settings:
    enable_tensorrt: bool = field(default_factory=lambda: os.getenv('ENABLE_TENSORRT','true').lower()=='true')
    trt_builder_opt_level: int = field(default_factory=lambda: int(os.getenv('TRT_BUILDER_OPT_LEVEL','1')))
    encoder_factory: str = field(default_factory=lambda: os.getenv('ENCODER_FACTORY',''))
    backend: str = field(default_factory=lambda: os.getenv('OCR_BACKEND','auto'))
    model_dir: str = field(default_factory=lambda: os.getenv('MODEL_DIR','models'))
    upstream: str = 'https://api.inceptionlabs.ai/v1'
    model: str = 'mercury-3'
    gateway_token: str = field(repr=False,default_factory=lambda: os.getenv('GATEWAY_TOKEN',''))
    admin_token: str = field(repr=False,default_factory=lambda: os.getenv('GATEWAY_ADMIN_TOKEN',''))
    allow_mock: bool = field(default_factory=lambda: os.getenv('ALLOW_MOCK_WHEN_PLACEHOLDER','false').lower()=='true')
    allow_remote_images: bool = field(default_factory=lambda: os.getenv('ALLOW_REMOTE_IMAGES','false').lower()=='true')
    remote_hosts: tuple[str,...] = field(default_factory=lambda: tuple(x.strip().lower() for x in os.getenv('IMAGE_HOST_ALLOWLIST','i.pinimg.com').split(',') if x.strip()))
    keys: list[str] = field(repr=False,default_factory=lambda: [x.strip() for x in os.getenv('INCEPTION_API_KEYS','').split(',') if x.strip()] or INCEPTION_API_KEY_POOL.copy())
    max_upstream_attempts: int = 3
    rate_limit_scope: str = field(default_factory=lambda: os.getenv('KEY_RATE_LIMIT_SCOPE','pool'))
    max_image_bytes: int = 8_000_000
    max_body_bytes: int = 24_000_000
    max_pixels: int = 12_000_000
    max_images: int = 8
    max_concurrent_requests: int = 2
    max_cache_bytes: int = 64_000_000
    max_cache_entries: int = 64
    http_timeout: float = 60.0
    detector_shape: tuple[int,int] = (384,640)
    high_shape: tuple[int,int] = (448,768)
