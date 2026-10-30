# Bounded serving safety — 2026-10-30

The private Kaggle live session stops after ten minutes without OCR/chat workload, or at its one-hour serving deadline, whichever comes first. Health and model-discovery polling does not reset workload activity. The Kaggle submission additionally has a 5,400-second total runtime cap (including setup).

The activity timestamp is touched only after authentication and request-size checks on `/v1/ocr` and `/v1/chat/completions`, and while their response streams produce output. Administrative and health polling cannot keep a GPU allocated indefinitely.

Controller staging checks: 77 passed, 1 skipped (optional backend dependency), one deprecation warning. A missing HTTP/2 `h2` controller dependency was fixed using the pinned staging requirements. No GPU latency or live readiness is implied by these CPU tests.
