from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "chatgpt-research-loop.yml"
TEST_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
EXAMPLE_WORKFLOW = ROOT / "examples" / "post-completion-receipt.yml"
WAKE = ROOT / "tools" / "wake_chatgpt.ps1"
PARSER = ROOT / "tools" / "parse_completion_receipt.py"

SHA_PIN = re.compile(r"uses:\s+[^@\s]+@[0-9a-f]{40}(?:\s+#.*)?$")


class SecurityContractTests(unittest.TestCase):
    def test_public_comment_validation_precedes_self_hosted_wake(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("<!-- chatgpt-research-loop:receipt-v1 -->", text)
        self.assertIn("contains(github.event.comment.body, 'TASK_DECISION=')", text)
        self.assertIn("github.actor == github.repository_owner", text)
        self.assertIn("vars.CHATGPT_LOOP_AUTHORIZED_ACTORS", text)
        self.assertIn("validate-receipt:", text)
        self.assertIn("runs-on: ubuntu-latest", text)
        self.assertIn("needs: validate-receipt", text)
        self.assertIn("if: needs.validate-receipt.outputs.eligible == 'true'", text)
        self.assertIn("runs-on: [self-hosted, windows, x64, chatgpt-loop]", text)

    def test_actions_are_commit_sha_pinned(self):
        for path in (WORKFLOW, TEST_WORKFLOW, EXAMPLE_WORKFLOW):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "uses: actions/" in line:
                    self.assertRegex(line.strip(), SHA_PIN, msg=f"unpinned action in {path}: {line}")

    def test_checkout_does_not_persist_credentials(self):
        for path in (WORKFLOW, TEST_WORKFLOW, EXAMPLE_WORKFLOW):
            text = path.read_text(encoding="utf-8")
            checkout_count = text.count("uses: actions/checkout@")
            self.assertGreater(checkout_count, 0)
            self.assertEqual(
                text.count("persist-credentials: false"),
                checkout_count,
                msg=f"every checkout must disable credential persistence in {path}",
            )

    def test_workflow_has_read_only_global_permissions(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("issues: write", text)
        self.assertNotIn("pull-requests: write", text)

    def test_real_conversation_secret_only_appears_in_privileged_job(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        before_wake = text.split("wake-existing-chatgpt-conversation:", 1)[0]
        self.assertNotIn("CHATGPT_RESEARCH_BRAIN_URL", before_wake)
        self.assertIn("secrets.CHATGPT_RESEARCH_BRAIN_URL", text)

    def test_parser_requires_explicit_marker_and_strict_control_tokens(self):
        text = PARSER.read_text(encoding="utf-8")
        self.assertIn("<!-- chatgpt-research-loop:receipt-v1 -->", text)
        self.assertIn(r"^[A-Z][A-Z0-9_]{0,79}$", text)
        self.assertIn("ALLOWED_FIELDS", text)

    def test_example_producer_emits_protocol_marker(self):
        text = EXAMPLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("<!-- chatgpt-research-loop:receipt-v1 -->", text)
        self.assertIn("github-actions[bot]", text)
        self.assertIn("CHATGPT_LOOP_AUTHORIZED_ACTORS", text)

    def test_wake_does_not_echo_browser_control_native_output(self):
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("$null = & browser-control @Arguments 2>&1", text)
        self.assertNotIn("Write-Host $_", text)
        self.assertNotIn("return { url:", text)

    def test_exact_conversation_is_default(self):
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn('$adoptMode = "EXACT"', text)
        self.assertIn("-and $AllowUniqueConversationFallback", text)
        self.assertNotIn("-AllowUniqueConversationFallback\n", WORKFLOW.read_text(encoding="utf-8"))

    def test_dedupe_keeps_bounded_history(self):
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("recent_wake_keys", text)
        self.assertIn("$newKeys.Count -gt 256", text)

    def test_native_browser_output_is_not_logged(self):
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("Invoke-BrowserControlQuiet", text)
        self.assertNotIn("page.url(), submitted", text)


if __name__ == "__main__":
    unittest.main()
