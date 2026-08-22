#!/usr/bin/env python3
"""Parse a minimal, trusted GitHub completion receipt for ChatGPT Research Loop.

Security properties:
- a dedicated receipt marker is required;
- only explicit machine-readable ALL_CAPS=value lines are considered;
- only a very small field allowlist survives parsing;
- the repository owner is trusted by default; every other actor must be explicit;
- control values are strict uppercase underscore tokens, never free-form prose/URLs;
- secret-like keys/values are never forwarded;
- success is never inferred from CI state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

RECEIPT_MARKER = "<!-- chatgpt-research-loop:receipt-v1 -->"
FIELD_RE = re.compile(r"^([A-Z][A-Z0-9_]{1,63})=(.*)$")
CONTROL_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")
HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")

# V0.1 intentionally forwards only the minimum information needed to wake the
# existing conversation. ChatGPT is expected to re-read GitHub for detail.
ALLOWED_FIELDS = {
    "TASK_DECISION",
    "FINAL_HEAD",
    "HEAD_COMMIT",
    "HEAD",
    "NEXT_ACTION",
}
HEAD_FIELDS = {"FINAL_HEAD", "HEAD_COMMIT", "HEAD"}

SECRET_KEY_FRAGMENTS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "PRIVATE_KEY",
    "COOKIE",
    "SESSION",
    "CREDENTIAL",
    "AUTHORIZATION",
)
TOKEN_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}\b", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def completion_class(decision: str) -> str:
    token = decision.strip().upper()
    if token == "BLOCKED" or token.startswith("BLOCKED_"):
        return "BLOCKED"
    if token in {"CANCELLED", "CANCELED"} or token.startswith(("CANCELLED_", "CANCELED_")):
        return "CANCELLED"
    if token == "FAIL" or token.startswith("FAIL_") or token.endswith("_FAIL"):
        return "FAILURE"
    if token == "PASS" or token.startswith("PASS_") or token.endswith("_PASS"):
        return "SUCCESS"
    return "TERMINAL_OTHER"


def is_secret_key(key: str) -> bool:
    upper = key.upper()
    return any(fragment in upper for fragment in SECRET_KEY_FRAGMENTS)


def looks_sensitive(value: str) -> bool:
    return any(pattern.search(value) for pattern in TOKEN_PATTERNS)


def _safe_machine_value(key: str, value: str) -> bool:
    if not value or looks_sensitive(value):
        return False
    if key in HEAD_FIELDS:
        return HEAD_RE.fullmatch(value) is not None
    # TASK_DECISION and NEXT_ACTION are deliberately not URLs, paths, shell
    # fragments, or prose. Keep them as compact protocol identifiers only.
    return CONTROL_TOKEN_RE.fullmatch(value) is not None


def parse_machine_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in body.splitlines():
        match = FIELD_RE.fullmatch(raw_line.strip())
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if key not in ALLOWED_FIELDS:
            continue
        if is_secret_key(key):
            continue
        if not _safe_machine_value(key, value):
            continue
        fields[key] = value
    return fields


def parse_actor_allowlist(raw: str) -> set[str]:
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def semantic_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def adapt_issue_comment_payload(payload: dict[str, Any], authorized_actors: set[str]) -> dict[str, Any]:
    if payload.get("action") not in {"created", "edited"}:
        return {"eligible": False, "reason": "unsupported_action"}

    repository_obj = payload.get("repository") or {}
    repository = str(repository_obj.get("full_name") or "").strip()
    repository_owner = str((repository_obj.get("owner") or {}).get("login") or "").strip()
    issue = payload.get("issue") or {}
    comment = payload.get("comment") or {}
    actor = str((comment.get("user") or {}).get("login") or (payload.get("sender") or {}).get("login") or "").strip()
    number = issue.get("number")
    comment_id = comment.get("id")
    body = str(comment.get("body") or "")

    if not repository or number is None or comment_id is None:
        return {"eligible": False, "reason": "missing_github_identity"}
    if RECEIPT_MARKER not in body:
        return {"eligible": False, "reason": "missing_receipt_marker"}

    # Fail closed: only the repository owner is implicit. Bots and collaborators
    # must be explicitly listed in CHATGPT_LOOP_AUTHORIZED_ACTORS.
    allowed = {item.lower() for item in authorized_actors}
    if repository_owner:
        allowed.add(repository_owner.lower())
    if actor.lower() not in allowed:
        return {"eligible": False, "reason": "unauthorized_actor", "actor": actor}

    fields = parse_machine_fields(body)
    decision = fields.get("TASK_DECISION", "").strip().upper()
    if not decision:
        return {"eligible": False, "reason": "missing_or_unsafe_task_decision"}

    is_pr = bool(issue.get("pull_request"))
    source_resource = f"#{number}"
    source_thread_key = f"{'pr' if is_pr else 'issue'}:{number}"
    source_url = str(comment.get("html_url") or issue.get("html_url") or "")
    source_head = fields.get("FINAL_HEAD") or fields.get("HEAD_COMMIT") or fields.get("HEAD") or None

    semantic_payload = {
        "schema": "chatgpt-research-loop-receipt-v1",
        "repository": repository,
        "source_resource": source_resource,
        "source_thread_key": source_thread_key,
        "source_comment_id": str(comment_id),
        "decision": decision,
        "fields": fields,
    }

    return {
        "eligible": True,
        "completion_class": completion_class(decision),
        "decision": decision,
        "repository": repository,
        "source_resource": source_resource,
        "source_thread_key": source_thread_key,
        "source_comment_id": str(comment_id),
        "source_url": source_url,
        "source_head": source_head,
        "next_action": fields.get("NEXT_ACTION"),
        "semantic_fingerprint": semantic_fingerprint(semantic_payload),
        "fields": fields,
        "actor": actor,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--authorized-actors", default="")
    args = parser.parse_args()

    payload = json.loads(Path(args.event_json).read_text(encoding="utf-8"))
    result = adapt_issue_comment_payload(payload, parse_actor_allowlist(args.authorized_actors))
    Path(args.output_json).write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"eligible": result.get("eligible"), "reason": result.get("reason")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
