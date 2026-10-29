# Mercury 3 Vision Gateway

**An OpenAI-compatible image-to-spatial-text proxy for text-only LLMs.**

Send a screenshot using a standard OpenAI `image_url` message. The gateway reads visible text, attaches bounding boxes and normalized coordinates, converts the observation to compact spatial Markdown, then forwards a text-only request to Inception's Mercury 3 API.

> **Experimental.** This is an independent open-source project, not an Inception Labs product. A dual-T4 TensorRT FP16 configuration measured **29.03 ms p50 / 31.13 ms p95** on 20 warm uncached synthetic-frame requests using the reported OCR-stage timer (before final Markdown serialization). The ≥700 end-to-end tokens/s goal is **not a demonstrated live-provider result**. Model decode speed, mock responses and projected throughput are not live benchmarks.

## What it does

- Accepts `POST /v1/chat/completions`, including JSON and SSE responses, plus authenticated `GET /v1/models` for agent discovery.
- Rewrites screenshot `image_url` blocks while preserving text, tool history and tool schemas.
- Provides `POST /v1/ocr` for standalone text, boxes, confidence, frame metadata and geometric reading-order relationships.
- Implements PP-OCRv4 ONNX detection and recognition, with experimental TensorRT FP16 acceleration and concurrent dual-GPU recognition.
- Uses rectangular detector canvases and GPU JPEG decoding on supported CUDA installations.
- Caches exact frames and eligible unchanged-region recognition results.
- Supports authenticated provider-key hot reload, round-robin selection, bounded safe failover, placeholder-only dry runs, cooldowns and masked status.
- Includes a private Kaggle serving-session packager, one-use HTTPS runtime enrollment and a public ingress that blocks admin routes.
- Lets you replace the baseline through a trusted local encoder factory.

## What it does not do

This is **not a full vision model**. The OCR baseline cannot reliably identify icons, visual meaning, widget roles, focus state or arbitrary scene content. Coordinates are observations, not guaranteed click targets. Strict GPU mode currently accepts **JPEG only**; PNG/WebP work in explicit CPU staging. Delta caching reruns detection rather than claiming unmeasured partial-detection speedups.

## Use cases

- UI-agent experiments with text-only language models.
- Screenshot-to-text and spatial UI extraction.
- Comparing OCR encoders, cache policies and GPU inference backends.
- Testing existing OpenAI-compatible clients without changing their screenshot message format.

See [use cases and limitations](docs/USE_CASES.md) before using this for autonomous clicking.

## Quick start: CPU staging

Python **3.13** is the tested baseline. Use a fresh environment; do not mix CPU and GPU ONNX Runtime packages.

```bash
git clone https://github.com/Xero-cooks/mercury3-vision-gateway.git
cd mercury3-vision-gateway
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements-staging.txt
pip install onnxruntime==1.22.0 onnx==1.18.0 numpy==2.2.6 Pillow==11.0.0 opencv-python-headless==4.10.0.84

# Generate two distinct local secrets. Store production secrets in a secret manager.
export GATEWAY_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export GATEWAY_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export OCR_BACKEND=cpu
bash run_gateway.sh
```

First launch downloads pinned model artifacts, warms sessions and runs tests/benchmarks. The server binds to **127.0.0.1:8000** by default. CPU staging validates behavior, not T4 performance. Set `RUN_BENCHMARK=0` to skip the startup benchmark after your own validation.

### Extract a screenshot

Convert screenshots to JPEG for strict GPU deployments. With the server running:

```python
import base64, os
from pathlib import Path
import httpx
image = base64.b64encode(Path("screenshot.jpg").read_bytes()).decode()
response = httpx.post(
    "http://127.0.0.1:8000/v1/ocr",
    headers={"Authorization": "Bearer " + os.environ["GATEWAY_TOKEN"]},
    json={"image_url": "data:image/jpeg;base64," + image, "frame_id": "turn-1"},
    timeout=120,
)
response.raise_for_status()
print(response.json()["markdown"])
```

### Use the chat proxy

Install `openai` separately if using this example. Real upstream requests require a legitimate Inception API key in the gateway pool; the client uses the **gateway** token, not that provider key.

```python
import os
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key=os.environ["GATEWAY_TOKEN"])
result = client.chat.completions.create(
    model="mercury-3",
    messages=[{"role":"user", "content":[
        {"type":"text", "text":"Describe the visible controls."},
        {"type":"image_url", "image_url":{"url":"data:image/jpeg;base64,..."}}
    ]}],
)
print(result.choices[0].message.content)
```

See [API reference](docs/API.md) for real-image dry runs, streaming, key injection and telemetry. For a session-limited agent-facing endpoint, see [live Kaggle hosting](docs/HOSTING.md).

## Kaggle: 2× Tesla T4

The target is two 16 GB Turing `sm_75` GPUs, without NVLink. Use TensorRT **FP16**, not BF16 or FP8. Two actual T4s and 51 remote tests were observed. A later staged run completed TensorRT preparation in about 12 minutes and measured 29.03 ms warm p50. This is a controlled synthetic benchmark, not a general latency guarantee.

The Python 3.13 candidate stack uses ORT-GPU 1.22, torch 2.7.1 / torchvision 0.22.1 CUDA 12.6 and TensorRT 10.9. Follow the complete [Kaggle compatibility and deployment guide](docs/KAGGLE.md). Kaggle is an ephemeral, quota-limited development environment—not an always-on production host.

## Validation status

- **76 local unit/contract tests pass** for the current repository. Earlier GPU validation snapshots passed 51 remote tests; live deployment runs its own bundled contract suite before startup.
- Actual CPU OCR baseline: **902.58 ms p50**, **989.15 ms p95**, 20 uncached synthetic-frame measurements. Not a GPU result.
- Terminal CTC ArgMax/ReduceMax matched the original recognizer's IDs and scores in a CPU numerical equivalence test.
- Actual dual-T4 TensorRT configuration: **29.03 ms warm p50 / 31.13 ms p95**,20 uncached synthetic measurements; cold preparation/warmup **722.76 seconds**, first encoded frame **1397.58 ms**. Three cached engines were observed.
- A subsequent session-limited public gateway passed real image OCR, live Mercury JSON/SSE, tool-call forwarding, authentication/admin isolation, and the OpenAI SDK PNG-to-JPEG adapter. Both GPU recognizers and the detector listed TensorRT/CUDA providers, with three cached engines. All three provider keys were exercised. See [live verification evidence](evidence/live-gateway-validation.json).
- That external smoke sample observed **93.41 ms OCR-stage latency** and **608.82 ms client wall time for an 11-token completion**. These are individual checks, not p50 measurements or ≥700 tokens/s proof.
- **Live Mercury ≥700 paired tokens/s, stable always-on hosting and production readiness remain unverified.**

See [benchmark methodology](docs/BENCHMARKING.md) and [sanitized evidence](evidence/validation-status.json). Historical measurements must not be interpreted as results for every subsequent commit.

## Documentation

| Guide | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Data flow, modules, precision, caching and encoder plugins |
| [API](docs/API.md) | Endpoints, credentials, examples, SSE and metrics |
| [Kaggle](docs/KAGGLE.md) | Hardware constraints, dependency pins, validation jobs and troubleshooting |
| [Live hosting](docs/HOSTING.md) | Secure Kaggle session, tunnel, key pool, agent pairing and expiry |
| [Use cases](docs/USE_CASES.md) | Where this approach helps and where it fails |
| [Benchmarking](docs/BENCHMARKING.md) | Measured vs projected vs simulated throughput |
| [Security](SECURITY.md) | Threat model and safe deployment |
| [Contributing](CONTRIBUTING.md) | Tests and contribution expectations |
| [Roadmap](docs/ROADMAP.md) | Remaining validation and engineering work |

## License and dependencies

Original project code is [MIT licensed](LICENSE). Third-party models, packages, GPU runtimes and hosted APIs have their own terms; they are not relicensed by this repository. No weights or credentials are committed. See [third-party notices](THIRD_PARTY_NOTICES.md).

### Native pixel-coordinate clarification

The current source serializer emits explicit `pixel_x/pixel_y` text centers alongside separately named `norm_x/norm_y` values. Text centers are not inferred controls or guaranteed click targets. This addresses observed normalized-versus-native confusion in an experimental XeroKratos integration. The renewed 2026-10-29 private Kaggle session bundled this serializer and passed external real JSON/SSE/tool-call checks. That allocation is ephemeral, not always-on hosting. The XeroKratos integration can also apply native-pixel serialization client-side to diagnostic `/v1/ocr` results without rebuilding GPU engines. Source changes alone do not hot-patch a running Kaggle process.
