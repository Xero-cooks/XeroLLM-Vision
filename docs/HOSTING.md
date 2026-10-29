# Live Kaggle model gateway

## Serving architecture

`Agent → HTTPS quick tunnel → public_edge:8080 → gateway_server:8000 → dual-T4 encoder → Mercury API pool`

The public edge accepts only authenticated model discovery, health, OCR and chat. Admin endpoints remain local. A client uses a generated **gateway** bearer token; it never needs the provider API keys. This remains a text-observation adapter, not native semantic vision.

## What the live runner does

1. A private Kaggle script exchanges a short-lived, one-use bootstrap ticket with an authenticated HTTPS enrollment broker.
2. The broker delivers the provider-key pool, distinct gateway/admin tokens and an authenticated reporting token into process memory. No provider or reusable gateway credentials appear in notebook source.
3. The job installs the pinned GPU stack, runs contract tests and prepares TensorRT sessions on two T4s.
4. It warms actual JPEG OCR using a synthetic UI image, starts the narrow public edge and a checksum-verified official cloudflared client.
5. It checks public model discovery, real screenshot-to-Mercury JSON, live SSE, unauthorized access rejection and blocked admin paths.
6. Only after these checks does it report a ready URL and expiration. It supervises the service for a bounded session and terminates processes at expiry. There are no anti-idle or quota-bypass tricks.

Kaggle initialization and TensorRT preparation can take many minutes. `ready` is different from `submitted` or `installing`. The default serving window is **one hour after readiness**, capped by platform limits and remaining GPU quota. There is no always-on guarantee, custom-domain provisioning or persistent tunnel claim.

## Prepare a private job

The controller needs the official Kaggle client configured with your own existing credentials. Install it separately (`kaggle==2.2.5`, `kagglesdk==0.1.38`); GPU jobs do not need your Kaggle token embedded.

Run `deployment_broker:app` locally using `DEPLOYMENT_BROKER_CONFIG` pointing to a protected JSON file with these fields:

- `bootstrap_token`, `report_token`: independent random high-entropy capabilities.
- `gateway_token`, `admin_token`: distinct generated service credentials.
- `expires_unix`: a short bootstrap deadline.
- `provider_pool_file`: protected JSON file shaped `{"keys":["YOUR_PROVIDER_KEY"]}`.
- `report_file`: protected deployment-status output file.

Expose only that broker through a temporary HTTPS tunnel. Do not expose its config or provider file. Then generate the private job:

```bash
python deploy_live.py \
  --owner YOUR_KAGGLE_USER \
  --out /secure/private/live-prepared \
  --broker-url https://YOUR-BROKER.trycloudflare.com \
  --ticket-file /secure/private/bootstrap-ticket \
  --cloudflared-manifest deploy/cloudflared-manifest.json \
  --session-seconds 3600 \
  --cache-kernel YOUR_KAGGLE_USER/YOUR_COMPLETED_VALIDATION_KERNEL
```

`--cache-kernel` is optional. It attaches your own completed validation output, allowing the runner to restore compatible model/TensorRT caches rather than rebuild them. Never load untrusted serialized engine caches. Regenerate caches when model, runtime, GPU architecture or build settings change.

Submit the generated directory with the official Kaggle client, requesting two T4s and enough **bounded** runtime for setup plus serving. The metadata is private. Never push the generated directory to GitHub. Keep the controller alive through enrollment/readiness; after credentials and service startup, serving does not depend on the controller remaining online.

The current live runner enables per-key cooldown/failover in response to an explicit independent-key pool deployment request; use the default pool-wide policy when quotas are shared. Explicit account/global quota signals still stop the pool. See [API retry semantics](API.md).

## Pair an agent

Use the **ready** URL, not the broker URL. Configure:

```text
OPENAI_BASE_URL=https://YOUR-READY-SESSION.trycloudflare.com/v1
OPENAI_API_KEY=YOUR_GENERATED_GATEWAY_CLIENT_TOKEN
OPENAI_MODEL=mercury-3
```

Use ordinary chat-completions tool schemas and JSON/SSE clients. Send JPEG `image_url` blocks; the proxy rewrites them into untrusted spatial text. Other OpenAI APIs such as Responses, audio and embeddings are not implemented.

Keep the client token in a secret manager or private connection file. Never put provider keys in an agent's public config. The administrator token is different and should not be distributed with agent configuration. Public ingress blocks admin hot-reload routes; update from the trusted host/network or provision a new private session.

When the session ends, the quick-tunnel URL stops working. A new session gets a new URL and credentials. For stable production use, deploy the same application on a persistent supervised GPU host and a properly authenticated named tunnel/domain.

## PNG-producing agents

The strict GPU server accepts JPEG. If an agent produces PNG/WebP data URLs, convert them on the **agent computer**, not on the Kaggle inference CPU path. `agent_client.normalize_messages` handles this while preserving message/tool history. The optional OpenAI SDK wrapper loads the private connection file and disables extra client retries to avoid stacking retries on top of the gateway policy:

```python
# Agent-side dependency: pip install openai
from agent_client import GatewayAgentClient
client = GatewayAgentClient('/secure/private/gateway-agent.json')
result = client.create(messages=your_messages, stream=False)
```

Any standard OpenAI client can connect directly if it already emits JPEG. This helper does not fetch remote image URLs; remote URL handling remains explicitly opt-in at the server. Image conversion adds client-side work and is not included in the reported GPU OCR-stage timer.

## Fresh tunnel DNS

Some sandbox resolvers briefly cache NXDOMAIN for a newly issued quick-tunnel hostname. `cloudflare_transport.py` resolves these hostnames through HTTPS DNS, pins only global IP addresses, and preserves the original Host and TLS SNI/hostname verification. Certificate verification is **not** disabled. Live self-checks and the optional agent wrapper use this transport; ordinary clients can use their normal resolver once propagation settles.
