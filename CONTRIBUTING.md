# Contributing

Contributions are welcome, especially around browser robustness, receipt schemas, security review, and additional durable control planes.

## Design invariants

Please preserve these unless a change explicitly justifies relaxing them:

1. GitHub (or another durable store) remains authoritative; the browser message is only a wake pointer.
2. Do not infer PASS from CI status alone.
3. Public/untrusted input is validated on a non-privileged runner before a browser-capable self-hosted runner is scheduled.
4. Do not forward arbitrary Issue/PR prose into ChatGPT.
5. Only a minimal machine-field allowlist crosses the wake boundary.
6. Bots/collaborators are explicit trust decisions; do not silently widen the actor allowlist.
7. Do not export cookies, session tokens, conversation URLs, or browser profile data into logs/artifacts.
8. Do not scrape ChatGPT responses in the core wake bridge.
9. Exact conversation targeting is the default and wrong-target ambiguity fails closed.
10. Keep repository permissions minimal and pin external Actions used on privileged paths to immutable commit SHAs.
11. Keep model/API execution out of the core bridge; integrations can be separate optional layers.

## Tests

Run:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

On Windows, also run the wake-script dry-run contract:

```powershell
$env:CHATGPT_RESEARCH_BRAIN_URL = "https://chatgpt.com/c/synthetic-contract-only"
# Create an eligible receipt JSON and invoke tools/wake_chatgpt.ps1 -DryRun.
```

Do not run live browser wake tests against somebody else's ChatGPT session.

## Security-sensitive changes

Changes to any of these areas deserve extra scrutiny:

- public-event -> self-hosted-runner boundaries;
- actor authorization;
- receipt parsing/filtering;
- target URL matching;
- Browser Control execution/logging;
- dedupe state;
- GitHub Actions permissions and dependency pins;
- secret handling;
- any feature that reads model output.

Please explain the threat model and fail-closed behavior in the PR description.
