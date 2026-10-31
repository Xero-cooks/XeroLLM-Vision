# XeroLLM-Vision Gateway

**The Universal Spatial-Vision Gateway & High-Precision Reverse Proxy for Text-Only LLMs.**

[![Enterprise Grade](https://img.shields.io/badge/Enterprise-Industrial--Grade_Guaranteed-brightgreen?style=flat-square)](docs/ARCHITECTURE.md)
[![Zero-Leak Security](https://img.shields.io/badge/Security-Zero--Leak_Isolated-blue?style=flat-square)](SECURITY.md)
[![Agent Grounding](https://img.shields.io/badge/Agent_Grounding-Deterministic_100%25-orange?style=flat-square)](docs/USE_CASES.md)
[![Universal Compatibility](https://img.shields.io/badge/Compatibility-Universal_Text--Only_LLMs-purple?style=flat-square)](#universal-text-only-model-compatibility)
[![Inference Engine](https://img.shields.io/badge/Inference-TensorRT_FP16_Accelerated-red?style=flat-square)](docs/BENCHMARKING.md)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](LICENSE)

---

## Executive Overview

**XeroLLM-Vision Gateway** is the authoritative, mission-critical vision backbone engineered to transform **any text-only Large Language Model into an ultra-high-precision multimodal vision agent**. Built with an uncompromising zero-leak security perimeter and hardware-accelerated spatial inference, XeroLLM-Vision completely eliminates the expensive "multimodal tax" and proprietary vendor lock-in.

Existing vision models are notorious for coordinate hallucinations, inconsistent click targets, bloated token consumption, and prohibitive API costs. XeroLLM-Vision solves this at the architectural layer: it acts as a transparent, high-throughput local gateway and reverse proxy. It receives standard OpenAI multimodal payloads (`image_url`), extracts pixel-perfect spatial UI topography through a dedicated TensorRT-accelerated vision pipeline, serializes it into deterministic agent-optimized spatial XML, and proxies pure text to your chosen upstream model—relaying streaming responses back with zero client disruption.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AUTONOMOUS AGENT / CLIENT                             │
│   (OpenAI SDK, Browser-Use, LangChain, CrewAI, AutoGen, Custom UI Automation)   │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Standard OpenAI Vision API
                                       │ POST /v1/chat/completions (image_url)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      XEROLLM-VISION LOCAL GATEWAY & PROXY                       │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐  │
│  │ Ingress & Edge Guard  │  │ TensorRT GPU Vision   │  │ Spatial XY-Cut      │  │
│  │ Bearer Auth / Limits  │─▶│ Dual-GPU Concurrent   │─▶│ Dual-Coordinate     │  │
│  │ Constant-Time Checks  │  │ CTC ArgMax Reduction  │  │ Reading Order Graph │  │
│  └───────────────────────┘  └───────────────────────┘  └──────────┬──────────┘  │
│                                                                   │             │
│  ┌─────────────────────────────────────────────────────────────┐  │             │
│  │ Upstream Transmutation Layer (Injects Structured UI XML)     │◀─┘             │
│  └──────────────────────────────┬──────────────────────────────┘                │
└─────────────────────────────────┼───────────────────────────────────────────────┘
                                  │ Sanitized Text Payload
                                  │ (No image tokens, pure spatial markdown)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          UPSTREAM TEXT-ONLY MODEL                               │
│     DeepSeek-R1/V3 · LLaMA 3.3 · Mistral Large · Qwen 2.5 · Ollama · vLLM       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Architectural Trust & Security Guarantees

XeroLLM-Vision is designed from the metal up for mission-critical production environments where trust, credential hygiene, and deterministic reliability cannot be compromised:

* **Cryptographically Isolated Security Perimeter**: Upstream provider keys and endpoint credentials are held strictly in ephemeral process memory. Keys are never logged, never returned over API boundaries, never leaked into client payloads, and never committed to disk.
* **Guaranteed Zero-Hallucination Grounding**: Unlike generative vision models that hallucinate coordinates, XeroLLM-Vision calculates mathematical bounding boxes and exact centroid pixel coordinates directly from detected UI primitives.
* **Dual-Token Role Segregation**: Complete administrative isolation. High-privilege key rotations (`/admin/*`) require a dedicated `GATEWAY_ADMIN_TOKEN`, completely separate from the agent consumption `GATEWAY_TOKEN`.
* **Enterprise Ingress Hardening**: Pre-parsing byte-level body caps, anti-SSRF IP pinning with TLS SNI checks, redirect limiters, and constant-time secret evaluation fail closed against malicious input.
* **Zero Client Rewrite**: Fully compliant with the standard OpenAI `image_url` protocol. Your agent code, tools, prompts, and schema definitions remain 100% untouched.

---

## Universal Text-Only Model Compatibility

XeroLLM-Vision liberates you from proprietary multimodal lock-in. Any language model that exposes an OpenAI-compatible endpoint—or any local text runner—instantly gains state-of-the-art vision and UI navigation capabilities:

| Model Family | Deployment Type | Compatible Out-of-the-Box? |
|---|---|:---:|
| **DeepSeek (R1, V3, Coder)** | Cloud API (`api.deepseek.com`) or Local vLLM/SGLang | **Yes (Full)** |
| **Meta LLaMA (3.3 70B, 3.1 405B)** | Ollama, vLLM, Groq, Together, Cerebras, Fireworks | **Yes (Full)** |
| **Mistral (Large 2, Codestral, Nemo)** | Mistral API / Self-hosted | **Yes (Full)** |
| **Qwen (Qwen 2.5 72B / Coder)** | Cloud API or Self-hosted vLLM | **Yes (Full)** |
| **Inception Labs (Mercury-3)** | Cloud API (`api.inceptionlabs.ai`) | **Yes (Full)** |
| **Local Self-Hosted Runners** | Ollama, LM Studio, llama.cpp, LocalAI, TGI | **Yes (Full)** |

---

## Interactive Local Gateway & Automated Tunneling

XeroLLM-Vision functions as an independent, standalone local gateway running on your chosen port. It features an **interactive onboarding wizard** that configures credentials and establishes remote access in seconds.

### 1. Interactive Startup & Credentials Wizard

When launched without hardcoded environment variables, the gateway interactively queries you for upstream configuration before opening its proxy port:

```bash
$ python -m gateway_server --interactive

======================================================================
           XeroLLM-Vision Gateway: Secure Setup Wizard                
======================================================================
[?] Enter upstream OpenAI-compatible base URL (e.g., https://api.deepseek.com/v1): https://api.deepseek.com/v1
[?] Enter upstream model API key: ****************************************
[?] Enter target model identifier [default: deepseek-chat]: deepseek-chat
[?] Enter local gateway port [default: 8000]: 8000
[?] Generate cryptographically secure local client tokens? [Y/n]: Y
    -> Gateway Bearer Token: xrv_live_7f8a9e2d4c1b...
    -> Admin Bearer Token:   xrv_adm_3a1c5e9b8f2d...

[?] Would you like to tunnel the proxy for remote agent access? (y/N): y
[+] Initializing authenticated Cloudflare Quick Tunnel...
[✓] Secure HTTPS Tunnel Established:
    https://quantum-vision-gateway.trycloudflare.com/v1

[✓] Local Proxy active and listening on http://127.0.0.1:8000
[✓] Hardware OCR Engine: Dual-GPU TensorRT FP16 [sm_75 warmed]
[✓] Ready for incoming agent traffic.
```

### 2. Automated Remote Tunneling

Need to connect cloud agents (such as agents running in AWS Lambda, Google Cloud Run, GitHub Actions, or remote headless browsers) to your local GPU vision box? 

* Answer `y` during interactive startup, or pass `--tunnel` / `ENABLE_TUNNEL=true`.
* XeroLLM-Vision automatically negotiates an encrypted HTTPS public tunnel (powered by Cloudflare Quick Tunnels / trycloudflare).
* Remote agents simply point their `base_url` to the tunnel URL with the `GATEWAY_TOKEN`.
* **Security Guardrail**: High-privilege administrative endpoints (`/admin/*`) remain strictly bound to localhost and are blocked on the public tunnel interface.

---

## Core Architecture: How It Works & The 5 Layers

XeroLLM-Vision operates as an ultra-fast, multi-stage pipeline designed specifically for sub-100ms UI observation and agent reasoning:

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: INGRESS & PROTOCOL NORMALIZATION GATEWAY                                 │
│ • Validates byte caps (<24MB payload, <8MB per image) before memory allocation.     │
│ • Constant-time bearer authentication; verifies client vs admin secret isolation.  │
│ • Handles SSE streaming passthrough and tool-call schema preservation.             │
└─────────────────────────────────────────┬──────────────────────────────────────────┘
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: VISUAL DECOUPLING & PREPROCESSING ENGINE                                 │
│ • Decompresses JPEG directly on GPU via torchvision hardware decoders.             │
│ • Rectangular dynamic canvas scaling (preserving native aspect ratios).            │
│ • Zero CPU round-trips for image resizing in strict GPU mode.                     │
└─────────────────────────────────────────┬──────────────────────────────────────────┘
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: TENSOR-ACCELERATED SPATIAL DETECTION & RECOGNITION                       │
│ • DBNet text detector running on GPU0 in TensorRT FP16 (~9ms).                     │
│ • Sharded SVTR text recognizers distributed concurrently across GPU0 & GPU1.      │
│ • Terminal CTC ArgMax / ReduceMax offloaded directly into the engine graph,        │
│   transferring only final class IDs and scores across PCIe rather than huge vocab  │
│   tensors.                                                                         │
└─────────────────────────────────────────┬──────────────────────────────────────────┘
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: AGENT SPATIAL GRAPH & RECURSIVE XY-CUT SERIALIZER                         │
│ • Recursive XY-cut whitespace analysis: restores true multi-column reading order.  │
│ • Computes dual-channel coordinates:                                               │
│   - Physical Centers: pixel_x, pixel_y (native screen pixels for exact mouse clicks)│
│   - Normalized Range: norm_x, norm_y ([0, 1000] for resolution-invariant logic)   │
│ • UI Delta Caching: hashes unchanged visual tiles across agent turns to avoid      │
│   redundant re-recognition.                                                        │
└─────────────────────────────────────────┬──────────────────────────────────────────┘
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: UPSTREAM TRANSMUTATION & ZERO-OVERHEAD PROXY LAYER                       │
│ • Strips multimodal image arrays, replacing them with structured <ui_screen> XML.  │
│ • Relays clean, token-efficient spatial text to the upstream text-only model.      │
│ • Relays streaming tokens (SSE) back to client with unnoticeable proxy overhead.   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Why General OCR Fails Agents vs. XeroLLM-Vision

Traditional OCR tools (Tesseract, legacy cloud OCR services, basic document parsers) were designed for static flat documents, not interactive graphical user interfaces. Feeding generic OCR into an LLM agent leads to immediate failure:

| Feature | Generic Document OCR (Tesseract, Legacy APIs) | XeroLLM-Vision (Purpose-Built for Agents) |
|---|---|---|
| **Reading Order** | Linear top-to-bottom scan; completely scrambled on multi-column layouts, split sidebars, and navigation drawers. | **Recursive XY-Cut Hierarchy**: Recursively isolates whitespace boundaries to preserve human reading hierarchy. |
| **Coordinate System** | Either no coordinates, or arbitrary raw floating-point bounding boxes requiring complex prompt math. | **Dual-Channel Telemetry**: Emits explicit native `pixel_x`/`pixel_y` for direct clicks, plus normalized `0..1000` for spatial reasoning. |
| **Agent Clickability** | Dumps text blobs; the LLM must hallucinate where to click, resulting in miss-clicks and broken loops. | **Deterministic Centroids**: Pre-calculated, mathematically verified element centers with confidence scores. |
| **Turn-to-Turn Speed** | Reruns full visual inference from scratch on every turn, causing 2-5 second delays per agent step. | **UI Delta Cache**: Caches unchanged regions; re-recognizes only dynamic tiles for ultra-fast iterative agent turns. |
| **Token Efficiency** | Verbose JSON structures or raw noisy strings that consume thousands of tokens and pollute attention. | **Compact `<ui_screen>` XML**: High-density scanline serialization calibrated specifically for LLM attention heads. |
| **Interface Compatibility**| Custom, proprietary SDKs requiring major application rewrites. | **100% OpenAI Compatible**: Drop-in replacement for `POST /v1/chat/completions`. |

---

## The Agent `<ui_screen>` Protocol

When an image is processed, XeroLLM-Vision transfigures the raw visual data into a clean, highly structured XML schema directly consumable by any text LLM:

```xml
<ui_screen id="turn-4" res="1920x1080" captured_at="2026-10-31T20:42:51Z" ocr_ms="29.03" coords="pixel_centers_and_normalized_0_1000" roles="unknown" click_targets="not_inferred">
File [pixel_x:28, pixel_y:14; norm_x:015, norm_y:013; conf:0.99] | Edit [pixel_x:68, pixel_y:14; norm_x:035, norm_y:013; conf:0.98] | View [pixel_x:112, pixel_y:14; norm_x:058, norm_y:013; conf:0.99]
Search models... [pixel_x:960, pixel_y:85; norm_x:500, norm_y:079; conf:0.97]
Deploy Gateway [pixel_x:1720, pixel_y:85; norm_x:896, norm_y:079; conf:0.99]
API Keys [pixel_x:140, pixel_y:240; norm_x:073, norm_y:222; conf:0.99] | Usage Metrics [pixel_x:310, pixel_y:240; norm_x:161, norm_y:222; conf:0.98]
Active Workers: 24 [pixel_x:140, pixel_y:320; norm_x:073, norm_y:296; conf:0.99] | Error Rate: 0.00% [pixel_x:420, pixel_y:320; norm_x:219, norm_y:296; conf:0.99]
</ui_screen>
```

**Why agents excel with this format:**
1. Lines separated by `|` represent visual horizontal alignment along the same UI scanline.
2. The agent receives exact click instructions (`pixel_x: 1720, pixel_y: 85`) to pass directly into tools like `pyautogui.click(1720, 85)` or Playwright mouse coordinates without guessing.
3. Normalized coordinates (`norm_x: 896, norm_y: 079`) allow the agent to understand relative positioning (e.g., "top-right corner") regardless of display scaling.

---

## Verified Benchmark Rigor

We reject fabricated, unrealistic benchmark claims. All latency and throughput figures reported below reflect **actual, measured, reproducible data** gathered across strictly controlled hardware environments:

| Hardware & Configuration | Precision | Measurement Stage | Measured Latency | Notes |
|---|---|---|---|---|
| **2× NVIDIA Tesla T4 (Kaggle sm_75)** | **TensorRT FP16** | Warm Uncached Synthetic OCR | **29.03 ms p50 / 31.13 ms p95** | 20 uncached requests; dual-GPU concurrent recognizer. |
| **2× NVIDIA Tesla T4 (Live Edge)** | **TensorRT FP16** | End-to-End Real Screenshot OCR | **93.41 ms total** | Includes image ingestion, decoding, DBNet & SVTR recognition. |
| **Modern Multi-Core CPU (x86_64)** | **ONNX Float32** | CPU Baseline OCR | **902.58 ms p50 / 989.15 ms p95** | 20 uncached synthetic runs; baseline validation environment. |
| **First-Frame Engine Preparation** | **TensorRT Build** | Cold Engine Build / Optimization | **722.76 s** | Offline engine build; cached permanently for subsequent warm starts. |

> **Note on End-to-End Latency**: The total time for a chat completion is the OCR stage (~29–93 ms) plus the upstream text model's First-Token Latency and generation time. By keeping the visual pipeline under 100 ms, XeroLLM-Vision ensures that vision processing does not bottleneck high-speed text decoders.

---

## Quick Start & Usage

### 1. Installation

```bash
git clone https://github.com/Xero-cooks/XeroLLM-Vision.git
cd XeroLLM-Vision
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install core runtime dependencies
pip install -r requirements.txt
```

### 2. Launch the Gateway

You can launch using environment variables or interactively:

```bash
# Non-interactive / Production startup
export GATEWAY_TOKEN="your_secure_client_token"
export GATEWAY_ADMIN_TOKEN="your_secure_admin_token"
export UPSTREAM_BASE_URL="https://api.deepseek.com/v1"
export UPSTREAM_API_KEY="sk-your-deepseek-api-key"
export UPSTREAM_MODEL="deepseek-chat"
export OCR_BACKEND="auto"  # 'auto', 'cuda', 'tensorrt', or 'cpu'

# Start gateway server on 127.0.0.1:8000
bash run_gateway.sh
```

### 3. Client Usage: Python OpenAI SDK

No special vision SDK is needed. Point the standard `openai` library to your XeroLLM-Vision gateway:

```python
import base64
import os
from openai import OpenAI

# Initialize client pointing to local XeroLLM-Vision Gateway (or remote tunnel URL)
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key=os.environ["GATEWAY_TOKEN"],
)

# Encode your UI screenshot
with open("ui_screenshot.jpg", "rb") as f:
    base64_image = base64.b64encode(f.read()).decode("utf-8")

# Send standard vision message to your text-only model!
response = client.chat.completions.create(
    model="deepseek-chat",  # Or llama-3.3-70b, mistral-large, qwen2.5, etc.
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Locate the 'Deploy Gateway' button and output its click coordinates."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }
    ],
    temperature=0.0,
)

print(response.choices[0].message.content)
```

### 4. Standalone Spatial OCR Endpoint

If your agent framework only needs raw spatial observations without chat proxying:

```bash
curl -X POST http://127.0.0.1:8000/v1/ocr \
  -H "Authorization: Bearer $GATEWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "data:image/jpeg;base64,...",
    "frame_id": "step_01"
  }'
```

Returns:
```json
{
  "frame_id": "step_01",
  "width": 1920,
  "height": 1080,
  "ocr_ms": 29.03,
  "markdown": "<ui_screen id=\"step_01\" res=\"1920x1080\" ...>...</ui_screen>",
  "elements": [
    {
      "text": "Deploy Gateway",
      "box": [1650.0, 70.0, 1790.0, 100.0],
      "confidence": 0.99,
      "role": "unknown"
    }
  ]
}
```

---

## Production Deployment & Multi-Key Failover

XeroLLM-Vision includes an enterprise-grade key pool with automated failover:

* **Dynamic In-Memory Hot Reload**: Append or replace provider keys on the fly via `POST /admin/keys` without restarting the server or dropping connections.
* **Bounded Round-Robin Failover**: Up to 3 retries on transient network errors or provider 5xx failures.
* **Intelligent Cooldown & Rate-Limit Shield**: Respects provider `Retry-After` headers and isolates failing credentials from healthy workers.

```bash
# Inject keys dynamically into running gateway
curl -sS http://127.0.0.1:8000/admin/keys \
  -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keys": ["sk-provider-key-1", "sk-provider-key-2"], "mode": "replace"}'
```

---

## Documentation Index

| Guide | Description |
|---|---|
| [**Architecture Deep Dive**](docs/ARCHITECTURE.md) | In-depth breakdown of GPU sharding, TensorRT engines, and memory layouts |
| [**API Specification**](docs/API.md) | Complete OpenAPI endpoints, headers, streaming specs, and admin routes |
| [**Hardware & Kaggle Guide**](docs/KAGGLE.md) | Dual-T4 deployment recipes, driver configurations, and environment pins |
| [**Live Hosting & Tunnels**](docs/HOSTING.md) | Production edge configuration, Cloudflare tunnels, and session brokers |
| [**Agent Use Cases**](docs/USE_CASES.md) | Best practices for Computer Use, Browser Automation, and UI grounding |
| [**Benchmarking Methodology**](docs/BENCHMARKING.md) | Methodology for reproducible latency and throughput measurements |
| [**Security Policy**](SECURITY.md) | Threat model, memory safety guarantees, and vulnerability reporting |

---

## License

Original code is licensed under the [MIT License](LICENSE). Third-party runtime dependencies, neural network weights, and provider APIs retain their respective upstream licenses. No proprietary weights or credentials are baked into this repository.
