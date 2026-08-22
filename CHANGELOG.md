# Changelog

## v0.1.0 — initial public release candidate

- explicit `<!-- chatgpt-research-loop:receipt-v1 -->` protocol marker plus `TASK_DECISION=` terminal receipt contract;
- actor prefilter before hosted validation, with parser-side authorization re-check;
- public-comment validation on a GitHub-hosted runner before privileged self-hosted wake;
- repository-owner default trust with explicit bot/collaborator allowlist;
- minimal machine-field forwarding allowlist;
- strict uppercase-underscore control-token validation and commit-head validation;
- secret-like key/value filtering;
- semantic fingerprinting plus bounded local wake-history dedupe;
- exact existing ChatGPT conversation targeting;
- Browser Control based local wake bridge;
- suppression of Browser Control native output to avoid leaking the configured conversation URL into public logs;
- immutable SHA pins for GitHub Actions dependencies and disabled checkout credential persistence;
- no OpenAI API dependency in the core bridge;
- no ChatGPT output scraping;
- dedicated Windows self-hosted runner label example;
- success, failure, blocked, and cancellation-style terminal decisions treated explicitly;
- security model, setup guide, related-work comparison, and regression tests.
