# Benchmarking without misleading speed claims

```bash
python -m pytest -q tests
python verify_quality.py
python benchmark_700toks.py
# With real provider keys configured and an authenticated running gateway:
python benchmark_700toks.py --live-url http://127.0.0.1:8000
```

The encoder benchmark generates five1920×1080 synthetic frames sharing a text-heavy UI layout, runs three warmups, twenty uncached requests and a five-frame sequence. Exact-repeat caching is reported separately. These fixtures are not a varied real-world screenshot dataset or full terminal/form/icon quality suite.

## Keep the clocks separate

- Cold dependency/model/engine preparation is not warm image-encoding latency.
- Uncached encoding, changed-frame caching and exact-repeat hits are separate populations.
- The assumed1068tok/s vendor baseline and18ms extra overhead are **projection inputs**, not measured upstream behavior.
- Mock streams simulate lexical units; they are not real token usage.
- Live paired speed uses **actual completion-token usage / client wall seconds**. Real prefill, TTFT, networking, queueing and output length matter.

For output lengthN and actual provider generation rateR:

`paired_rate = N / (encoding + proxy + network + prefill + N/R)`

A fast decoder cannot guarantee a universal paired rate independent of output length. The current live probe records requested and actual token counts; a max-token budget does not force the model to emit exactly that many tokens. Multiple repetitions and realistic task-quality evaluation are needed before broad performance claims.

## Recorded evidence

`evidence/cpu-baseline.json` contains an actual CPU PP-OCRv4 baseline:20uncached samples,902.58ms median and989.15ms nearest-rank p95. It predates later GPU-only CTC/runtime changes; it is not a T4 measurement. `evidence/ctc-graph-equivalence.json` records exact IDs/scores against the original real recognizer on CPU. `evidence/validation-status.json` records sanitized hardware/test status without private notebook URLs.

No ≥700tok/s live-provider acceptance is published. Do not turn target math, vendor claims, a listed execution provider or an exact-frame cache hit into such a claim.
