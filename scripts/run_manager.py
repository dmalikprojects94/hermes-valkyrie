#!/usr/bin/env python3
"""
Watcher run-manager: classify finished/stalled managed runs, deliver rich
continuations, route operator questions, and resume from answers.

Hierarchy:
  watcher detects -> closeout extracts -> manager classifies/acts
  -> transport delivers -> cleanup enforces lifecycle

All manager state is written back to the durable run ledger so actions
remain idempotent — running the manager twice must not double-post,
double-clean, or double-answer.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# ─── Status vocabularies ──────────────────────────────────────────────────────

MANAGER_STATUS_VALUES = (
    "not_ready",
    "classified",
    "continued",
    "asked_operator",
    "answered_runtime",
    "awaiting_continuation_decision",
    "needs_review",
    "failed",
)

MANAGER_CLASSIFICATION_VALUES = (
    "finished_clean",
    "closed_without_postback_decision",
    "finished_blocked",
    "finished_unstructured",
    "waiting_for_continuation",
    "question_for_operator",
    "answerable_question",
    "auth_blocked",
    "permission_blocked",
    "failed",
    "stale",
    "unknown",
)

MANAGER_ACTION_VALUES = (
    "post_continuation",
    "review_continuation",
    "cleanup_terminal",
    "ask_operator",
    "send_runtime_reply",
    "keep_open",
    "needs_manual_review",
)

# Runtime/manifest status the watcher recognizes as a hand-off trigger. The new
# value is non-final for the run (tmux session stays alive) but terminal for the
# watcher (it wakes and hands off to the manager).
RUNTIME_CONTINUATION_STATUS = "waiting_for_continuation"

# ─── Pattern matching ─────────────────────────────────────────────────────────

_QUESTION_RE = re.compile(
    r"(\?\s*$"
    r"|(?:should|would|could|can|do\s+you\s+want|shall|will\s+you)\b.*\?"
    r"|(?:\bconfirm\b|\bproceed\?|\bcontinue\?|yes\s+or\s+no))",
    re.IGNORECASE | re.MULTILINE,
)

_AUTH_RE = re.compile(
    r"(?:log\s*in|authenticate|credentials?\s*(?:required|needed|missing)?"
    r"|api\s*key|access\s*token|unauthorized|permission\s*denied|403\b|401\b)",
    re.IGNORECASE,
)

_PERMISSION_RE = re.compile(
    r"(?:do\s+you\s+(?:trust|allow|permit|accept)"
    r"|bypass.*permission|trust\s+this\s+folder|dangerously)",
    re.IGNORECASE,
)

_OPTION_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s+|(?:\d{1,2}|[A-Z])(?:[.)]|:)\s+).+",
    re.IGNORECASE,
)

# ─── Continuation detection ──────────────────────────────────────────────────
# A continuation is a clean intermediate checkpoint with more work to do, where
# the next move is a decision. Detection is biased toward NOT stealing finality:
# it requires a positive signal (structured runtime event, report sentinel, or
# an option block plus a forward-looking prompt), never a silent default.

# Report sentinels: a `## Continuation Options` heading or a `Continuation:` line.
_CONTINUATION_HEADING_RE = re.compile(
    r"^\s*(?:[●•]\s*)?#{0,3}\s*Continuation Options\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_CONTINUATION_SENTINEL_RE = re.compile(
    r"^\s*(?:[-*]\s*)?Continuation\s*:\s*(\S.*)$",
    re.IGNORECASE | re.MULTILINE,
)

# Forward-looking prose: "which option…", "should I continue with…", "next I can…".
_CONTINUATION_PROSE_RE = re.compile(
    r"(?:which\s+(?:option|approach|path|one)\b"
    r"|should\s+i\s+continue\s+with"
    r"|how\s+(?:would|do)\s+you\s+want\s+me\s+to\s+(?:continue|proceed)"
    r"|next\s+i\s+(?:can|could|will)\b"
    r"|more\s+(?:work|to\s+do)\s+remains"
    r"|ready\s+to\s+continue\s+with"
    r"|waiting\s+for\s+continuation)",
    re.IGNORECASE,
)

# ponytail: a small dedicated allowlist — continuation options are declarative
# ("Run the remaining tests") so the question-shaped _SAFE_AUTO_PATTERNS can't
# match them. Broaden the verbs here if more safe-operational steps are needed.
_SAFE_CONTINUATION_RE = re.compile(
    r"\b(?:run\s+(?:the\s+)?(?:remaining\s+|integration\s+|unit\s+)?tests?"
    r"|continue\s+(?:with\s+)?(?:the\s+)?(?:already[\s-]*)?(?:agreed\s+)?plan"
    r"|proceed\s+with\s+(?:the\s+)?(?:next|agreed|already[\s-]*agreed|planned)"
    r"|next\s+(?:obvious\s+)?(?:sub-?)?step)\b",
    re.IGNORECASE,
)


def _clean_option(line: str) -> str:
    cleaned = re.sub(
        r"^\s*(?:[-*]\s+|(?:\d{1,2}|[A-Za-z])[.)]\s+|[A-Za-z]:\s+)", "", line
    ).strip()
    return cleaned[:200]


def _continuation_options_from_text(text: str) -> list[str]:
    """Extract up to 6 trailing option lines from a bounded output tail."""
    if not text:
        return []
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    recent = lines[-40:]
    opts = [_clean_option(line) for line in recent if _OPTION_LINE_RE.search(line)]
    return opts[-6:]


def detect_report_continuation(report_text: str | None) -> dict:
    """Detect a continuation sentinel in a closeout report.

    Returns {detected, checkpoint, options}. Looks for a `Continuation:` line or
    a `## Continuation Options` block. The report extractor schema is untouched;
    this scans the saved report text directly.
    """
    result: dict[str, Any] = {"detected": False, "checkpoint": "", "options": []}
    if not report_text:
        return result
    sentinel = _CONTINUATION_SENTINEL_RE.search(report_text)
    heading = _CONTINUATION_HEADING_RE.search(report_text)
    if not sentinel and not heading:
        return result
    result["detected"] = True
    if sentinel:
        result["checkpoint"] = sentinel.group(1).strip()[:280]
    if heading:
        opts: list[str] = []
        for raw in report_text[heading.end():].splitlines()[:20]:
            stripped = raw.strip()
            if not stripped:
                if opts:
                    break
                continue
            if _OPTION_LINE_RE.search(stripped):
                opts.append(_clean_option(stripped))
                if len(opts) >= 6:
                    break
            elif opts:
                break
        result["options"] = opts
    if not result["checkpoint"] and result["options"]:
        result["checkpoint"] = result["options"][0]
    return result


def _structured_continuation_event(data: dict) -> bool:
    """True when the runtime explicitly signalled a non-final continuation.

    Authoritative high-confidence signal: the manifest status itself, or a stop
    runtime event whose payload carries `continuation: waiting_for_continuation`.
    """
    if (data.get("status") or "") == RUNTIME_CONTINUATION_STATUS:
        return True
    event = data.get("last_runtime_event") or {}
    if not isinstance(event, dict):
        return False
    if event.get("continuation") == RUNTIME_CONTINUATION_STATUS:
        return True
    if (event.get("status") or "") == RUNTIME_CONTINUATION_STATUS:
        return True
    payload = event.get("payload")
    if isinstance(payload, dict) and payload.get("continuation") == RUNTIME_CONTINUATION_STATUS:
        return True
    return False

# ─── Phase 5: Auto-answer allowlist ──────────────────────────────────────────
# Only safe, reversible, non-destructive, non-auth questions may auto-answer.

_SAFE_AUTO_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:should\s+i|shall\s+i)\s+run\s+(?:the\s+)?tests?", re.IGNORECASE), "yes"),
    (re.compile(r"(?:should\s+i|shall\s+i|do\s+you\s+want\s+me\s+to)\s+continue", re.IGNORECASE), "continue"),
    (re.compile(r"\bcontinue\?$", re.IGNORECASE), "yes"),
    (re.compile(r"\bproceed\?$", re.IGNORECASE), "yes"),
    (re.compile(r"ready\s+to\s+(?:proceed|continue|start)\s*\?", re.IGNORECASE), "yes, proceed"),
]

_UNSAFE_KEYWORDS: frozenset[str] = frozenset([
    "credential", "password", "token", "api key", "secret", "private key",
    "payment", "purchase", "billing", "cost", "charge",
    "deploy", "production", "publish",
    "delete all", "drop table", "rm -rf", "reset --hard",
    "personal", "sensitive", "pii",
    "sign in", "log in", "oauth", "2fa", "mfa",
])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Phase 5 public API ───────────────────────────────────────────────────────

def try_auto_answer(question: str, task_goal: str = "") -> tuple[str | None, str]:
    """Return (answer, reason) or (None, reason) for refusal.

    Never auto-answers credentials, auth, cost, destructive ops, public
    posting, or ambiguous design decisions. Those must go to the operator.
    """
    if not question:
        return None, "empty question"
    q_lower = question.lower()
    for keyword in _UNSAFE_KEYWORDS:
        if keyword in q_lower:
            return None, f"unsafe keyword detected: {keyword!r}"
    for pattern, answer in _SAFE_AUTO_PATTERNS:
        if pattern.search(question):
            return answer, f"matched safe pattern"
    return None, "no safe pattern matched — routing to operator"


# ─── Output inspection helpers ────────────────────────────────────────────────

def _extract_question(text: str) -> str:
    """Extract the most likely question block from runtime output.

    Keep this bounded and conservative: include the detected question plus nearby
    option lines immediately above it, so Discord/operator messages preserve the
    choices Claude/Codex is asking about without dumping the whole pane.
    """
    if not text:
        return ""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    recent = lines[-40:]
    question_index: int | None = None
    for idx in range(len(recent) - 1, -1, -1):
        if _QUESTION_RE.search(recent[idx]):
            question_index = idx
            break
    if question_index is None:
        return ""

    start = question_index
    option_count = 0
    idx = question_index - 1
    while idx >= 0 and option_count < 6:
        line = recent[idx]
        if _OPTION_LINE_RE.search(line):
            start = idx
            option_count += 1
            idx -= 1
            continue
        if option_count and line.lower().endswith(("either:", "options:", "choices:", "paths:")):
            start = idx
        break

    block = "\n".join(recent[start : question_index + 1]).strip()
    return (block[:1199] + "…") if len(block) > 1200 else block


def _looks_like_question(text: str) -> bool:
    return bool(text and _QUESTION_RE.search(text[-2000:]))


def _looks_like_auth_block(text: str) -> bool:
    return bool(text and _AUTH_RE.search(text[-2000:]))


def _looks_like_permission_block(text: str) -> bool:
    return bool(text and _PERMISSION_RE.search(text[-2000:]))


# ─── Phase 1: Deterministic classifier ───────────────────────────────────────

def classify_run(
    data: dict,
    ledger_row: dict,
    *,
    latest_output: str | None = None,
    report_text: str | None = None,
) -> dict:
    """Conservative deterministic classifier from existing manifest/ledger state.

    Reads: closeout_status, report_has_blockers, manifest status, lifecycle
    state, optionally latest terminal/runtime output and the saved report text.

    Continuation precedence (Section 3 of the design):
      structured runtime event > report sentinel > bounded prose fallback >
      normal finality guard. Continuation always requires a positive signal; a
      clean structured no-blocker report with no signal stays finished_clean.

    Returns dict with keys: classification, action, reason, extracted_question,
    confidence, continuation_options, continuation_checkpoint. When uncertain,
    always defaults to needs_manual_review — never guesses.
    """
    closeout_status = (
        data.get("closeout_status")
        or ledger_row.get("closeout_status")
        or "not_run"
    )
    has_blockers = data.get("report_has_blockers")
    if has_blockers is None:
        has_blockers = ledger_row.get("has_blockers")
    manifest_status = data.get("status") or "unknown"

    result: dict[str, Any] = {
        "classification": "unknown",
        "action": "needs_manual_review",
        "reason": "",
        "extracted_question": "",
        "confidence": "",
        "continuation_options": [],
        "continuation_checkpoint": "",
    }

    report_cont = detect_report_continuation(report_text)

    def _continuation_result(*, confidence: str, reason: str) -> dict:
        options = report_cont["options"] or _continuation_options_from_text(latest_output or "")
        checkpoint = report_cont["checkpoint"] or (options[0] if options else "")
        result["classification"] = "waiting_for_continuation"
        result["action"] = "review_continuation"
        result["reason"] = reason
        result["confidence"] = confidence
        result["continuation_options"] = options
        result["continuation_checkpoint"] = checkpoint
        return result

    # ── Precedence 1: structured runtime continuation event (high) ───────────
    if _structured_continuation_event(data):
        return _continuation_result(
            confidence="high", reason="structured runtime continuation event"
        )

    # ── Precedence 2: report sentinel (high) ─────────────────────────────────
    if report_cont["detected"]:
        return _continuation_result(
            confidence="high", reason="continuation sentinel in closeout report"
        )

    # ── Closeout available: classify by quality ──────────────────────────────
    if closeout_status == "structured":
        if has_blockers is False:
            # ── Precedence 3: bounded prose fallback (medium) ────────────────
            if (
                latest_output
                and not _looks_like_auth_block(latest_output)
                and not _looks_like_permission_block(latest_output)
            ):
                tail = latest_output[-2000:]
                forward = bool(_CONTINUATION_PROSE_RE.search(tail))
                options = _continuation_options_from_text(latest_output)
                if forward and len(options) >= 2:
                    return _continuation_result(
                        confidence="medium",
                        reason="prose continuation pattern (options + forward-looking prompt)",
                    )
                if forward:
                    # ── Precedence 4 guard: ambiguity fails toward review ────
                    result["classification"] = "finished_unstructured"
                    result["action"] = "needs_manual_review"
                    result["reason"] = (
                        "ambiguous: clean closeout with unfinished-looking tail "
                        "and no continuation options"
                    )
                    return result
            # Legacy done-means-done: a Discord run using the old generic
            # postback lane is not clean until a postback decision is recorded.
            # Managed loadout runs are different: manage-on-closeout is now the
            # canonical reportback decision, so a pending old postback_status must
            # not block the manager from posting its one response.
            postback_status = ledger_row.get("postback_status") or ""
            manager_owned_closeout = bool(
                ledger_row.get("managed_launcher") == "run_loaded_agent.py"
                or ledger_row.get("launch_origin") == "managed"
                or ledger_row.get("manager_response_status")
            )
            if (
                ledger_row.get("discord_thread_id")
                and not manager_owned_closeout
                and postback_status in ("", "not_ready", "pending")
            ):
                result["classification"] = "closed_without_postback_decision"
                result["action"] = "needs_manual_review"
                result["reason"] = (
                    "structured closeout but no postback decision recorded "
                    f"(postback_status={postback_status or 'missing'}) for a legacy Discord reportback-expected run"
                )
                result["confidence"] = "high"
                return result
            result["classification"] = "finished_clean"
            result["action"] = "post_continuation"
            result["reason"] = "structured closeout with no blockers"
            result["confidence"] = "high"
        elif has_blockers:
            result["classification"] = "finished_blocked"
            result["action"] = "needs_manual_review"
            result["reason"] = "structured closeout but has blockers"
        else:
            result["classification"] = "finished_blocked"
            result["action"] = "needs_manual_review"
            result["reason"] = "structured closeout but blocker status unknown"
        return result

    if closeout_status not in ("", "not_run", "no_final_message"):
        result["classification"] = "finished_unstructured"
        result["action"] = "needs_manual_review"
        result["reason"] = f"closeout={closeout_status} (unstructured or partial)"
        return result

    # ── No usable closeout: classify from lifecycle state ──────────────────
    if manifest_status in ("blocked", "failed"):
        if latest_output:
            if _looks_like_auth_block(latest_output):
                result["classification"] = "auth_blocked"
                result["action"] = "ask_operator"
                result["reason"] = "blocked/failed with auth pattern in output"
            elif _looks_like_permission_block(latest_output):
                result["classification"] = "permission_blocked"
                result["action"] = "ask_operator"
                result["reason"] = "blocked/failed with permission pattern in output"
            elif _looks_like_question(latest_output):
                question = _extract_question(latest_output)
                result["classification"] = "question_for_operator"
                result["action"] = "ask_operator"
                result["reason"] = "blocked with question detected in output"
                result["extracted_question"] = question
            else:
                result["classification"] = "failed"
                result["action"] = "needs_manual_review"
                result["reason"] = f"status={manifest_status} without recognized pattern"
        else:
            result["classification"] = "failed"
            result["action"] = "needs_manual_review"
            result["reason"] = f"status={manifest_status} with no output to inspect"
        return result

    if manifest_status in ("waiting_for_input", "stale"):
        if latest_output and _looks_like_question(latest_output):
            question = _extract_question(latest_output)
            result["classification"] = "question_for_operator"
            result["action"] = "ask_operator"
            result["reason"] = "waiting_for_input with question detected"
            result["extracted_question"] = question
        elif manifest_status == "stale":
            result["classification"] = "stale"
            result["action"] = "keep_open"
            result["reason"] = "stale without detectable question — leaving open"
        else:
            # TODO(bug-D diagnostic): a Claude TUI can look waiting_for_input while
            # subagents are still active; without inspectable output we cannot
            # distinguish the two from manifest/ledger state alone. Root-cause repro
            # still needed (see 2026-07-22 deterministic upgrade plan, B7/Bug D).
            result["classification"] = "question_for_operator"
            result["action"] = "ask_operator"
            result["reason"] = (
                "waiting_for_input without inspectable output — possible subagents/"
                "multi-agent work still active or output not inspectable; verify the "
                "terminal before treating this as an operator question"
            )
        return result

    if manifest_status in ("starting", "ready", "working"):
        result["classification"] = "unknown"
        result["action"] = "keep_open"
        result["reason"] = f"run still in progress: status={manifest_status}"
        return result

    result["reason"] = f"unclassifiable: closeout={closeout_status} status={manifest_status}"
    return result


# ─── Phase 2: Rich continuation message builder ───────────────────────────────

def _section_line(sections: dict, heading: str, max_chars: int = 280) -> str:
    body = (sections.get(heading) or "").strip()
    if not body:
        return ""
    first = next((ln.strip("-* ").strip() for ln in body.splitlines() if ln.strip()), "")
    return (first[: max_chars - 1] + "…") if len(first) > max_chars else first


def _bounded(value: str, max_chars: int = 280) -> str:
    value = " ".join((value or "").split())
    return (value[: max_chars - 1] + "…") if len(value) > max_chars else value


def _commit_push_summary(sections: dict) -> str:
    text = "\n".join(str(sections.get(key) or "") for key in ("Changes", "Verification", "Next Steps"))
    commit = "not reported"
    match = re.search(r"(?:Committed locally|Commit)\s*:\s*`?([0-9a-f]{7,40}\s+[^`\n]+)`?", text, re.IGNORECASE)
    if match:
        commit = _bounded(match.group(1), 180)
    elif re.search(r"\b(no files? .*committed|nothing committed|not committed)\b", text, re.IGNORECASE):
        commit = "not committed"

    push = "not reported"
    if re.search(r"\b(no push|not pushed|nothing pushed)\b", text, re.IGNORECASE):
        push = "not pushed"
    elif re.search(r"\bpushed\b", text, re.IGNORECASE):
        push = "pushed"
    return f"{commit}; push: {push}"


def _visible_proof_summary(ledger_row: dict) -> str:
    proof = ledger_row.get("visible_terminal_proof") or {}
    if not isinstance(proof, dict):
        proof = {}
    status = proof.get("status") or "unproven"
    windows = proof.get("desktop_window_ids") or []
    if windows:
        return f"{status}; windows: {', '.join(str(item) for item in windows[:4])}"
    desktop_windows = proof.get("desktop_windows")
    if desktop_windows:
        return f"{status}; windows: {desktop_windows}"
    return f"{status}; windows: none"


def _terminal_summary(ledger_row: dict) -> str:
    status = ledger_row.get("status") or ledger_row.get("manifest_status") or "unknown"
    policy = ledger_row.get("terminal_closeout_policy") or ledger_row.get("closeout_policy") or {}
    if isinstance(policy, dict) and policy.get("keep_open_after_closeout"):
        reason = policy.get("keep_open_reason") or "kept open for inspection"
        return f"stopped/open for inspection — {reason}"
    if isinstance(policy, dict) and policy.get("cleanup_after_response"):
        return "auto-clean eligible after response"
    return f"{status} — inspect operator-status for lifecycle details"


def build_manager_continuation_message(
    ledger_row: dict,
    sections: dict,
    *,
    cleanup_result: dict | None = None,
    git_status: str = "",
) -> str:
    """Canonical user-facing completion message for a finished_clean run."""
    label = ledger_row.get("session_label") or "unknown"
    runtime = ledger_row.get("runtime") or "?"
    loadout = ledger_row.get("loadout") or "?"
    changes = _section_line(sections, "Changes") or "not reported"
    verification = _section_line(sections, "Verification") or "not reported"
    next_step = _section_line(sections, "Next Steps") or "no further action recorded"
    blockers_text = _section_line(sections, "Blockers") or "none"
    context = ledger_row.get("conversation_context") or {}
    title = context.get("session_title") or ledger_row.get("discord_thread_name") or ""
    report_path = ledger_row.get("report_path") or ""
    hermes_profile = ledger_row.get("hermes_profile") or ""
    manifest_path = ledger_row.get("manifest_path") or ""
    outcome = "structured; blockers: none" if blockers_text.lower().startswith(("none", "no blockers")) else f"structured; blockers: {blockers_text}"

    lines = [
        "Managed coding-terminal complete",
        "",
        f"Runtime/loadout: {runtime} / {loadout}",
        f"Session: {label}" + (f" — {title}" if title else ""),
    ]
    if hermes_profile:
        lines.append(f"Hermes profile: {hermes_profile}")
    lines += [
        f"Outcome: {outcome}",
        f"Visible proof: {_visible_proof_summary(ledger_row)}",
        f"Changed: {changes}",
        f"Commit: {_commit_push_summary(sections)}",
        f"Verification: {verification}",
    ]
    if git_status:
        lines.append(f"Git: {_bounded(git_status, 200)}")
    if cleanup_result is not None:
        cleaned = cleanup_result.get("cleaned") or cleanup_result.get("status") == "stopped"
        lines.append(f"Terminal: {'closed' if cleaned else 'left open'}")
    else:
        lines.append(f"Terminal: {_terminal_summary(ledger_row)}")
    lines += [
        f"Report: {report_path}",
        f"Manifest: {manifest_path}",
        f"Next: {next_step}",
    ]
    return "\n".join(lines)


# ─── Phase 3: Question message builder ───────────────────────────────────────

def build_manager_question_message(
    ledger_row: dict,
    question: str,
    *,
    classification: str = "question_for_operator",
    reason: str = "",
) -> str:
    """Question routing message for the operator (Phase 3)."""
    label = ledger_row.get("session_label") or "unknown"
    runtime = ledger_row.get("runtime") or "?"
    loadout = ledger_row.get("loadout") or "?"
    manifest = ledger_row.get("manifest_path") or ""

    lines = [
        f"[run-manager] Operator question from: {label}",
        f"Runtime: {runtime}/{loadout}",
        f"Classification: {classification}",
    ]
    if reason:
        lines.append(f"Reason: {reason}")
    lines += [
        "",
        f"Question: {question or '(could not extract — inspect the terminal)'}",
    ]
    recommended_answer, recommendation_reason = try_auto_answer(question)
    if recommended_answer:
        lines += [
            f"Recommendation: {recommended_answer}",
            f"Why: {recommendation_reason}",
        ]
    elif question:
        lines += [
            "Recommendation: operator decision required",
            f"Why: {recommendation_reason}",
        ]
    lines += [
        "",
        f"Manifest: {manifest}",
        (
            "To answer: python scripts/coding_terminal_runner.py manage answer"
            f" --manifest {manifest} --answer <your-answer-text> --json"
        ),
    ]
    return "\n".join(lines)


# ─── Continuation recommendation + message builder ────────────────────────────

def recommend_continuation(options: list[str], task_goal: str = "") -> dict:
    """Classify the most-likely next step into a safety band.

    One source of truth for safety: reuses _UNSAFE_KEYWORDS and the safe-pattern
    tables. Bands:
      - safe-operational  → recommend the step, confidence high
      - operator-preferred → recommend a default, confidence medium, route to the operator
      - decision-required  → no substantive default, confidence low, route to the operator
    """
    options = options or []
    blob = " ".join(options + [task_goal or ""]).lower()
    for keyword in _UNSAFE_KEYWORDS:
        if keyword in blob:
            return {
                "band": "decision-required",
                "recommendation": "operator decision required",
                "why": f"unsafe keyword detected: {keyword!r}",
                "confidence": "low",
            }
    if not options:
        return {
            "band": "operator-preferred",
            "recommendation": "operator decision required",
            "why": "no continuation options extracted — routing to operator",
            "confidence": "low",
        }
    first = options[0]
    if _SAFE_CONTINUATION_RE.search(first):
        return {
            "band": "safe-operational",
            "recommendation": first,
            "why": "matched safe-operational pattern",
            "confidence": "high",
        }
    auto_answer, _ = try_auto_answer(first, task_goal)
    if auto_answer:
        return {
            "band": "safe-operational",
            "recommendation": first,
            "why": "matched safe-pattern allowlist",
            "confidence": "high",
        }
    return {
        "band": "operator-preferred",
        "recommendation": first,
        "why": "no safe pattern matched — routing to operator",
        "confidence": "medium",
    }


def build_manager_continuation_decision_message(
    ledger_row: dict,
    sections: dict,
    classification: dict,
    *,
    git_status: str = "",
) -> str:
    """Combined continuation-decision message: what happened + how to continue.

    One message, one resume command (the existing `manage answer` path). Bounded
    and Discord-safe: option block capped at 6, fields trimmed.
    """
    label = ledger_row.get("session_label") or "unknown"
    runtime = ledger_row.get("runtime") or "?"
    loadout = ledger_row.get("loadout") or "?"
    manifest = ledger_row.get("manifest_path") or ""
    report_path = ledger_row.get("report_path") or ""
    confidence = classification.get("confidence") or "medium"
    options = list(classification.get("continuation_options") or [])[:6]
    checkpoint = classification.get("continuation_checkpoint") or ""
    context = ledger_row.get("conversation_context") or {}
    title = context.get("session_title") or ledger_row.get("discord_thread_name") or ""
    goal = context.get("conversation_goal") or context.get("user_request") or ""
    changes = _section_line(sections, "Changes") or "not reported"
    verification = _section_line(sections, "Verification") or "not reported"

    recommendation = recommend_continuation(options, goal)

    lines = [f"[run-manager] Continuation decision: {label}"]
    if title:
        lines.append(f"Session: {title}")
    lines += [
        f"Runtime: {runtime}/{loadout}",
        f"State: waiting_for_continuation ({confidence})",
        f"Did: {changes}",
        f"Verified: {verification}",
    ]
    if checkpoint:
        lines.append(f"Stopped at: {checkpoint}")
    if goal:
        lines.append(f"Session goal: this advances {goal}")
    quoted_lines: list[str] = []
    if checkpoint:
        quoted_lines.append(f"Continuation: {checkpoint}")
    if options:
        quoted_lines.append("")
        quoted_lines.append("Continuation Options")
        for index, option in enumerate(options, 1):
            quoted_lines.append(f"{index}. {option}")
    if not quoted_lines:
        quoted_lines.append("(No bounded continuation text was extracted; inspect the terminal before answering.)")

    lines += [
        "",
        f"This is what {label} coding terminal said:",
        "```text",
        "\n".join(quoted_lines),
        "```",
        "",
        f"Recommendation: {recommendation['recommendation']}",
        f"Why: {recommendation['why']}",
        f"Confidence: {recommendation['confidence']}",
        "",
        "How do we continue the chat?",
    ]
    if git_status:
        lines.append(f"Git: {git_status.strip()[:200]}")
    lines += [
        "",
        f"Manifest: {manifest}",
        f"Report: {report_path}",
        "Reply here with your choice and Hermes can resume the same Claude session.",
        (
            "To continue: python scripts/coding_terminal_runner.py manage answer"
            f" --manifest {manifest} --answer \"<your choice>\" --json"
        ),
    ]
    return "\n".join(lines)


# ─── Manager response packet ──────────────────────────────────────────────────

def build_manager_response_packet(
    ledger_row: dict,
    data: dict,
    classification: dict,
    message: str,
    *,
    kind: str = "manager_continuation",
    sections: dict | None = None,
) -> dict:
    """First-class closeout response packet for Hermes to continue the chat.

    Prefers ledger-row fields, falls back to manifest data. Section text
    (Changes/Verification/Blockers/Next Steps) is pulled from the parsed
    closeout report when available so a consumer never has to re-open the file.
    """
    sections = sections or {}

    def _sec(heading: str) -> str:
        return (sections.get(heading) or "").strip()

    return {
        "schema_version": 1,
        "kind": kind,
        "run_id": ledger_row.get("run_id") or "",
        "manifest_path": str(ledger_row.get("manifest_path") or data.get("manifest_path") or ""),
        "session_label": ledger_row.get("session_label") or data.get("session_label") or "",
        "runtime": ledger_row.get("runtime") or data.get("runtime") or "",
        "loadout": ledger_row.get("loadout") or data.get("loadout") or "",
        "hermes_profile": ledger_row.get("hermes_profile") or data.get("hermes_profile") or "",
        "report_path": ledger_row.get("report_path") or data.get("latest_closeout_report") or "",
        "classification": classification.get("classification") or "",
        "manager_status": ledger_row.get("manager_status") or "",
        "message": message,
        "changed_files": _sec("Changes"),
        "verification": _sec("Verification"),
        "blockers": _sec("Blockers"),
        "next_action": _sec("Next Steps"),
        "origin_context": data.get("origin_context") or ledger_row.get("origin_context") or {},
        "conversation_context": data.get("conversation_context") or ledger_row.get("conversation_context") or {},
    }


# ─── Ledger field helpers ─────────────────────────────────────────────────────

def apply_manager_fields(
    ledger_row: dict,
    *,
    manager_status: str,
    classification: dict | None = None,
    message_id: str = "",
    transport: str = "",
    error: str = "",
    cleanup_result: dict | None = None,
    pending_question: str = "",
) -> dict:
    """Merge manager state into a ledger row — idempotent, never deletes prior fields."""
    row = dict(ledger_row)
    row["manager_status"] = manager_status
    row["manager_last_attempt_at"] = _now_iso()
    if classification:
        row["manager_classification"] = classification.get("classification", "unknown")
        row["manager_action"] = classification.get("action", "needs_manual_review")
        row["manager_reason"] = classification.get("reason", "")
    if message_id:
        row["manager_message_id"] = message_id
    if transport:
        row["manager_transport"] = transport
    if error:
        row["manager_error"] = error
    else:
        row.pop("manager_error", None)
    if cleanup_result is not None:
        row["manager_cleanup_result"] = cleanup_result
    if pending_question:
        row["manager_pending_question"] = pending_question
    return row
