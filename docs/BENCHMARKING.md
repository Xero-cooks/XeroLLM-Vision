# Benchmarking without misleading speed claims

```bash
python -m pytest -q tests
python verify_quality.py
python benchmark_700toks.py
# With real provider keys configured and an authenticated running gateway:
python benchmark_700toks.py --live-url http://127.0.0.1:8000
```

The encoder benchmark generates five 1920×1080 synthetic frames sharing a text-heavy UI layout, runs three warmups, twenty uncached requests and a five-frame sequence. Exact-repeat caching is reported separately. These fixtures are not a varied real-world screenshot dataset or full terminal/form/icon quality suite.

## Keep the clocks separate

**Current timer boundary:** the recorded engine OCR timer stops before final spatial Markdown serialization. It includes image decode, preprocessing, detection, recognition, cache handling and synchronization. The reported 29.03 ms therefore is an OCR-stage result, not a measured complete image-to-Markdown or API response time. Future complete-encoder validation should wrap `engine.encode()` with an outer wall clock.

- Cold dependency/model/engine preparation is not warm image-encoding latency.
- Uncached encoding, changed-frame caching and exact-repeat hits are separate populations.
- The assumed 1068 tok/s vendor baseline and 18 ms extra overhead are **projection inputs**, not measured upstream behavior.
- Mock streams simulate lexical units; they are not real token usage.
- Live paired speed uses **actual completion-token usage / client wall seconds**. Real prefill, TTFT, networking, queueing and output length matter.

For output length N and actual provider generation rate R:

`paired_rate = N / (encoding + proxy + network + prefill + N/R)`

A fast decoder cannot guarantee a universal paired rate independent of output length. The current live probe records requested and actual token counts; a max-token budget does not force the model to emit exactly that many tokens. Multiple repetitions and realistic task-quality evaluation are needed before broad performance claims.

## Recorded evidence

`evidence/cpu-baseline.json` contains an actual CPU PP-OCRv4 baseline:20 uncached samples,902.58 ms median and989.15 ms nearest-rank p95. It predates later GPU-only CTC/runtime changes; it is not a T4 measurement. `evidence/ctc-graph-equivalence.json` records exact IDs/scores against the original real recognizer on CPU. `evidence/validation-status.json` records sanitized hardware/test status without private notebook URLs.

## Completed dual-T4 run

| Mode | Warm uncached p50 | Warm uncached p95 | Samples |
|---|---:|---:|---:|
| CUDA-only graph precision | 101.77 ms | 109.13 ms | 20 |
| TensorRT FP16 requested | 29.03 ms | 31.13 ms | 20 |

Both GPU runs used the same synthetic fixture family and actual two-T4 environment. TensorRT preparation/warmup took722.76 seconds; its first frame took1397.58 ms. Exact-repeat-cache timing is separate and is not the headline result. The small shared-layout sample does not establish production latency or quality on arbitrary UIs.

See `evidence/gpu-cuda-benchmark.json` and `evidence/gpu-tensorrt-benchmark.json`. Independent sorted-sample median and nearest-rank p95 checks reproduced the results. Both reported 31 recognized elements per sample and matching recorded sample text. The separate CUDA synthetic-label check matched 15/16 exact labels; full TensorRT quality/HTTP checks remain future work. TensorRT warned about FP16 layer normalization; numerical quality on realistic frames needs evaluation.

No ≥700 tok/s live-provider acceptance is published. Do not turn target math, vendor claims, a listed execution provider or an exact-frame cache hit into such a claim.
