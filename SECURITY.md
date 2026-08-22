# Security

ChatGPT Research Loop controls an already-authenticated browser tab. Treat the local runner, browser profile, and Browser Control installation as privileged infrastructure.

## Default trust model

The public example is fail-closed:

- a v0.1 receipt must contain the exact protocol marker `<!-- chatgpt-research-loop:receipt-v1 -->` plus a safe `TASK_DECISION=` machine token;
- the marker reduces accidental triggers but is **not** a signature or authorization mechanism;
- arbitrary public Issue/PR comments are parsed first on a GitHub-hosted runner;
- the self-hosted Windows runner is scheduled only after the receipt is accepted;
- the repository owner is the only implicitly trusted receipt author;
- bots and collaborators must be explicitly listed in `CHATGPT_LOOP_AUTHORIZED_ACTORS`;
- only five machine fields are accepted: `TASK_DECISION`, `FINAL_HEAD`, `HEAD_COMMIT`, `HEAD`, and `NEXT_ACTION`;
- `TASK_DECISION` and `NEXT_ACTION` must be compact machine tokens, not prose;
- commit-head fields must look like hexadecimal commit IDs;
- the exact ChatGPT conversation URL is stored as a GitHub secret and is not intentionally printed to Actions logs;
- exact-conversation targeting is the default; fallback targeting is opt-in only;
- GitHub remains the durable source of truth. A wake message is only a pointer.

## Public repository runner isolation

Do **not** route an `issue_comment` event directly to a privileged self-hosted runner in a public repository.

The included workflow has two jobs:

1. `validate-receipt` runs on `ubuntu-latest`, validates the marker, actor and minimized receipt;
2. `wake-existing-chatgpt-conversation` runs on `[self-hosted, windows, x64, chatgpt-loop]` only when validation succeeds.

Use a dedicated `chatgpt-loop` runner label. Do not run fork pull-request code on that browser-capable runner.

## Authorized actors

The repository owner is trusted automatically. No other identity is trusted automatically.

If a GitHub Actions workflow posts receipts, explicitly configure:

```text
CHATGPT_LOOP_AUTHORIZED_ACTORS=github-actions[bot]
```

For an organization-owned repository, explicitly list the human/bot accounts that may emit receipts.

Keep this list minimal. Any authorized producer can cause a wake-up message to be sent to the configured ChatGPT conversation.

## Receipt marker

Every v0.1 terminal receipt starts with:

```text
<!-- chatgpt-research-loop:receipt-v1 -->
```

The marker's purpose is operational disambiguation: a trusted user can discuss or quote `TASK_DECISION=PASS_TESTS` without necessarily creating a receipt. It does not prove who created the comment. Actor authorization is still mandatory.

## Prompt-injection resistance

Public Issue/PR prose is attacker-controlled. It is never copied into the wake prompt.

The parser keeps only a minimal allowlist of machine fields. Free-form `NEXT_ACTION` values are discarded. The wake bridge tells ChatGPT to re-read authoritative GitHub state rather than treating the wake message as evidence.

This reduces the attack surface but does not make arbitrary automation safe. Protect the workflows and every trusted receipt producer.

## Secret handling

Never put secrets in GitHub receipt comments. Public comments are public regardless of parser filtering.

Do not include:

- API keys or PATs;
- passwords;
- cookies or session tokens;
- private keys;
- cloud credentials;
- private dataset URLs or signed download URLs.

`CHATGPT_RESEARCH_BRAIN_URL` should be stored as a repository Actions secret. The wake script suppresses Browser Control native stdout/stderr because those tools may echo the target URL.

## Browser session authority

The attached ChatGPT tab uses your real logged-in browser profile. Browser Control is a trusted local driver, not a sandbox.

The tested dependency is:

```text
@opencode-ai/browser-control@0.4.0
```

Audit upgrades before changing the pinned version in your deployment. Keep its relay local to the machine.

## Supply-chain controls

The included workflows pin GitHub Actions dependencies to full commit SHAs and disable checkout credential persistence. Review dependency updates before changing those SHAs, especially for any step that runs on the self-hosted machine.

## Wrong-conversation delivery

Exact matching against one configured `https://chatgpt.com/c/...` URL is the default. If that tab cannot be adopted, the bridge returns `SKIP`.

`-AllowUniqueConversationFallback` is an explicit local opt-in and is intentionally not enabled by the included GitHub workflow.

## DOM drift and service changes

ChatGPT's web UI and third-party browser tooling can change. Selector or adoption failures must fail closed. Do not add broad click fallbacks that could submit into unrelated UI.

This is an unofficial integration. Users are responsible for checking the terms and policies applicable to the services and automation tools they use.

## Recommended repository settings

- protect the default branch;
- require review for `.github/workflows/**` changes;
- keep workflow `GITHUB_TOKEN` permissions minimal;
- use a dedicated self-hosted runner label or runner group;
- do not expose the Browser Control relay to a network;
- keep `CHATGPT_LOOP_AUTHORIZED_ACTORS` minimal;
- enable private vulnerability reporting if you expect external users.

## Reporting a vulnerability

Do not post credentials, conversation URLs, browser state, or exploit details in a public Issue. Use GitHub private vulnerability reporting when enabled, or contact the repository owner privately.
