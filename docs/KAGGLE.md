# Kaggle compatibility and deployment

## Target and current status

Target: **2× Tesla T4, `sm_75`, approximately16 GB per device**, PCIe rather than NVLink. Actual validation confirmed two T4s on Python3.13.15. Provider enumeration alone does not prove an execution session initialized. Read benchmark and health receipts.

No GPU latency or ≥700tok/s paired-performance acceptance is currently published. Earlier TensorRT preparation exceeded a 600-second process budget; the staged job preserves CUDA results before a separately bounded TensorRT attempt.

## Candidate dependency stack

Use a fresh GPU environment and internet access for initial wheels/model acquisition. The requirements are pinned candidates, not a universal driver compatibility guarantee.

```bash
pip uninstall -y onnxruntime
pip install -r requirements.txt
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
pip install tensorrt-cu12==10.9.0.34
export OCR_BACKEND=gpu
# Set distinct GATEWAY_TOKEN and GATEWAY_ADMIN_TOKEN secrets, then:
bash run_gateway.sh
```

Do not install CPU `onnxruntime` beside `onnxruntime-gpu`: the distributions share a namespace. Kaggle's preinstalled applications can conflict with pinned FastAPI/NumPy dependencies; use an isolated environment for a persistent deployment.

T4 does not provide BF16 or FP8 hardware support. TensorRT uses FP16 with model I/O dtype preserved; some sensitive layers may use FP32. No NVLink or peer-memory speed guarantee is assumed.

## Inspect first

```bash
nvidia-smi
python doctor.py
```

`run_gateway.sh` exports discovered pip NVIDIA library directories before Python starts. The encoder also tries preloading TensorRT and explicitly retries CUDA if ORT silently selects CPU after a provider error. Strict `OCR_BACKEND=gpu` fails if CUDA cannot initialize.

For an explicitly labeled CUDA-only diagnostic run:

```bash
export ENABLE_TENSORRT=false
python benchmark_700toks.py --output evidence/benchmark-cuda.json
```

This is **not** FP16 target acceptance. TensorRT preparation is enabled by default; `TRT_BUILDER_OPT_LEVEL=1` bounds tactic-search complexity relative to more expensive levels, but does not guarantee build time or runtime speed.

## Private validation job

Install/configure the official Kaggle client locally using your own credentials. Never put credentials in notebooks, repository files or command history.

```bash
python deploy_kaggle.py --owner YOUR_KAGGLE_USERNAME --out ../gateway-kaggle-run
kaggle kernels push -p ../gateway-kaggle-run --accelerator NvidiaTeslaT4
```

The script packages source and tests, records hardware first, installs dependencies, runs tests, then CUDA baseline/quality/HTTP checks before the separately bounded TensorRT benchmark. Generated gateway tokens stay in the job process environment. No tunnel or provider key is included. Read `REMOTE_FAILURE.json` and `TRT_FAILURE.json` when present; a completed job is not automatic performance acceptance. Confirm the allocated machine rather than trusting requested metadata.

Engine preparation can take minutes. Keep caches between launches where feasible, record cold preparation separately, and inspect available GPU quota before reruns. A preparation timeout must not become a fabricated warm-latency result.

## Hosting limits

Kaggle sessions stop and quotas apply. A tunnel does not make them durable. For a public service, use a supervised host, HTTPS/access control, authentication, rate limits, isolated secrets and appropriate GPU/runtime licensing. This project does not provision a public tunnel or modify DNS.
