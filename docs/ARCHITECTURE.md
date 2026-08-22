# Architecture

ChatGPT Research Loop is deliberately split so untrusted public input never reaches the privileged browser runner directly and the browser bridge never becomes the durable source of truth.

## 1. Durable completion plane

A long-running task writes an explicit v0.1 terminal receipt into GitHub:

```text
<!-- chatgpt-research-loop:receipt-v1 -->
TASK_DECISION=PASS_TESTS
FINAL_HEAD=0123456789abcdef0123456789abcdef01234567
NEXT_ACTION=REVIEW_EXACT_HEAD
```

The receipt marker is an operational protocol marker, not a signature. Actor authorization is checked separately.

The receipt is evidence produced by the task/workflow that actually ran. The loop never converts a green CI badge into a scientific or engineering PASS by itself.

## 2. Public validation plane

The workflow first applies a cheap GitHub-expression prefilter for:

- the exact v0.1 receipt marker;
- an explicit `TASK_DECISION=` line;
- repository-owner or explicitly allowlisted actor identity.

The Python parser then independently re-checks all of those assumptions on `ubuntu-latest`, not on the browser-capable self-hosted machine.

`tools/parse_completion_receipt.py` applies these reductions before the self-hosted job may start:

1. requires `<!-- chatgpt-research-loop:receipt-v1 -->`;
2. authorizes only the repository owner plus an explicit actor allowlist;
3. accepts only explicit `ALL_CAPS=value` lines;
4. keeps only `TASK_DECISION`, `FINAL_HEAD`, `HEAD_COMMIT`, `HEAD`, and `NEXT_ACTION`;
5. restricts decision/action values to uppercase underscore protocol identifiers;
6. rejects invalid commit IDs;
7. applies defense-in-depth secret/token filtering;
8. computes a deterministic semantic fingerprint;
9. serializes only the minimized result into a base64 job output.

Arbitrary Issue/PR prose is never passed to the browser runner.

The fingerprint is a dedupe identity, not a cryptographic signature.

## 3. Privileged local wake plane

Only an accepted minimized receipt schedules:

```text
[self-hosted, windows, x64, chatgpt-loop]
```

The custom `chatgpt-loop` label is intentional. It keeps this job bound to the Windows machine that owns the attached browser session instead of any generic self-hosted runner.

The workflow reconstructs the sanitized receipt in the runner temp directory and reads `CHATGPT_RESEARCH_BRAIN_URL` from a GitHub Actions secret.

The checkout action on this path is pinned to an immutable commit SHA and configured with `persist-credentials: false`.

## 4. Browser-control plane

`tools/wake_chatgpt.ps1` uses Browser Control to adopt an already-attached ChatGPT conversation tab.

Default behavior requires the adopted page URL to exactly equal the configured `https://chatgpt.com/c/...` URL.

The script sends only:

- source repository;
- source Issue/PR number;
- source comment URL/ID;
- semantic fingerprint;
- completion class/decision;
- a compact machine `NEXT_ACTION` token when present;
- instructions to re-read GitHub before acting.

The bridge does not inspect ChatGPT's response.

Browser Control native stdout/stderr is suppressed because it may include the adopted target URL. The JavaScript execution result also deliberately omits `page.url()`.

## Why GitHub stays authoritative

A browser UI is not durable enough to be a research or engineering control plane. Tabs close, sessions expire, selectors change, and laptops sleep.

Browser delivery is therefore a best-effort wake-up only. If it fails, the completion receipt remains in GitHub and can be recovered later by a human, scheduled checker, or another trusted agent.

## Event serialization and dedupe

The workflow serializes deliveries per repository to avoid concurrent writes into one browser session.

The local bridge stores a bounded history (currently 256 entries) of:

```text
source_comment_id | semantic_fingerprint
```

This prevents duplicate ordering such as `A -> B -> A` from causing a second delivery of `A`.

The state file contains no ChatGPT conversation URL, cookies, or browser credentials.

## Fail-closed behavior

The public implementation returns `SKIP` when an identity/safety assumption fails, including:

- missing receipt marker;
- unauthorized receipt actor;
- malformed or unsafe `TASK_DECISION`;
- missing/invalid ChatGPT conversation URL;
- no attached browser tab;
- exact conversation cannot be adopted;
- unreadable dedupe state;
- Browser Control failure.

A duplicate returns `NO_OP`.

The optional local `-AllowUniqueConversationFallback` switch exists for tightly controlled environments, but the included GitHub workflow does not enable it.

## Trust boundaries

```text
Public GitHub Issue/PR comment
  | marker + actor prefilter
  v
GitHub-hosted validator
  | marker + actor + strict field allowlist
  v
minimized receipt
  |
  v
self-hosted Windows runner (chatgpt-loop label)
  | exact secret URL, serialized delivery, local dedupe
  v
Browser Control
  | fill + send only; native output suppressed
  v
exact existing ChatGPT conversation
  |
  v
ChatGPT re-reads GitHub authority
```

The local browser profile remains a high-trust environment. Do not run untrusted fork code on that runner and do not expose the browser relay remotely.

## Supply-chain boundary

GitHub Actions used by the included workflows are pinned to immutable commit SHAs and checkout credential persistence is disabled. This matters most for the self-hosted path, where a compromised mutable action reference could execute on the user's browser machine.

Browser Control is not vendored. The documented v0.1 baseline pins the npm package version and treats it as a trusted local dependency.

## Related-work boundary

### GitHub Agentic Workflows / CI Doctor

Projects such as `githubnext/agentics` can start an agent directly inside GitHub automation after CI or repository events. ChatGPT Research Loop instead keeps the decision context in an existing ChatGPT web conversation and uses GitHub as the durable event/evidence plane.

### Codex Action

`openai/codex-action` runs Codex in GitHub Actions. This is a different architecture: model execution occurs in CI rather than by waking an already logged-in browser conversation.

### pi-oracle

`fitchmultz/pi-oracle` can send asynchronous work to web providers such as ChatGPT and later wake a local `pi` agent. The direction here is reversed: an external task finishes first, then the existing ChatGPT conversation is woken.

### RightClickGPT

`eimexdev/RightClickGPT` demonstrates browser-level patterns for targeting configured ChatGPT conversations. This project combines a local trusted browser driver with a bounded GitHub completion contract.

## Non-goals

- remotely controlling arbitrary ChatGPT sessions;
- bypassing authentication;
- exporting session tokens/cookies;
- scraping model responses;
- treating untrusted Issue prose as instructions;
- replacing human review gates;
- silently consuming held-out/private evidence;
- guaranteeing compatibility with future ChatGPT DOM changes.
