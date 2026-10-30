# Live dual-T4 validation — 2026-10-30

Kaggle accepted private live-session version 5 and allocated two NVIDIA Tesla T4 GPUs. Health reported warmed detector/recognizer sessions with TensorRT/CUDA providers and three FP16 sm75 engine-cache files. Three real provider keys were loaded privately; no credentials are in this document.

Verified end-to-end checks: authenticated health and OCR; actual Mercury-3 JSON completion and SSE `[DONE]`; public unauthenticated requests rejected; admin endpoints not exposed by the public edge.

## Measured warm uncached OCR

Three warmup requests followed by 20 measured synthetic 1920x1080 UI screenshot requests, each in a fresh cache namespace. Every sample had zero cache hits, recognized 31 elements, and contained the expected Dashboard/API Keys/Settings labels.

- Server OCR p50: **30.568 ms**.
- Server OCR p95 (nearest rank): **32.239 ms**.
- Controller-observed request wall-time p50: **122.308 ms**. This includes transport and is not the server OCR figure.

The server OCR metric excludes client network transport and LLM inference. Synthetic screenshots do not establish real-world OCR accuracy or production p95. No >=700 tokens/sec paired throughput claim is made from these measurements.

## Bounded hosting

The service stops after ten minutes without OCR/chat work, or after one hour of serving. The submission has a 5,400-second total runtime cap including setup. Health/model polling does not reset idle time. This is temporary Kaggle serving, not permanent hosting.

Staging checks: 77 passed, 1 skipped. Independent pipeline and native-integration results live in the separate XeroKratos integration project.
