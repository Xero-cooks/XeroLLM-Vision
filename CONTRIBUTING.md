# Contributing

Use Python3.13 and a fresh environment. Follow the CPU quick start in README, then run:

```bash
python -m pytest -q tests
python verify_quality.py
python benchmark_700toks.py
```

Unit tests deliberately use fixture encoders/mock upstreams for isolation; real encoding benchmarks never substitute fake text. GPU changes need actual hardware receipts and labeled provider/precision status. Keep CPU staging functional.

In a pull request, describe the behavior changed, correctness tests, hardware/driver/runtime versions, cold vs warm timing, quality regressions and known limitations. Include actual sample counts and wall-clock boundaries. Never submit provider keys, private notebook outputs, user screenshots or confidential project notes. Use synthetic or explicitly licensed fixtures.

Do not claim a speedup from projection math. Keep model transformations reproducible and numerically checked; do not overwrite the original pinned artifacts. Do not add account/quota-evasion behavior. Open an issue before a large compatibility or API change.
