# Security policy

This project is experimental and has not received a production security audit. Do not publicly expose it without additional deployment controls.

- Bind localhost by default. Require HTTPS and authenticated access before remote exposure.
- Use distinct client/admin secrets. Never expose an unauthenticated admin route.
- Keep provider keys in a secret manager; never in Git, screenshots, issues, logs or shell history.
- Remote images are opt-in and strictly allowlisted; do not disable SSRF/payload bounds for arbitrary public users.
- Screenshot observations remain untrusted data, not privileged instructions. OCR output can contain adversarial text.
- Encoder factories execute trusted local Python code. Never import a user-supplied arbitrary module on a public service.
- The cache/token model is single-principal, not multi-tenant isolation.
- Add rate limits, admission control, end-to-end deadlines, dependency scanning, access logs without payloads and deployment supervision before production.
- A Cloudflare tunnel is transport, not authorization or persistent hosting.

For a suspected secret exposure, revoke/rotate it immediately and report through the repository's private vulnerability reporting feature if available. Otherwise contact the maintainer through their GitHub profile; open a public issue only with a non-sensitive summary. Do not post exploit credentials or private screenshots.

## Live Kaggle enrollment

`deployment_broker.py` must run behind TLS. Its bootstrap ticket is single-use, short-lived and present only in generated **private** deployment code. Provider and gateway keys are fetched at runtime into memory, not embedded into notebook source. Never publish the generated bootstrap or broker config. Reports are authenticated and restricted to non-secret fields. Use distinct client/admin credentials and keep the private controller files mode0600.

`public_edge.py` is the only tunnel origin. It blocks admin/docs/arbitrary paths and requires the client token before forwarding. Do not tunnel the unrestricted gateway port by accident. Quick tunnels have no SLA; session expiry and GPU quota still apply.
