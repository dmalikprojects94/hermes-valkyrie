"""Canonical run-lifecycle derivation for managed coding terminals.

Pure, stdlib-only, no I/O — mirrors `run_manager.py` style. This is the single
place run state is derived from (manifest, ledger row, latest turn-matched
event) per the watcher-pipeline lifecycle design. Callers pass
pre-read dicts and a pre-matched event; file reading and turn matching stay in
the runner. Derivation never raises on legacy or partial data: unknown
combinations map to RunState.UNKNOWN with a reason and never block launches.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from scripts.report_extractor import HEADINGS as REPORT_HEADINGS, _parse_sections


class RunState(str, Enum):
    LAUNCHING = "launching"
    RUNNING = "running"
    AWAITING_CLOSEOUT = "awaiting_closeout"
    NEEDS_OPERATOR = "needs_operator"
    AWAITING_CONTINUATION = "awaiting_continuation"
    COMPLETED_CLEAN = "completed_clean"
    COMPLETED_BLOCKED = "completed_blocked"
    FAILED = "failed"
    STALE = "stale"
    CLOSED = "closed"
    UNKNOWN = "unknown"


# Only live/open sessions in these states block fresh launches. Anything on a
# closed session is historical residue by definition.
LAUNCH_BLOCKING_STATES: frozenset[RunState] = frozenset({
    RunState.LAUNCHING,
    RunState.RUNNING,
    RunState.NEEDS_OPERATOR,
    RunState.AWAITING_CONTINUATION,
    RunState.FAILED,
})

LEGAL_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.LAUNCHING: frozenset({RunState.RUNNING, RunState.FAILED}),
    RunState.RUNNING: frozenset({
        RunState.AWAITING_CLOSEOUT,
        RunState.AWAITING_CONTINUATION,
        RunState.NEEDS_OPERATOR,
        RunState.FAILED,
        RunState.STALE,
    }),
    RunState.AWAITING_CLOSEOUT: frozenset({
        RunState.COMPLETED_CLEAN,
        RunState.COMPLETED_BLOCKED,
        RunState.NEEDS_OPERATOR,
        RunState.FAILED,
    }),
    RunState.NEEDS_OPERATOR: frozenset({
        RunState.RUNNING,
        RunState.AWAITING_CLOSEOUT,
        RunState.CLOSED,
    }),
    RunState.AWAITING_CONTINUATION: frozenset({RunState.RUNNING, RunState.CLOSED}),
    RunState.COMPLETED_CLEAN: frozenset({RunState.CLOSED}),
    RunState.COMPLETED_BLOCKED: frozenset({RunState.CLOSED}),
    RunState.FAILED: frozenset({RunState.CLOSED, RunState.RUNNING}),
    RunState.STALE: frozenset({RunState.CLOSED, RunState.RUNNING}),
    RunState.CLOSED: frozenset(),
    # Legacy manifests can be in any real state; leaving UNKNOWN is always legal.
    RunState.UNKNOWN: frozenset(set(RunState) - {RunState.UNKNOWN}),
}

_OPERATOR_CLASSIFICATIONS = {"question_for_operator", "auth_blocked", "permission_blocked"}
_TERMINAL_EVENT_STATUSES = {"waiting_for_input", "finished", "blocked", "failed", "stale"}

MANIFEST_SCHEMA_VERSION = 2
TRANSITION_LOG_CAP = 50

_RAW_STATUS_TO_STATE: dict[str | None, RunState] = {
    "starting": RunState.LAUNCHING,
    "ready": RunState.LAUNCHING,
    "working": RunState.RUNNING,
    "waiting_for_input": RunState.AWAITING_CLOSEOUT,
    "waiting_for_continuation": RunState.AWAITING_CONTINUATION,
    "blocked": RunState.FAILED,
    "needs_attention": RunState.FAILED,
    "failed": RunState.FAILED,
    "stale": RunState.STALE,
    "finished": RunState.CLOSED,
}

# A new prompt turn (`working`) and an operator/manager stop (`finished`) may
# land from any state; a rollback to an unknown prior status is a restore, not
# a state-machine step. Everything else must follow LEGAL_TRANSITIONS.
_ALWAYS_LEGAL_TARGETS = {"working", "finished"}


@dataclass(frozen=True)
class ResolvedState:
    state: RunState
    reason: str
    launch_blocking: bool
    superseded_question: bool = False
    report_shaped_final_message: bool | None = None

    def as_dict(self) -> dict:
        return {
            "state": self.state.value,
            "reason": self.reason,
            "launch_blocking": self.launch_blocking,
            "superseded_question": self.superseded_question,
            "report_shaped_final_message": self.report_shaped_final_message,
        }


def is_structured_report_text(text: str | None) -> bool:
    """True when text carries the full five-heading report contract."""
    if not text or not isinstance(text, str):
        return False
    sections = _parse_sections(text)
    return all(heading in sections for heading in REPORT_HEADINGS)


def is_legal_transition(current: RunState, new: RunState) -> bool:
    if current == new:
        return True
    return new in LEGAL_TRANSITIONS.get(current, frozenset())


def is_legal_status_transition(old_status: object, new_status: object) -> bool:
    """Legality of a raw manifest-status write, via the RunState machine."""
    if old_status == new_status or old_status is None or new_status is None:
        return True
    if new_status in _ALWAYS_LEGAL_TARGETS:
        return True
    return is_legal_transition(
        _RAW_STATUS_TO_STATE.get(old_status, RunState.UNKNOWN),
        _RAW_STATUS_TO_STATE.get(new_status, RunState.UNKNOWN),
    )


def transition_manifest_status(
    data: dict,
    new_status: object,
    *,
    reason: str,
    actor: str,
    timestamp: str | None = None,
) -> dict:
    """The single lifecycle status writer.

    Sets `data["status"]` and appends an audit entry to `data["transitions"]`
    (`{ts, from, to, reason, actor, legal}`, capped at the newest
    TRANSITION_LOG_CAP entries). Mutates `data` in place; the caller persists
    the manifest. Manifests without a transitions list gain one lazily, so
    schema_version-1 manifests stay readable; the first transition stamps
    `schema_version` 2. Illegal transitions are flagged, never rejected —
    rejecting a write would strand live sessions on legacy data.
    """
    old_status = data.get("status")
    entry = {
        "ts": timestamp or datetime.now(timezone.utc).isoformat(),
        "from": old_status,
        "to": new_status,
        "reason": reason,
        "actor": actor,
        "legal": is_legal_status_transition(old_status, new_status),
    }
    transitions = data.get("transitions")
    if not isinstance(transitions, list):
        transitions = []
    transitions.append(entry)
    data["transitions"] = transitions[-TRANSITION_LOG_CAP:]
    data["status"] = new_status
    data["schema_version"] = MANIFEST_SCHEMA_VERSION
    return entry


def resolve_run_state(
    manifest: dict | None,
    ledger_row: dict | None = None,
    latest_event: dict | None = None,
    *,
    final_message: str | None = None,
    tmux_exists: bool | None = None,
) -> ResolvedState:
    """Derive the canonical RunState from persisted lifecycle facts.

    `latest_event` must already be matched to the current turn by the caller.
    `final_message` is the turn-final assistant message when available; it is
    only consulted to disambiguate `waiting_for_input`. `tmux_exists=None`
    means unknown; only an explicit False marks the session closed.
    """
    if not isinstance(manifest, dict) or not manifest:
        return ResolvedState(RunState.UNKNOWN, "empty or invalid manifest", False)

    row = ledger_row if isinstance(ledger_row, dict) else {}
    event = latest_event if isinstance(latest_event, dict) else {}
    status = manifest.get("status")
    closeout_status = manifest.get("closeout_status") or row.get("closeout_status") or "not_run"
    structured_closeout = closeout_status == "structured"
    question_pending = bool(
        row.get("manager_status") == "asked_operator"
        or row.get("manager_classification") in _OPERATOR_CLASSIFICATIONS
    )
    # A continuation decision is produced FROM a closeout, so a structured
    # closeout never supersedes it; only a resume or explicit close ends it.
    continuation_decision_pending = bool(
        row.get("manager_status") == "awaiting_continuation_decision"
        or row.get("manager_continuation_pending")
    )
    superseded = question_pending and structured_closeout
    report_shaped = is_structured_report_text(final_message) if final_message is not None else None
    live = tmux_exists is not False

    def resolved(state: RunState, reason: str) -> ResolvedState:
        return ResolvedState(
            state=state,
            reason=reason,
            launch_blocking=state in LAUNCH_BLOCKING_STATES and live,
            superseded_question=superseded,
            report_shaped_final_message=report_shaped,
        )

    if structured_closeout:
        # Supersession: a stale asked_operator question can never derive
        # NEEDS_OPERATOR once a structured closeout exists.
        has_blockers = manifest.get("report_has_blockers")
        if has_blockers is None:
            has_blockers = row.get("has_blockers")
        if tmux_exists is False and status == "finished":
            return resolved(RunState.CLOSED, "structured closeout and tmux session is closed")
        if continuation_decision_pending:
            return resolved(
                RunState.AWAITING_CONTINUATION,
                "manager posted continuation options; operator decision pending",
            )
        if has_blockers:
            return resolved(RunState.COMPLETED_BLOCKED, "structured closeout reports blockers")
        return resolved(RunState.COMPLETED_CLEAN, "structured closeout with no blockers")

    if continuation_decision_pending:
        return resolved(
            RunState.AWAITING_CONTINUATION,
            "manager posted continuation options; operator decision pending",
        )

    if question_pending:
        return resolved(
            RunState.NEEDS_OPERATOR,
            "manager classified an operator question with no newer structured closeout",
        )

    if status == "failed":
        return resolved(RunState.FAILED, "manifest status is failed")
    if status in ("blocked", "needs_attention"):
        return resolved(RunState.FAILED, f"manifest status is {status} with no operator question detected")

    if status == "waiting_for_continuation" or event.get("status") == "waiting_for_continuation":
        return resolved(RunState.AWAITING_CONTINUATION, "run offered continuation options")

    if status in ("starting", "ready"):
        return resolved(RunState.LAUNCHING, f"manifest status is {status}; runtime settling")

    if status == "working":
        if event.get("status") in _TERMINAL_EVENT_STATUSES:
            return resolved(
                RunState.AWAITING_CLOSEOUT,
                "turn-matched terminal event recorded but closeout has not run",
            )
        return resolved(RunState.RUNNING, "turn in flight with no terminal event")

    if status == "waiting_for_input":
        if report_shaped:
            return resolved(
                RunState.AWAITING_CLOSEOUT,
                "turn-final message is a structured report, not an operator question",
            )
        if report_shaped is False:
            return resolved(
                RunState.NEEDS_OPERATOR,
                "waiting_for_input with a non-report final message",
            )
        return resolved(
            RunState.AWAITING_CLOSEOUT,
            "terminal event recorded but closeout has not run",
        )

    if status == "stale":
        return resolved(RunState.STALE, "no signal within watcher lease")

    if status == "finished":
        if tmux_exists is False:
            return resolved(RunState.CLOSED, "manifest finished and tmux session is closed")
        return resolved(
            RunState.AWAITING_CLOSEOUT,
            f"manifest finished with closeout_status={closeout_status}",
        )

    return ResolvedState(
        RunState.UNKNOWN,
        f"unrecognized manifest status: {status!r}",
        False,
        superseded_question=superseded,
        report_shaped_final_message=report_shaped,
    )
