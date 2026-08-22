# Tested compatibility baseline

Initial public release candidate prepared on **2026-08-23**.

## Browser wake baseline

The architecture was developed against:

- Windows 10/11 self-hosted GitHub Actions runner
- Python 3.11+
- Node.js 20+
- Chromium-family browser
- `@opencode-ai/browser-control` 0.4.0
- ChatGPT web conversation URL shape: `https://chatgpt.com/c/...`
- ChatGPT composer selector: `#prompt-textarea[contenteditable="true"]`
- send-button selectors: `button[data-testid="send-button"]` or `button[aria-label="Send prompt"]`

## Hosted workflow dependency pins

The v0.1 release candidate pins these GitHub Actions releases by full commit SHA:

- `actions/checkout` v4.2.2 — `11bd71901bbe5b1630ceea73d27597364c9af683`
- `actions/setup-python` v5.6.0 — `a26af69be951a213d495a4c3e4e4022e16d87065`
- example producer: `actions/github-script` v7.1.0 — `f28e40c7f34bde8b3046d885e986cb6290c5673b`

The publisher creates the new repository as **private first**, waits for the exact initial commit's hosted `Tests` workflow to complete successfully, and only then changes visibility to public. Therefore a public v0.1 repository should have passed its own Ubuntu parser/security tests and Windows PowerShell dry-run contract before first visibility.

## Compatibility warning

The ChatGPT DOM is not a stable public API. Browser UI or Browser Control changes may require selector/driver maintenance.

When compatibility breaks, prefer a narrow selector/driver update over weakening actor authorization, exact-conversation targeting, output suppression, or other fail-closed safety rules.
