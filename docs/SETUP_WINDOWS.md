# Windows setup guide

This guide configures the wake bridge on the Windows machine that owns the logged-in ChatGPT browser session.

## 1. Install prerequisites

Install:

- Git
- Python 3.11+
- Node.js 20+
- a Chromium-family browser
- a GitHub Actions self-hosted runner

Verify:

```powershell
python --version
node --version
npm --version
```

## 2. Install the tested Browser Control version

The v0.1 compatibility baseline is:

```powershell
npm install --global @opencode-ai/browser-control@0.4.0
```

Print the extension path:

```powershell
Join-Path (npm root --global) "@opencode-ai/browser-control/extension/dist"
```

Open `chrome://extensions` or your browser equivalent:

1. enable Developer mode;
2. choose **Load unpacked**;
3. select the extension directory printed above;
4. pin the Browser Control toolbar button.

Check local status:

```powershell
browser-control doctor
browser-control status
```

Keep the Browser Control relay local to the machine.

## 3. Prepare the ChatGPT conversation

Open the exact conversation you want to use as the persistent decision context.

Its URL should be:

```text
https://chatgpt.com/c/<conversation-id>
```

Click the Browser Control extension button to attach that tab.

Keep the browser profile logged in. The workflow cannot complete interactive authentication for you.

## 4. Configure a dedicated self-hosted runner label

The live wake job intentionally requires:

```yaml
runs-on: [self-hosted, windows, x64, chatgpt-loop]
```

Add the custom label:

```text
chatgpt-loop
```

to the Windows runner that owns the browser session. This avoids accidentally scheduling the browser-control job onto another generic self-hosted machine.

Do not use this runner for untrusted fork pull-request code.

## 5. Configure GitHub secrets and actors

Create this Actions secret:

```text
CHATGPT_RESEARCH_BRAIN_URL
```

Value: the exact ChatGPT conversation URL.

The repository owner is the only actor trusted by default.

If other trusted accounts may post receipts, create the repository variable:

```text
CHATGPT_LOOP_AUTHORIZED_ACTORS
```

Use a comma-separated list without spaces, for example:

```text
alice,release-bot
```

If your receipt producer is GitHub Actions, explicitly add:

```text
github-actions[bot]
```

For example:

```text
github-actions[bot],release-bot
```

`github-actions[bot]` is intentionally **not** trusted automatically in the public template.

## 6. Understand the public-repository isolation

The included workflow does not send public `issue_comment` events directly to your Windows runner.

The sequence is:

```text
public Issue/PR comment
        |
        | must contain the v0.1 receipt marker + TASK_DECISION
        v
GitHub-hosted validate-receipt job
        |
        | accepted + minimized receipt only
        v
self-hosted Windows wake job
        |
        v
attached ChatGPT conversation
```

An unauthorized, unmarked, or malformed comment stops before the self-hosted job is scheduled.

## 7. Dry-run the wake bridge locally

Create a temporary eligible receipt JSON:

```powershell
@{
  eligible = $true
  completion_class = "SUCCESS"
  decision = "PASS_SYNTHETIC"
  repository = "example/demo"
  source_resource = "#1"
  source_comment_id = "synthetic-1"
  source_url = "https://github.com/example/demo/issues/1#issuecomment-synthetic-1"
  semantic_fingerprint = "sha256:synthetic"
  next_action = "STOP"
} | ConvertTo-Json | Set-Content "$env:TEMP\chatgpt-loop-receipt.json" -Encoding UTF8
```

Set a synthetic URL for dry-run prompt construction:

```powershell
$env:CHATGPT_RESEARCH_BRAIN_URL = "https://chatgpt.com/c/synthetic-contract-only"
```

Run:

```powershell
.\tools\wake_chatgpt.ps1 `
  -ReceiptJsonPath "$env:TEMP\chatgpt-loop-receipt.json" `
  -DryRun
```

Expected:

```text
CHATGPT_RESEARCH_LOOP_WAKE=DRY_RUN_PASS
```

Dry run does not touch the browser and does not print a real conversation ID.

## 8. Live synthetic acceptance

Before using real experiment receipts, post one non-sensitive synthetic receipt from an authorized actor:

```text
<!-- chatgpt-research-loop:receipt-v1 -->
TASK_DECISION=PASS_SYNTHETIC
NEXT_ACTION=STOP
```

The marker prevents accidental wake-ups when a trusted user merely quotes a `TASK_DECISION=` line; it does not replace actor authorization.

If the receipt is produced by GitHub Actions, first add `github-actions[bot]` to `CHATGPT_LOOP_AUTHORIZED_ACTORS`.

A successful self-hosted run should contain only generic status such as:

```text
CHATGPT_RESEARCH_LOOP_WAKE=PASS
ADOPT_MODE=EXACT
```

It should not print the exact ChatGPT conversation URL.

The configured ChatGPT conversation should receive one wake message.

Editing or re-delivering the same semantic receipt should not create another wake for the same source comment + semantic fingerprint. The local bridge keeps a bounded history of recent wake keys.

## 9. Operational advice

- Keep the dedicated ChatGPT tab open when practical.
- Prevent the Windows machine from sleeping during long unattended work.
- Do not expose Browser Control's relay to the network.
- Protect workflow-file changes on the default branch.
- Review upgrades to Browser Control before changing from the tested version.
- Keep final/held-out/private evidence behind separate authorization gates when your research or evaluation process requires them.
- Remember that the GitHub receipt remains authoritative even if browser wake delivery fails.
