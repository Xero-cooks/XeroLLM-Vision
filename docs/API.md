# API reference

All `/v1/*` endpoints and `/health` require `Authorization: Bearer $GATEWAY_TOKEN`. `/admin/*` requires the distinct `$GATEWAY_ADMIN_TOKEN`. Missing auth configuration fails closed; identical configured secrets are rejected.

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI chat image-block rewriting and JSON/SSE proxying |
| `GET /v1/models` | Authenticated model discovery (`mercury-3`) |
| `POST /v1/ocr` | Standalone spatial Markdown, elements and metadata |
| `GET /health` | Actual session providers, GPU memory, cache/precision and masked key status |
| `POST /admin/keys` | Append/replace the provider key pool |
| `GET /admin/keys/status` | Masked IDs, request counts, placeholders and cooldowns |

## Provider keys

Use legitimate keys within the provider's terms. The pool is not a quota-evasion or account-rotation mechanism. A 429 honors Retry-After and conservatively cools down the pool by default. Explicit per-key mode and bounded failover are described below.

Set `INCEPTION_API_KEYS` as runtime secrets, or create a protected local JSON file containing `{"keys":["YOUR_PROVIDER_KEY"],"mode":"replace"}` and inject it:

```bash
curl --fail-with-body -sS http://127.0.0.1:8000/admin/keys \
  -H "Authorization: Bearer $GATEWAY_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  --data-binary @/secure/path/inception-pool.json
```

Keys are never returned. Hot reload is in-memory, single-worker and does not survive restarts unless your external secret-management setup reapplies it. Placeholders are never sent upstream.

## Images and frame metadata

`/v1/ocr` accepts `{"image_url":"data:image/jpeg;base64,...","frame_id":"turn-1","captured_at":"2026-01-01T00:00:00Z"}`. `image_url` may alternatively be an object with a `url` field. A chat image uses the standard `{"type":"image_url","image_url":{"url":"..."}}` block.

- `X-UI-Resolution: high` selects a 768×448 detector canvas; default 640×384.
- `X-Session-ID` namespaces caches; this is not multi-tenant authentication.
- Strict GPU mode accepts JPEG only; CPU staging also supports PNG/WebP.
- Remote images are disabled by default. Opt in with `ALLOW_REMOTE_IMAGES=true` and exact `IMAGE_HOST_ALLOWLIST` hostnames. HTTPS, public-address validation, IP pinning, redirect/size/time bounds apply.
- Outputs include normalized center coordinates 0..1000, original pixel boxes and geometric relationships. They do not assert widget roles or icon meaning.

## Dry runs

Send `X-Dry-Run: true` with a normal chat request. It runs the **real selected image encoder**, then simulates provider output. It uses `mercury-3-MOCK`, `X-Gateway-Simulation: true` and simulated lexical units—not measured provider tokens. `ALLOW_MOCK_WHEN_PLACEHOLDER=true` enables automatic placeholder fallback explicitly. Without either opt-in, placeholder-only upstream requests fail 503.

## Streaming and metrics

`stream:true` relays SSE while preserving tool fragments. The default reasoning effort is `instant`; allowed overrides are `low`, `medium`, `high`. Model forwarding is intentionally restricted to `mercury-3`.

Headers include `X-OCR-Latency-Ms`, `X-Images-Processed`, `X-Cache-Hit-Ratio`, `X-Effective-Paired-Tok-Per-Sec`. For SSE, final throughput cannot be known when headers are sent, so it is `pending`. Request `X-Gateway-Metrics:true` for an optional final metrics chunk. A real rate still needs completion-token usage from the provider. JSON responses compute rate after receipt. Client-side networking is included only by the live benchmark, not the server's own wall clock.

This is a chat-completions adapter, not every OpenAI endpoint. Upstream error bodies are sanitized; HTTP2 is negotiated, not guaranteed by client configuration.

## Bounded failover

Requests rotate eligible keys round-robin. Up to three distinct keys can be tried for connection establishment failures, key-specific 401/403 errors and transient 500/502/503/504 responses **before output delivery**. Rejected keys are disabled or cooled down. Ordinary 400 bad-input errors, ambiguous read/write transport failures and partially delivered streams are not replayed. Upstream error bodies and credentials are never relayed. `X-Upstream-Attempts` reports the attempt count.

Rate-limit scope defaults to `KEY_RATE_LIMIT_SCOPE=pool`, safe when keys share one account quota. Set `KEY_RATE_LIMIT_SCOPE=key` only for legitimately independent key quotas: a 429 cools that key until Retry-After and an eligible alternate may be tried. Explicit account/global/billing/credit/quota signals still stop the pool. This option must not be used to evade provider account restrictions or terms.

The public ingress exposes only model discovery, health, OCR and chat. `/admin/*` stays private even with a valid client bearer token. Perform hot reload from the trusted host/network, not the public tunnel.
