# Architecture

## Request path

1. Authenticate and bound the request body before parsing.
2. Validate OpenAI chat roles and image blocks. Images in privileged system/developer/tool messages are rejected.
3. Decode allowed image bytes. Remote HTTPS images are disabled unless explicitly enabled with an exact hostname allowlist; public-address validation and IP pinning mitigate SSRF/DNS rebinding.
4. Detect text on GPU0. Rectangular canvases preserve aspect ratio with small padding, not square padding or arbitrary stretching.
5. Crop in GPU memory and shard recognition across GPU0/GPU1. Single-GPU and CPU staging are labeled fallbacks.
6. GPU recognition appends ONNX ArgMax/ReduceMax so only IDs/scores cross PCIe, instead of full vocabulary tensors. Original model files are preserved.
7. Decode CTC and serialize visible text with normalized coordinates and geometric reading-order relationships.
8. Replace image blocks with untrusted observations in the original message role, then forward text-only chat through one persistent HTTP/2-capable client.
9. Return JSON or relay SSE. Real throughput needs actual provider usage and total wall time.

## Modules

- `config.py`: settings, limits, placeholder keys and backend selection.
- `api_pool.py`: single-event-loop round robin, hot reload, masked status and cooldowns. Not a distributed lock-free pool.
- `gpu_ocr_engine.py`: real ONNX inference, preprocessing, sharding and bounded caches.
- `ctc_graph.py`: exact terminal recognition reductions.
- `runtime_env.py`: pip-installed NVIDIA library discovery and TensorRT preload.
- `ui_delta_cache.py`: bounded frame/crop LRU and tile matching.
- `spatial_serializer.py`: reading order, scanline grouping and escaped spatial Markdown.
- `payload_transformer.py`: validated image acquisition and chat rewriting.
- `gateway_server.py`: authenticated API, shared upstream client and JSON/SSE forwarding.
- `encoder_protocol.py`: trusted local encoder plugin contract.
- `deploy_kaggle.py`: private, bounded validation-job packaging; never embeds credentials.

## Precision and hardware

TensorRT FP16 is requested on supported GPUs. ONNX model input/output dtypes are preserved. TensorRT can retain some numerically sensitive operations in FP32; an FP16 builder flag is not proof every operator executes in FP16. CUDA-only fallback executes graph precision and is **not** TensorRT FP16 acceptance. No BF16/FP8 path exists.

GPU JPEG decode is supported through torchvision. GPU PNG decoding is not implemented. Detector postprocessing uses a small CPU probability map; full screenshot CPU decoding/resizing is not used in strict GPU mode. Crops are axis-aligned; rotated perspective correction is not implemented.

The `dual_cuda` backend label denotes two CUDA devices; inspect actual session provider lists and cached engines to distinguish TensorRT from CUDA-only execution.

## Cache correctness

Exact-frame caching and unchanged-tile/crop recognition reuse are bounded. GPU tile comparisons use exact equality. Detection reruns globally to avoid missing boxes crossing tile boundaries. Frame IDs/timestamps are regenerated on cache hits. Cache speed is reported separately from uncached performance.

## Encoder plugins

Set `ENCODER_FACTORY=your_module:create_encoder`. This imports trusted local code receiving Settings. Implement the protocol and return actual observed text/boxes, dimensions, confidence and frame metadata. This interface is not restricted to OCR. Do not fabricate semantics an encoder did not observe. Plugins are executable code, not untrusted user uploads.
