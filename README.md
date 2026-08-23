# ChatGPT Research Loop

> Event-driven, API-free wake-up bridge from trusted GitHub completion receipts to an exact existing ChatGPT conversation.

**Status:** experimental v0.1.0 — first public release

**Unofficial project. Not affiliated with or endorsed by OpenAI or GitHub.**

ChatGPT Research Loop is a small, auditable bridge for long-running work that finishes outside the chat window.

```text
experiment / CI / background job
        |
        v
structured GitHub completion receipt
        |
        v
GitHub-hosted validation + minimization
        |
        v
semantic fingerprint + bounded dedupe
        |
        v
trusted self-hosted Windows runner
        |
        v
local Browser Control bridge
        |
        v
exact existing ChatGPT conversation
        |
        v
ChatGPT re-reads authoritative GitHub state
        |
        v
next decision / next task
```

The core bridge does **not** call the OpenAI API, scrape ChatGPT answers, export cookies, or treat a green CI check as truth. It submits one compact wake-up pointer into a browser tab that you already logged into and explicitly attached.

## Why this exists

Long-running experiments, CI jobs, benchmarks, and agent tasks often finish after the original chat turn is over. Common solutions either start a new model call in CI or send a notification to a human.

This project explores a different pattern:

> keep one persistent ChatGPT conversation as the decision context, keep GitHub as durable evidence, and wake that exact conversation when a trusted terminal receipt appears.

That can preserve context across hours-long asynchronous work without introducing a separate API-backed orchestration service.

## Core properties

- **Event-driven:** reacts to explicit v0.1 receipt markers plus `TASK_DECISION=...` fields in GitHub Issue/PR comments.
- **API-free wake path:** the core bridge uses the existing logged-in ChatGPT web session rather than an OpenAI API key.
- **Exact-conversation targeting:** one configured `https://chatgpt.com/c/...` conversation is the default target.
- **Public-repo isolation:** arbitrary public comments are validated on a GitHub-hosted runner before any privileged self-hosted runner is scheduled.
- **Minimal trust:** only the repository owner is trusted implicitly; bots/collaborators must be explicitly allowlisted.
- **Minimal data:** only `TASK_DECISION`, `FINAL_HEAD`, `HEAD_COMMIT`, `HEAD`, and `NEXT_ACTION` can survive parsing.
- **Machine-token controls:** free-form prose is not forwarded as `TASK_DECISION` or `NEXT_ACTION`.
- **Fail-closed:** malformed receipts, unauthorized actors, missing browser attachment, wrong conversation, or selector drift produce `SKIP`.
- **Deduplicated:** recent source-comment + semantic-fingerprint pairs are stored locally to prevent repeated wake-ups.
- **Conversation URL protection:** Browser Control native output is suppressed so the exact ChatGPT conversation URL is not intentionally written to public Actions logs.
- **GitHub remains authoritative:** ChatGPT is told to re-read the source receipt/current controller before acting.
- **No output scraping:** the bridge sends one message and stops. It does not collect the ChatGPT reply.

## What this is not

This is not a replacement for GitHub Actions, Codex, workflow engines, CI Doctor, or a general autonomous-agent framework.

It also does not guarantee unattended operation forever. Browser sessions expire, web UIs change, laptops sleep, and self-hosted runners go offline. The GitHub receipt therefore remains the durable truth; browser wake-up is a convenience layer.

## Security model first

A public repository must not send arbitrary `issue_comment` events directly to a browser-capable self-hosted runner.

The included workflow deliberately splits the path:

```text
untrusted public comment
        |
        v
validate-receipt (ubuntu-latest)
        |
        | accepted + minimized receipt only
        v
wake-existing-chatgpt-conversation
(self-hosted Windows + chatgpt-loop label)
```

The repository owner is trusted by default. `github-actions[bot]` is **not** trusted by default. If your own Actions workflow emits receipts, explicitly add it to `CHATGPT_LOOP_AUTHORIZED_ACTORS`.

Read [`SECURITY.md`](SECURITY.md) before deploying this in a public repository.

## Quick start

### 1. Requirements

- Windows machine with a self-hosted GitHub Actions runner
- custom runner label `chatgpt-loop`
- Node.js 20+
- Python 3.11+
- Chromium-family browser
- logged-in ChatGPT conversation that will act as the persistent decision context

### 2. Install the tested browser driver

```powershell
npm install --global @opencode-ai/browser-control@0.4.0
```

Find the extension:

```powershell
Join-Path (npm root --global) "@opencode-ai/browser-control/extension/dist"
```

Load that directory as an unpacked browser extension, then attach the exact ChatGPT conversation tab.

### 3. Configure GitHub

Create an Actions secret:

```text
CHATGPT_RESEARCH_BRAIN_URL=https://chatgpt.com/c/<conversation-id>
```

Do not put the URL in workflow YAML or repository files.

Optionally configure trusted receipt producers:

```text
CHATGPT_LOOP_AUTHORIZED_ACTORS=trusted-bot,github-actions[bot]
```

Use only accounts you intentionally trust to wake the conversation.

### 4. Add the workflow

Copy:

```text
.github/workflows/chatgpt-research-loop.yml
```

into the repository where terminal receipts will appear.

The self-hosted runner must have these labels:

```text
self-hosted
windows
x64
chatgpt-loop
```

### 5. Emit a terminal receipt

Every v0.1 receipt starts with:

```text
<!-- chatgpt-research-loop:receipt-v1 -->
```

The marker is not a signature; actor authorization still applies. It prevents accidental wake-ups when a trusted user merely quotes an old `TASK_DECISION=` line.

From the repository owner:

```text
<!-- chatgpt-research-loop:receipt-v1 -->
TASK_DECISION=PASS_EXPERIMENT
FINAL_HEAD=0123456789abcdef0123456789abcdef01234567
NEXT_ACTION=REVIEW_RESULT
```

Failure and blocked states are first-class too:

```text
<!-- chatgpt-research-loop:receipt-v1 -->
TASK_DECISION=FAIL_TESTS
NEXT_ACTION=DIAGNOSE_FAILURE
```

```text
<!-- chatgpt-research-loop:receipt-v1 -->
TASK_DECISION=BLOCKED_RUNNER
NEXT_ACTION=CHECK_RUNNER
```

The control values must be compact machine tokens. Free-form prose is intentionally rejected/dropped.

### 6. Wake message

A valid receipt becomes a compact pointer similar to:

```text
CHATGPT_RESEARCH_LOOP_WAKE
SOURCE_REPOSITORY=owner/repo
SOURCE_RESOURCE=#42
SOURCE_COMMENT_ID=123456789
SOURCE_URL=https://github.com/owner/repo/issues/42#issuecomment-123456789
SEMANTIC_FINGERPRINT=sha256:...
COMPLETION_CLASS=SUCCESS
COMPLETION_DECISION=PASS_EXPERIMENT
NEXT_ACTION=REVIEW_RESULT

Read the authoritative GitHub source receipt and current repository/controller state before taking further action.
...
```

The bridge intentionally does not paste full experiment output into the chat. ChatGPT should retrieve the authoritative evidence from GitHub using its available connector/tooling.

## Repository layout

```text
.github/workflows/
  chatgpt-research-loop.yml   # validate -> trusted local wake
  tests.yml                   # hosted CI contracts

tools/
  parse_completion_receipt.py # marker, actor gate, allowlist, fingerprint
  wake_chatgpt.ps1            # exact-tab browser wake + local dedupe

tests/
  test_receipt.py             # receipt parser contracts
  test_security_contract.py   # public-runner/logging/supply-chain invariants

docs/
  ARCHITECTURE.md
  SETUP_WINDOWS.md

examples/
  completion-receipts.md
  post-completion-receipt.yml
```

## Receipt philosophy

The bridge recognizes an explicit protocol marker plus explicit machine fields because implicit signals are ambiguous.

A green CI run can mean tests passed; it does not automatically mean a scientific claim is valid, a deployment is safe, or the next task is authorized. That decision belongs to the persistent decision context and the repository's own gates.

For that reason the bridge never converts `workflow conclusion=success` into `TASK_DECISION=PASS` on its own.

## Dedupe model

The semantic identity is based on:

```text
repository
source resource/thread
source comment id
accepted machine fields
```

A SHA-256 fingerprint is computed after minimization. The Windows bridge keeps a bounded history of recent wake keys so event ordering such as `A -> B -> A` does not re-deliver `A`.

## Failure behavior

Examples:

```text
CHATGPT_RESEARCH_LOOP_WAKE=SKIP
REASON=UNAUTHORIZED_ACTOR
```

```text
CHATGPT_RESEARCH_LOOP_WAKE=SKIP
REASON=CHATGPT_TAB_NOT_ATTACHED_OR_ADOPT_FAILED
```

```text
CHATGPT_RESEARCH_LOOP_WAKE=NO_OP
```

A wake failure should not erase the original GitHub completion receipt.

## Tested baseline

See [`TESTED_WITH.md`](TESTED_WITH.md). The v0.1 design currently targets Windows and `@opencode-ai/browser-control@0.4.0`.

## Related work

This project is intentionally narrow. Nearby projects solve related but different problems:

- [`githubnext/agentics`](https://github.com/githubnext/agentics) — agentic GitHub/CI workflows.
- [`openai/codex-action`](https://github.com/openai/codex-action) — run Codex in GitHub Actions.
- [`fitchmultz/pi-oracle`](https://github.com/fitchmultz/pi-oracle) — asynchronous ChatGPT-web interaction from another agent context.
- [`eimexdev/RightClickGPT`](https://github.com/eimexdev/RightClickGPT) — browser interaction patterns for configured ChatGPT conversations.
- [`anomalyco/browser-control`](https://github.com/anomalyco/browser-control) — local browser driver used by this project.

The distinguishing focus here is the combination of a trusted structured GitHub receipt, minimal event validation, and an API-free wake-up into an exact already-existing ChatGPT conversation.

## Limitations

- ChatGPT DOM selectors can change.
- Browser Control is an external trusted dependency.
- Windows is the only live bridge documented in v0.1.
- A logged-in browser session must remain usable.
- This is an unofficial integration and may require maintenance when upstream products change.
- Users are responsible for checking applicable service terms and policies.

## License

MIT. See [`LICENSE`](LICENSE) and [`NOTICE.md`](NOTICE.md).

## Contributing

Security-sensitive changes should preserve the core invariants:

1. public input is validated before reaching a privileged local runner;
2. GitHub remains authoritative;
3. exact-conversation targeting stays fail-closed by default;
4. the bridge does not scrape ChatGPT output;
5. secrets and private browser state are never intentionally exported;
6. external Actions running on the self-hosted path are pinned to immutable commit SHAs.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`ROADMAP.md`](ROADMAP.md).
