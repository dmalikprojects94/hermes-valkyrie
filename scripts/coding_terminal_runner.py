#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import select
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.artifact_router import default_routes, redact_secrets, resolve_obsidian_vault_path, route_report_artifacts
from scripts.loadoutlib import load_loadouts, validate_loadouts
from scripts.prompt_manager import OUTPUT_DEFINITIONS, prepare_prompt
from scripts.report_extractor import HEADINGS as REPORT_HEADINGS, _parse_sections, extract_report, extract_report_from_text
from scripts.terminal_lifecycle import (
    ResolvedState,
    RunState,
    resolve_run_state,
    transition_manifest_status,
)
from scripts.run_manager import (
    apply_manager_fields,
    build_manager_continuation_decision_message,
    build_manager_continuation_message,
    build_manager_question_message,
    build_manager_response_packet,
    classify_run,
    detect_report_continuation,
    recommend_continuation,
    try_auto_answer,
)
from scripts.runtime_adapters import (
    MANAGED_BYPASS_POSTURE,
    MANUAL_DIAGNOSTIC_POSTURE,
    get_adapter,
    permission_posture_metadata,
    resolve_claude_model,
    resolve_real_home,
)
from scripts.tmux_terminal import (
    TerminalManifest,
    capture_pane,
    create_tmux_session,
    desktop_window_ids_for_title,
    ensure_artifact_dirs,
    kill_session,
    list_clients,
    open_desktop_client,
    read_manifest,
    save_manifest,
    send_literal_prompt,
    session_exists,
    run_tmux,
    update_manifest_status,
    write_manifest,
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_mark(value: bool) -> str:
    return "ok" if value else "missing"


def _visible_terminal_proof(*, requested: bool, clients: str, dry_run: bool, desktop_window_ids: list[str] | None = None) -> dict[str, Any]:
    if not requested:
        return {"status": "not_requested", "attached_clients": 0, "desktop_windows": 0, "details": "terminal visibility not requested"}
    if dry_run:
        return {"status": "not_proven", "attached_clients": 0, "desktop_windows": 0, "details": "dry run cannot prove desktop terminal attachment"}
    attached_clients = len([line for line in (clients or "").splitlines() if line.strip()])
    window_ids = [window_id for window_id in (desktop_window_ids or []) if window_id]
    if window_ids:
        return {"status": "desktop_window", "attached_clients": attached_clients, "desktop_windows": len(window_ids), "desktop_window_ids": window_ids, "details": clients}
    if attached_clients:
        return {"status": "tmux_attached_without_desktop_proof", "attached_clients": attached_clients, "desktop_windows": 0, "details": clients}
    return {"status": "not_proven", "attached_clients": 0, "desktop_windows": 0, "details": "visible launch requested but no tmux client attached"}


def _format_runtime_lanes(by_runtime: dict | None) -> list[str]:
    if not by_runtime:
        return []
    lines = ["Runtime raw paths:"]
    for runtime, preflight in by_runtime.items():
        lines.append(f"- {runtime}: {preflight.get('raw_path') or preflight.get('raw_root')} (source={preflight.get('raw_path_source') or preflight.get('raw_root_source')})")
    return lines


def _format_doctor(payload: dict) -> str:
    counts = payload.get("operator_summary") or {}
    route = payload.get("route_preflight") or {}
    lines = [
        "Coding Terminal Doctor",
        f"Status: {payload.get('status')}",
        f"Summary: {payload.get('summary')}",
        "",
        "Session counts: "
        f"active={counts.get('active', 0)} stopped={counts.get('stopped', 0)} "
        f"needs_attention={counts.get('needs_attention', 0)} open_total={counts.get('open_total', 0)} "
        f"orphans={counts.get('orphan_tmux', 0)}",
        f"Report routing: raw={route.get('raw_path_source') or route.get('raw_root_source')} project={route.get('project_path_source') or route.get('project_root_source')}",
        f"Default path: {route.get('default_path')}",
        f"Raw path: {route.get('raw_path') or route.get('raw_root')}",
        f"Project path: {route.get('project_path') or route.get('project_root') or route.get('sorted_path')}",
    ]
    lines.extend(_format_runtime_lanes(payload.get("route_preflight_by_runtime")))
    warnings = route.get("warnings") or []
    if warnings:
        lines.append("Route warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    issues = payload.get("issues") or []
    lines.append("")
    if issues:
        lines.append("Issues:")
        lines.extend(f"- {issue.get('kind')}: {issue.get('count', issue.get('warnings', ''))}" for issue in issues)
    else:
        lines.append("Issues: none")
    actions = payload.get("recommended_actions") or []
    if actions:
        lines.append("Recommended actions:")
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("Recommended actions: none")
    return "\n".join(lines)


def _format_origin_context(origin: dict | None) -> str:
    origin = origin or {}
    if origin.get("platform") != "discord":
        return ""
    parts = []
    if origin.get("thread_name") or origin.get("thread_id"):
        label = origin.get("thread_name") or origin.get("thread_id")
        if origin.get("thread_name") and origin.get("thread_id"):
            label = f"{origin['thread_name']} ({origin['thread_id']})"
        parts.append(f"thread={label}")
    if origin.get("channel_id"):
        parts.append(f"channel={origin['channel_id']}")
    if origin.get("guild_id"):
        parts.append(f"guild={origin['guild_id']}")
    return " discord:" + " ".join(parts) if parts else " discord"


def _format_operator_status(payload: dict) -> str:
    counts = payload.get("summary") or {}
    route = payload.get("route_preflight") or {}
    trust = payload.get("operator_trust") or {}
    residue = trust.get("historical_residue") or {}
    hygiene = payload.get("artifact_hygiene") or {}
    lines = [
        "Coding Terminal Operator Status",
        f"Repo: {payload.get('repo')}",
        f"Artifact root: {payload.get('artifact_root')}",
        "",
        "Open state: "
        f"active={counts.get('active', 0)} stopped={counts.get('stopped', 0)} "
        f"needs_attention={counts.get('needs_attention', 0)} open_managed={counts.get('open_managed', 0)} "
        f"orphans={counts.get('orphan_tmux', 0)} open_total={counts.get('open_total', 0)}",
        f"Runtime HOME: {(payload.get('runtime_home') or {}).get('HOME')}",
        f"Report routing: raw={route.get('raw_path_source') or route.get('raw_root_source')} project={route.get('project_path_source') or route.get('project_root_source')}",
        f"Default path: {route.get('default_path')}",
        f"Raw path: {route.get('raw_path') or route.get('raw_root')}",
        f"Project path: {route.get('project_path') or route.get('project_root') or route.get('sorted_path')}",
        f"Launch blocking: {trust.get('launch_blocking', 'unknown')}",
    ]
    if hygiene.get("prune_candidate_count"):
        lines.append(
            "Artifact hygiene: "
            f"session_dirs={hygiene.get('session_dir_count', 0)} closed={hygiene.get('closed_session_count', 0)} "
            f"prune_candidates={hygiene.get('prune_candidate_count', 0)} "
            f"reclaimable_bytes={hygiene.get('prune_candidate_bytes', 0)} "
            f"cutoff_days={hygiene.get('prune_cutoff_days', 14)}"
        )
    if residue.get("closed_without_closeout"):
        lines.append(
            "Historical residue: "
            f"closed_without_closeout={residue.get('closed_without_closeout', 0)} "
            "(not live launch blocking; inspect list/reports for audit detail)"
        )
    lines.extend(_format_runtime_lanes(payload.get("route_preflight_by_runtime")))
    if counts.get("continuation_failed") or counts.get("continuation_pending") or counts.get("continuation_needs_origin_review"):
        lines.append(
            "Continuation review: "
            f"pending={counts.get('continuation_pending', 0)} failed={counts.get('continuation_failed', 0)} "
            f"needs_origin_review={counts.get('continuation_needs_origin_review', 0)} posted={counts.get('continuation_posted', 0)}"
        )
    if counts.get("manager_asked") or counts.get("manager_failed") or counts.get("manager_needs_review"):
        lines.append(
            "Run manager: "
            f"asked_operator={counts.get('manager_asked', 0)} "
            f"needs_review={counts.get('manager_needs_review', 0)} "
            f"failed={counts.get('manager_failed', 0)} "
            f"continued={counts.get('manager_continued', 0)}"
        )
    if counts.get("manager_response_posted") or counts.get("manager_response_dry_run") or counts.get("manager_response_missing"):
        lines.append(
            "Manager responses: "
            f"posted={counts.get('manager_response_posted', 0)} "
            f"dry_run={counts.get('manager_response_dry_run', 0)} "
            f"missing={counts.get('manager_response_missing', 0)}"
        )
    if counts.get("manager_historical_total"):
        lines.append(
            "Run manager history: "
            f"asked_operator={counts.get('manager_historical_asked', 0)} "
            f"needs_review={counts.get('manager_historical_needs_review', 0)} "
            f"failed={counts.get('manager_historical_failed', 0)} "
            f"continued={counts.get('manager_historical_continued', 0)}"
        )
    warnings = route.get("warnings") or []
    if warnings:
        lines.append("Route warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    open_sessions = payload.get("open_sessions") or []
    lines.append("")
    if open_sessions:
        lines.append("Open managed sessions:")
        for session in open_sessions:
            lines.append(
                f"- {session.get('session_label')} [{session.get('runtime')}/{session.get('loadout')}] "
                f"state={session.get('lifecycle_state')} status={session.get('status')} tmux={session.get('tmux_session')}"
                f"{_format_origin_context(session.get('origin_context'))}"
            )
            if session.get("latest_report"):
                lines.append(f"  report: {session.get('latest_report')}")
    else:
        lines.append("Open managed sessions: none")
    orphans = payload.get("orphan_tmux_records") or []
    if orphans:
        lines.append("Orphan tmux sessions:")
        for orphan in orphans:
            lines.append(f"- {orphan.get('name')} attach: {orphan.get('attach_command')}")
    else:
        lines.append("Orphan tmux sessions: none")
    external = payload.get("external_managed_tmux_sessions") or []
    if external:
        lines.append("Tmux sessions managed by another repo (not blockers here):")
        for record in external:
            lines.append(f"- {record.get('name')} manifest: {record.get('manifest_path')}")
    if not open_sessions and not orphans:
        lines.append("Closed historical sessions are omitted from this human view; use --json or the list/reports commands for audit details.")
    return "\n".join(lines)


def _format_reports(payload: dict) -> str:
    reports = payload.get("reports") or []
    lines = [
        "Coding Terminal Reports",
        f"Repo: {payload.get('repo')}",
        f"Artifact root: {payload.get('artifact_root')}",
        f"Reports shown: {len(reports)} of {payload.get('count')}",
    ]
    if not reports:
        lines.append("Reports: none")
        return "\n".join(lines)
    for report in reports:
        missing = report.get("missing") or []
        lines.extend([
            "",
            f"- {report.get('session_label')} [{report.get('runtime')}/{report.get('loadout')}] origin={report.get('origin')} closeout={report.get('closeout_status')} missing={','.join(missing) if missing else 'none'}",
            f"  local: {_bool_mark(report.get('local_report_exists'))} {report.get('local_report') or '<none>'}",
            f"  raw: {_bool_mark(report.get('raw_report_exists'))} {report.get('raw_report') or '<none>'}",
            f"  raw summary: {_bool_mark(report.get('raw_summary_exists'))} {report.get('raw_summary') or '<none>'}",
            f"  project: {_bool_mark(report.get('project_report_exists'))} {report.get('project_report') or '<none>'}",
            f"  project summary: {_bool_mark(report.get('project_summary_exists'))} {report.get('project_summary') or '<none>'}",
        ])
    return "\n".join(lines)


def _format_prune(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    mode = "applied" if payload.get("applied") else "dry-run"
    lines = [
        "Coding Terminal Prune",
        f"Repo: {payload.get('repo')}",
        f"Mode: {mode} (older-than-days={payload.get('older_than_days')})",
        f"Candidates: {payload.get('candidate_count')} removed={payload.get('removed_count')} freed_bytes={payload.get('freed_bytes')}",
    ]
    if not candidates:
        lines.append("No closed sessions older than the cutoff. Nothing to prune.")
        return "\n".join(lines)
    for candidate in candidates:
        mark = "removed" if candidate.get("removed") else "candidate"
        lines.append(f"- [{mark}] {candidate.get('session_label')} {candidate.get('size_bytes')}B {candidate.get('session_dir')}")
    if not payload.get("applied"):
        lines.append("Dry run only. Re-run with --yes to remove these local derived manifests.")
    return "\n".join(lines)


def _format_selftest(payload: dict) -> str:
    lines = [
        "Coding Terminal Release Check",
        f"Repo: {payload.get('repo')}",
        f"Status: {payload.get('status')} (passed={payload.get('passed_count')} failed={payload.get('failed_count')})",
        "",
        "Checks:",
    ]
    for check in payload.get("checks") or []:
        mark = "pass" if check.get("passed") else "FAIL"
        lines.append(f"- [{mark}] {check.get('name')}: {check.get('detail')}")
    return "\n".join(lines)


def _format_payload(payload: dict) -> str:
    if "checks" in payload and "passed_count" in payload:
        return _format_selftest(payload)
    if "freed_bytes" in payload and "candidates" in payload:
        return _format_prune(payload)
    if "operator_summary" in payload and "missing_report_copies" in payload:
        return _format_doctor(payload)
    if "latest_sessions" in payload and "open_sessions" in payload:
        return _format_operator_status(payload)
    if "reports" in payload and "checked_count" not in payload:
        return _format_reports(payload)
    return "\n".join(f"{key}: {value}" for key, value in payload.items())


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(_format_payload(payload))


KNOWN_RUNTIMES = ("claude", "codex")
MAX_ACTIVE_SESSIONS_PER_RUNTIME = 10
ACTIVE_SESSION_STATUSES = {"starting", "ready", "working"}
SAFE_STOPPED_SESSION_STATUSES = {"waiting_for_input", "finished", "stale"}
ATTENTION_SESSION_STATUSES = {"blocked", "failed", "needs_attention"}


def _route_preflight(routes: dict[str, str]) -> dict[str, object]:
    default_path = Path(routes.get("default_path") or "") if routes.get("default_path") else None
    raw_path = Path(routes.get("raw_path") or routes.get("raw_root") or "") if (routes.get("raw_path") or routes.get("raw_root")) else None
    project_path = Path(routes.get("project_path") or routes.get("project_root") or routes.get("sorted_path") or "") if (routes.get("project_path") or routes.get("project_root") or routes.get("sorted_path")) else None
    vault_path = resolve_obsidian_vault_path()
    resolved_default = default_path or vault_path
    warnings: list[str] = []
    if routes.get("raw_root_source") != "save_destination":
        warnings.append("raw reports are not routed to a save destination; set SAVE_DESTINATION_PATH to an existing writable folder")
    if routes.get("project_root_source") != "save_destination":
        warnings.append("project reports are not routed to a save destination; set SAVE_DESTINATION_PATH to an existing writable folder")
    return {
        "default_path": str(resolved_default) if resolved_default else "",
        "default_path_exists": bool(resolved_default and resolved_default.exists()),
        "default_path_source": routes.get("default_path_source", routes.get("raw_root_source", "")),
        "raw_path": str(raw_path) if raw_path else "",
        "raw_path_exists": bool(raw_path and raw_path.exists()),
        "raw_path_source": routes.get("raw_root_source", ""),
        "project_path": str(project_path) if project_path else "",
        "project_path_exists": bool(project_path and project_path.exists()),
        "project_path_source": routes.get("project_root_source", ""),
        "sorted_path": str(project_path) if project_path else "",
        "sorted_path_exists": bool(project_path and project_path.exists()),
        "sorted_path_source": routes.get("project_root_source", ""),
        "obsidian_vault_path": str(vault_path) if vault_path else "",
        "obsidian_vault_exists": bool(vault_path and vault_path.exists()),
        "raw_root": str(raw_path) if raw_path else "",
        "raw_root_exists": bool(raw_path and raw_path.exists()),
        "raw_root_source": routes.get("raw_root_source", ""),
        "project_root": str(project_path) if project_path else "",
        "project_root_exists": bool(project_path and project_path.exists()),
        "project_root_source": routes.get("project_root_source", ""),
        "warnings": warnings,
    }


def _load_launch_env(repo: Path) -> dict[str, str]:
    manifest = repo / "hermes-loadout.json"
    default_home = resolve_real_home()
    if not manifest.exists():
        return {"HOME": default_home}
    try:
        data = json.loads(manifest.read_text())
        env = data.get("launch", {}).get("env", {})
        return {"HOME": env.get("HOME", default_home)}
    except Exception:
        return {"HOME": default_home}


def _runtime_event_command(*, manifest_path: Path, runtime: str, event: str, status: str) -> str:
    script = ROOT / "scripts" / "record_runtime_event.py"
    return " ".join(shlex.quote(str(part)) for part in [
        sys.executable,
        str(script),
        "--manifest",
        str(manifest_path),
        "--runtime",
        runtime,
        "--event",
        event,
        "--status",
        status,
    ])


def _codex_stop_hook_override(command: str) -> str:
    return "hooks.Stop=[{hooks=[{type=\"command\",command=" + json.dumps(command) + ",timeout=10}]}]"


def _write_runtime_settings(data: dict) -> None:
    settings_path = Path(data["artifacts"]["runtime_settings"])
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    runtime = data["runtime"]
    if runtime == "claude":
        command = _runtime_event_command(
            manifest_path=Path(data["artifacts"]["manifest"]),
            runtime="claude",
            event="Stop",
            status="waiting_for_input",
        )
        data["runtime_event_hook"] = {
            "runtime": "claude",
            "event": "Stop",
            "status": "waiting_for_input",
            "transport": "claude_settings",
            "configured": True,
            "trust_bypass_required": False,
            "command": command,
        }
        settings = {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {"type": "command", "command": command}
                        ]
                    }
                ]
            }
        }
    elif runtime == "codex":
        command = _runtime_event_command(
            manifest_path=Path(data["artifacts"]["manifest"]),
            runtime="codex",
            event="Stop",
            status="waiting_for_input",
        )
        override = _codex_stop_hook_override(command)
        data["codex_config_overrides"] = [override]
        data["runtime_event_hook"] = {
            "runtime": "codex",
            "event": "Stop",
            "status": "waiting_for_input",
            "transport": "codex_cli_override",
            "configured": True,
            "trust_bypass_required": True,
            "command": command,
            "config_override": override,
        }
        settings = {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {"type": "command", "command": command, "timeout": 10}
                        ]
                    }
                ]
            },
            "runtime_event_hook": data["runtime_event_hook"],
            "codex_cli_overrides": [override],
            "note": "Codex has no Claude-style --settings file; pass these with -c plus --dangerously-bypass-hook-trust.",
        }
    else:
        settings = {"hooks": {}}
    settings_path.write_text(json.dumps(settings, indent=2))


def _settle_startup_dialogs(tmux_session: str, *, runtime: str, bypass_permissions: bool) -> None:
    text = capture_pane(tmux_session).lower()
    if runtime == "claude" and ("trust this folder" in text or "do you trust" in text):
        run_tmux(["tmux", "send-keys", "-t", tmux_session, "Enter"], check=False)
        time.sleep(1.5)
        text = capture_pane(tmux_session).lower()
    if runtime == "codex" and "do you trust the contents of this directory" in text:
        run_tmux(["tmux", "send-keys", "-t", tmux_session, "Enter"], check=False)
        time.sleep(1.5)
        text = capture_pane(tmux_session).lower()
    if runtime == "claude" and bypass_permissions and ("no, exit" in text or "yes, i accept" in text):
        run_tmux(["tmux", "send-keys", "-t", tmux_session, "Down"], check=False)
        time.sleep(0.2)
        run_tmux(["tmux", "send-keys", "-t", tmux_session, "Enter"], check=False)
        time.sleep(1.5)


def _first_nonempty(*values: str | None) -> str:
    for value in values:
        if value:
            stripped = str(value).strip()
            if stripped:
                return stripped
    return ""


def _discord_session_env() -> dict:
    """Twin of run_loaded_agent._discord_session_env — keep behavior identical (parity test enforced)."""
    if (os.environ.get("HERMES_SESSION_PLATFORM") or "").strip() != "discord":
        return {}
    thread_id = (os.environ.get("HERMES_SESSION_THREAD_ID") or "").strip()
    chat_id = (os.environ.get("HERMES_SESSION_CHAT_ID") or "").strip()
    channel_id = (os.environ.get("HERMES_SESSION_PARENT_CHAT_ID") or "").strip()
    if not channel_id and chat_id and chat_id != thread_id:
        channel_id = chat_id
    return {
        "guild_id": (os.environ.get("HERMES_SESSION_SCOPE_ID") or "").strip(),
        "channel_id": channel_id,
        "thread_id": thread_id,
        "thread_name": (os.environ.get("HERMES_SESSION_CHAT_NAME") or "").strip(),
    }


def _looks_like_placeholder_discord_id(value: str | None) -> bool:
    text = _first_nonempty(value)
    return bool(re.fullmatch(r"(?:guild|channel|thread)-[A-Za-z0-9_-]+", text))


def _discord_origin_has_placeholder_ids(row: dict) -> bool:
    return any(
        _looks_like_placeholder_discord_id(row.get(key))
        for key in ("discord_guild_id", "discord_channel_id", "discord_thread_id")
    )


def _origin_context_from_args(args: argparse.Namespace) -> dict:
    session = _discord_session_env()
    guild_id = _first_nonempty(getattr(args, "discord_guild_id", None), session.get("guild_id"), os.environ.get("HERMES_SESSION_GUILD_ID"), os.environ.get("DISCORD_GUILD_ID"))
    channel_id = _first_nonempty(getattr(args, "discord_channel_id", None), session.get("channel_id"), os.environ.get("HERMES_SESSION_CHANNEL_ID"), os.environ.get("DISCORD_CHANNEL_ID"))
    thread_id = _first_nonempty(getattr(args, "discord_thread_id", None), session.get("thread_id"), os.environ.get("HERMES_SESSION_THREAD_ID"), os.environ.get("DISCORD_THREAD_ID"))
    thread_name = _first_nonempty(getattr(args, "discord_thread_name", None), session.get("thread_name"), os.environ.get("HERMES_SESSION_THREAD_NAME"), os.environ.get("DISCORD_THREAD_NAME"))
    if not any((guild_id, channel_id, thread_id, thread_name)):
        return {}
    context = {"platform": "discord"}
    if guild_id:
        context["guild_id"] = guild_id
    if channel_id:
        context["channel_id"] = channel_id
    if thread_id:
        context["thread_id"] = thread_id
    if thread_name:
        context["thread_name"] = thread_name
    return context


def _hermes_profile_from_args(args: argparse.Namespace) -> str:
    return _first_nonempty(
        getattr(args, "hermes_profile", None),
        os.environ.get("HERMES_PROFILE"),
        os.environ.get("HERMES_SESSION_PROFILE"),
        os.environ.get("HERMES_ACTIVE_PROFILE"),
        os.environ.get("HERMES_PROFILE_NAME"),
    )


def _origin_verification_from_args(args: argparse.Namespace, origin_context: dict) -> dict:
    explicit_ids = [
        getattr(args, "discord_guild_id", None),
        getattr(args, "discord_channel_id", None),
        getattr(args, "discord_thread_id", None),
    ]
    explicit_complete = all(_first_nonempty(value) for value in explicit_ids)
    if origin_context.get("platform") == "discord" and explicit_complete:
        return {"origin_verified": True, "origin_verification": "explicit_discord_origin", "needs_origin_review": False}
    if origin_context.get("platform") == "discord":
        return {"origin_verified": False, "origin_verification": "env_fallback_audit_only", "needs_origin_review": True}
    return {"origin_verified": False, "origin_verification": "missing_origin", "needs_origin_review": True}


CONTEXT_FIELD_MAX_CHARS = 280
CONVERSATION_CONTEXT_FIELDS = ("session_title", "user_request", "conversation_goal", "previous_work_summary", "next_question")
CONTINUATION_PROFILES = ("none", "minimal", "session", "debug")


def _bounded_context_text(value: str | None, *, max_chars: int = CONTEXT_FIELD_MAX_CHARS) -> str:
    text = _first_nonempty(value)
    if not text:
        return ""
    flattened = " ".join(text.split())
    if len(flattened) > max_chars:
        flattened = flattened[: max_chars - 1].rstrip() + "…"
    return flattened


def _conversation_context_from_args(args: argparse.Namespace, origin_context: dict) -> dict:
    env_lookup = {
        "session_title": "HERMES_SESSION_TITLE",
        "user_request": "HERMES_SESSION_REQUEST",
        "conversation_goal": "HERMES_SESSION_GOAL",
        "previous_work_summary": "HERMES_SESSION_PREVIOUS_WORK",
        "next_question": "HERMES_SESSION_NEXT_QUESTION",
    }
    has_cli = any(_first_nonempty(getattr(args, field, None)) for field in CONVERSATION_CONTEXT_FIELDS)
    packet: dict[str, str] = {}
    for field in CONVERSATION_CONTEXT_FIELDS:
        bounded = _bounded_context_text(_first_nonempty(getattr(args, field, None), os.environ.get(env_lookup[field])))
        if bounded:
            packet[field] = bounded
    if not packet:
        return {}
    thread_name = (origin_context or {}).get("thread_name")
    if "session_title" not in packet and thread_name:
        packet["session_title"] = _bounded_context_text(thread_name)
    surface = (origin_context or {}).get("platform")
    if surface:
        packet["surface"] = surface
    packet["source"] = _first_nonempty(getattr(args, "context_source", None)) or ("explicit_cli" if has_cli else "env")
    packet["captured_at"] = _now_iso()
    return packet


def _ledger_path_for_repo(repo: Path, artifact_root: Path | None = None) -> Path:
    return (artifact_root if artifact_root else repo / ".hermes" / "coding-terminals") / "run-ledger.jsonl"


def _read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_ledger(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text)


def _ledger_id(manifest_path: Path) -> str:
    return hashlib.sha256(str(manifest_path.resolve()).encode()).hexdigest()[:16]


def _upsert_ledger_row(repo: Path, manifest_path: Path, data: dict, *, artifact_root: Path | None = None) -> dict:
    ledger_path = _ledger_path_for_repo(repo, artifact_root)
    rows = _read_ledger(ledger_path)
    manifest_key = str(manifest_path.resolve())
    existing = next((row for row in rows if row.get("manifest_path") == manifest_key), {})
    origin = data.get("origin_context") or {}
    conversation_context = data.get("conversation_context") or existing.get("conversation_context") or {}
    row = {
        **existing,
        "run_id": existing.get("run_id") or _ledger_id(manifest_path),
        "current_prompt_id": data.get("current_prompt_id") or data.get("last_prompt_id") or existing.get("current_prompt_id") or "",
        "updated_at": _now_iso(),
        "session_label": data.get("session_label"),
        "manifest_path": manifest_key,
        "runtime": data.get("runtime"),
        "loadout": data.get("loadout"),
        "status": data.get("status"),
        "closeout_status": data.get("closeout_status") or "not_run",
        "has_blockers": data.get("report_has_blockers"),
        "report_path": data.get("latest_routed_report") or data.get("latest_project_report") or data.get("latest_raw_report") or data.get("latest_closeout_report") or "",
        "summary_path": data.get("latest_closeout_summary") or "",
        "origin_verified": bool(data.get("origin_verified")),
        "origin_verification": data.get("origin_verification") or "missing_origin",
        "needs_origin_review": bool(data.get("needs_origin_review", True)),
        "managed_launcher": data.get("managed_launcher", existing.get("managed_launcher", "")),
        "launch_origin": data.get("launch_origin", existing.get("launch_origin", "manual")),
        "hermes_profile": data.get("hermes_profile", existing.get("hermes_profile", "")),
        "hermes_session_id": data.get("hermes_session_id", existing.get("hermes_session_id", "")),
        "discord_guild_id": origin.get("guild_id", ""),
        "discord_channel_id": origin.get("channel_id", ""),
        "discord_thread_id": origin.get("thread_id", ""),
        "discord_thread_name": origin.get("thread_name", ""),
        "conversation_context": conversation_context,
    }
    if not row.get("postback_status"):
        row["postback_status"] = "not_ready"
    if row["closeout_status"] and row["closeout_status"] != "not_run" and row.get("report_path") and row.get("postback_status") == "not_ready":
        row["postback_status"] = "pending" if row["origin_verified"] else "needs_origin_review"
    if not row.get("continuation_status"):
        row["continuation_status"] = "not_ready"
    if row.get("postback_status") == "posted" and row.get("report_path") and row.get("continuation_status") == "not_ready":
        row["continuation_status"] = "pending" if row["origin_verified"] else "needs_origin_review"
    replaced = False
    for idx, candidate in enumerate(rows):
        if candidate.get("manifest_path") == manifest_key:
            rows[idx] = row
            replaced = True
            break
    if not replaced:
        row.setdefault("created_at", _now_iso())
        rows.append(row)
    _write_ledger(ledger_path, rows)
    return row


def cmd_start(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve()
    adapter = get_adapter(args.runtime)
    launch_env = _load_launch_env(repo)
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    manifest = TerminalManifest.create(
        runtime=args.runtime,
        repo_path=repo,
        loadout=args.loadout,
        session_label=args.label,
        launch_env=launch_env,
        artifact_root=artifact_root,
        dry_run=args.dry_run,
    )
    data = manifest.to_dict()
    project_slug = args.project_slug or repo.name
    data["project_slug"] = project_slug
    origin_context = _origin_context_from_args(args)
    if origin_context:
        data["origin_context"] = origin_context
    data.update(_origin_verification_from_args(args, origin_context))
    managed_launcher = _first_nonempty(getattr(args, "managed_launcher", None))
    data["managed_launcher"] = managed_launcher
    data["managed_launch_policy_version"] = _first_nonempty(getattr(args, "managed_launch_policy_version", None))
    data["launch_origin"] = "managed" if managed_launcher else "manual"
    permission_posture = MANAGED_BYPASS_POSTURE if managed_launcher else MANUAL_DIAGNOSTIC_POSTURE
    if permission_posture == MANAGED_BYPASS_POSTURE and not args.bypass_permissions:
        raise SystemExit(
            "Refusing managed launch without bypass permissions: managed Claude/Codex sessions must launch with bypass-required posture."
        )
    data.update(permission_posture_metadata(args.runtime, bypass_permissions=args.bypass_permissions, permission_posture=permission_posture))
    hermes_session_id = _first_nonempty(getattr(args, "hermes_session_id", None), os.environ.get("HERMES_SESSION_ID"))
    if hermes_session_id:
        data["hermes_session_id"] = hermes_session_id
    hermes_profile = _hermes_profile_from_args(args)
    if hermes_profile:
        data["hermes_profile"] = hermes_profile
    data["watcher_required"] = bool(getattr(args, "watcher_required", False))
    data["origin_required"] = bool(getattr(args, "origin_required", False))
    data["terminal_visible"] = bool(args.visible)
    data["terminal_visibility_reason"] = _first_nonempty(
        getattr(args, "terminal_visibility_reason", None),
        "cli:--visible" if args.visible else "default_not_visible",
    )
    data["visible_terminal_proof"] = _visible_terminal_proof(
        requested=bool(args.visible), clients="", dry_run=bool(args.dry_run)
    )
    data["terminal_closeout_policy"] = resolve_terminal_closeout_policy(
        stop_after_closeout=bool(getattr(args, "stop_after_closeout", False)),
        keep_open_after_closeout=bool(getattr(args, "keep_open_after_closeout", False)),
        keep_open_reason=_first_nonempty(getattr(args, "keep_open_reason", None)) or "",
        visibility_reason=data["terminal_visibility_reason"],
    )
    conversation_context = _conversation_context_from_args(args, origin_context)
    if conversation_context:
        data["conversation_context"] = conversation_context
    data["artifact_routes"] = default_routes(
        artifact_root=Path(data["artifacts"]["root"]),
        repo_path=repo,
        project_slug=project_slug,
        runtime=args.runtime,
    )
    if args.raw_output_root:
        data["artifact_routes"]["raw_root"] = str(Path(args.raw_output_root).resolve())
        data["artifact_routes"]["raw_root_source"] = "cli_override"
    if args.project_output_root:
        data["artifact_routes"]["project_root"] = str(Path(args.project_output_root).resolve())
    path = Path(data["artifacts"]["manifest"])
    additional_dirs = []
    seen_dirs: set[str] = set()
    for raw_dir in getattr(args, "add_dirs", []) or []:
        candidate = str(Path(raw_dir).expanduser().resolve())
        if candidate == str(repo) or candidate in seen_dirs:
            continue
        seen_dirs.add(candidate)
        additional_dirs.append(candidate)
    data["additional_dirs"] = additional_dirs
    data.setdefault("launch_env", {}).update({
        "HERMES_CODING_TERMINAL_MANIFEST": str(path),
        "HERMES_RUNTIME": args.runtime,
        "HERMES_LOADOUT": args.loadout,
    })
    if args.runtime == "claude":
        data["claude_model"] = resolve_claude_model()
        data["launch_env"]["HERMES_RUN_REPORT_PATH"] = data["artifacts"]["events"]
    ensure_artifact_dirs(data)
    _write_runtime_settings(data)
    path.write_text(json.dumps(data, indent=2))
    command = adapter.launch_command(
        repo_path=str(repo),
        prompt=args.initial_prompt,
        bypass_permissions=args.bypass_permissions,
        permission_posture=data["permission_posture"],
        add_dirs=additional_dirs,
        settings_path=data["artifacts"]["runtime_settings"] if args.runtime == "claude" else None,
        extra_env=data.get("launch_env"),
        config_overrides=data.get("codex_config_overrides") if args.runtime == "codex" else None,
        model=data.get("claude_model") if args.runtime == "claude" else None,
    )
    data["launch_command_verified"] = data["required_runtime_bypass_flag"] in command
    data["required_bypass_flag_present"] = data["launch_command_verified"]
    if data["permission_posture"] == MANAGED_BYPASS_POSTURE and not data["launch_command_verified"]:
        raise SystemExit(
            "Refusing managed launch without verified runtime bypass flag: "
            f"{data['required_runtime_bypass_flag']} missing from final launch command."
        )
    path.write_text(json.dumps(data, indent=2))
    if not args.dry_run:
        desktop_window_ids = []
        # The session-environment stamp lets any repo's operator-status prove
        # ownership of a hermes-* tmux session it does not manage itself.
        create_tmux_session(manifest.tmux_session, command, environment={"HERMES_CODING_TERMINAL_MANIFEST": str(path)})
        if args.visible:
            title = f"{args.runtime.title()} Code - {manifest.tmux_session} - {repo.name}"
            open_desktop_client(manifest.tmux_session, title=title)
            time.sleep(args.visible_wait)
            desktop_window_ids = desktop_window_ids_for_title(title)
        time.sleep(args.startup_wait)
        _settle_startup_dialogs(manifest.tmux_session, runtime=args.runtime, bypass_permissions=args.bypass_permissions)
        status = adapter.detect_status(capture_pane(manifest.tmux_session))
        clients = list_clients(manifest.tmux_session)
    else:
        status = "ready"
        clients = ""
        desktop_window_ids = []
    data = update_manifest_status(path, status, reason="startup status detection", actor="start")
    data["visible_terminal_proof"] = _visible_terminal_proof(
        requested=bool(args.visible), clients=clients, dry_run=bool(args.dry_run), desktop_window_ids=desktop_window_ids
    )
    save_manifest(path, data)
    if args.visible and data["visible_terminal_proof"].get("status") != "desktop_window" and not args.dry_run:
        data = update_manifest_status(path, "blocked", reason="visible launch lacks desktop window proof", actor="start")
    _upsert_ledger_row(repo, path, data, artifact_root=artifact_root)
    routes = data.get("artifact_routes", {})
    return {
        "status": data["status"],
        "runtime": data.get("runtime"),
        "loadout": data.get("loadout"),
        "manifest_path": str(path),
        "tmux_session": manifest.tmux_session,
        "command": command,
        "visible": bool(args.visible),
        "terminal_visible": data.get("terminal_visible", bool(args.visible)),
        "terminal_visibility_reason": data.get("terminal_visibility_reason", ""),
        "visible_terminal_proof": data.get("visible_terminal_proof", {}),
        "clients": clients,
        "origin_context": data.get("origin_context", {}),
        "conversation_context": data.get("conversation_context", {}),
        "managed_launcher": data.get("managed_launcher", ""),
        "launch_origin": data.get("launch_origin", "manual"),
        "hermes_session_id": data.get("hermes_session_id", ""),
        "managed_launch_policy_version": data.get("managed_launch_policy_version", ""),
        "watcher_required": data.get("watcher_required", False),
        "origin_required": data.get("origin_required", False),
        "artifact_routes": routes,
        "artifact_route_preflight": _route_preflight(routes),
        "runtime_event_hook": data.get("runtime_event_hook", {"configured": False}),
        "additional_dirs": additional_dirs,
        "terminal_closeout_policy": data.get("terminal_closeout_policy", {}),
        "permission_posture": data.get("permission_posture", ""),
        "bypass_permissions_effective": data.get("bypass_permissions_effective", False),
        "required_runtime_bypass_flag": data.get("required_runtime_bypass_flag", ""),
        "required_bypass_flag_present": data.get("required_bypass_flag_present", False),
        "launch_command_verified": data.get("launch_command_verified", False),
    }


def cmd_send(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest)
    data = read_manifest(manifest_path)
    ensure_artifact_dirs(data)
    existing_prompts = [path for path in Path(data["artifacts"]["inputs"]).glob("*.md") if not path.name.endswith("-original.md")]
    prompt_id = f"{_stamp()}-{len(existing_prompts) + 1:03d}"
    prompt_path = Path(data["artifacts"]["inputs"]) / f"{prompt_id}.md"
    original_path = Path(data["artifacts"]["inputs"]) / f"{prompt_id}-original.md"
    raw_text = args.prompt if args.prompt is not None else Path(args.prompt_file).read_text()
    original_path.write_text(raw_text)
    if args.raw_prompt:
        prompt_text = raw_text
    else:
        prepared = prepare_prompt(
            request=raw_text,
            runtime=data["runtime"],
            loadout=data.get("loadout", "default"),
            repo_path=data["repo_path"],
            project_slug=data.get("project_slug"),
            output_contract=args.output_contract,
            output_type=args.output_type,
            vault_path=resolve_obsidian_vault_path(),
        )
        prompt_text = prepared.prompt
        data["last_output_type"] = prepared.output_type
    prompt_path.write_text(prompt_text)
    existing_watcher = dict(data.get("watcher") or {})
    if not args.dry_run and not data.get("dry_run"):
        # Modern coding TUIs can leave pasted multiline text staged after the
        # first Enter; a second submit key starts the turn. This has been
        # observed in both Codex and Claude Code visible tmux smoke runs.
        enter_count = 2
        send_literal_prompt(data["tmux_session"], prompt_text, enter_count=enter_count)
    cleared_watcher = _start_new_turn(data, prompt_id=prompt_id, manifest_path=manifest_path)
    transition_manifest_status(data, "working", reason=f"new prompt turn {prompt_id}", actor="send")
    if cleared_watcher.get("pid"):
        data["last_watcher_restart"] = cleared_watcher
    save_manifest(manifest_path, data)
    restarted_watcher = None
    if existing_watcher and not args.dry_run and not data.get("dry_run"):
        restarted_watcher = cmd_watch_start(_watcher_restart_namespace(manifest_path, existing_watcher))
    return {
        "status": data["status"],
        "prompt_id": prompt_id,
        "prompt_path": str(prompt_path),
        "original_prompt_path": str(original_path),
        "manifest_path": str(manifest_path),
        "cleared_watcher": cleared_watcher,
        "restarted_watcher": restarted_watcher,
    }


def _clear_turn_closeout_state(data: dict) -> None:
    for key in (
        "last_runtime_event",
        "latest_closeout_report",
        "latest_closeout_summary",
        "latest_routed_report",
        "latest_raw_report",
        "latest_project_report",
        "closeout_status",
        "closeout_source",
        "closeout_routed",
    ):
        data.pop(key, None)
    artifacts = data.setdefault("artifacts", {})
    for key in ("latest_report", "latest_routed_report", "latest_raw_report", "latest_project_report"):
        artifacts[key] = ""


def _stop_tracked_watcher(data: dict, manifest_path: Path | None = None, *, grace: float = 1.0) -> dict:
    """Terminate the currently tracked background watcher, if it is still alive.

    A new prompt starts a new logical runtime turn. The previous turn's watcher
    must not remain alive while its pid/result files are cleared; otherwise the
    watcher can later write completion JSON to an unlinked result file and the
    operator surface will show the terminal as stopped with closeout not run.
    """
    paths = _watcher_artifact_paths(data)
    pid = _read_watcher_pid(paths, data)
    stopped = False
    if pid is not None and _pid_alive(pid) and (manifest_path is None or _pid_matches_watcher(pid, manifest_path.resolve())):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            stopped = True
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        deadline = time.time() + grace
        while _pid_alive(pid) and time.time() < deadline:
            time.sleep(0.05)
        if _pid_alive(pid):
            try:
                os.killpg(pid, signal.SIGKILL)
            except OSError:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        stopped = not _pid_alive(pid)
    return {"pid": pid, "stopped": stopped}


def _clear_watcher_result(data: dict, manifest_path: Path | None = None) -> dict:
    stopped = _stop_tracked_watcher(data, manifest_path)
    paths = _watcher_artifact_paths(data)
    for key in ("result", "pid"):
        path = paths.get(key)
        if path and path.exists():
            try:
                path.unlink()
            except OSError:
                pass
    data.pop("watcher", None)
    return stopped


def _start_new_turn(data: dict, *, prompt_id: str, manifest_path: Path | None = None) -> dict:
    data["last_prompt_id"] = prompt_id
    data["current_prompt_id"] = prompt_id
    data["current_prompt_started_at"] = _now_iso()
    _clear_turn_closeout_state(data)
    return _clear_watcher_result(data, manifest_path)


def _write_snapshot(manifest_path: Path, text: str) -> dict:
    data = read_manifest(manifest_path)
    ensure_artifact_dirs(data)
    snapshot_path = Path(data["artifacts"]["snapshots"]) / f"{_stamp()}-snapshot.txt"
    snapshot_path.write_text(text)
    latest = Path(data["artifacts"].get("latest_snapshot") or Path(data["artifacts"]["root"]) / "latest-snapshot.txt")
    if latest.name != "latest-snapshot.txt":
        latest = Path(data["artifacts"]["root"]) / "latest-snapshot.txt"
    latest.write_text(text)
    adapter = get_adapter(data["runtime"])
    status = adapter.detect_status(text)
    report = extract_report_from_text(
        text=redact_secrets(text),
        reports_dir=Path(data["artifacts"]["reports"]),
        source_label="snapshot",
        source_path=snapshot_path,
        origin="snapshot",
    )
    report.setdefault("snapshot_path", str(snapshot_path))
    routed = route_report_artifacts(
        manifest=data,
        snapshot_path=snapshot_path,
        report_path=Path(report["report_path"]),
        summary_path=Path(report["summary_path"]),
    )
    updated = update_manifest_status(
        manifest_path,
        status,
        reason="adapter detected status from pane snapshot",
        actor="snapshot",
        latest_snapshot=str(latest),
        last_snapshot=str(snapshot_path),
        latest_report=report["report_path"],
        latest_routed_report=routed.get("project_report") or routed.get("raw_report", ""),
    )
    snap_data = read_manifest(manifest_path)
    snap_data["report_origin"] = "snapshot"
    snap_data["report_status"] = report["status"]
    snap_data["report_routed"] = routed
    snap_data["latest_raw_report"] = routed.get("raw_report", "")
    snap_data["latest_project_report"] = routed.get("project_report", "")
    snap_data["latest_routed_report"] = routed.get("project_report") or routed.get("raw_report", "")
    save_manifest(manifest_path, snap_data)
    return {
        "status": updated["status"],
        "snapshot_path": str(snapshot_path),
        "latest_snapshot": str(latest),
        "report_path": report["report_path"],
        "summary_path": report["summary_path"],
        "route": routed,
        "manifest_path": str(manifest_path),
    }


def cmd_snapshot(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest)
    data = read_manifest(manifest_path)
    if args.text is not None:
        text = args.text
    elif args.text_file:
        text = Path(args.text_file).read_text()
    else:
        text = capture_pane(data["tmux_session"], start=args.start)
    return _write_snapshot(manifest_path, text)


def _events_path_from_manifest(data: dict) -> Path | None:
    artifacts = data.get("artifacts") or {}
    raw = artifacts.get("events")
    if raw:
        return Path(raw)
    root = artifacts.get("root")
    if root:
        return Path(root) / "events.jsonl"
    return None


def _event_summary(event: object) -> dict | None:
    if not isinstance(event, dict):
        return None
    return {
        "timestamp": event.get("timestamp"),
        "runtime": event.get("runtime"),
        "event": event.get("event") or event.get("hook_event_name"),
        "status": event.get("status"),
        "prompt_id": event.get("prompt_id"),
        "runtime_turn_id": event.get("runtime_turn_id"),
        "has_last_assistant_message": bool(_message_from_event(event)),
    }


def _event_status_payload(manifest_path: Path, data: dict) -> dict:
    events_path = _events_path_from_manifest(data)
    event_count = 0
    latest_event = None
    if events_path is not None and events_path.is_file():
        for line in events_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            event_count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if _event_matches_current_turn(data, record):
                latest_event = record
    last_runtime_event = data.get("last_runtime_event") or latest_event
    status = data["status"]
    if isinstance(last_runtime_event, dict) and last_runtime_event.get("status"):
        status = last_runtime_event["status"]
    watched_directories = [str(path) for path in _watch_dirs_for_manifest_events(manifest_path)]
    return {
        "status": status,
        "manifest_status": data.get("status"),
        "manifest_path": str(manifest_path),
        "tmux_session": data["tmux_session"],
        "runtime": data.get("runtime"),
        "last_prompt_id": data.get("last_prompt_id"),
        "last_runtime_event": last_runtime_event,
        "last_runtime_event_summary": _event_summary(last_runtime_event),
        "event_count": event_count,
        "events_path": str(events_path) if events_path is not None else "",
        "events_path_exists": bool(events_path is not None and events_path.exists()),
        "watched_directories": watched_directories,
    }


def _watch_dirs_for_manifest_events(manifest_path: Path) -> list[Path]:
    data = read_manifest(manifest_path)
    candidates = [manifest_path.parent]
    events = _events_path_from_manifest(data)
    if events is not None:
        candidates.append(events.parent)
    root = data.get("artifacts", {}).get("root")
    if root:
        candidates.append(Path(root))
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved not in seen:
            unique.append(resolved)
            seen.add(resolved)
    return unique


def _wait_for_filesystem_event(paths: list[Path], timeout: float) -> str:
    if timeout <= 0:
        return "timeout"
    if sys.platform != "linux":
        time.sleep(timeout)
        return "fallback_sleep"
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        inotify_init1 = libc.inotify_init1
        inotify_init1.argtypes = [ctypes.c_int]
        inotify_init1.restype = ctypes.c_int
        inotify_add_watch = libc.inotify_add_watch
        inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        inotify_add_watch.restype = ctypes.c_int
        fd = inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if fd < 0:
            raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
        try:
            mask = 0x00000002 | 0x00000008 | 0x00000080 | 0x00000100 | 0x00000200 | 0x00000400
            for path in paths:
                watch = inotify_add_watch(fd, os.fsencode(path), mask)
                if watch < 0:
                    err = ctypes.get_errno()
                    if err not in (errno.ENOENT, errno.EACCES):
                        raise OSError(err, os.strerror(err))
            readable, _, _ = select.select([fd], [], [], timeout)
            if not readable:
                return "timeout"
            try:
                os.read(fd, 65536)
            except BlockingIOError:
                pass
            return "filesystem_event"
        finally:
            os.close(fd)
    except Exception:
        time.sleep(timeout)
        return "fallback_sleep"


def cmd_status(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest)
    data = read_manifest(manifest_path)
    if getattr(args, "event_only", False):
        return _event_status_payload(manifest_path, data)
    exists = not data.get("dry_run") and session_exists(data["tmux_session"])
    if args.refresh and not data.get("dry_run") and not exists:
        current = data.get("status")
        # A vanished tmux session implies completion only for an in-flight run.
        # Preserve an already-meaningful manifest status (e.g. blocked/failed/
        # waiting_for_input) so a closed window cannot erase attention signal.
        if current is not None and current not in ACTIVE_SESSION_STATUSES:
            return {"status": current, "manifest_path": str(manifest_path), "tmux_session": data["tmux_session"], "artifacts": data["artifacts"], "clients": ""}
        updated = update_manifest_status(
            manifest_path, "finished",
            reason="tmux session gone while active", actor="status.refresh",
        )
        return {"status": updated["status"], "manifest_path": str(manifest_path), "tmux_session": data["tmux_session"], "artifacts": updated["artifacts"], "clients": ""}
    if args.refresh and exists:
        snapshot = cmd_snapshot(argparse.Namespace(manifest=str(manifest_path), text=None, text_file=None, start=-80))
        snapshot["clients"] = list_clients(data["tmux_session"])
        return snapshot
    clients = list_clients(data["tmux_session"]) if exists else ""
    return {"status": data["status"], "manifest_path": str(manifest_path), "tmux_session": data["tmux_session"], "artifacts": data["artifacts"], "clients": clients}


def cmd_watch(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest)
    deadline = time.time() + args.timeout
    terminal_states = set(args.terminal_state)
    last: dict = {}
    wake_reason = "timeout" if args.timeout <= 0 else "initial"

    def _is_complete(payload: dict) -> bool:
        has_runtime_event = bool(payload.get("last_runtime_event"))
        status_is_terminal = payload.get("status") in terminal_states
        manifest_finished = payload.get("status") == "finished" and payload.get("manifest_status") == "finished"
        if args.event_only:
            # Prefer runtime Stop events, but do not strand a managed run that the
            # manifest already marked fully finished. Do not relax this for
            # blocked/waiting states: those can be startup or pre-hook states and
            # must still wait for the current runtime event.
            return status_is_terminal and (has_runtime_event or manifest_finished)
        return status_is_terminal

    def _finalize_watch_result(result: dict) -> dict:
        if result.get("watch_result") != "terminal_state":
            return result
        status = result.get("status")
        if getattr(args, "manage_on_closeout", False) and status in {"waiting_for_input", "waiting_for_continuation", "blocked", "failed", "stale"}:
            if status == "waiting_for_input" and _final_message_is_structured_report(manifest_path):
                return _run_closeout_pipeline(result)
            result["manage"] = _manage_manifest_once(
                manifest_path,
                transport=getattr(args, "postback_transport", "file_log"),
                delivery_log=None,
                continuation_profile=getattr(args, "continuation_profile", "session"),
                dry_run=False,
                auto_answer=False,
                auto_continue=getattr(args, "auto_continue", False),
            )
            return result
        if not getattr(args, "closeout_on_complete", False):
            return result
        return _run_closeout_pipeline(result)

    def _run_closeout_pipeline(result: dict) -> dict:
        closeout = cmd_closeout(argparse.Namespace(
            manifest=str(manifest_path),
            wait=False,
            timeout=0,
            allow_snapshot_fallback=getattr(args, "allow_snapshot_fallback", False),
            json=True,
        ))
        manifest_data = read_manifest(manifest_path)
        closeout_policy = _manifest_closeout_policy(manifest_data)
        result = {**result, "closeout": closeout, "closeout_policy": closeout_policy}
        manager_enabled = bool(getattr(args, "manage_on_closeout", False))
        if manager_enabled:
            # The run-manager response is the canonical user-facing reportback.
            # Do not also emit the older generic postback message, or Discord gets
            # reportback + continuation + final-answer noise for one terminal run.
            result["manage"] = _manage_manifest_once(
                manifest_path,
                transport=getattr(args, "postback_transport", "file_log"),
                delivery_log=None,
                continuation_profile=getattr(args, "continuation_profile", "session"),
                dry_run=False,
                auto_answer=False,
                auto_continue=getattr(args, "auto_continue", False),
            )
            result["completion_ingress"] = _maybe_send_completion_ingress_for_manifest(manifest_path, args)
        elif getattr(args, "postback_on_closeout", False):
            repo, artifact_root = _postback_repo_from_manifest(manifest_path)
            manage_data_for_scope = read_manifest(manifest_path)
            owner_launcher = manage_data_for_scope.get("managed_launcher") or ""
            owner_thread = manage_data_for_scope.get("discord_thread_id") or ""
            owner_session = manage_data_for_scope.get("hermes_session_id") or ""
            result["postback"] = cmd_postback(argparse.Namespace(
                postback_command="scan",
                repo=str(repo),
                artifact_root=str(artifact_root) if artifact_root else None,
                delivery_log=None,
                transport=getattr(args, "postback_transport", "auto"),
                continuation=(not getattr(args, "no_continuation", False)),
                continuation_profile=getattr(args, "continuation_profile", "session"),
                owner=owner_launcher or None,
                thread_id=owner_thread or None,
                hermes_session_id=owner_session or None,
                include_unowned=not bool(owner_launcher),
                include_all=not bool(owner_launcher or owner_thread or owner_session),
                completion_ingress=True,
                completion_ingress_transport=getattr(args, "completion_ingress_transport", "auto"),
                completion_ingress_url=getattr(args, "completion_ingress_url", None),
                completion_ingress_secret=getattr(args, "completion_ingress_secret", None),
                completion_ingress_log=getattr(args, "completion_ingress_log", None),
                cleanup_after_response=closeout_policy["cleanup_after_response"],
                cleanup_dry_run=closeout_policy["cleanup_dry_run"],
                cleanup_grace=getattr(args, "cleanup_grace", None) or closeout_policy["cleanup_grace_seconds"],
                json=True,
            ))
        managed = bool(manifest_data.get("managed_launcher") or manifest_data.get("launch_origin") == "managed")
        stop_requested = bool(
            getattr(args, "stop_after_closeout", False)
            or (managed and closeout_policy["auto_close_finished_terminals"])
        )
        if closeout_policy["keep_open_after_closeout"]:
            result["stop_skipped_reason"] = closeout_policy["keep_open_reason"] or "keep-open policy active"
        elif (
            stop_requested
            and closeout.get("status") == "structured"
            and closeout.get("has_blockers") is False
        ):
            response_recorded = _response_posted_to_hermes(_ledger_row_for_manifest(manifest_path))
            if managed and not response_recorded:
                # Never close a finished terminal whose answer has not reached
                # Hermes; the response gate keeps it open for the backup paths.
                result["stop_skipped_reason"] = "awaiting_hermes_response"
            else:
                result["stop_result"] = cmd_stop(argparse.Namespace(
                    manifest=str(manifest_path),
                    dry_run=False,
                    grace=getattr(args, "stop_grace", 2.0),
                    json=True,
                ))
        return result

    while time.time() <= deadline:
        last = cmd_status(argparse.Namespace(manifest=str(manifest_path), refresh=not args.event_only, event_only=args.event_only, json=True))
        last["wake_reason"] = wake_reason
        if _is_complete(last):
            return _finalize_watch_result({**last, "watch_result": "terminal_state"})
        remaining = max(0.0, deadline - time.time())
        if args.event_driven:
            # Bound each inotify wait by the poll interval. An event recorded in
            # the window between the status read above and inotify arming produces
            # no edge for this wait, so an unbounded wait would strand the watcher
            # (and Discord closeout/postback/continuation) for the whole lease.
            # Capping the wait guarantees a re-check within poll_interval.
            poll_interval = getattr(args, "poll_interval", None)
            wait_window = min(remaining, poll_interval) if poll_interval and poll_interval > 0 else remaining
            wake_reason = _wait_for_filesystem_event(_watch_dirs_for_manifest_events(manifest_path), wait_window)
        else:
            time.sleep(args.poll_interval)
            wake_reason = "poll_interval"
    final = cmd_status(argparse.Namespace(manifest=str(manifest_path), refresh=not args.event_only, event_only=args.event_only, json=True))
    final["wake_reason"] = wake_reason
    if _is_complete(final):
        return _finalize_watch_result({**final, "watch_result": "terminal_state"})
    return {**final, "watch_result": "timeout"}



def _watcher_artifact_paths(data: dict) -> dict[str, Path]:
    artifacts = data.setdefault("artifacts", {})
    manifest_value = artifacts.get("manifest") or data.get("manifest_path")
    if manifest_value:
        fallback_root = Path(manifest_value).parent
    else:
        # Older failed-launch manifests may not have recorded artifact paths yet.
        # Keep operator-status/doctor robust so one malformed stale manifest does
        # not block new managed terminal launches.
        fallback_root = Path(".")
    root = Path(artifacts.get("root") or fallback_root)
    return {
        "result": Path(artifacts.get("watcher_result") or root / "watcher-result.json"),
        "log": Path(artifacts.get("watcher_log") or root / "watcher.log"),
        "pid": Path(artifacts.get("watcher_pid") or root / "watcher.pid"),
    }


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_cmdline(pid: int | None) -> list[str]:
    if not pid or pid <= 0 or sys.platform != "linux":
        return []
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [part.decode(errors="replace") for part in raw.split(b"\0") if part]


def _pid_matches_watcher(pid: int | None, manifest_path: Path) -> bool:
    cmdline = _pid_cmdline(pid)
    if not cmdline:
        return False
    joined = " ".join(cmdline)
    return (
        "coding_terminal_runner.py" in joined
        and "watch" in cmdline
        and str(manifest_path) in cmdline
    )


def _read_watcher_pid(paths: dict[str, Path], data: dict) -> int | None:
    raw = (data.get("watcher") or {}).get("pid")
    if not raw and paths["pid"].exists():
        raw = paths["pid"].read_text().strip()
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _watcher_restart_namespace(manifest_path: Path, watcher: dict) -> argparse.Namespace:
    command = list(watcher.get("command") or [])

    def _value_after(flag: str, default):
        try:
            return command[command.index(flag) + 1]
        except (ValueError, IndexError):
            return default

    terminal_states: list[str] = []
    for index, part in enumerate(command):
        if part == "--terminal-state" and index + 1 < len(command):
            terminal_states.append(command[index + 1])
    return argparse.Namespace(
        manifest=str(manifest_path),
        timeout=float(_value_after("--timeout", 900)),
        poll_interval=float(_value_after("--poll-interval", 30.0)),
        terminal_state=terminal_states or ["finished", "waiting_for_input", "waiting_for_continuation", "blocked", "failed", "stale"],
        event_only=watcher.get("event_only", "--event-only" in command),
        event_driven=watcher.get("event_driven", "--event-driven" in command),
        closeout_on_complete=watcher.get("closeout_on_complete", "--closeout-on-complete" in command),
        allow_snapshot_fallback=watcher.get("allow_snapshot_fallback", "--allow-snapshot-fallback" in command),
        stop_after_closeout=watcher.get("stop_after_closeout", "--stop-after-closeout" in command),
        stop_grace=float(_value_after("--stop-grace", 2.0)),
        postback_on_closeout=watcher.get("postback_on_closeout", "--postback-on-closeout" in command),
        manage_on_closeout=watcher.get("manage_on_closeout", "--manage-on-closeout" in command),
        postback_transport=_value_after("--postback-transport", watcher.get("postback_transport", "auto")),
        continuation_profile=_value_after("--continuation-profile", watcher.get("continuation_profile", "session")),
        completion_ingress=True,
        completion_ingress_transport=_value_after("--completion-ingress-transport", watcher.get("completion_ingress_transport", "auto")),
        completion_ingress_url=_value_after("--completion-ingress-url", watcher.get("completion_ingress_url", None)),
        completion_ingress_secret=None,
        completion_ingress_log=_value_after("--completion-ingress-log", watcher.get("completion_ingress_log", None)),
        cleanup_grace=float(_value_after("--cleanup-grace", 2.0)),
    )


def cmd_watch_start(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest).resolve()
    data = read_manifest(manifest_path)
    ensure_artifact_dirs(data)
    paths = _watcher_artifact_paths(data)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    existing_pid = _read_watcher_pid(paths, data)
    if _pid_alive(existing_pid) and _pid_matches_watcher(existing_pid, manifest_path):
        return {
            "watcher_status": "running",
            "pid": existing_pid,
            "manifest_path": str(manifest_path),
            "result_path": str(paths["result"]),
            "log_path": str(paths["log"]),
            "reused": True,
        }
    command = [sys.executable, str(Path(__file__).resolve()), "watch", "--manifest", str(manifest_path), "--timeout", str(args.timeout), "--json"]
    if args.event_only:
        command.append("--event-only")
    if args.event_driven:
        command.append("--event-driven")
    if getattr(args, "closeout_on_complete", False):
        command.append("--closeout-on-complete")
    if getattr(args, "allow_snapshot_fallback", False):
        command.append("--allow-snapshot-fallback")
    if getattr(args, "stop_after_closeout", False):
        command.append("--stop-after-closeout")
    if getattr(args, "postback_on_closeout", False):
        command.append("--postback-on-closeout")
        command.extend(["--postback-transport", getattr(args, "postback_transport", "auto")])
        command.extend(["--continuation-profile", getattr(args, "continuation_profile", "session") or "session"])
    if getattr(args, "manage_on_closeout", False):
        command.append("--manage-on-closeout")
        if not getattr(args, "postback_on_closeout", False):
            command.extend(["--postback-transport", getattr(args, "postback_transport", "file_log")])
            command.extend(["--continuation-profile", getattr(args, "continuation_profile", "session") or "session"])
    command.extend(["--completion-ingress-transport", getattr(args, "completion_ingress_transport", "auto") or "auto"])
    if getattr(args, "completion_ingress_url", None):
        command.extend(["--completion-ingress-url", getattr(args, "completion_ingress_url")])
    if getattr(args, "completion_ingress_log", None):
        command.extend(["--completion-ingress-log", getattr(args, "completion_ingress_log")])
    if getattr(args, "stop_grace", None) is not None:
        command.extend(["--stop-grace", str(args.stop_grace)])
    if args.poll_interval is not None:
        command.extend(["--poll-interval", str(args.poll_interval)])
    for terminal_state in args.terminal_state or []:
        command.extend(["--terminal-state", terminal_state])
    stdout = paths["result"].open("w")
    stderr = paths["log"].open("w")
    try:
        process = subprocess.Popen(command, cwd=str(ROOT), stdout=stdout, stderr=stderr, text=True, start_new_session=True)
    finally:
        stdout.close()
        stderr.close()
    paths["pid"].write_text(str(process.pid))
    data["watcher"] = {
        "status": "running",
        "pid": process.pid,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "event_only": bool(args.event_only),
        "event_driven": bool(args.event_driven),
        "closeout_on_complete": bool(getattr(args, "closeout_on_complete", False)),
        "allow_snapshot_fallback": bool(getattr(args, "allow_snapshot_fallback", False)),
        "stop_after_closeout": bool(getattr(args, "stop_after_closeout", False)),
        "stop_grace": getattr(args, "stop_grace", None),
        "postback_on_closeout": bool(getattr(args, "postback_on_closeout", False)),
        "manage_on_closeout": bool(getattr(args, "manage_on_closeout", False)),
        "postback_transport": getattr(args, "postback_transport", "auto"),
        "continuation_profile": getattr(args, "continuation_profile", "session"),
        "completion_ingress_transport": getattr(args, "completion_ingress_transport", "auto"),
        "completion_ingress_url": getattr(args, "completion_ingress_url", None) or "",
        "completion_ingress_log": getattr(args, "completion_ingress_log", None) or "",
        "result_path": str(paths["result"]),
        "log_path": str(paths["log"]),
        "pid_path": str(paths["pid"]),
    }
    save_manifest(manifest_path, data)
    return {
        "watcher_status": "running",
        "pid": process.pid,
        "manifest_path": str(manifest_path),
        "result_path": str(paths["result"]),
        "log_path": str(paths["log"]),
        "pid_path": str(paths["pid"]),
        "command": command,
        "reused": False,
    }


def cmd_watch_status(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest).resolve()
    data = read_manifest(manifest_path)
    paths = _watcher_artifact_paths(data)
    pid = _read_watcher_pid(paths, data)
    alive = _pid_alive(pid)
    pid_matches_watcher = alive and _pid_matches_watcher(pid, manifest_path)
    result = None
    invalid_result = False
    result_exists = paths["result"].exists()
    result_size = paths["result"].stat().st_size if result_exists else 0
    log_exists = paths["log"].exists()
    log_size = paths["log"].stat().st_size if log_exists else 0
    if result_exists and result_size:
        try:
            result = json.loads(paths["result"].read_text())
        except json.JSONDecodeError:
            invalid_result = True
            result = {"error": "invalid_json", "raw": paths["result"].read_text(errors="replace")}
    watch_result = result.get("watch_result") if isinstance(result, dict) else None
    closeout_status = data.get("closeout_status") or "not_run"
    timed_out_before_closeout = (
        watch_result == "timeout"
        and data.get("status") in ACTIVE_SESSION_STATUSES.union(SAFE_STOPPED_SESSION_STATUSES)
        and closeout_status == "not_run"
    )
    if pid_matches_watcher:
        status = "running"
    elif timed_out_before_closeout:
        status = "timed_out"
    elif alive and pid:
        status = "stale_pid" if not result and not invalid_result else ("failed" if invalid_result else "completed")
    else:
        status = "failed" if invalid_result else ("completed" if result else "not_running")
    return {
        "watcher_status": status,
        "pid": pid,
        "alive": alive,
        "pid_matches_watcher": pid_matches_watcher,
        "manifest_path": str(manifest_path),
        "result_path": str(paths["result"]),
        "log_path": str(paths["log"]),
        "pid_path": str(paths["pid"]),
        "result_empty": not bool(result_size),
        "result_size": result_size,
        "log_empty": not bool(log_size),
        "log_size": log_size,
        "result": result,
    }


def _read_watcher_result(data: dict) -> dict | None:
    result_path = _watcher_artifact_paths(data)["result"]
    if not result_path.exists() or not result_path.stat().st_size:
        return None
    try:
        return json.loads(result_path.read_text())
    except json.JSONDecodeError:
        return None


def _message_from_event(event: object) -> str | None:
    if not isinstance(event, dict):
        return None
    payload = event.get("payload")
    if isinstance(payload, dict) and payload.get("last_assistant_message"):
        return payload["last_assistant_message"]
    if event.get("last_assistant_message"):
        return event["last_assistant_message"]
    return None


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _event_matches_current_turn(data: dict, event: object) -> bool:
    if not isinstance(event, dict):
        return False
    current_prompt_id = data.get("current_prompt_id") or data.get("last_prompt_id")
    current_started = _parse_iso(data.get("current_prompt_started_at"))
    event_prompt_id = event.get("prompt_id")
    if not event_prompt_id and isinstance(event.get("last_runtime_event"), dict):
        event_prompt_id = event["last_runtime_event"].get("prompt_id")
    if current_prompt_id and event_prompt_id:
        return event_prompt_id == current_prompt_id
    if current_prompt_id and not event_prompt_id and current_started:
        event_time = _parse_iso(event.get("timestamp"))
        return bool(event_time and event_time >= current_started)
    return True


def _latest_event_from_events_jsonl(data: dict) -> dict | None:
    events_path = _events_path_from_manifest(data)
    if events_path is None or not events_path.is_file():
        return None
    latest: dict | None = None
    for line in events_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if _message_from_event(record) and _event_matches_current_turn(data, record):
            latest = record
    return latest


def _extract_final_message_source(data: dict, *, allow_snapshot_fallback: bool = False) -> tuple[str | None, str | None]:
    """Resolve the runtime's final assistant message and its provenance label.

    Priority follows the closeout contract: watcher-result payload, watcher-result
    top-level event, manifest event, latest events.jsonl line, then an explicit
    snapshot fallback only when allowed. Never scrapes a live tmux pane.
    """
    watcher_result = _read_watcher_result(data)
    if watcher_result and _event_matches_current_turn(data, watcher_result):
        runtime_event = watcher_result.get("last_runtime_event")
        message = _message_from_event(runtime_event)
        if message and _event_matches_current_turn(data, runtime_event):
            return message, "runtime_event"
        if not message:
            message = _message_from_event(watcher_result)
        if message:
            return message, "runtime_event"
    runtime_event = data.get("last_runtime_event")
    manifest_message = _message_from_event(runtime_event)
    if manifest_message and _event_matches_current_turn(data, runtime_event):
        return manifest_message, "manifest_event"
    events_message = _message_from_event(_latest_event_from_events_jsonl(data))
    if events_message:
        return events_message, "events_jsonl"
    if allow_snapshot_fallback:
        latest_snapshot = data.get("artifacts", {}).get("latest_snapshot")
        if latest_snapshot and Path(latest_snapshot).exists():
            return Path(latest_snapshot).read_text(), "snapshot_fallback"
    return None, None


def _final_message_is_structured_report(manifest_path: Path) -> bool:
    """Codex/Claude Stop hooks record `waiting_for_input` after every turn, even
    when the turn ended with a complete five-heading report. A report-shaped
    final message means the run actually finished, so closeout must extract it
    before the manager classifies — otherwise a clean finish is managed as an
    operator question and the report is never routed."""
    data = read_manifest(manifest_path)
    text, _source = _extract_final_message_source(data)
    if not text:
        return False
    sections = _parse_sections(text)
    return all(heading in sections for heading in REPORT_HEADINGS)


def _wait_for_watcher(manifest_path: Path, *, timeout: float, poll: float = 0.5) -> dict:
    deadline = time.time() + timeout
    last = cmd_watch_status(argparse.Namespace(manifest=str(manifest_path)))
    while True:
        status = last.get("watcher_status")
        if status == "completed" or (status == "not_running" and last.get("result")):
            return last
        if status == "failed":
            return {**last, "wait_result": "watcher_failed"}
        if time.time() >= deadline:
            return {**last, "wait_result": "timeout"}
        time.sleep(poll)
        last = cmd_watch_status(argparse.Namespace(manifest=str(manifest_path)))


def cmd_closeout(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest).resolve()
    data = read_manifest(manifest_path)
    ensure_artifact_dirs(data)

    watcher_wait: dict | None = None
    text, source = _extract_final_message_source(data, allow_snapshot_fallback=args.allow_snapshot_fallback)
    if args.wait and not text:
        watcher_wait = _wait_for_watcher(manifest_path, timeout=args.timeout)
        data = read_manifest(manifest_path)
        text, source = _extract_final_message_source(data, allow_snapshot_fallback=args.allow_snapshot_fallback)
    base = {
        "runtime": data.get("runtime"),
        "loadout": data.get("loadout"),
        "session_label": data.get("session_label"),
        "manifest_path": str(manifest_path),
    }

    if not text:
        watcher_paths = _watcher_artifact_paths(data)
        transition_manifest_status(
            data, "needs_attention",
            reason="closeout found no final assistant message", actor="closeout",
        )
        data["closeout_status"] = "no_final_message"
        data["closeout_source"] = None
        save_manifest(manifest_path, data)
        events_path = (data.get("artifacts") or {}).get("events") or ""
        events_failed_path = manifest_path.with_suffix(".events.failed.jsonl")
        recovery = (
            "No final assistant message was captured. Inspect the event files "
            f"({events_path or '<events.jsonl>'}, {events_failed_path}), then re-run "
            "`coding_terminal_runner.py watch --event-only --event-driven` or "
            "`coding_terminal_runner.py closeout --wait` to recover the closeout."
        )
        return {
            **base,
            "status": "no_final_message",
            "report_path": "",
            "summary_path": "",
            "raw_report": "",
            "project_report": "",
            "has_blockers": None,
            "verification": "",
            "source": None,
            "message_excerpt": "",
            "watcher_result_path": str(watcher_paths["result"]),
            "watcher_wait": watcher_wait,
            "recovery": recovery,
        }

    text = redact_secrets(text)
    reports_dir = Path(data["artifacts"]["reports"])
    report = extract_report_from_text(text=text, reports_dir=reports_dir, source_label=source, origin="closeout")
    provenance_path = reports_dir / f"{Path(report['report_path']).stem}-final-message.txt"
    provenance_path.write_text(text)

    routed = route_report_artifacts(
        manifest=data,
        report_path=Path(report["report_path"]),
        summary_path=Path(report["summary_path"]),
        provenance_path=provenance_path,
        provenance_label=source,
    )

    data["latest_closeout_report"] = report["report_path"]
    data["latest_closeout_summary"] = report["summary_path"]
    data["latest_routed_report"] = routed.get("project_report") or routed.get("raw_report", "")
    data["latest_raw_report"] = routed.get("raw_report", "")
    data["latest_project_report"] = routed.get("project_report", "")
    data.setdefault("artifacts", {})["latest_report"] = report["report_path"]
    data["artifacts"]["latest_routed_report"] = data["latest_routed_report"]
    data["artifacts"]["latest_raw_report"] = data["latest_raw_report"]
    data["artifacts"]["latest_project_report"] = data["latest_project_report"]
    data["closeout_status"] = report["status"]
    data["closeout_source"] = source
    data["closeout_routed"] = routed
    data["report_origin"] = "closeout"
    data["report_status"] = report["status"]
    data["report_has_blockers"] = report["has_blockers"]
    if (
        report["status"] == "structured"
        and report["has_blockers"] is False
        and data.get("status") in ("waiting_for_input", "stale")
        and not detect_report_continuation(text)["detected"]
    ):
        # Stop hooks record `waiting_for_input` for every turn, so a run that
        # actually finished clean would otherwise keep a waiting status forever
        # and read as an open operator question to cleanup/manager surfaces.
        transition_manifest_status(
            data, "finished",
            reason="structured closeout with no blockers and no continuation", actor="closeout",
        )
    save_manifest(manifest_path, data)
    _upsert_ledger_row(Path(data["repo_path"]).resolve(), manifest_path, data)

    return {
        **base,
        "status": report["status"],
        "report_path": report["report_path"],
        "summary_path": report["summary_path"],
        "raw_report": routed.get("raw_report", ""),
        "raw_summary": routed.get("raw_summary", ""),
        "project_report": routed.get("project_report", ""),
        "project_summary": routed.get("project_summary", ""),
        "has_blockers": report["has_blockers"],
        "verification": report["verification"],
        "source": source,
        "message_excerpt": text[:280],
        "routed": routed,
        "watcher_wait": watcher_wait,
    }


def cmd_stop(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest)
    data = read_manifest(manifest_path)
    if not args.dry_run and not data.get("dry_run") and session_exists(data["tmux_session"]):
        try:
            send_literal_prompt(data["tmux_session"], "/exit")
            time.sleep(args.grace)
        finally:
            if session_exists(data["tmux_session"]):
                kill_session(data["tmux_session"])
    updated = update_manifest_status(manifest_path, "finished", reason="session stopped", actor="stop")
    return {"status": updated["status"], "manifest_path": str(manifest_path), "tmux_session": data["tmux_session"]}


def _latest_report_from_manifest(data: dict) -> str:
    artifacts = data.get("artifacts") or {}
    return (
        data.get("latest_routed_report")
        or data.get("latest_project_report")
        or data.get("latest_raw_report")
        or data.get("latest_closeout_report")
        or artifacts.get("latest_routed_report")
        or artifacts.get("latest_project_report")
        or artifacts.get("latest_raw_report")
        or artifacts.get("latest_report")
        or ""
    )


def _events_recording_failed(manifest_path: Path) -> bool:
    """True when the Stop-hook event-recording sink captured failures.

    A non-empty `<manifest>.events.failed.jsonl` means runtime events did not
    record cleanly, so the live session must stay open for inspection and never
    be auto-cleaned regardless of derived state.
    """
    failed_path = manifest_path.with_suffix(".events.failed.jsonl")
    try:
        return failed_path.exists() and failed_path.stat().st_size > 0
    except OSError:
        return False


def _response_posted_to_hermes(row: dict | None) -> bool:
    """True once the run has a canonical operator-facing response recorded.

    Closeout extracts the answer; this gate represents the operator's extra lifecycle
    step: Hermes has actually emitted the response (Discord/file-log dry
    run does not count as a live response for unattended cleanup).
    """
    row = row or {}
    return bool(
        row.get("canonical_response_status") == "posted"
        or row.get("manager_response_status") == "posted"
        or row.get("postback_status") == "posted"
    )


def _terminal_response_state(*, data: dict, row: dict | None, lifecycle_state: str, auto_cleanup_safe: bool) -> dict:
    """Derive the response/closure gate shown by operator-status and cleanup.

    A managed terminal is only fully ready to be closed after a structured
    closeout AND a recorded Hermes response. Blockers are report metadata
    that still get surfaced to the operator, but they do not require keeping the
    terminal window open once the response has been recorded. This separates
    local closeout from terminal closure so launch-time hygiene never kills a
    finished terminal whose answer has not been surfaced yet.
    """
    row = row or {}
    managed = bool(
        data.get("managed_launcher") == "run_loaded_agent.py"
        or data.get("launch_origin") == "managed"
        or row.get("managed_launcher") == "run_loaded_agent.py"
        or row.get("launch_origin") == "managed"
    )
    closeout_status = data.get("closeout_status") or row.get("closeout_status") or "not_run"
    has_blockers = data.get("report_has_blockers")
    if has_blockers is None:
        has_blockers = row.get("has_blockers")
    if lifecycle_state == "closed":
        state = "closed"
        reason = "terminal is already closed"
        ready = False
    elif not managed:
        state = "not_required"
        reason = "unmanaged/manual session; response gate is not required"
        ready = bool(auto_cleanup_safe)
    elif closeout_status != "structured":
        state = "awaiting_closeout"
        reason = f"closeout_status={closeout_status}; response cannot be sent yet"
        ready = False
    elif _response_posted_to_hermes(row):
        state = "ready_to_close"
        reason = "structured closeout response is posted"
        ready = True
    else:
        state = "awaiting_hermes_response"
        reason = "structured closeout exists but no Hermes response is recorded yet"
        ready = False
    return {"state": state, "ready_to_close": ready, "reason": reason}


def _classify_session(
    data: dict,
    *,
    tmux_exists: bool,
    watcher_status: str,
    resolved: ResolvedState | None = None,
    runtime_event_failed: bool = False,
) -> tuple[str, bool, str]:
    """Coarse operator-facing classification over the canonical derived state.

    The derived RunState is the decision source; tmux existence and a live
    watcher keep their historical precedence. A dead session with an attention
    status is historical residue, not a live blocker.

    `runtime_event_failed` is the single canonical safety override: a live
    session whose runtime events failed to record is never auto-cleanup-safe,
    so both the operator `cleanup-stopped` path and the manager auto-continue
    path leave it open for inspection.
    """
    if resolved is None:
        resolved = resolve_run_state(data, tmux_exists=tmux_exists)
    state = resolved.state
    status = data.get("status")
    if status in ATTENTION_SESSION_STATUSES or state is RunState.FAILED:
        if not tmux_exists:
            return "closed", False, f"manifest status is {status}; tmux session is closed (historical residue)"
        return "needs_attention", False, f"manifest status is {status}; leaving open for inspection"
    if tmux_exists and runtime_event_failed:
        return "needs_attention", False, f"manifest status is {status} but runtime event recording failed; leaving open for inspection"
    if not tmux_exists:
        return "closed", False, "tmux session is not running"
    if watcher_status == "running":
        return "active", False, "watcher is still running"
    if state in (RunState.LAUNCHING, RunState.RUNNING):
        return "active", False, f"manifest status is {status}"
    if state is RunState.AWAITING_CLOSEOUT and status in ACTIVE_SESSION_STATUSES:
        return "active", False, f"manifest status is {status}; closeout pending"
    if state is RunState.AWAITING_CONTINUATION:
        return "active", False, "waiting on a continuation decision"
    if state in (
        RunState.NEEDS_OPERATOR,
        RunState.AWAITING_CLOSEOUT,
        RunState.COMPLETED_CLEAN,
        RunState.COMPLETED_BLOCKED,
        RunState.STALE,
    ):
        return "stopped", True, f"manifest status is {status} and no watcher is running"
    return "unknown", False, f"unrecognized manifest status: {status}"


def _managed_launch_review(data: dict, *, tmux_exists: bool, watcher_status: str) -> str:
    """Flag open launches that cannot prove they came through the managed launcher.

    Closed sessions never need review. An open session is `manual_needs_review` when no
    managed_launcher stamped it, `watcher_missing_needs_review` when a managed launch
    declared a watcher requirement but none is attached, and `origin_missing_needs_review`
    when reportback was required but origin is unverified.
    """
    launch_origin = data.get("launch_origin") or ("managed" if data.get("managed_launcher") else "manual")
    if not tmux_exists:
        return "closed"
    if launch_origin != "managed":
        return "manual_needs_review"
    watcher_present = watcher_status in {"running", "completed"}
    if data.get("watcher_required") and not watcher_present:
        return "watcher_missing_needs_review"
    if data.get("origin_required") and not data.get("origin_verified"):
        return "origin_missing_needs_review"
    return "managed"


def _ledger_row_for_manifest(manifest_path: Path) -> dict | None:
    ledger_path = manifest_path.parent.parent / "run-ledger.jsonl"
    manifest_key = str(manifest_path.resolve())
    for row in _read_ledger(ledger_path):
        if row.get("manifest_path") == manifest_key:
            return row
    return None


def _session_record(manifest_path: Path) -> dict:
    data = read_manifest(manifest_path)
    watcher = cmd_watch_status(argparse.Namespace(manifest=str(manifest_path)))
    tmux_session = data.get("tmux_session", "")
    exists = bool(tmux_session) and not data.get("dry_run") and session_exists(tmux_session)
    routes = data.get("artifact_routes") or {}
    ledger_row = _ledger_row_for_manifest(manifest_path) or {}
    event = data.get("last_runtime_event")
    if not _event_matches_current_turn(data, event):
        event = None
    final_message = None
    if data.get("status") == "waiting_for_input":
        final_message, _source = _extract_final_message_source(data)
    resolved = resolve_run_state(
        data,
        ledger_row=ledger_row,
        latest_event=event,
        final_message=final_message,
        tmux_exists=exists,
    )
    events_failed_path = manifest_path.with_suffix(".events.failed.jsonl")
    runtime_event_recording_failed = events_failed_path.exists() and events_failed_path.stat().st_size > 0
    lifecycle_state, auto_cleanup_safe, cleanup_reason = _classify_session(
        data,
        tmux_exists=exists,
        watcher_status=watcher.get("watcher_status", "not_running"),
        resolved=resolved,
        runtime_event_failed=runtime_event_recording_failed,
    )
    response_gate = _terminal_response_state(
        data=data, row=ledger_row, lifecycle_state=lifecycle_state, auto_cleanup_safe=auto_cleanup_safe
    )
    if auto_cleanup_safe and not response_gate["ready_to_close"]:
        auto_cleanup_safe = False
        cleanup_reason = response_gate["reason"]
    manifest_status = data.get("status")
    display_status = "closed" if lifecycle_state == "closed" else (manifest_status or "unknown")
    closeout_status = data.get("closeout_status") or "not_run"
    runtime_event_failure_count = (
        sum(1 for line in events_failed_path.read_text().splitlines() if line.strip())
        if runtime_event_recording_failed
        else 0
    )
    record = {
        "manifest_path": str(manifest_path),
        "runtime": data.get("runtime"),
        "loadout": data.get("loadout"),
        "session_label": data.get("session_label"),
        "origin_context": data.get("origin_context", {}),
        "launch_origin": data.get("launch_origin") or ("managed" if data.get("managed_launcher") else "manual"),
        "managed_launcher": data.get("managed_launcher", ""),
        "hermes_session_id": data.get("hermes_session_id", ""),
        "permission_posture": data.get("permission_posture", ""),
        "bypass_permissions_effective": data.get("bypass_permissions_effective", False),
        "required_runtime_bypass_flag": data.get("required_runtime_bypass_flag", ""),
        "required_bypass_flag_present": data.get("required_bypass_flag_present", False),
        "launch_command_verified": data.get("launch_command_verified", False),
        "managed_launch_review": _managed_launch_review(
            data,
            tmux_exists=exists,
            watcher_status=watcher.get("watcher_status", "not_running"),
        ),
        "terminal_visible": data.get("terminal_visible"),
        "terminal_visibility_reason": data.get("terminal_visibility_reason", ""),
        "visible_terminal_proof": data.get("visible_terminal_proof", {}),
        "tmux_session": tmux_session,
        "tmux_exists": exists,
        "lifecycle_state": lifecycle_state,
        "derived_state": resolved.state.value,
        "derived_reason": resolved.reason,
        "derived_launch_blocking": resolved.launch_blocking,
        "derived_superseded_question": resolved.superseded_question,
        "auto_cleanup_safe": auto_cleanup_safe,
        "cleanup_reason": cleanup_reason,
        "status": display_status,
        "manifest_status": manifest_status,
        "closeout_status": closeout_status,
        "terminal_response_state": response_gate["state"],
        "terminal_ready_to_close": response_gate["ready_to_close"],
        "terminal_response_reason": response_gate["reason"],
        "watcher_status": watcher.get("watcher_status"),
        "watcher_result_empty": watcher.get("result_empty", False),
        "watcher_log_empty": watcher.get("log_empty", False),
        "latest_report": _latest_report_from_manifest(data),
        "raw_root": routes.get("raw_root", ""),
        "raw_root_source": routes.get("raw_root_source", ""),
        "runtime_event_recording_failed": runtime_event_recording_failed,
        "runtime_event_failure_count": runtime_event_failure_count,
        "events_failed_path": str(events_failed_path) if runtime_event_recording_failed else "",
    }
    record["closeout_policy"] = _manifest_closeout_policy(data)
    record["activity_gate"] = _session_activity_gate(record)
    record["terminal_cleanup_policy"] = _terminal_cleanup_policy(record)
    return record


def _session_manifests(repo: Path, artifact_root: Path | None = None) -> list[Path]:
    root = artifact_root if artifact_root else repo / ".hermes" / "coding-terminals"
    return sorted(root.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def _session_activity_gate(session: dict) -> dict:
    """Return the first non-invasive activity gate for a session record.

    Cleanup preflight must not refresh, capture, send input to, or mutate an
    active terminal. This helper consumes fields already present on
    ``_session_record`` output and produces a descriptive bucket only.
    """
    if not session.get("tmux_exists"):
        return {"bucket": "closed", "gate": "tmux_closed", "reason": "tmux session is not running"}
    if session.get("watcher_status") == "running":
        return {"bucket": "active", "gate": "watcher_running", "reason": "watcher is running"}
    if session.get("manifest_status") in ACTIVE_SESSION_STATUSES:
        return {
            "bucket": "active",
            "gate": "manifest_active_status",
            "reason": f"manifest status is {session.get('manifest_status')}",
        }
    if session.get("runtime_event_recording_failed"):
        return {
            "bucket": "needs_attention",
            "gate": "runtime_event_recording_failed",
            "reason": "runtime event recording failed",
        }
    if session.get("derived_state") in {
        RunState.LAUNCHING.value,
        RunState.RUNNING.value,
        RunState.AWAITING_CONTINUATION.value,
        RunState.NEEDS_OPERATOR.value,
    }:
        return {
            "bucket": "active",
            "gate": "derived_active_state",
            "reason": f"derived state is {session.get('derived_state')}",
        }
    if session.get("lifecycle_state") == "needs_attention":
        return {
            "bucket": "needs_attention",
            "gate": "needs_attention",
            "reason": session.get("cleanup_reason") or "session needs attention",
        }
    if session.get("auto_cleanup_safe"):
        reason = session.get("cleanup_reason") or "safe stopped session"
        policy = session.get("terminal_cleanup_policy") or {}
        bucket = policy.get("terminal_state") or "stopped_safe"
        if bucket not in {"stopped_safe", "stopped_inspection"}:
            bucket = "stopped_safe"
        return {"bucket": bucket, "gate": "cleanup_safe", "reason": reason}
    if session.get("lifecycle_state") == "unknown":
        return {
            "bucket": "unknown",
            "gate": "unknown_lifecycle",
            "reason": session.get("cleanup_reason") or "session lifecycle is unknown",
        }
    return {
        "bucket": "unknown",
        "gate": "not_cleanup_safe",
        "reason": session.get("cleanup_reason") or "session is not safe to close",
    }


def _terminal_cleanup_policy(session: dict, *, requested_keep_open: bool | None = None) -> dict:
    gate = session.get("activity_gate") or _session_activity_gate(session)
    if gate["bucket"] == "closed":
        return {
            "terminal_state": "closed",
            "cleanup_allowed": False,
            "cleanup_mode": "none",
            "safe_for_auto_clean": False,
            "safe_for_manual_clean": False,
            "reason": gate["reason"],
        }
    if gate["bucket"] in {"active", "needs_attention", "unknown"}:
        return {
            "terminal_state": gate["bucket"],
            "cleanup_allowed": False,
            "cleanup_mode": "keep-open",
            "safe_for_auto_clean": False,
            "safe_for_manual_clean": False,
            "reason": gate["reason"],
        }
    if not session.get("auto_cleanup_safe"):
        return {
            "terminal_state": session.get("lifecycle_state") or "unknown",
            "cleanup_allowed": False,
            "cleanup_mode": "keep-open",
            "safe_for_auto_clean": False,
            "safe_for_manual_clean": False,
            "reason": session.get("cleanup_reason") or "session is not safe to close",
        }
    closeout_policy = session.get("closeout_policy") or {}
    if requested_keep_open is None:
        requested_keep_open = bool(closeout_policy.get("keep_open_after_closeout"))
    if requested_keep_open or session.get("terminal_visibility_reason") in INSPECTION_VISIBILITY_REASONS:
        return {
            "terminal_state": "stopped_inspection",
            "cleanup_allowed": True,
            "cleanup_mode": "manual-clean",
            "safe_for_auto_clean": False,
            "safe_for_manual_clean": True,
            "reason": closeout_policy.get("keep_open_reason")
            or "kept open for operator inspection; cleanup-stopped may close it later",
        }
    if closeout_policy and not closeout_policy.get("cleanup_after_response", True):
        return {
            "terminal_state": "stopped_safe",
            "cleanup_allowed": True,
            "cleanup_mode": "manual-clean",
            "safe_for_auto_clean": False,
            "safe_for_manual_clean": True,
            "reason": f"closeout policy disables cleanup after response (policy_source={closeout_policy.get('policy_source', 'unknown')})",
        }
    return {
        "terminal_state": "stopped_safe",
        "cleanup_allowed": True,
        "cleanup_mode": "auto-clean-eligible",
        "safe_for_auto_clean": True,
        "safe_for_manual_clean": True,
        "reason": session.get("cleanup_reason") or "safe stopped session",
    }


TERMINAL_CLOSEOUT_POLICY_VERSION = "terminal-closeout-policy-v1"
INSPECTION_VISIBILITY_REASONS = {"operator_requested", "visible_verification"}


def _env_flag(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def resolve_terminal_closeout_policy(
    *,
    stop_after_closeout: bool = False,
    keep_open_after_closeout: bool = False,
    keep_open_reason: str = "",
    visibility_reason: str = "",
    cleanup_grace: float = 2.0,
) -> dict:
    """Single resolver for whether a managed terminal auto-closes after closeout.

    Resolution order: explicit keep-open/inspection > explicit stop flag >
    launcher default. This decides
    intent only; the response gate and `_terminal_cleanup_policy` safety gates
    always win at cleanup time.
    """
    cleanup_dry_run = False
    inspection = visibility_reason in INSPECTION_VISIBILITY_REASONS
    if keep_open_after_closeout or inspection:
        reason = keep_open_reason or (
            "cli:--keep-open-after-closeout" if keep_open_after_closeout else f"inspection:{visibility_reason}"
        )
        return {
            "auto_close_finished_terminals": False,
            "cleanup_after_response": False,
            "cleanup_dry_run": cleanup_dry_run,
            "cleanup_grace_seconds": cleanup_grace,
            "keep_open_after_closeout": True,
            "keep_open_reason": reason,
            "cleanup_mode": "manual-clean",
            "policy_source": "cli" if keep_open_after_closeout else "inspection",
            "policy_version": TERMINAL_CLOSEOUT_POLICY_VERSION,
        }
    if stop_after_closeout:
        auto_close, source = True, "cli"
    else:
        # System default: normal managed one-shot terminals auto-close once
        # the response is recorded and every safety gate passes.
        auto_close, source = True, "default"
    return {
        "auto_close_finished_terminals": auto_close,
        "cleanup_after_response": auto_close,
        "cleanup_dry_run": cleanup_dry_run,
        "cleanup_grace_seconds": cleanup_grace,
        "keep_open_after_closeout": False,
        "keep_open_reason": "",
        "cleanup_mode": "auto-clean-eligible" if auto_close else "manual-clean",
        "policy_source": source,
        "policy_version": TERMINAL_CLOSEOUT_POLICY_VERSION,
    }


def _manifest_closeout_policy(data: dict | None) -> dict:
    policy = (data or {}).get("terminal_closeout_policy")
    if isinstance(policy, dict) and policy.get("policy_version"):
        return policy
    # Manifests that predate persisted policy resolve live: system default is
    # auto-close after response, env/inspection can still override.
    return resolve_terminal_closeout_policy(
        visibility_reason=(data or {}).get("terminal_visibility_reason", ""),
    )


def _cleanup_after_response_for_rows(rows: list[dict], *, scan_requested: bool, scan_dry_run: bool, grace: float) -> list[dict]:
    """Close exactly the terminals whose response was just recorded.

    Each row's own manifest policy decides eligibility; the session-record
    safety gates (active/blocked/needs-attention/awaiting-response) always win.
    """
    results: list[dict] = []
    for row in rows:
        manifest_value = row.get("manifest_path")
        if not manifest_value or not Path(manifest_value).exists():
            continue
        manifest_path = Path(manifest_value)
        data = read_manifest(manifest_path)
        policy = _manifest_closeout_policy(data)
        record = _session_record(manifest_path)
        cleanup_policy = record.get("terminal_cleanup_policy") or {}
        entry = {
            "manifest_path": manifest_value,
            "tmux_session": record.get("tmux_session"),
            "closeout_policy": policy,
            "terminal_cleanup_policy": cleanup_policy,
        }
        if policy["keep_open_after_closeout"]:
            entry["action"] = "keep_open"
            entry["reason"] = policy["keep_open_reason"]
        elif not scan_requested and not policy["cleanup_after_response"]:
            entry["action"] = "policy_disabled"
            entry["reason"] = f"cleanup_after_response off (policy_source={policy['policy_source']})"
        elif scan_dry_run or policy["cleanup_dry_run"]:
            entry["action"] = "dry_run"
        elif not record.get("tmux_exists"):
            entry["action"] = "already_closed"
        elif not cleanup_policy.get("safe_for_auto_clean"):
            entry["action"] = "kept_open_unsafe"
            entry["reason"] = cleanup_policy.get("reason") or record.get("cleanup_reason")
        else:
            stop_result = cmd_stop(argparse.Namespace(manifest=manifest_value, dry_run=False, grace=grace, json=True))
            entry["action"] = "closed"
            entry["stop_status"] = stop_result.get("status")
        results.append(entry)
    return results


def _activity_tally(sessions: list[dict], orphans: list[dict] | list[str] | None = None) -> dict:
    tally = {
        "active": [],
        "cleanup_candidates": [],
        "stopped_safe": [],
        "stopped_inspection": [],
        "needs_attention": [],
        "closed": [],
        "unknown": [],
        "orphans": list(orphans or []),
    }
    for session in sessions:
        gate = session.get("activity_gate") or _session_activity_gate(session)
        row = {
            "session_label": session.get("session_label"),
            "manifest_path": session.get("manifest_path"),
            "runtime": session.get("runtime"),
            "tmux_session": session.get("tmux_session"),
            "lifecycle_state": session.get("lifecycle_state"),
            "status": session.get("status"),
            "gate": gate,
        }
        bucket = gate.get("bucket") or "unknown"
        tally.setdefault(bucket, []).append(row)
        if bucket in {"stopped_safe", "stopped_inspection"}:
            tally["cleanup_candidates"].append(row)
    tally["summary"] = {key: len(value) for key, value in tally.items() if isinstance(value, list)}
    return tally


def _list_sessions(repo: Path, artifact_root: Path | None = None) -> tuple[Path, list[dict]]:
    root = artifact_root if artifact_root else repo / ".hermes" / "coding-terminals"
    return root, [_session_record(path) for path in _session_manifests(repo, artifact_root)]


def cmd_list(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root, sessions = _list_sessions(repo, artifact_root)
    if args.open_only:
        sessions = [session for session in sessions if session["tmux_exists"]]
    if args.state:
        sessions = [session for session in sessions if session["lifecycle_state"] == args.state]
    return {"repo": str(repo), "artifact_root": str(root), "count": len(sessions), "sessions": sessions}


def _path_exists(value: str) -> bool:
    return bool(value) and Path(value).exists()


def _copy_existing_redacted(src: str, dst: str, *, dry_run: bool) -> bool:
    if not src or not dst or not Path(src).exists() or Path(dst).exists():
        return False
    if not dry_run:
        target = Path(dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(redact_secrets(Path(src).read_text()))
    return True


def _report_origin(data: dict) -> str:
    origin = data.get("report_origin")
    if origin:
        return origin
    if data.get("latest_closeout_report"):
        return "closeout"
    if _latest_report_from_manifest(data) or (data.get("artifacts") or {}).get("latest_report"):
        return "snapshot"
    return "status"


def _report_record(manifest_path: Path) -> dict:
    data = read_manifest(manifest_path)
    artifacts = data.get("artifacts") or {}
    routed = data.get("closeout_routed") or data.get("report_routed") or {}
    raw_report = data.get("latest_raw_report") or artifacts.get("latest_raw_report") or routed.get("raw_report", "")
    project_report = data.get("latest_project_report") or artifacts.get("latest_project_report") or routed.get("project_report", "")
    local_report = data.get("latest_closeout_report") or artifacts.get("latest_report") or ""
    raw_summary = routed.get("raw_summary", "")
    project_summary = routed.get("project_summary", "")
    routes = data.get("artifact_routes") or {}
    closeout_status = data.get("closeout_status") or "not_run"
    origin = _report_origin(data)
    report_status = data.get("report_status") or closeout_status
    return {
        "manifest_path": str(manifest_path),
        "runtime": data.get("runtime"),
        "loadout": data.get("loadout"),
        "session_label": data.get("session_label"),
        "origin_context": data.get("origin_context", {}),
        "tmux_session": data.get("tmux_session", ""),
        "origin": origin,
        "report_status": report_status,
        "routing_status": routed.get("routing_status", "ok"),
        "routing_error": routed.get("routing_error", ""),
        "closeout_status": closeout_status,
        "closeout_source": data.get("closeout_source"),
        "local_report": local_report,
        "local_report_exists": _path_exists(local_report),
        "raw_report": raw_report,
        "raw_report_exists": _path_exists(raw_report),
        "raw_summary": raw_summary,
        "raw_summary_exists": _path_exists(raw_summary),
        "project_report": project_report,
        "project_report_exists": _path_exists(project_report),
        "project_summary": project_summary,
        "project_summary_exists": _path_exists(project_summary),
        "latest_report": _latest_report_from_manifest(data),
        "raw_root": routes.get("raw_root", ""),
        "raw_root_source": routes.get("raw_root_source", ""),
        "project_root": routes.get("project_root", ""),
    }


def _report_has_any_path(report: dict) -> bool:
    return bool(
        report["local_report"]
        or report["raw_report"]
        or report["project_report"]
        or report["raw_summary"]
        or report["project_summary"]
        or report.get("latest_report")
    )


def _report_missing_expected_copies(report: dict) -> list[str]:
    missing: list[str] = []
    if report["raw_report"] and not report["raw_report_exists"]:
        missing.append("raw_report")
    if report["raw_summary"] and not report["raw_summary_exists"]:
        missing.append("raw_summary")
    if report.get("report_status") == "structured":
        if report["project_report"] and not report["project_report_exists"]:
            missing.append("project_report")
        if report["project_summary"] and not report["project_summary_exists"]:
            missing.append("project_summary")
    return missing


def _report_has_routed_copy(report: dict) -> bool:
    return any(
        report.get(key)
        for key in ("raw_report", "raw_summary", "project_report", "project_summary")
    )


def _report_current_routing_failure(report: dict) -> bool:
    """Return true only for routing failures that still affect current trust.

    Older manifests can retain ``routing_status=failed`` after the missing raw/project
    copies have been repaired or manually backfilled. Doctor should not keep blocking
    launches on that stale ledger text; it should block only when a routed copy is
    still missing, or when the failed route produced no routed handles at all.
    """
    if report.get("routing_status") != "failed":
        return False
    if _report_missing_expected_copies(report):
        return True
    return not _report_has_routed_copy(report)


def _postback_message(row: dict) -> str:
    status = row.get("closeout_status") or "unknown"
    blockers = row.get("has_blockers")
    blocker_text = "unknown" if blockers is None else ("yes" if blockers else "none")
    lines = [
        f"Coding-terminal reportback: {row.get('session_label')}",
        f"Outcome: {status}; blockers: {blocker_text}",
        f"Loadout: {row.get('loadout') or 'unknown'}",
    ]
    if row.get("report_path"):
        lines.append(f"Report: {row['report_path']}")
    return "\n".join(lines)


def _read_report_text(path: str) -> tuple[str, str | None]:
    if not path:
        return "", "no saved report path recorded for continuation review"
    try:
        return Path(path).read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", f"saved report unreadable at {path}: {exc}"


def _section_line(sections: dict, heading: str, max_chars: int = 280) -> str:
    body = (sections.get(heading) or "").strip()
    if not body:
        return ""
    first = next((line.strip("-* ").strip() for line in body.splitlines() if line.strip()), "")
    if len(first) > max_chars:
        first = first[: max_chars - 1].rstrip() + "…"
    return first


def _section_points(sections: dict, heading: str, *, limit: int = 6) -> list[str]:
    body = (sections.get(heading) or "").strip()
    if not body:
        return []
    points: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        cleaned = line.lstrip("-*0123456789. ").strip()
        if cleaned:
            points.append(cleaned)
        if len(points) >= limit:
            break
    return points


def _terminal_checkpoint_summary(latest_output: str, sections: dict) -> str:
    blocker = _section_line(sections, "Blockers", max_chars=220)
    if blocker:
        return blocker
    for raw in latest_output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            continue
        if line.lower().startswith("final report"):
            continue
        if len(line) > 220:
            return line[:219].rstrip() + "…"
        return line
    return ""


def _blocked_review_classification(row: dict, sections: dict, latest_output: str) -> dict | None:
    if (row.get("closeout_status") or "") != "structured":
        return None
    blockers = row.get("has_blockers")
    if not blockers:
        return None
    options = _section_points(sections, "Next Steps")
    checkpoint = _terminal_checkpoint_summary(latest_output, sections)
    if not options and not checkpoint:
        return None
    return {
        "classification": "waiting_for_continuation",
        "action": "review_continuation",
        "reason": "structured blocked closeout with resumable next-step guidance",
        "confidence": "medium",
        "continuation_options": options,
        "continuation_checkpoint": checkpoint,
    }


def _continuation_minimal_message(row: dict, sections: dict) -> str:
    status = row.get("closeout_status") or "unknown"
    blockers = row.get("has_blockers")
    blocker_text = "unknown" if blockers is None else ("yes" if blockers else "none")
    label = row.get("session_label")
    report_path = row.get("report_path", "")
    structured = all(heading in sections for heading in REPORT_HEADINGS)
    if not structured or status not in ("structured",) or blockers:
        verification = _section_line(sections, "Verification") or "missing/partial"
        manifest = row.get("manifest_path", "")
        lines = [
            f"Coding-terminal continuation review: {label}",
            f"This run needs review before more automation. Closeout was {status}; blockers: {blocker_text}.",
            f"Loadout: {row.get('loadout') or 'unknown'}",
            f"I found the saved report at {report_path}, but verification was {verification}.",
            f"Next: inspect manifest {manifest} and the report before launching another implementation pass.",
        ]
        return "\n".join(lines)
    changes = _section_line(sections, "Changes") or "not reported"
    verification = _section_line(sections, "Verification") or "not reported"
    next_step = _section_line(sections, "Next Steps") or "no further action recorded"
    lines = [
        f"Coding-terminal continuation review: {label}",
        f"I reviewed the saved closeout report from {row.get('runtime') or '?'}/{row.get('loadout') or '?'}.",
        f"Loadout: {row.get('loadout') or 'unknown'}",
        f"Outcome: {status}; blockers: {blocker_text}.",
        f"What changed: {changes}",
        f"Verification: {verification}",
        f"Next: {next_step}",
        f"Report: {report_path}",
    ]
    return "\n".join(lines)


def _continuation_session_message(row: dict, sections: dict, *, profile: str, latest_output: str = "") -> str:
    status = row.get("closeout_status") or "unknown"
    blockers = row.get("has_blockers")
    blocker_text = "unknown" if blockers is None else ("yes" if blockers else "none")
    label = row.get("session_label")
    report_path = row.get("report_path", "")
    structured = all(heading in sections for heading in REPORT_HEADINGS)
    context = row.get("conversation_context") or {}
    title = context.get("session_title") or _first_nonempty(row.get("discord_thread_name"))
    goal = context.get("conversation_goal") or context.get("user_request")
    manifest = row.get("manifest_path", "")
    blocked_review = _blocked_review_classification(row, sections, latest_output)
    if blocked_review:
        return build_manager_continuation_decision_message(row, sections, blocked_review)
    if not structured or status not in ("structured",) or blockers:
        verification = _section_line(sections, "Verification") or "missing/partial"
        pointer = f"manifest {manifest} and report {report_path}" if profile == "debug" else f"report {report_path}"
        lines = [
            f"Coding-terminal continuation review: {label}",
            f"This run needs review before we continue the session. Closeout was {status}; blockers: {blocker_text}.",
            f"Loadout: {row.get('loadout') or 'unknown'}",
            f"What I could verify: {verification}",
            "Session impact: I cannot safely advance the previous session goal from this run yet.",
            f"Next: inspect {pointer} before launching another implementation pass.",
        ]
        return "\n".join(lines)
    changes = _section_line(sections, "Changes") or "not reported"
    verification = _section_line(sections, "Verification") or "not reported"
    next_step = _section_line(sections, "Next Steps") or "no further action recorded"
    lines = [f"Coding-terminal continuation review: {label}"]
    if title or goal:
        lines.append(f"I reviewed the Claude Code run and the session context for {title or goal}.")
    else:
        lines.append("I reviewed the Claude Code run; no session context was captured at launch, so this is report-only.")
    lines.append(f"Loadout: {row.get('loadout') or 'unknown'}")
    lines.append(f"Claude did: {changes}")
    lines.append(f"Verification: {verification}")
    if goal:
        lines.append(f"Session impact: this advances {goal} — {changes}")
    else:
        lines.append("Session impact: report-only; advances the run goal as recorded in the closeout.")
    next_question = context.get("next_question")
    if next_question:
        lines.append(f"Recommended next step: {next_step} (open question: {next_question})")
    else:
        lines.append(f"Recommended next step: {next_step}")
    if profile == "debug":
        lines.append(f"Manifest: {manifest}")
    lines.append(f"Report: {report_path}")
    return "\n".join(lines)


def _continuation_review_message(row: dict, *, repo: Path, profile: str = "session") -> tuple[str, str | None]:
    text, error = _read_report_text(row.get("report_path", ""))
    if error:
        return "", error
    sections = _parse_sections(text)
    latest_output = ""
    manifest_value = row.get("manifest_path") or ""
    if manifest_value and Path(manifest_value).exists():
        try:
            latest_output = _read_latest_output_for_manage(read_manifest(Path(manifest_value)))
        except Exception:
            latest_output = ""
    if profile == "minimal":
        return _continuation_minimal_message(row, sections), None
    return _continuation_session_message(row, sections, profile=profile, latest_output=latest_output), None


def _maybe_send_continuation(row: dict, *, repo: Path, transport: str, delivery_log: Path, profile: str = "session") -> str:
    if row.get("continuation_status") == "posted":
        return "skipped"
    if row.get("postback_status") != "posted" or not row.get("report_path"):
        row["continuation_status"] = "not_ready"
        return "not_ready"
    if not row.get("origin_verified") or not row.get("discord_thread_id"):
        row["continuation_status"] = "needs_origin_review"
        row["needs_origin_review"] = True
        row["continuation_last_attempt_at"] = _now_iso()
        return "needs_origin_review"
    message, error = _continuation_review_message(row, repo=repo, profile=profile)
    if error:
        row["continuation_status"] = "failed"
        row["continuation_last_attempt_at"] = _now_iso()
        row["continuation_error"] = error
        row["continuation_transport"] = _resolve_postback_transport(transport)
        return "failed"
    try:
        message_id, resolved_transport = _send_postback(row, message, transport=transport, delivery_log=delivery_log, kind="continuation")
    except PostbackDeliveryError as exc:
        row["continuation_status"] = "failed"
        row["continuation_last_attempt_at"] = _now_iso()
        row["continuation_error"] = str(exc)
        row["continuation_transport"] = _resolve_postback_transport(transport)
        return "failed"
    row["continuation_status"] = "posted"
    row["continuation_message_id"] = message_id
    row["continuation_posted_at"] = _now_iso()
    row["continuation_transport"] = resolved_transport
    row.pop("continuation_error", None)
    return "posted"


def _continuation_signal_log_for_ledger(ledger_path: Path) -> Path:
    return ledger_path.with_name("continuation-signals.jsonl")


def _continuation_signal_key(row: dict) -> str:
    """Stable idempotency key from durable run handles — never terminal text."""
    basis = "|".join([
        str(row.get("run_id") or ""),
        str(row.get("report_path") or ""),
        str(row.get("postback_message_id") or ""),
    ])
    return hashlib.sha256(basis.encode()).hexdigest()[:18]


def _continuation_signal_already_recorded(signal_log: Path, key: str) -> bool:
    if not signal_log.exists():
        return False
    for raw in signal_log.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            if json.loads(line).get("idempotency_key") == key:
                return True
        except json.JSONDecodeError:
            continue
    return False


def _record_continuation_signal(row: dict, *, signal_log: Path) -> str:
    """Emit the machine-readable continuation signal for Hermes to consume.

    Distinct from the human-facing continuation message: this carries only durable
    handles + metadata + an idempotency key so Hermes can run the continuation
    prompt against the saved report/manifest without reading its own Discord
    postback or any raw terminal transcript. Fails closed on a missing report path
    or an unverified Discord origin. Idempotent by key across ledger resets: the
    signal log is append-once per idempotency key.
    """
    if row.get("continuation_signal_status") == "recorded":
        return "skipped"
    if row.get("postback_status") != "posted" or not row.get("report_path"):
        row["continuation_signal_status"] = "not_ready"
        return "not_ready"
    if not row.get("origin_verified") or not row.get("discord_thread_id"):
        row["continuation_signal_status"] = "needs_origin_review"
        row["needs_origin_review"] = True
        row["continuation_signal_last_attempt_at"] = _now_iso()
        return "needs_origin_review"
    key = _continuation_signal_key(row)
    recorded_at = _now_iso()
    if not _continuation_signal_already_recorded(signal_log, key):
        record = {
            "schema_version": 1,
            "kind": "continuation_signal",
            "idempotency_key": key,
            "run_id": row.get("run_id") or "",
            "manifest_path": row.get("manifest_path") or "",
            "report_path": row.get("report_path") or "",
            "runtime": row.get("runtime") or "",
            "loadout": row.get("loadout") or "",
            "origin_thread_id": row.get("discord_thread_id") or "",
            "postback_message_id": row.get("postback_message_id") or "",
            "recorded_at": recorded_at,
        }
        signal_log.parent.mkdir(parents=True, exist_ok=True)
        with signal_log.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    row["continuation_signal_status"] = "recorded"
    row["continuation_signal_key"] = key
    row["continuation_signal_recorded_at"] = recorded_at
    row.pop("continuation_signal_error", None)
    return "recorded"


def _send_postback_to_log(row: dict, message: str, delivery_log: Path, *, kind: str = "postback") -> str:
    delivery_log.parent.mkdir(parents=True, exist_ok=True)
    message_id = hashlib.sha256((kind + ":" + row["run_id"] + message).encode()).hexdigest()[:18]
    delivery = {
        "message_id": message_id,
        "kind": kind,
        "run_id": row["run_id"],
        "session_label": row.get("session_label"),
        "discord_guild_id": row.get("discord_guild_id", ""),
        "discord_channel_id": row.get("discord_channel_id", ""),
        "discord_thread_id": row.get("discord_thread_id", ""),
        "message": message,
        "sent_at": _now_iso(),
    }
    with delivery_log.open("a") as handle:
        handle.write(json.dumps(delivery, sort_keys=True) + "\n")
    return message_id


class PostbackDeliveryError(RuntimeError):
    pass


def _env_file_value(path: Path, key: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip().strip('"').strip("'")
        return value
    return ""


def _discord_bot_token() -> str:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if token:
        return token
    candidates: list[Path] = []
    if os.getenv("HERMES_ENV_FILE"):
        candidates.append(Path(os.environ["HERMES_ENV_FILE"]).expanduser())
    hermes_home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    candidates.extend([
        hermes_home / ".env",
        hermes_home / "profiles" / "default" / ".env",
        hermes_home / "profiles" / "gateway" / ".env",
    ])
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        token = _env_file_value(candidate, "DISCORD_BOT_TOKEN").strip()
        if token:
            return token
    return ""


def _discord_message_chunks(message: str, *, limit: int = 1900) -> list[str]:
    """Split manager/postback text into Discord-safe message chunks.

    Discord rejects message content over 2000 characters. The manager must never
    convert a successful closeout into manager_failed just because the human-facing
    continuation text is long, so split on line boundaries with a safety margin.
    """
    text = message or ""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > limit:
            if current:
                chunks.append(current.rstrip())
                current = ""
            for idx in range(0, len(line), limit):
                chunks.append(line[idx: idx + limit].rstrip())
            continue
        if current and len(current) + len(line) > limit:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current or not chunks:
        chunks.append(current.rstrip())
    total = len(chunks)
    if total <= 1:
        return chunks
    return [f"[{index}/{total}]\n{chunk}" for index, chunk in enumerate(chunks, 1)]


def _send_discord_message(channel_id: str, token: str, content: str) -> str:
    body = json.dumps({"content": content}).encode("utf-8")
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Hermes-Coding-Terminal-Loadout-System",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    message_id = str(payload.get("id") or "").strip()
    if not message_id:
        raise PostbackDeliveryError("Discord delivery returned no message id")
    return message_id


def _send_postback_to_discord(row: dict, message: str) -> str:
    if _discord_origin_has_placeholder_ids(row):
        raise PostbackDeliveryError("verified Discord origin contains placeholder ids; refusing Discord delivery")
    token = _discord_bot_token()
    if not token:
        raise PostbackDeliveryError("DISCORD_BOT_TOKEN is not available in the environment or Hermes .env")
    channel_id = row.get("discord_thread_id") or row.get("discord_channel_id")
    if not channel_id:
        raise PostbackDeliveryError("verified Discord origin has no thread/channel id")
    message_ids: list[str] = []
    try:
        for chunk in _discord_message_chunks(message):
            message_ids.append(_send_discord_message(channel_id, token, chunk))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PostbackDeliveryError(f"Discord API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PostbackDeliveryError(f"Discord delivery failed: {exc.reason}") from exc
    return message_ids[0] if len(message_ids) == 1 else ",".join(message_ids)


def _resolve_postback_transport(requested: str) -> str:
    if requested == "auto":
        return "discord" if _discord_bot_token() else "file_log"
    return requested


# Manager clean-run kinds own the canonical completion message for a run.
_MANAGER_CANONICAL_KINDS = {"manager_continuation", "manager_continuation_auto"}
# Kinds whose successful post claims the run's single canonical human-facing
# response. Actionable operator messages (manager_question,
# manager_continuation_decision) are deliberately excluded: an operator must
# always receive one actionable message even after a canonical response.
_CANONICAL_MARKING_KINDS = {"postback"} | _MANAGER_CANONICAL_KINDS


def _canonical_turn_key(row: dict) -> str:
    """Stable identity for one run turn.

    Prefers (run_id, current_prompt_id): a genuinely new prompt turn gets a new
    prompt id and may post its own canonical response, while report-file
    timestamp drift within one closeout keeps the same key. Falls back to
    report_path only when no prompt id is recorded (legacy rows).
    """
    run_id = str(row.get("run_id") or "")
    prompt_id = str(row.get("current_prompt_id") or "")
    if prompt_id:
        return f"{run_id}::{prompt_id}"
    return f"{run_id}::{row.get('report_path') or ''}"


def _canonical_response_already_posted(row: dict) -> bool:
    """True when this run already emitted its one canonical clean-run message.

    Scoped to the current run turn (run_id + prompt id) so a genuinely new turn
    can still post its own canonical response, but a repeat emitter for the same
    closeout is deduped even when the report file was rewritten with a slightly
    different timestamp.
    """
    if row.get("canonical_response_status") != "posted":
        return False
    recorded = row.get("canonical_response_turn_key")
    if recorded:
        return recorded == _canonical_turn_key(row)
    # Legacy rows written before turn-key scoping: fall back to report_path.
    recorded_report = row.get("canonical_response_report_path")
    current = row.get("report_path")
    if recorded_report and current:
        return recorded_report == current
    return True


def _suppress_clean_emitter(row: dict, kind: str) -> bool:
    """Decide whether a clean-run emitter must skip to avoid a duplicate message.

    A generic postback is suppressed once any canonical response exists (dedupes
    repeat scans and manager-owned runs). A continuation follow-on is suppressed
    only when the manager already owns the canonical message; the legacy
    postback+continuation pair still emits two distinct messages. Manager kinds
    suppress against any prior canonical.
    """
    if not _canonical_response_already_posted(row):
        return False
    if kind == "postback" or kind in _MANAGER_CANONICAL_KINDS:
        return True
    if kind == "continuation":
        return row.get("canonical_response_kind") in _MANAGER_CANONICAL_KINDS
    return False


def _mark_canonical_response(row: dict, *, kind: str, message_id: str, transport: str) -> None:
    row["canonical_response_status"] = "posted"
    row["canonical_response_kind"] = kind
    row["canonical_response_message_id"] = message_id
    row["canonical_response_transport"] = transport
    row["canonical_response_report_path"] = row.get("report_path") or ""
    row["canonical_response_turn_key"] = _canonical_turn_key(row)
    row["canonical_response_event_id"] = _completion_ingress_event_id(row)
    row["canonical_response_posted_at"] = _now_iso()


def _send_postback(row: dict, message: str, *, transport: str, delivery_log: Path, kind: str = "postback") -> tuple[str, str]:
    if _suppress_clean_emitter(row, kind):
        # A canonical clean-run message already went out for this run; skip the
        # duplicate so Discord/Hermes shows exactly one completion message.
        return (
            row.get("canonical_response_message_id") or "",
            row.get("canonical_response_transport") or _resolve_postback_transport(transport),
        )
    resolved = _resolve_postback_transport(transport)
    if resolved == "discord":
        message_id = _send_postback_to_discord(row, message)
    elif resolved == "file_log":
        message_id = _send_postback_to_log(row, message, delivery_log, kind=kind)
    else:
        raise PostbackDeliveryError(f"unsupported postback transport: {transport}")
    if kind in _CANONICAL_MARKING_KINDS:
        _mark_canonical_response(row, kind=kind, message_id=message_id, transport=resolved)
    return message_id, resolved


def _postback_repo_from_manifest(manifest_path: Path) -> tuple[Path, Path | None]:
    data = read_manifest(manifest_path)
    repo = Path(data.get("repo_path") or Path.cwd()).resolve()
    # Start/closeout write the durable run ledger under the repo-level
    # .hermes/coding-terminals root. A manifest's artifact root is the per-run
    # session directory, not the ledger root, so automatic postback must not pass
    # it as --artifact-root.
    return repo, None


class CompletionIngressError(RuntimeError):
    pass


def _completion_ingress_enabled(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "completion_ingress", False)
        or getattr(args, "completion_ingress_url", None)
        or os.getenv("HERMES_TERMINAL_COMPLETION_WEBHOOK_URL")
    )


def _completion_ingress_event_id(row: dict) -> str:
    basis = "|".join([
        str(row.get("run_id") or ""),
        str(row.get("manifest_path") or ""),
        str(row.get("report_path") or ""),
        str(row.get("postback_message_id") or ""),
    ])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def _read_report_sections(report_path: str) -> dict[str, str]:
    if not report_path or not Path(report_path).exists():
        return {}
    try:
        report_text = Path(report_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    return {key.lower().replace(" ", "_"): value.strip() for key, value in _parse_sections(report_text).items()}


def _completion_ingress_payload(row: dict) -> dict:
    sections = _read_report_sections(str(row.get("report_path") or ""))
    hermes_profile = row.get("hermes_profile") or ""
    return {
        "event": "managed_terminal.completed",
        "event_type": "managed_terminal.completed",
        "event_id": row.get("completion_ingress_event_id") or _completion_ingress_event_id(row),
        "run_id": row.get("run_id") or "",
        "manifest_path": row.get("manifest_path") or "",
        "report_path": row.get("report_path") or "",
        "runtime": row.get("runtime") or "",
        "loadout": row.get("loadout") or "",
        "hermes_profile": hermes_profile,
        "session_label": row.get("session_label") or "",
        "outcome": row.get("closeout_status") or "",
        "has_blockers": row.get("has_blockers"),
        "postback_message_id": row.get("postback_message_id") or row.get("manager_response_message_id") or "",
        "manager_response_message_id": row.get("manager_response_message_id") or "",
        "manager_response_kind": row.get("manager_response_kind") or "",
        "origin": {
            "platform": "discord" if row.get("discord_thread_id") or row.get("discord_channel_id") else "",
            "discord_guild_id": row.get("discord_guild_id") or "",
            "discord_channel_id": row.get("discord_channel_id") or "",
            "discord_thread_id": row.get("discord_thread_id") or "",
            "discord_thread_name": row.get("discord_thread_name") or "",
            "hermes_profile": hermes_profile,
            "hermes_session_id": row.get("hermes_session_id") or "",
        },
        "sections": {
            "request": sections.get("request", ""),
            "changes": sections.get("changes", ""),
            "verification": sections.get("verification", ""),
            "blockers": sections.get("blockers", ""),
            "next_steps": sections.get("next_steps", ""),
        },
    }


def _send_completion_ingress_to_log(row: dict, payload: dict, delivery_log: Path) -> str:
    delivery_log.parent.mkdir(parents=True, exist_ok=True)
    event_id = payload.get("event_id") or _completion_ingress_event_id(row)
    delivery = {
        "event_id": event_id,
        "kind": "completion_ingress",
        "status": "posted",
        "transport": "file_log",
        "hermes_profile": payload.get("hermes_profile") or "",
        "discord_thread_id": (payload.get("origin") or {}).get("discord_thread_id") or "",
        "payload": payload,
        "sent_at": _now_iso(),
    }
    with delivery_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(delivery, sort_keys=True) + "\n")
    return str(event_id)


def _send_completion_ingress_to_webhook(row: dict, payload: dict, *, url: str, secret: str) -> str:
    if not url:
        raise CompletionIngressError("completion ingress webhook url is missing")
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    event_id = str(payload.get("event_id") or _completion_ingress_event_id(row))
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Hermes-Coding-Terminal-Loadout-System",
        "X-Request-ID": event_id,
    }
    if secret:
        timestamp = str(int(time.time()))
        signed_content = timestamp.encode("utf-8") + b"." + body
        signature = hmac.new(secret.encode("utf-8"), signed_content, hashlib.sha256).hexdigest()
        headers["X-Webhook-Timestamp"] = timestamp
        headers["X-Webhook-Signature-V2"] = signature
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CompletionIngressError(f"completion ingress webhook error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise CompletionIngressError(f"completion ingress webhook failed: {exc.reason}") from exc
    try:
        response_payload = json.loads(response_body) if response_body.strip() else {}
    except json.JSONDecodeError:
        response_payload = {}
    return str(response_payload.get("message_id") or response_payload.get("event_id") or payload.get("event_id") or _completion_ingress_event_id(row))


def _maybe_send_completion_ingress(row: dict, args: argparse.Namespace, *, default_log: Path) -> str:
    if not _completion_ingress_enabled(args):
        return "disabled"
    if row.get("completion_ingress_status") == "posted":
        return "skipped"
    response_posted = row.get("postback_status") == "posted" or row.get("manager_response_status") == "posted"
    if not response_posted or not row.get("report_path"):
        row["completion_ingress_status"] = "not_ready"
        return "not_ready"
    if not row.get("origin_verified") or not row.get("discord_thread_id"):
        row["completion_ingress_status"] = "needs_origin_review"
        return "needs_origin_review"
    row["completion_ingress_event_id"] = row.get("completion_ingress_event_id") or _completion_ingress_event_id(row)
    payload = _completion_ingress_payload(row)
    transport = getattr(args, "completion_ingress_transport", "file_log") or "file_log"
    if transport == "auto":
        transport = "webhook" if (getattr(args, "completion_ingress_url", None) or os.getenv("HERMES_TERMINAL_COMPLETION_WEBHOOK_URL")) else "file_log"
    manager_owned_discord = (
        row.get("manager_response_status") == "posted"
        and row.get("manager_response_transport") == "discord"
        and row.get("postback_status") != "posted"
    )
    canonical_owned_discord = (
        _canonical_response_already_posted(row)
        and row.get("canonical_response_transport") == "discord"
    )
    if transport == "webhook" and (manager_owned_discord or canonical_owned_discord):
        # A canonical Discord response already went out (run-manager or postback).
        # Sending the completion webhook too makes Hermes emit a second generic
        # "Coding-terminal reportback" for the same closeout.
        outcome = "skipped_manager_response" if manager_owned_discord else "skipped_canonical_response"
        row["completion_ingress_status"] = outcome
        row["completion_ingress_transport"] = transport
        row["completion_ingress_last_attempt_at"] = _now_iso()
        return outcome
    if transport == "webhook" and _discord_origin_has_placeholder_ids(row):
        row["completion_ingress_status"] = "needs_origin_review"
        row["needs_origin_review"] = True
        row["completion_ingress_last_attempt_at"] = _now_iso()
        row["completion_ingress_error"] = "placeholder Discord origin ids; refusing webhook delivery"
        return "needs_origin_review"
    delivery_log = Path(getattr(args, "completion_ingress_log", None) or default_log).resolve()
    try:
        if transport == "file_log":
            delivery_id = _send_completion_ingress_to_log(row, payload, delivery_log)
        elif transport == "webhook":
            delivery_id = _send_completion_ingress_to_webhook(
                row,
                payload,
                url=getattr(args, "completion_ingress_url", None) or os.getenv("HERMES_TERMINAL_COMPLETION_WEBHOOK_URL", ""),
                secret=getattr(args, "completion_ingress_secret", None) or os.getenv("HERMES_TERMINAL_COMPLETION_WEBHOOK_SECRET", ""),
            )
        else:
            raise CompletionIngressError(f"unsupported completion ingress transport: {transport}")
    except CompletionIngressError as exc:
        row["completion_ingress_status"] = "failed"
        row["completion_ingress_last_attempt_at"] = _now_iso()
        row["completion_ingress_error"] = str(exc)
        row["completion_ingress_transport"] = transport
        return "failed"
    row["completion_ingress_status"] = "posted"
    row["completion_ingress_delivery_id"] = delivery_id
    row["completion_ingress_posted_at"] = _now_iso()
    row["completion_ingress_transport"] = transport
    row.pop("completion_ingress_error", None)
    return "posted"


def _maybe_send_completion_ingress_for_manifest(manifest_path: Path, args: argparse.Namespace) -> dict:
    """Emit completion ingress for the manifest-scoped manager hot path.

    Normal watcher closeout now uses manage-on-closeout as the single canonical
    user-facing reportback. That bypasses the broad postback scan, so completion
    ingress must be emitted directly from the manifest's ledger row after the
    manager response is recorded.
    """
    repo, artifact_root = _postback_repo_from_manifest(manifest_path)
    ledger_path = _ledger_path_for_repo(repo, artifact_root)
    data = read_manifest(manifest_path)
    _upsert_ledger_row(repo, manifest_path, data, artifact_root=artifact_root)
    rows = _read_ledger(ledger_path)
    manifest_key = str(manifest_path.resolve())
    idx = next((i for i, row in enumerate(rows) if row.get("manifest_path") == manifest_key), None)
    if idx is None:
        return {"status": "not_ready", "reason": "ledger row missing", "manifest_path": manifest_key}
    default_log = ledger_path.with_name("completion-ingress-deliveries.jsonl")
    outcome = _maybe_send_completion_ingress(rows[idx], args, default_log=default_log)
    _write_ledger(ledger_path, rows)
    return {
        "status": outcome,
        "ledger_path": str(ledger_path),
        "manifest_path": manifest_key,
        "completion_ingress_status": rows[idx].get("completion_ingress_status"),
        "completion_ingress_transport": rows[idx].get("completion_ingress_transport"),
        "completion_ingress_error": rows[idx].get("completion_ingress_error", ""),
        "completion_ingress_event_id": rows[idx].get("completion_ingress_event_id", ""),
    }


def cmd_postback(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    ledger_path = _ledger_path_for_repo(repo, artifact_root)
    rows = _read_ledger(ledger_path)
    delivery_log = Path(args.delivery_log).resolve() if args.delivery_log else ledger_path.with_name("postback-deliveries.jsonl")
    transport = getattr(args, "transport", "file_log")
    continuation_profile = getattr(args, "continuation_profile", "session") or "session"
    continuation_enabled = getattr(args, "continuation", True) and continuation_profile != "none"
    explicit_owner_scope = bool(
        getattr(args, "owner", None)
        or getattr(args, "thread_id", None)
        or getattr(args, "hermes_session_id", None)
    )
    if explicit_owner_scope:
        # Reportback scans only narrow when the caller explicitly provides a
        # scope. Plain operator/test sweeps must not inherit ambient Hermes
        # Discord/session env and silently skip eligible ledger rows.
        owner_launcher = getattr(args, "owner", None) or None
        owner_thread_id = getattr(args, "thread_id", None) or None
        owner_session_id = getattr(args, "hermes_session_id", None) or None
    else:
        owner_launcher = owner_thread_id = owner_session_id = None
    include_unowned = bool(getattr(args, "include_unowned", False))
    include_all = bool(getattr(args, "include_all", False)) or not explicit_owner_scope
    posted: list[dict] = []
    skipped: list[dict] = []
    needs_review: list[dict] = []
    failed: list[dict] = []
    updated: list[dict] = []
    skipped_owner_filter: list[dict] = []
    continuation_tally = {"posted": 0, "skipped": 0, "failed": 0, "needs_origin_review": 0, "not_ready": 0}
    completion_ingress_tally = {"posted": 0, "skipped": 0, "failed": 0, "needs_origin_review": 0, "not_ready": 0, "disabled": 0, "skipped_manager_response": 0, "skipped_canonical_response": 0}
    completion_ingress_log = ledger_path.with_name("completion-ingress-deliveries.jsonl")

    def _run_completion_ingress(target: dict) -> None:
        outcome = _maybe_send_completion_ingress(target, args, default_log=completion_ingress_log)
        completion_ingress_tally[outcome] = completion_ingress_tally.get(outcome, 0) + 1

    def _run_continuation(target: dict) -> None:
        if not continuation_enabled:
            return
        outcome = _maybe_send_continuation(target, repo=repo, transport=transport, delivery_log=delivery_log, profile=continuation_profile)
        continuation_tally[outcome] = continuation_tally.get(outcome, 0) + 1

    for row in rows:
        manifest_value = row.get("manifest_path")
        if manifest_value and Path(manifest_value).exists():
            data = read_manifest(Path(manifest_value))
            row = _upsert_ledger_row(repo, Path(manifest_value), data, artifact_root=artifact_root)
        if not include_all and not _row_matches_owner(
            row,
            owner_launcher,
            owner_thread_id,
            owner_session_id,
            include_unowned=include_unowned,
        ):
            skipped_owner_filter.append(row)
            updated.append(row)
            continue
        status = row.get("postback_status")
        if status == "posted":
            skipped.append(row)
            _run_completion_ingress(row)
            _run_continuation(row)
            updated.append(row)
            continue
        if not row.get("report_path") or row.get("closeout_status") in ("", "not_run"):
            row["postback_status"] = "not_ready"
            updated.append(row)
            continue
        if not row.get("origin_verified") or not row.get("discord_thread_id"):
            row["postback_status"] = "needs_origin_review"
            row["needs_origin_review"] = True
            row["postback_last_attempt_at"] = _now_iso()
            needs_review.append(row)
            updated.append(row)
            continue
        message = _postback_message(row)
        try:
            message_id, resolved_transport = _send_postback(row, message, transport=transport, delivery_log=delivery_log)
        except PostbackDeliveryError as exc:
            row["postback_status"] = "failed"
            row["postback_last_attempt_at"] = _now_iso()
            row["postback_error"] = str(exc)
            row["postback_transport"] = _resolve_postback_transport(transport)
            failed.append(row)
            updated.append(row)
            continue
        row["postback_status"] = "posted"
        row["postback_message_id"] = message_id
        row["postback_posted_at"] = _now_iso()
        row["postback_transport"] = resolved_transport
        row.pop("postback_error", None)
        posted.append(row)
        _run_completion_ingress(row)
        _run_continuation(row)
        updated.append(row)

    by_manifest = {row.get("manifest_path"): row for row in updated}
    final_rows = [by_manifest.get(row.get("manifest_path"), row) for row in rows]
    # Post-response cleanup is exact-manifest: only the rows whose response was
    # just recorded are considered, never a broad repo-wide sweep. The startup
    # cleanup preflight remains the backup path for safe leftovers.
    cleanup_requested = bool(getattr(args, "cleanup_after_response", False))
    cleanup_dry_run = bool(getattr(args, "cleanup_dry_run", False))
    cleanup_results = _cleanup_after_response_for_rows(
        [row for row in final_rows if row.get("postback_status") == "posted"],
        scan_requested=cleanup_requested,
        scan_dry_run=cleanup_dry_run,
        grace=float(getattr(args, "cleanup_grace", 2.0)),
    )
    cleanup_after_response = {
        "mode": "exact_manifest",
        "dry_run": cleanup_dry_run,
        "closed_count": sum(1 for entry in cleanup_results if entry.get("action") == "closed"),
        "results": cleanup_results,
    }
    cleanup_by_manifest = {entry["manifest_path"]: entry for entry in cleanup_results}
    for row in final_rows:
        entry = cleanup_by_manifest.get(row.get("manifest_path"))
        if entry is None:
            continue
        action = entry.get("action")
        if action == "closed":
            row["terminal_cleanup_status"] = "applied"
        elif action == "dry_run":
            row["terminal_cleanup_status"] = "dry_run"
        else:
            row["terminal_cleanup_status"] = f"skipped:{action}"
        row["terminal_cleanup_last_attempt_at"] = _now_iso()
    if final_rows:
        _write_ledger(ledger_path, final_rows)
    return {
        "repo": str(repo),
        "ledger_path": str(ledger_path),
        "delivery_log": str(delivery_log),
        "posted_count": len(posted),
        "skipped_count": len(skipped),
        "needs_origin_review_count": len(needs_review),
        "failed_count": len(failed),
        "skipped_owner_filter_count": len(skipped_owner_filter),
        "not_ready_count": sum(1 for row in final_rows if row.get("postback_status") == "not_ready"),
        "transport": _resolve_postback_transport(transport),
        "owner": {"launcher": owner_launcher, "thread_id": owner_thread_id, "hermes_session_id": owner_session_id},
        "posted": posted,
        "failed": failed,
        "needs_origin_review": needs_review,
        "skipped_owner_filter": skipped_owner_filter,
        "continuation_posted_count": continuation_tally["posted"],
        "continuation_skipped_count": continuation_tally["skipped"],
        "continuation_failed_count": continuation_tally["failed"],
        "continuation_needs_origin_review_count": continuation_tally["needs_origin_review"],
        "completion_ingress_posted_count": completion_ingress_tally["posted"],
        "completion_ingress_skipped_count": completion_ingress_tally["skipped"],
        "completion_ingress_failed_count": completion_ingress_tally["failed"],
        "completion_ingress_needs_origin_review_count": completion_ingress_tally["needs_origin_review"],
        "completion_ingress_not_ready_count": completion_ingress_tally["not_ready"],
        "completion_ingress_disabled_count": completion_ingress_tally["disabled"],
        "cleanup_after_response": cleanup_after_response,
    }


def _repair_report_copies(report: dict, *, dry_run: bool) -> dict:
    repaired: list[str] = []
    report_source = report["local_report"] if report["local_report_exists"] else (report["project_report"] if report["project_report_exists"] else report["raw_report"])
    summary_source = report["project_summary"] if report["project_summary_exists"] else (report["raw_summary"] if report["raw_summary_exists"] else "")
    if _copy_existing_redacted(report_source, report["raw_report"], dry_run=dry_run):
        repaired.append("raw_report")
    if _copy_existing_redacted(summary_source, report["raw_summary"], dry_run=dry_run):
        repaired.append("raw_summary")
    if report.get("report_status") == "structured":
        if _copy_existing_redacted(report_source, report["project_report"], dry_run=dry_run):
            repaired.append("project_report")
        if _copy_existing_redacted(summary_source, report["project_summary"], dry_run=dry_run):
            repaired.append("project_summary")
    return {**report, "missing": _report_missing_expected_copies(report), "repaired": repaired}


def cmd_reports(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root = artifact_root if artifact_root else repo / ".hermes" / "coding-terminals"
    reports = [_report_record(path) for path in _session_manifests(repo, artifact_root)]
    if not args.include_empty:
        reports = [report for report in reports if _report_has_any_path(report)]
    if args.reports_command == "list":
        reports = [{**report, "missing": _report_missing_expected_copies(report)} for report in reports]
        total_count = len(reports)
        if args.limit is not None:
            reports = reports[:args.limit]
        return {"repo": str(repo), "artifact_root": str(root), "count": total_count, "reports": reports}
    if args.reports_command == "repair":
        repairable = [report for report in reports if _report_missing_expected_copies(report)]
        if args.limit is not None:
            repairable = repairable[:args.limit]
        repaired = [_repair_report_copies(report, dry_run=args.dry_run) for report in repairable]
        return {
            "repo": str(repo),
            "artifact_root": str(root),
            "dry_run": bool(args.dry_run),
            "checked_count": len(reports),
            "repair_target_count": len(repairable),
            "repaired_file_count": sum(len(report["repaired"]) for report in repaired),
            "reports": repaired,
        }
    raise SystemExit("reports requires a supported subcommand")


def _tmux_list_sessions() -> list[str]:
    completed = subprocess.run(["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _tmux_session_details(session_name: str) -> dict:
    fmt = "#{session_name}|#{session_attached}|#{session_windows}|#{session_created}|#{session_activity}"
    completed = subprocess.run(["tmux", "display-message", "-p", "-t", session_name, fmt], capture_output=True, text=True)
    if completed.returncode != 0:
        return {
            "name": session_name,
            "exists": False,
            "attached_clients": 0,
            "windows": 0,
            "created": "",
            "activity": "",
            "attach_command": f"tmux attach -t {session_name}",
            "cleanup_command": f"python scripts/coding_terminal_runner.py orphans cleanup --session {session_name} --yes --json",
        }
    parts = completed.stdout.strip().split("|", 4)
    _, attached, windows, created, activity = (parts + [""] * 5)[:5]
    try:
        attached_count = int(attached)
    except ValueError:
        attached_count = 0
    try:
        window_count = int(windows)
    except ValueError:
        window_count = 0
    return {
        "name": session_name,
        "exists": True,
        "attached_clients": attached_count,
        "windows": window_count,
        "created": created,
        "activity": activity,
        "attach_command": f"tmux attach -t {session_name}",
        "cleanup_command": f"python scripts/coding_terminal_runner.py orphans cleanup --session {session_name} --yes --json",
    }


def _tmux_session_manifest_env(session_name: str) -> str:
    try:
        completed = subprocess.run(
            ["tmux", "show-environment", "-t", session_name, "HERMES_CODING_TERMINAL_MANIFEST"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return ""
    if completed.returncode != 0:
        return ""
    line = completed.stdout.strip()
    return line.split("=", 1)[1] if "=" in line else ""


def _split_unmanaged_tmux(sessions: list[dict]) -> tuple[list[str], list[dict]]:
    """Split hermes-* tmux sessions this repo does not manage into true orphans
    and sessions managed by another repo's artifact root.

    Every managed launch stamps its manifest path into the tmux session
    environment, so a session whose stamp resolves to an existing manifest is
    owned elsewhere — it must not block launches here or be offered to
    `orphans cleanup`, which would kill another repo's live managed run."""
    managed = {session.get("tmux_session") for session in sessions if session.get("tmux_session")}
    orphans: list[str] = []
    external: list[dict] = []
    for name in _tmux_list_sessions():
        if not (name.startswith("hermes-claude-") or name.startswith("hermes-codex-")):
            continue
        if name in managed:
            continue
        manifest = _tmux_session_manifest_env(name)
        if manifest and Path(manifest).exists():
            external.append({"name": name, "manifest_path": manifest, "attach_command": f"tmux attach -t {name}"})
        else:
            orphans.append(name)
    return orphans, external


def _orphan_tmux_sessions(sessions: list[dict]) -> list[str]:
    return _split_unmanaged_tmux(sessions)[0]


def _orphan_tmux_records(sessions: list[dict]) -> list[dict]:
    return [_tmux_session_details(name) for name in _orphan_tmux_sessions(sessions)]


def _session_counts(sessions: list[dict]) -> dict[str, int]:
    counts = {"active": 0, "stopped": 0, "needs_attention": 0, "closed": 0, "unknown": 0}
    for session in sessions:
        state = session.get("lifecycle_state") or "unknown"
        counts[state] = counts.get(state, 0) + 1
    counts["open_managed"] = sum(1 for session in sessions if session.get("tmux_exists"))
    counts["runtime_event_recording_failed"] = sum(1 for session in sessions if session.get("runtime_event_recording_failed"))
    counts["terminal_ready_to_close"] = sum(1 for session in sessions if session.get("tmux_exists") and session.get("terminal_ready_to_close"))
    counts["terminal_awaiting_response"] = sum(1 for session in sessions if session.get("tmux_exists") and session.get("terminal_response_state") == "awaiting_hermes_response")
    counts["manual_launch"] = sum(1 for session in sessions if session.get("tmux_exists") and session.get("launch_origin") != "managed")
    counts["manual_needs_review"] = sum(1 for session in sessions if session.get("managed_launch_review", "").endswith("needs_review"))
    return counts


def _historical_residue_summary(sessions: list[dict]) -> dict[str, int]:
    closed = [session for session in sessions if session.get("lifecycle_state") == "closed"]
    return {
        "closed_without_closeout": sum(
            1
            for session in closed
            if (session.get("closeout_status") or "not_run") == "not_run"
            and session.get("manifest_status") in {"finished", "working", "waiting_for_input", "waiting_for_continuation", "blocked", "failed", "stale"}
        ),
        "closed_with_timed_out_watcher": sum(1 for session in closed if session.get("watcher_status") == "timed_out"),
        "closed_needs_attention": sum(
            1 for session in closed if session.get("manifest_status") in ATTENTION_SESSION_STATUSES
        ),
    }


def _prune_candidates(sessions: list[dict], *, older_than_days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - older_than_days * 86400
    now_ts = datetime.now(timezone.utc).timestamp()
    candidates: list[dict] = []
    for session in sessions:
        if session.get("lifecycle_state") != "closed":
            continue
        if session.get("manifest_status") in ATTENTION_SESSION_STATUSES:
            # Attention residue is closed for launch-blocking purposes but its
            # artifacts stay until an operator has reviewed the failure.
            continue
        manifest_path = Path(session["manifest_path"])
        manifest_mtime = manifest_path.stat().st_mtime
        if manifest_mtime >= cutoff:
            continue
        session_dir = manifest_path.parent
        age_days = max(0.0, (now_ts - manifest_mtime) / 86400)
        candidates.append({
            **session,
            "session_dir": str(session_dir),
            "manifest_mtime": manifest_mtime,
            "age_days": round(age_days, 1),
            "size_bytes": _dir_size_bytes(session_dir),
        })
    return candidates


def _artifact_hygiene_summary(sessions: list[dict], *, prune_cutoff_days: int = 14) -> dict[str, object]:
    closed_count = sum(1 for session in sessions if session.get("lifecycle_state") == "closed")
    candidates = _prune_candidates(sessions, older_than_days=prune_cutoff_days)
    reclaimable_bytes = sum(candidate["size_bytes"] for candidate in candidates)
    oldest_days = max((candidate["age_days"] for candidate in candidates), default=0.0)
    return {
        "session_dir_count": len(sessions),
        "closed_session_count": closed_count,
        "prune_cutoff_days": prune_cutoff_days,
        "prune_candidate_count": len(candidates),
        "prune_candidate_bytes": reclaimable_bytes,
        "oldest_prune_candidate_days": oldest_days,
        "prune_candidates": candidates[:10],
    }


def _operator_trust_summary(counts: dict[str, int], sessions: list[dict], route_preflight: dict[str, object]) -> dict[str, object]:
    current_blockers: list[dict[str, object]] = []
    for key in ("active", "needs_attention", "orphan_tmux", "runtime_event_recording_failed"):
        if counts.get(key, 0):
            current_blockers.append({"kind": key, "count": counts[key]})
    if counts.get("manager_asked", 0):
        current_blockers.append({"kind": "manager_asked_operator", "count": counts["manager_asked"]})
    if counts.get("manager_awaiting_continuation", 0):
        current_blockers.append({"kind": "manager_awaiting_continuation", "count": counts["manager_awaiting_continuation"]})
    if counts.get("manager_failed", 0):
        current_blockers.append({"kind": "manager_failed", "count": counts["manager_failed"]})
    derived_blocking_sessions = [
        {
            "manifest_path": session.get("manifest_path"),
            "derived_state": session.get("derived_state"),
            "derived_reason": session.get("derived_reason"),
        }
        for session in sessions
        if session.get("tmux_exists") and session.get("derived_launch_blocking")
    ]
    return {
        "canonical_lifecycle_source": "manifest_and_runtime_events",
        "watcher_role": "process_bookkeeping_and_orchestration",
        "launch_blocking": not not current_blockers,
        "current_blockers": current_blockers,
        "derived_launch_blocking": bool(derived_blocking_sessions),
        "derived_blocking_sessions": derived_blocking_sessions,
        "route_preflight_warnings": route_preflight.get("warnings") or [],
        "historical_residue": _historical_residue_summary(sessions),
    }


def _manager_attention_counts(ledger_rows: list[dict], sessions: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    sessions_by_manifest = {
        str(Path(session["manifest_path"]).resolve()): session
        for session in sessions
        if session.get("manifest_path")
    }
    actionable: dict[str, int] = {}
    historical: dict[str, int] = {}
    for row in ledger_rows:
        status = row.get("manager_status") or "not_ready"
        manifest_path = row.get("manifest_path")
        session = None
        if manifest_path:
            try:
                session = sessions_by_manifest.get(str(Path(manifest_path).resolve()))
            except OSError:
                session = None
        superseded_question = bool(
            status == "asked_operator" and session and session.get("derived_superseded_question")
        )
        live = bool(session and session.get("lifecycle_state") != "closed")
        bucket = actionable if live and not superseded_question else historical
        bucket[status] = bucket.get(status, 0) + 1
    return actionable, historical


def cmd_operator_status(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root, sessions = _list_sessions(repo, artifact_root)
    open_sessions = [session for session in sessions if session["tmux_exists"]]
    orphan_tmux, external_managed_tmux = _split_unmanaged_tmux(sessions)
    orphan_records = [_tmux_session_details(name) for name in orphan_tmux]
    routes = default_routes(artifact_root=root, repo_path=repo, project_slug=repo.name, runtime="claude")
    route_preflight_by_runtime = {
        runtime: _route_preflight(
            default_routes(artifact_root=root, repo_path=repo, project_slug=repo.name, runtime=runtime)
        )
        for runtime in KNOWN_RUNTIMES
    }
    counts = _session_counts(sessions)
    ledger_rows = _read_ledger(_ledger_path_for_repo(repo, artifact_root))
    postback_counts: dict[str, int] = {}
    continuation_counts: dict[str, int] = {}
    manager_response_counts: dict[str, int] = {}
    for row in ledger_rows:
        state = row.get("postback_status") or "unknown"
        postback_counts[state] = postback_counts.get(state, 0) + 1
        cont_state = row.get("continuation_status") or "unknown"
        continuation_counts[cont_state] = continuation_counts.get(cont_state, 0) + 1
        response_state = row.get("manager_response_status") or "unknown"
        manager_response_counts[response_state] = manager_response_counts.get(response_state, 0) + 1
    counts["postback_pending"] = postback_counts.get("pending", 0)
    counts["postback_needs_origin_review"] = postback_counts.get("needs_origin_review", 0)
    counts["postback_posted"] = postback_counts.get("posted", 0)
    counts["postback_failed"] = postback_counts.get("failed", 0)
    counts["continuation_pending"] = continuation_counts.get("pending", 0)
    counts["continuation_needs_origin_review"] = continuation_counts.get("needs_origin_review", 0)
    counts["continuation_posted"] = continuation_counts.get("posted", 0)
    counts["continuation_failed"] = continuation_counts.get("failed", 0)
    counts["manager_response_posted"] = manager_response_counts.get("posted", 0)
    counts["manager_response_dry_run"] = manager_response_counts.get("dry_run", 0)
    counts["manager_response_missing"] = manager_response_counts.get("unknown", 0)
    manager_counts, historical_manager_counts = _manager_attention_counts(ledger_rows, sessions)
    counts["manager_asked"] = manager_counts.get("asked_operator", 0)
    counts["manager_continued"] = manager_counts.get("continued", 0)
    counts["manager_awaiting_continuation"] = manager_counts.get("awaiting_continuation_decision", 0)
    counts["manager_needs_review"] = manager_counts.get("needs_review", 0)
    counts["manager_failed"] = manager_counts.get("failed", 0)
    counts["manager_not_ready"] = manager_counts.get("not_ready", 0)
    counts["manager_historical_asked"] = historical_manager_counts.get("asked_operator", 0)
    counts["manager_historical_continued"] = historical_manager_counts.get("continued", 0)
    counts["manager_historical_awaiting_continuation"] = historical_manager_counts.get("awaiting_continuation_decision", 0)
    counts["manager_historical_needs_review"] = historical_manager_counts.get("needs_review", 0)
    counts["manager_historical_failed"] = historical_manager_counts.get("failed", 0)
    counts["manager_historical_not_ready"] = historical_manager_counts.get("not_ready", 0)
    counts["manager_historical_total"] = sum(historical_manager_counts.values())
    counts["orphan_tmux"] = len(orphan_tmux)
    counts["external_managed_tmux"] = len(external_managed_tmux)
    counts["open_total"] = counts["open_managed"] + len(orphan_tmux)
    activity_tally = _activity_tally(sessions, orphan_tmux)
    route_preflight = _route_preflight(routes)
    artifact_hygiene = _artifact_hygiene_summary(sessions)

    # Join manager response state (ledger) onto the latest sessions (manifests)
    # so the operator sees "how did the run go?" without opening the ledger.
    rows_by_manifest: dict[str, dict] = {}
    for row in ledger_rows:
        mp = row.get("manifest_path")
        if not mp:
            continue
        try:
            rows_by_manifest[str(Path(mp).resolve())] = row
        except OSError:
            continue

    def _with_manager_response(session: dict) -> dict:
        manifest_path = session.get("manifest_path")
        row = {}
        if manifest_path:
            try:
                row = rows_by_manifest.get(str(Path(manifest_path).resolve()), {})
            except OSError:
                row = {}
        managed = bool(session.get("managed_launcher") == "run_loaded_agent.py" or session.get("launch_origin") == "managed")
        terminalish = session.get("status") in {"closed", "finished", "waiting_for_input"} or session.get("manifest_status") in {"finished", "waiting_for_input"}
        is_historical_closed = session.get("lifecycle_state") == "closed" and not session.get("tmux_exists")
        manager_response_status = row.get("manager_response_status", "missing")
        missing_closeout = bool(
            managed and terminalish and (
                session.get("closeout_status") != "structured"
                or manager_response_status not in {"posted", "dry_run"}
            )
        )
        empty_watcher_result = bool(
            managed and terminalish and session.get("watcher_result_empty") and session.get("closeout_status") != "structured"
        )
        closeout_recovery_needed = missing_closeout and not is_historical_closed
        watcher_empty_result = empty_watcher_result and not is_historical_closed
        return {
            **session,
            "manager_status": row.get("manager_status", ""),
            "manager_response_status": manager_response_status,
            "manager_response_message_id": row.get("manager_response_message_id", ""),
            "manager_response_packet_path": row.get("manager_response_packet_path", ""),
            "closeout_recovery_needed": closeout_recovery_needed,
            "watcher_empty_result_failure": watcher_empty_result,
        }

    sessions_with_manager = [_with_manager_response(session) for session in sessions]
    fresh_sessions = sessions_with_manager[:10]
    counts["closeout_recovery_needed"] = sum(1 for session in fresh_sessions if session.get("closeout_recovery_needed"))
    counts["watcher_empty_result_failure"] = sum(1 for session in fresh_sessions if session.get("watcher_empty_result_failure"))
    latest_sessions = fresh_sessions
    return {
        "repo": str(repo),
        "artifact_root": str(root),
        "summary": counts,
        "activity_tally": activity_tally,
        "operator_trust": _operator_trust_summary(counts, sessions, route_preflight),
        "artifact_hygiene": artifact_hygiene,
        "route_preflight": route_preflight,
        "route_preflight_by_runtime": route_preflight_by_runtime,
        "runtime_home": {"HOME": resolve_real_home()},
        "open_sessions": open_sessions,
        "orphan_tmux_sessions": orphan_tmux,
        "orphan_tmux_records": orphan_records,
        "external_managed_tmux_sessions": external_managed_tmux,
        "latest_sessions": latest_sessions,
    }


def _doctor_from_operator_status(status: dict) -> dict:
    counts = status["summary"]
    route = status["route_preflight"]
    artifact_hygiene = status.get("artifact_hygiene") or {}
    issues: list[dict] = []
    actions: list[str] = []
    latest_sessions = status.get("latest_sessions") or []
    recent_obsidian_routing = any(
        session.get("raw_root_source") in {"save_destination", "obsidian_vault"}
        for session in latest_sessions
    )

    if counts.get("needs_attention", 0):
        issues.append({"kind": "needs_attention", "count": counts["needs_attention"], "severity": "action_required"})
        actions.append("Inspect needs-attention sessions with `coding_terminal_runner.py list --state needs_attention --json` before closing anything.")
    if counts.get("runtime_event_recording_failed", 0):
        issues.append({"kind": "runtime_event_recording_failed", "count": counts["runtime_event_recording_failed"], "severity": "action_required"})
        actions.append("Inspect the reported .events.failed.jsonl files; Stop-hook recording failed for those runs. Re-run `coding_terminal_runner.py watch` or `coding_terminal_runner.py closeout` to recover the final message.")
    if counts.get("watcher_empty_result_failure", 0):
        issues.append({"kind": "watcher_empty_result", "count": counts["watcher_empty_result_failure"], "severity": "action_required"})
        actions.append("Watcher result/log is empty for a finished managed run. Run `coding_terminal_runner.py recover-closeouts --json` to backfill closeout and manager response.")
    if counts.get("closeout_recovery_needed", 0):
        issues.append({"kind": "closeout_recovery_needed", "count": counts["closeout_recovery_needed"], "severity": "action_required"})
        actions.append("Run `coding_terminal_runner.py recover-closeouts --json` to idempotently run closeout, manager response, and completion ingress for missed managed runs.")
    if counts.get("orphan_tmux", 0):
        issues.append({"kind": "orphan_tmux", "count": counts["orphan_tmux"], "severity": "action_required"})
        actions.append("Inspect orphan sessions with `coding_terminal_runner.py orphans list --json`; close them with `coding_terminal_runner.py orphans cleanup --yes --json` after confirming they are stale.")
    if counts.get("continuation_failed", 0):
        issues.append({"kind": "continuation_failed", "count": counts["continuation_failed"], "severity": "action_required"})
        actions.append("Continuation reviews failed after postback; inspect `continuation_error` in the run ledger and re-run `coding_terminal_runner.py postback scan` once the saved report path is recoverable.")
    if route.get("warnings"):
        if recent_obsidian_routing:
            issues.append({
                "kind": "route_preflight_caller_limited",
                "warnings": route["warnings"],
                "severity": "warn",
                "recent_save_destination_routing": True,
            })
            actions.append("This caller cannot prove save-destination routing, but recent stored runs used save-destination routes. Verify the managed child environment before changing route configuration.")
        else:
            issues.append({"kind": "report_routing", "warnings": route["warnings"], "severity": "action_required"})
            actions.append("Fix SAVE_DESTINATION_PATH or raw-output routing before relying on durable capture.")
    if counts.get("stopped", 0):
        issues.append({"kind": "safe_cleanup_available", "count": counts["stopped"], "severity": "warn"})
        actions.append("Run `coding_terminal_runner.py cleanup-stopped --json` to close safe stopped sessions.")
    if artifact_hygiene.get("prune_candidate_count", 0):
        issues.append({
            "kind": "artifact_hygiene_prune_available",
            "count": artifact_hygiene["prune_candidate_count"],
            "severity": "warn",
            "prune_cutoff_days": artifact_hygiene.get("prune_cutoff_days"),
            "reclaimable_bytes": artifact_hygiene.get("prune_candidate_bytes"),
            "oldest_prune_candidate_days": artifact_hygiene.get("oldest_prune_candidate_days"),
        })
        actions.append(
            "Historical closed session artifacts are piling up. Run "
            f"`coding_terminal_runner.py prune --older-than-days {artifact_hygiene.get('prune_cutoff_days', 14)} --json` "
            f"to review {artifact_hygiene['prune_candidate_count']} prune candidates "
            f"({artifact_hygiene.get('prune_candidate_bytes', 0)} bytes reclaimable) before the next cleanup pass."
        )
    if counts.get("active", 0):
        issues.append({"kind": "active_sessions", "count": counts["active"], "severity": "warn"})
        actions.append("Let active sessions finish, or stop them explicitly after capturing evidence; new launches block by default until active sessions are resolved.")
    if counts.get("manual_needs_review", 0):
        issues.append({"kind": "manual_launch_needs_review", "count": counts["manual_needs_review"], "severity": "warn"})
        actions.append("Open coding terminals lack managed-launch proof (no managed_launcher, or a required watcher/origin is missing). Inspect with `coding_terminal_runner.py list --json`; relaunch through run_loaded_agent.py or confirm they are intentional diagnostics.")
    if counts.get("manager_asked", 0):
        issues.append({"kind": "manager_asked_operator", "count": counts["manager_asked"], "severity": "action_required"})
        actions.append("Run-manager posted operator questions for stalled runs. Answer with `coding_terminal_runner.py manage answer --manifest <path> --answer <text> --json`.")
    if counts.get("manager_awaiting_continuation", 0):
        issues.append({"kind": "manager_awaiting_continuation", "count": counts["manager_awaiting_continuation"], "severity": "action_required"})
        actions.append("Run-manager is awaiting continuation decisions for paused-but-resumable runs. Review the options and resume with `coding_terminal_runner.py manage answer --manifest <path> --answer <choice> --json`.")
    if counts.get("manager_failed", 0):
        issues.append({"kind": "manager_failed", "count": counts["manager_failed"], "severity": "action_required"})
        actions.append("Run-manager failed to act on some runs. Inspect manager_error in the run ledger and re-run `coding_terminal_runner.py manage scan --json`.")
    if counts.get("manager_needs_review", 0):
        issues.append({"kind": "manager_needs_review", "count": counts["manager_needs_review"], "severity": "warn"})
        actions.append("Some runs are marked needs_review by the run-manager. Inspect with `coding_terminal_runner.py manage status --json`.")

    blocking = [issue for issue in issues if issue.get("severity") == "action_required"]
    warnings = [issue for issue in issues if issue.get("severity") == "warn"]
    health = "action_required" if blocking else ("warn" if warnings else "ok")
    if health == "ok":
        summary = "Healthy. No managed or orphan coding terminals are open. Report routing is ready."
    elif health == "warn":
        summary = "Usable, but cleanup is recommended before the next run."
    else:
        summary = "Action required before trusting the next delegated coding-terminal run."
    return {
        "status": health,
        "summary": summary,
        "issues": issues,
        "recommended_actions": actions,
    }


def cmd_doctor(args: argparse.Namespace) -> dict:
    operator = cmd_operator_status(args)
    diagnosis = _doctor_from_operator_status(operator)
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    report_records = [_report_record(path) for path in _session_manifests(repo, artifact_root)]
    missing_reports = [
        {
            "manifest_path": report["manifest_path"],
            "runtime": report["runtime"],
            "session_label": report["session_label"],
            "missing": _report_missing_expected_copies(report),
        }
        for report in report_records
        if _report_missing_expected_copies(report)
    ]
    routing_failures = [
        {
            "manifest_path": report["manifest_path"],
            "runtime": report["runtime"],
            "session_label": report["session_label"],
            "routing_error": report["routing_error"],
            "local_report": report["local_report"],
        }
        for report in report_records
        if _report_current_routing_failure(report)
    ]
    historical_routing_failures = [
        {
            "manifest_path": report["manifest_path"],
            "runtime": report["runtime"],
            "session_label": report["session_label"],
            "routing_error": report["routing_error"],
            "local_report": report["local_report"],
        }
        for report in report_records
        if report.get("routing_status") == "failed" and not _report_current_routing_failure(report)
    ]
    if missing_reports:
        diagnosis["status"] = "action_required"
        diagnosis["summary"] = "Action required before trusting the next delegated coding-terminal run."
        diagnosis["issues"].append({"kind": "missing_report_copies", "count": len(missing_reports), "severity": "action_required"})
        diagnosis["recommended_actions"].append("Run `coding_terminal_runner.py reports repair --json` to backfill missing save-destination/raw or project report copies from surviving local reports.")
    if routing_failures:
        diagnosis["status"] = "action_required"
        diagnosis["summary"] = "Action required before trusting the next delegated coding-terminal run."
        diagnosis["issues"].append({"kind": "routing_failed", "count": len(routing_failures), "severity": "action_required"})
        fallback_paths = ", ".join(failure["local_report"] for failure in routing_failures if failure["local_report"]) or "the local reports dir"
        diagnosis["recommended_actions"].append(f"Report routing failed; the local report copy remains at {fallback_paths}. Fix the routing root, then run `coding_terminal_runner.py reports repair --json`.")
    return {
        **diagnosis,
        "repo": operator["repo"],
        "artifact_root": operator["artifact_root"],
        "operator_summary": operator["summary"],
        "route_preflight": operator["route_preflight"],
        "route_preflight_by_runtime": operator.get("route_preflight_by_runtime", {}),
        "runtime_home": operator["runtime_home"],
        "open_sessions": operator["open_sessions"],
        "orphan_tmux_sessions": operator["orphan_tmux_sessions"],
        "orphan_tmux_records": operator.get("orphan_tmux_records", []),
        "missing_report_copies": missing_reports[:10],
        "routing_failures": routing_failures[:10],
        "historical_routing_failures": historical_routing_failures[:10],
    }


def _managed_closeout_recovery_needed(session: dict) -> bool:
    managed = bool(session.get("managed_launcher") == "run_loaded_agent.py" or session.get("launch_origin") == "managed")
    terminalish = session.get("status") in {"closed", "finished", "waiting_for_input"} or session.get("manifest_status") in {"finished", "waiting_for_input"}
    if not managed or not terminalish:
        return False
    if session.get("closeout_status") != "structured":
        return True
    return session.get("manager_response_status") not in {"posted", "dry_run"}


def cmd_recover_closeouts(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if getattr(args, "repo", None) else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if getattr(args, "artifact_root", None) else None
    root, raw_sessions = _list_sessions(repo, artifact_root)
    operator = cmd_operator_status(argparse.Namespace(repo=str(repo), artifact_root=str(root), json=True))
    sessions_by_manifest = {session.get("manifest_path"): session for session in operator.get("latest_sessions", [])}
    candidates: list[dict] = []
    for session in raw_sessions:
        enriched = sessions_by_manifest.get(session.get("manifest_path"), session)
        if _managed_closeout_recovery_needed(enriched):
            candidates.append(enriched)
    max_runs = max(0, int(getattr(args, "limit", 20)))
    if max_runs:
        candidates = candidates[:max_runs]
    results: list[dict] = []
    ingress_args = argparse.Namespace(
        completion_ingress=True,
        completion_ingress_transport=getattr(args, "completion_ingress_transport", "auto"),
        completion_ingress_url=getattr(args, "completion_ingress_url", None),
        completion_ingress_secret=getattr(args, "completion_ingress_secret", None),
        completion_ingress_log=getattr(args, "completion_ingress_log", None),
    )
    for session in candidates:
        manifest_path = Path(session["manifest_path"]).resolve()
        item: dict = {"manifest_path": str(manifest_path), "dry_run": bool(getattr(args, "dry_run", False))}
        if getattr(args, "dry_run", False):
            item["would_run"] = ["closeout", "manage_once", "completion_ingress"]
            results.append(item)
            continue
        data = read_manifest(manifest_path)
        if data.get("closeout_status") != "structured":
            item["closeout"] = cmd_closeout(argparse.Namespace(
                manifest=str(manifest_path),
                wait=False,
                timeout=0,
                allow_snapshot_fallback=getattr(args, "allow_snapshot_fallback", False),
                json=True,
            ))
        item["manage"] = _manage_manifest_once(
            manifest_path,
            transport=getattr(args, "postback_transport", "file_log"),
            delivery_log=None,
            continuation_profile=getattr(args, "continuation_profile", "session"),
            dry_run=False,
            auto_answer=False,
            auto_continue=getattr(args, "auto_continue", False),
        )
        item["completion_ingress"] = _maybe_send_completion_ingress_for_manifest(manifest_path, ingress_args)
        results.append(item)
    return {
        "repo": str(repo),
        "artifact_root": str(root),
        "candidate_count": len(candidates),
        "recovered_count": 0 if getattr(args, "dry_run", False) else len(results),
        "results": results,
    }


def cmd_orphans(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root, sessions = _list_sessions(repo, artifact_root)
    orphan_names, external_managed = _split_unmanaged_tmux(sessions)
    records = [_tmux_session_details(name) for name in orphan_names]
    if args.session:
        wanted = set(args.session)
        records = [record for record in records if record["name"] in wanted]
    if args.orphans_command == "list":
        return {
            "repo": str(repo),
            "artifact_root": str(root),
            "count": len(records),
            "orphans": records,
            "external_managed": external_managed,
        }
    if args.orphans_command == "cleanup":
        if not args.dry_run and not args.yes:
            raise SystemExit("orphans cleanup requires --yes unless --dry-run is passed")
        cleaned: list[dict] = []
        for record in records:
            if args.dry_run:
                result = {"status": "dry_run", "tmux_session": record["name"]}
            else:
                completed = subprocess.run(["tmux", "kill-session", "-t", record["name"]], capture_output=True, text=True)
                result = {
                    "status": "closed" if completed.returncode == 0 else "failed",
                    "tmux_session": record["name"],
                    "returncode": completed.returncode,
                    "stderr": completed.stderr.strip(),
                }
            cleaned.append({**record, "cleanup_result": result})
        return {
            "repo": str(repo),
            "artifact_root": str(root),
            "dry_run": bool(args.dry_run),
            "cleaned_count": len(cleaned),
            "cleaned": cleaned,
        }
    raise SystemExit("orphans requires list or cleanup")


def _cleanup_preflight_blockers(tally: dict, *, requested_runtime: str | None = None) -> list[str]:
    blockers: list[str] = []
    needs_attention_count = len(tally.get("needs_attention") or [])
    unknown_count = len(tally.get("unknown") or [])
    if needs_attention_count:
        blockers.append(f"{needs_attention_count} managed session(s) need attention")
    if unknown_count:
        blockers.append(f"{unknown_count} open managed session(s) have unknown cleanup state")
    if requested_runtime:
        active_same_runtime = [
            row for row in (tally.get("active") or [])
            if row.get("runtime") == requested_runtime
        ]
        if len(active_same_runtime) >= MAX_ACTIVE_SESSIONS_PER_RUNTIME:
            blockers.append(
                f"{len(active_same_runtime)} active {requested_runtime} managed coding-terminal session(s); "
                f"limit is {MAX_ACTIVE_SESSIONS_PER_RUNTIME}"
            )
    return blockers


def _cleanup_stopped_from_sessions(
    *,
    repo: Path,
    root: Path,
    artifact_root: Path | None,
    sessions: list[dict],
    orphan_tmux: list[str],
    dry_run: bool,
    grace: float,
    activity_tally: dict | None = None,
    auto_only: bool = False,
) -> dict:
    ledger_rows = _read_ledger(_ledger_path_for_repo(repo, artifact_root))
    manager_status_by_manifest = {row.get("manifest_path"): row.get("manager_status") for row in ledger_rows}
    tally = activity_tally or _activity_tally(sessions, orphan_tmux)
    candidates_by_manifest = {
        row.get("manifest_path")
        for row in (tally.get("cleanup_candidates") or [])
        if row.get("manifest_path")
    }
    stopped = [
        session for session in sessions
        if session.get("manifest_path") in candidates_by_manifest
        and (session.get("terminal_cleanup_policy") or {}).get("cleanup_allowed") is True
        # Unattended callers (startup preflight) only close auto-clean-safe
        # sessions; inspection/policy-off sessions wait for explicit cleanup-stopped.
        and (not auto_only or (session.get("terminal_cleanup_policy") or {}).get("safe_for_auto_clean") is True)
    ]
    cleaned: list[dict] = []
    skipped = [session for session in sessions if session["tmux_exists"] and session not in stopped]
    skipped_question: list[dict] = []
    skipped_waiting_response: list[dict] = []
    for session in skipped:
        derived_state = session.get("derived_state")
        question_pending = (
            derived_state in (RunState.NEEDS_OPERATOR.value, RunState.AWAITING_CONTINUATION.value)
            and not session.get("derived_superseded_question")
        )
        if not question_pending:
            continue
        manager_status = manager_status_by_manifest.get(session["manifest_path"])
        if manager_status in {"asked_operator", "awaiting_continuation_decision"}:
            skip_reason = f"manager status is {manager_status}; waiting on operator"
        else:
            skip_reason = f"derived state is {derived_state}; waiting on operator"
        skipped_question.append({**session, "skip_reason": skip_reason})
    skipped_question_manifests = {row.get("manifest_path") for row in skipped_question}
    skipped = [session for session in skipped if session.get("manifest_path") not in skipped_question_manifests]
    for session in stopped:
        # Cleanup follows the canonical derived state: a pending operator
        # question or continuation decision keeps the session open, and the
        # supersession rule (newer structured closeout beats a stale question)
        # is a property of the derivation, not of this call site.
        derived_state = session.get("derived_state")
        question_pending = (
            derived_state in (RunState.NEEDS_OPERATOR.value, RunState.AWAITING_CONTINUATION.value)
            and not session.get("derived_superseded_question")
        )
        if question_pending:
            manager_status = manager_status_by_manifest.get(session["manifest_path"])
            if manager_status in {"asked_operator", "awaiting_continuation_decision"}:
                skip_reason = f"manager status is {manager_status}; waiting on operator"
            else:
                skip_reason = f"derived state is {derived_state}; waiting on operator"
            skipped_question.append({**session, "skip_reason": skip_reason})
            continue
        closeout_result: dict | None = None
        if (session.get("closeout_status") or "not_run") == "not_run":
            # Cleanup must not erase lifecycle truth: extract and route the final
            # report before killing the session, or the run is stomped to
            # `finished` with its report stranded in events.jsonl. Skip when no
            # final message exists so cleanup never manufactures needs_attention.
            data = read_manifest(Path(session["manifest_path"]))
            text, _source = _extract_final_message_source(data)
            if text:
                if dry_run:
                    closeout_result = {"status": "dry_run_closeout_pending"}
                else:
                    try:
                        closeout_result = cmd_closeout(argparse.Namespace(
                            manifest=session["manifest_path"],
                            wait=False,
                            timeout=0,
                            allow_snapshot_fallback=False,
                            json=True,
                        ))
                    except Exception as exc:
                        closeout_result = {"status": "closeout_error", "error": str(exc)}
        if (
            closeout_result
            and closeout_result.get("status") == "structured"
            and not _response_posted_to_hermes(_ledger_row_for_manifest(Path(session["manifest_path"])))
        ):
            skipped_waiting_response.append({
                **session,
                "closeout_result": closeout_result,
                "skip_reason": "closeout recovered; waiting for Hermes response before closing terminal",
            })
            continue
        if not dry_run:
            stop_result = cmd_stop(argparse.Namespace(manifest=session["manifest_path"], dry_run=False, grace=grace))
        else:
            stop_result = {"status": "dry_run", "manifest_path": session["manifest_path"], "tmux_session": session["tmux_session"]}
        cleaned.append({**session, "closeout_result": closeout_result, "stop_result": stop_result})
    return {
        "repo": str(repo),
        "artifact_root": str(root),
        "dry_run": bool(dry_run),
        "activity_tally": tally,
        "cleaned_count": len(cleaned),
        "skipped_open_count": len(skipped),
        "skipped_question_count": len(skipped_question),
        "skipped_waiting_response_count": len(skipped_waiting_response),
        "orphan_tmux_count": len(orphan_tmux),
        "orphan_tmux_sessions": orphan_tmux,
        "cleaned": cleaned,
        "skipped_open": skipped,
        "skipped_question": skipped_question,
        "skipped_waiting_response": skipped_waiting_response,
    }


def cmd_cleanup_stopped(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root, sessions = _list_sessions(repo, artifact_root)
    orphan_tmux = _orphan_tmux_sessions(sessions)
    tally = _activity_tally(sessions, orphan_tmux)
    return _cleanup_stopped_from_sessions(
        repo=repo,
        root=root,
        artifact_root=artifact_root,
        sessions=sessions,
        orphan_tmux=orphan_tmux,
        dry_run=bool(args.dry_run),
        grace=args.grace,
        activity_tally=tally,
    )


def cmd_cleanup_preflight(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root, sessions = _list_sessions(repo, artifact_root)
    orphan_tmux = _orphan_tmux_sessions(sessions)
    tally = _activity_tally(sessions, orphan_tmux)
    cleanup = _cleanup_stopped_from_sessions(
        repo=repo,
        root=root,
        artifact_root=artifact_root,
        sessions=sessions,
        orphan_tmux=orphan_tmux,
        dry_run=bool(args.dry_run),
        grace=args.grace,
        activity_tally=tally,
        auto_only=True,
    )
    blockers = _cleanup_preflight_blockers(tally, requested_runtime=getattr(args, "runtime", None))
    return {
        **cleanup,
        "status": "launch_blocked" if blockers else "launch_allowed",
        "launch_allowed": not blockers,
        "blockers": blockers,
    }


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def cmd_prune(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    root, sessions = _list_sessions(repo, artifact_root)
    candidates = _prune_candidates(sessions, older_than_days=args.older_than_days)
    apply = bool(args.yes) and not args.dry_run
    results: list[dict] = []
    for candidate in candidates:
        removed = False
        if apply:
            shutil.rmtree(candidate["session_dir"], ignore_errors=True)
            removed = not Path(candidate["session_dir"]).exists()
        results.append({**candidate, "removed": removed})
    return {
        "repo": str(repo),
        "artifact_root": str(root),
        "older_than_days": args.older_than_days,
        "dry_run": not apply,
        "applied": apply,
        "candidate_count": len(candidates),
        "removed_count": sum(1 for result in results if result["removed"]),
        "freed_bytes": sum(candidate["size_bytes"] for candidate in candidates),
        "candidates": results,
    }


# `cleanup-closed` is the documented alias for `prune`.
cmd_cleanup_closed = cmd_prune


SELFTEST_CORE_COMMANDS = [
    "start", "send", "snapshot", "status", "watch", "closeout", "stop",
    "list", "reports", "postback", "operator_status", "doctor", "orphans",
    "cleanup_stopped", "prune", "manage",
]


def _selftest_loadout_validation() -> dict:
    try:
        loadouts = load_loadouts(ROOT)
        errors = validate_loadouts(loadouts=loadouts, repo_root=ROOT)
        return {"name": "loadout_validation", "passed": not errors, "detail": "loadouts valid" if not errors else "; ".join(errors[:5])}
    except Exception as exc:  # pragma: no cover - defensive
        return {"name": "loadout_validation", "passed": False, "detail": f"validation crashed: {exc}"}


def _selftest_command_inventory() -> dict:
    missing = [name for name in SELFTEST_CORE_COMMANDS if f"cmd_{name}" not in globals()]
    return {"name": "command_inventory", "passed": not missing, "detail": "all core commands present" if not missing else f"missing: {missing}"}


def _selftest_route_preflight(repo: Path, root: Path) -> dict:
    preflight = _route_preflight(default_routes(artifact_root=root, repo_path=repo, project_slug=repo.name))
    warnings = preflight.get("warnings") or []
    return {"name": "obsidian_route_preflight", "passed": not warnings, "detail": "obsidian routing ready" if not warnings else "; ".join(warnings)}


def _selftest_clean_lifecycle(operator: dict) -> dict:
    summary = operator.get("summary") or {}
    problems = {key: summary.get(key, 0) for key in ("active", "needs_attention", "orphan_tmux") if summary.get(key, 0)}
    return {"name": "clean_lifecycle", "passed": not problems, "detail": "no active/needs_attention/orphan sessions" if not problems else f"open/problem sessions: {problems}"}


def _selftest_report_repair(repo: Path, artifact_root: Path | None) -> dict:
    records = [_report_record(path) for path in _session_manifests(repo, artifact_root)]
    drifted = [record for record in records if _report_missing_expected_copies(record)]
    return {"name": "report_repair_dry_run", "passed": not drifted, "detail": "no report drift" if not drifted else f"{len(drifted)} session(s) need `reports repair --dry-run`"}


def _selftest_runtime_hooks() -> dict:
    failures: list[str] = []
    for runtime in KNOWN_RUNTIMES:
        command = _runtime_event_command(manifest_path=Path("<manifest>"), runtime=runtime, event="Stop", status="waiting_for_input")
        if "record_runtime_event.py" not in command or "--event Stop" not in command:
            failures.append(runtime)
    return {"name": "runtime_hook_configuration", "passed": not failures, "detail": "stop-hook command builds for claude and codex" if not failures else f"hook build failed for: {failures}"}


def cmd_selftest(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else None
    operator = cmd_operator_status(args)
    root = Path(operator["artifact_root"])
    checks = [
        _selftest_loadout_validation(),
        _selftest_command_inventory(),
        _selftest_route_preflight(repo, root),
        _selftest_clean_lifecycle(operator),
        _selftest_report_repair(repo, artifact_root),
        _selftest_runtime_hooks(),
    ]
    failed = [check for check in checks if not check["passed"]]
    return {
        "repo": str(repo),
        "artifact_root": str(root),
        "checks": checks,
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "status": "pass" if not failed else "fail",
    }


# `release-check` is the documented alias for `selftest`.
cmd_release_check = cmd_selftest


def _read_latest_output_for_manage(data: dict) -> str:
    """Best-effort extraction of latest terminal output for stall/question classification."""
    # 1. Latest snapshot file
    snap = (data.get("artifacts") or {}).get("latest_snapshot")
    if snap and Path(snap).exists():
        try:
            return Path(snap).read_text(errors="replace")[-4000:]
        except OSError:
            pass
    # 2. Events.jsonl — last assistant message
    msg = _message_from_event(_latest_event_from_events_jsonl(data))
    if msg:
        return msg[-4000:]
    return ""


# ── Phase B helpers: owner resolution and row filtering ──────────────────────

def _resolve_scan_owner(args: argparse.Namespace) -> tuple[str | None, str | None, str | None]:
    """Resolve owner identity while avoiding stale ambient cross-session scope.

    Explicit flags win. Environment fallback fills omitted fields, except a
    supplied --hermes-session-id is treated as the precise lane and suppresses
    ambient HERMES_SESSION_THREAD_ID so another Discord/Hermes surface cannot
    accidentally narrow the scan.
    """
    explicit_launcher = getattr(args, "owner", None) or None
    explicit_thread_id = getattr(args, "thread_id", None) or None
    explicit_session_id = getattr(args, "hermes_session_id", None) or None
    launcher = explicit_launcher or os.environ.get("HERMES_MANAGED_LAUNCHER") or None
    thread_id = explicit_thread_id or (None if explicit_session_id else os.environ.get("HERMES_SESSION_THREAD_ID") or None)
    session_id = explicit_session_id or os.environ.get("HERMES_SESSION_ID") or None
    return launcher, thread_id, session_id


def _row_matches_owner(
    row: dict,
    owner_launcher: str | None,
    owner_thread_id: str | None,
    owner_session_id: str | None = None,
    *,
    include_unowned: bool = False,
) -> bool:
    """Return True if this row belongs to the resolved owner.

    Owned = launch_origin=="managed" AND managed_launcher matches AND
    (if owner_thread_id set) discord_thread_id matches AND
    (if owner_session_id set) hermes_session_id matches.
    Rows with launch_origin=="manual" or empty managed_launcher are unowned;
    pass include_unowned=True to include them.
    """
    launch_origin = row.get("launch_origin") or ""
    row_launcher = row.get("managed_launcher") or ""

    if launch_origin == "manual" or not row_launcher:
        if not include_unowned:
            return False
        if owner_thread_id:
            row_thread = row.get("discord_thread_id") or ""
            if row_thread != owner_thread_id:
                return False
        if owner_session_id:
            row_session = row.get("hermes_session_id") or ""
            if row_session != owner_session_id:
                return False
        return True

    if owner_launcher and row_launcher != owner_launcher:
        return False

    if owner_thread_id:
        row_thread = row.get("discord_thread_id") or ""
        if row_thread != owner_thread_id:
            return False

    if owner_session_id:
        row_session = row.get("hermes_session_id") or ""
        if row_session != owner_session_id:
            return False

    return True


def _store_continuation_fields(row: dict, classification: dict, recommendation: dict, *, pending: bool) -> None:
    row["manager_continuation_options"] = list(classification.get("continuation_options") or [])
    row["manager_continuation_checkpoint"] = classification.get("continuation_checkpoint", "")
    row["manager_continuation_confidence"] = classification.get("confidence", "")
    row["manager_continuation_recommendation"] = recommendation.get("recommendation", "")
    row["manager_continuation_band"] = recommendation.get("band", "")
    row["manager_continuation_pending"] = pending


def _safe_packet_stem(row: dict) -> str:
    label = row.get("session_label") or Path(row.get("manifest_path") or "run").parent.name or "run"
    safe = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in str(label)).strip("-") or "run"
    return f"{safe}-{(row.get('run_id') or '')[:8]}".rstrip("-")


def _write_manager_response_packet(packet: dict, responses_dir: Path, stem: str) -> Path:
    responses_dir.mkdir(parents=True, exist_ok=True)
    path = responses_dir / f"{stem}-manager-response.json"
    path.write_text(json.dumps(packet, indent=2, sort_keys=True))
    return path


def _record_manager_response(
    row: dict,
    *,
    kind: str,
    message_id: str,
    transport: str,
    manifest_path: str,
    responses_dir: Path | None = None,
    data: dict | None = None,
    classification: dict | None = None,
    sections: dict | None = None,
    message: str = "",
) -> None:
    row["manager_response_status"] = "posted" if message_id and message_id != "dry_run" else "dry_run"
    row["manager_response_kind"] = kind
    row["manager_response_message_id"] = message_id
    row["manager_response_transport"] = transport
    row["manager_response_manifest_path"] = manifest_path
    row["manager_response_recorded_at"] = _now_iso()
    if row["manager_response_status"] == "posted":
        row["terminal_response_state"] = "ready_to_close"
        row["terminal_ready_to_close"] = True
        row["terminal_response_reason"] = "Hermes response posted; terminal may be closed by safe cleanup"
    else:
        row["terminal_response_state"] = "response_dry_run"
        row["terminal_ready_to_close"] = False
        row["terminal_response_reason"] = "manager response was a dry run; do not close unattended"
    if responses_dir is not None:
        packet = build_manager_response_packet(
            row, data or {}, classification or {}, message, kind=kind, sections=sections or {}
        )
        packet["message_id"] = message_id
        packet["transport"] = transport
        packet["recorded_at"] = row["manager_response_recorded_at"]
        packet_path = _write_manager_response_packet(packet, responses_dir, _safe_packet_stem(row))
        row["manager_response_packet_path"] = str(packet_path)


def _manage_review_continuation(
    row: dict,
    data: dict,
    sections: dict,
    classification: dict,
    *,
    manifest_value: str,
    transport: str,
    delivery_log: Path,
    dry_run: bool,
    auto_continue: bool,
    responses_dir: Path | None = None,
) -> dict:
    """Review a waiting_for_continuation checkpoint: summarize, recommend, route.

    Never calls cleanup/stop — the terminal must stay alive to be resumable.
    Fails closed on delivery errors. Auto-continue is opt-in and bounded.
    """
    context = data.get("conversation_context") or row.get("conversation_context") or {}
    goal = context.get("conversation_goal") or context.get("user_request") or ""
    options = list(classification.get("continuation_options") or [])
    recommendation = recommend_continuation(options, goal)
    confidence = classification.get("confidence") or "medium"
    message = build_manager_continuation_decision_message(row, sections, classification)

    # ── Opt-in auto-continue: only safe-operational + high confidence ────────
    tmux_session = data.get("tmux_session") or ""
    tmux_exists = bool(tmux_session) and not data.get("dry_run") and session_exists(tmux_session)
    if (
        auto_continue
        and not dry_run
        and confidence == "high"
        and recommendation["band"] == "safe-operational"
        and tmux_exists
    ):
        manifest_path = Path(manifest_value)
        original_status = data.get("status")
        original_resumed_at = data.get("continuation_resumed_at")
        watcher_restart_status: dict = {"attempted": False}
        try:
            transition_manifest_status(
                data, "working",
                reason="manager auto-continue resumed the run", actor="manage.auto_continue",
            )
            data["continuation_resumed_at"] = _now_iso()
            save_manifest(manifest_path, data)
            send_literal_prompt(tmux_session, recommendation["recommendation"], enter_count=2)
        except Exception as exc:
            # Resume failed; restore the durable paused lifecycle so the operator
            # can still answer/retry. This closes the race where tmux disappears
            # after session_exists() but before the prompt send completes.
            try:
                transition_manifest_status(
                    data, original_status,
                    reason="auto-continue send failed; restoring paused status", actor="manage.auto_continue",
                )
                if original_resumed_at is None:
                    data.pop("continuation_resumed_at", None)
                else:
                    data["continuation_resumed_at"] = original_resumed_at
                save_manifest(manifest_path, data)
            except Exception as restore_exc:
                row["_auto_continue_restore_error"] = str(restore_exc)
            # Fall through to operator routing.
            row["_auto_continue_error"] = str(exc)
        else:
            existing_watcher = dict(data.get("watcher") or {})
            if existing_watcher:
                watcher_restart_status["attempted"] = True
                try:
                    restart_result = cmd_watch_start(_watcher_restart_namespace(manifest_path, existing_watcher))
                except Exception as exc:
                    watcher_restart_status.update({"ok": False, "error": str(exc)})
                else:
                    watcher_restart_status.update({"ok": True, "result": restart_result})
            # Resumed. Record the action for visibility; a record-delivery
            # failure must not undo the (already sent) resume.
            try:
                _send_postback(
                    row, message, transport=transport, delivery_log=delivery_log,
                    kind="manager_continuation_auto",
                )
            except PostbackDeliveryError as exc:
                row["manager_continuation_record_error"] = str(exc)
            row = apply_manager_fields(
                row, manager_status="answered_runtime", classification=classification,
                message_id="auto_continue", transport="tmux_send",
            )
            _store_continuation_fields(row, classification, recommendation, pending=False)
            row["manager_watcher_restart_status"] = watcher_restart_status
            row["_manage_action"] = f"auto_continued: {recommendation['recommendation']!r}"
            return row

    # ── Default: post the decision and wait for the operator ─────────────────
    if dry_run:
        row = apply_manager_fields(
            row, manager_status="awaiting_continuation_decision",
            classification=classification, message_id="dry_run", transport="dry_run",
        )
        _record_manager_response(
            row, kind="manager_continuation_decision", message_id="dry_run",
            transport="dry_run", manifest_path=manifest_value,
            responses_dir=responses_dir, data=data, classification=classification,
            sections=sections, message=message,
        )
        _store_continuation_fields(row, classification, recommendation, pending=True)
        row["_manage_action"] = "continuation_dry_run"
        row["_manage_message"] = message
        return row
    try:
        message_id, resolved_transport = _send_postback(
            row, message, transport=transport, delivery_log=delivery_log,
            kind="manager_continuation_decision",
        )
    except PostbackDeliveryError as exc:
        # Delivery failed: do NOT cleanup or resume — leave the terminal open.
        return apply_manager_fields(row, manager_status="failed", error=f"continuation delivery: {exc}")
    row = apply_manager_fields(
        row, manager_status="awaiting_continuation_decision", classification=classification,
        message_id=message_id, transport=resolved_transport,
    )
    _record_manager_response(
        row, kind="manager_continuation_decision", message_id=message_id,
        transport=resolved_transport, manifest_path=manifest_value,
        responses_dir=responses_dir, data=data, classification=classification,
        sections=sections, message=message,
    )
    _store_continuation_fields(row, classification, recommendation, pending=True)
    row["_manage_action"] = "awaiting_continuation_decision"
    return row


def _question_superseded_by_closeout(row: dict) -> bool:
    """True when a pending operator question predates a structured closeout.

    The supersession rule itself lives in `resolve_run_state`; this helper only
    feeds it the manifest for a ledger row."""
    manifest_value = row.get("manifest_path")
    if not manifest_value or not Path(manifest_value).exists():
        return False
    try:
        data = read_manifest(Path(manifest_value))
    except Exception:
        return False
    return resolve_run_state(data, ledger_row=row).superseded_question


def _manage_scan_row(
    row: dict,
    *,
    repo: Path,
    transport: str,
    delivery_log: Path,
    continuation_profile: str,
    dry_run: bool,
    auto_answer: bool = False,
    auto_continue: bool = False,
) -> dict:
    """Classify and act on a single ledger row. Idempotent."""
    responses_dir = delivery_log.parent / "responses"
    manager_status = row.get("manager_status") or "not_ready"
    # Idempotency: already in a terminal manager state, skip — except a pending
    # operator question whose classification basis has been superseded by a
    # later structured closeout. That row must re-classify from the fresh
    # closeout truth, or the obsolete question blocks cleanup/launches forever.
    if manager_status in (
        "continued",
        "answered_runtime",
        "awaiting_continuation_decision",
    ):
        return {**row, "_manage_action": "skipped_idempotent"}
    if manager_status == "asked_operator":
        if not _question_superseded_by_closeout(row):
            return {**row, "_manage_action": "skipped_idempotent"}
        row = {**row, "manager_pending_question": ""}

    manifest_value = row.get("manifest_path")
    if not manifest_value or not Path(manifest_value).exists():
        return apply_manager_fields(row, manager_status="failed", error="manifest not found")

    try:
        data = read_manifest(Path(manifest_value))
    except Exception as exc:
        return apply_manager_fields(row, manager_status="failed", error=f"manifest unreadable: {exc}")

    # Stale-turn guard: skip if a newer prompt turn has started since this closeout
    current_prompt_id = data.get("current_prompt_id")
    last_event_prompt_id = (data.get("last_runtime_event") or {}).get("prompt_id")
    if current_prompt_id and last_event_prompt_id and current_prompt_id != last_event_prompt_id:
        row = apply_manager_fields(row, manager_status="classified")
        row["_manage_action"] = "keep_open:stale_turn"
        return row

    latest_output = _read_latest_output_for_manage(data)

    # Parse the saved report once: classify_run needs the text (for the
    # continuation sentinel) and the action branches need the parsed sections.
    report_path = row.get("report_path") or ""
    report_text = ""
    sections: dict[str, str] = {}
    if report_path and Path(report_path).exists():
        try:
            report_text = Path(report_path).read_text(errors="replace")
            sections = _parse_sections(report_text)
        except OSError:
            pass

    classification = classify_run(
        data, row, latest_output=latest_output or None, report_text=report_text or None
    )

    # Phase 1: mark classified, store classification fields
    row = apply_manager_fields(row, manager_status="classified", classification=classification)

    action = classification["action"]

    # Continuation: clean checkpoint, more work, decision pending. NEVER cleanup.
    if action == "review_continuation" and classification["classification"] == "waiting_for_continuation":
        return _manage_review_continuation(
            row, data, sections, classification,
            manifest_value=manifest_value, transport=transport,
            delivery_log=delivery_log, dry_run=dry_run, auto_continue=auto_continue,
            responses_dir=responses_dir,
        )

    # Phase 2: finished_clean -> rich continuation + cleanup (delivery before cleanup)
    if action == "post_continuation" and classification["classification"] == "finished_clean":
        # Determine cleanup eligibility — do NOT act yet; cleanup only after delivery
        watcher = cmd_watch_status(argparse.Namespace(manifest=manifest_value))
        tmux_session = data.get("tmux_session") or ""
        tmux_exists = bool(tmux_session) and not data.get("dry_run") and session_exists(tmux_session)
        watcher_state = watcher.get("watcher_status", "not_running")
        _, auto_cleanup_safe, _ = _classify_session(
            data, tmux_exists=tmux_exists, watcher_status=watcher_state,
            runtime_event_failed=_events_recording_failed(Path(manifest_value)),
        )
        closeout_policy = _manifest_closeout_policy(data)
        policy_blocked_reason = ""
        if closeout_policy["keep_open_after_closeout"]:
            policy_blocked_reason = closeout_policy["keep_open_reason"] or "keep-open policy active"
        elif not closeout_policy["cleanup_after_response"]:
            policy_blocked_reason = f"cleanup_after_response disabled by closeout policy (policy_source={closeout_policy['policy_source']})"

        # Build message before cleanup so the message reflects pre-cleanup state.
        # Include manifest-only proof fields (visible desktop proof, closeout policy)
        # that are intentionally too bulky for the durable run ledger.
        message = build_manager_continuation_message({**data, **row}, sections)
        if dry_run:
            cleanup_result: dict | None = {"cleaned": False, "dry_run": True} if auto_cleanup_safe else None
            row = apply_manager_fields(
                row, manager_status="continued", cleanup_result=cleanup_result,
                message_id="dry_run", transport="dry_run",
            )
            _record_manager_response(
                row, kind="manager_continuation", message_id="dry_run",
                transport="dry_run", manifest_path=manifest_value,
                responses_dir=responses_dir, data=data, classification=classification,
                sections=sections, message=message,
            )
            row["_manage_action"] = "continuation_dry_run"
            row["_manage_message"] = message
            return row
        try:
            message_id, resolved_transport = _send_postback(
                row, message, transport=transport, delivery_log=delivery_log, kind="manager_continuation"
            )
        except PostbackDeliveryError as exc:
            # Delivery failed: do NOT cleanup terminal — leave it open
            return apply_manager_fields(row, manager_status="failed", error=f"continuation delivery: {exc}")
        # Delivery confirmed — now safe to cleanup
        cleanup_result = None
        if auto_cleanup_safe and policy_blocked_reason:
            cleanup_result = {
                "cleaned": False,
                "policy_blocked": True,
                "reason": policy_blocked_reason,
                "cleanup_mode": closeout_policy["cleanup_mode"],
            }
        elif auto_cleanup_safe and closeout_policy["cleanup_dry_run"]:
            cleanup_result = {"cleaned": False, "dry_run": True}
        elif auto_cleanup_safe:
            try:
                stop_result = cmd_stop(argparse.Namespace(
                    manifest=manifest_value, dry_run=False,
                    grace=closeout_policy["cleanup_grace_seconds"],
                ))
                cleanup_result = {"cleaned": True, "status": stop_result.get("status")}
            except Exception as exc:
                cleanup_result = {"cleaned": False, "error": str(exc)}
        row = apply_manager_fields(
            row, manager_status="continued", message_id=message_id, transport=resolved_transport,
            cleanup_result=cleanup_result,
        )
        # The manager continuation is the lifecycle completion report for a clean
        # run. Clear any stale human-continuation delivery error left by earlier
        # overlong Discord attempts so operator-status does not keep reporting a
        # resolved run as pending/failed.
        row["continuation_status"] = "posted"
        row["continuation_message_id"] = message_id
        row["continuation_posted_at"] = row.get("manager_last_attempt_at") or _now_iso()
        row["continuation_transport"] = resolved_transport
        row.pop("continuation_error", None)
        _record_manager_response(
            row,
            kind="manager_continuation",
            message_id=message_id,
            transport=resolved_transport,
            manifest_path=manifest_value,
            responses_dir=responses_dir,
            data=data,
            classification=classification,
            sections=sections,
            message=message,
        )
        row["_manage_action"] = "continued"
        return row

    # Phase 3: question/blocked -> inspect and route to operator (or auto-answer)
    if action == "ask_operator":
        question = classification.get("extracted_question") or ""
        auto_answer_text, auto_reason = try_auto_answer(question)

        # Phase 5: safe auto-answer — opt-in only (requires auto_answer=True)
        if auto_answer and auto_answer_text and not dry_run:
            try:
                send_literal_prompt(data["tmux_session"], auto_answer_text, enter_count=2)
                row = apply_manager_fields(
                    row, manager_status="answered_runtime",
                    classification={**classification, "classification": "answerable_question"},
                    message_id="auto", transport="tmux_send",
                    pending_question=question,
                )
                row["_manage_action"] = f"auto_answered: {auto_answer_text!r}"
                return row
            except Exception as exc:
                # Auto-answer failed; fall through to operator routing
                row["_auto_answer_error"] = str(exc)

        # Phase 3: route to operator
        message = build_manager_question_message(row, question, classification=classification["classification"], reason=classification["reason"])
        if dry_run:
            row = apply_manager_fields(row, manager_status="asked_operator", pending_question=question, message_id="dry_run", transport="dry_run")
            _record_manager_response(
                row, kind="manager_question", message_id="dry_run",
                transport="dry_run", manifest_path=manifest_value,
                responses_dir=responses_dir, data=data, classification=classification,
                message=message,
            )
            row["_manage_action"] = "question_dry_run"
            row["_manage_message"] = message
            return row
        try:
            message_id, resolved_transport = _send_postback(
                row, message, transport=transport, delivery_log=delivery_log, kind="manager_question"
            )
        except PostbackDeliveryError as exc:
            return apply_manager_fields(row, manager_status="failed", error=f"question delivery: {exc}")
        row = apply_manager_fields(
            row, manager_status="asked_operator", pending_question=question,
            message_id=message_id, transport=resolved_transport,
        )
        _record_manager_response(
            row, kind="manager_question", message_id=message_id,
            transport=resolved_transport, manifest_path=manifest_value,
            responses_dir=responses_dir, data=data, classification=classification,
            message=message,
        )
        row["_manage_action"] = "asked_operator"
        return row

    # Needs manual review or keep_open
    if action == "needs_manual_review":
        continuation_outcome = None
        if row.get("continuation_status") != "posted":
            continuation_outcome = _maybe_send_continuation(
                row,
                repo=repo,
                transport=transport,
                delivery_log=delivery_log,
                profile=continuation_profile,
            )
            if continuation_outcome == "failed":
                return apply_manager_fields(
                    row,
                    manager_status="failed",
                    classification=classification,
                    error=f"manual-review continuation delivery: {row.get('continuation_error') or 'unknown error'}",
                )
        row = apply_manager_fields(row, manager_status="needs_review")
        row["_manage_action"] = "needs_review"
        if continuation_outcome:
            row["_manage_continuation_outcome"] = continuation_outcome
        return row

    row = apply_manager_fields(row, manager_status="classified")
    row["_manage_action"] = f"keep_open:{action}"
    return row


def _manage_manifest_once(
    manifest_path: Path,
    *,
    transport: str,
    delivery_log: Path | None,
    continuation_profile: str,
    dry_run: bool,
    auto_answer: bool = False,
    auto_continue: bool = False,
) -> dict:
    """Classify/act on exactly one manifest-backed run.

    This is the efficient watcher hot path: the watcher already knows which
    manifest reached a terminal/question state, so avoid broad owner-scoped
    ledger scans.
    """
    manifest_path = manifest_path.resolve()
    data = read_manifest(manifest_path)
    repo, artifact_root = _postback_repo_from_manifest(manifest_path)
    ledger_path = _ledger_path_for_repo(repo, artifact_root)
    if not dry_run:
        _upsert_ledger_row(repo, manifest_path, data, artifact_root=artifact_root)
    rows = _read_ledger(ledger_path)
    manifest_key = str(manifest_path)
    idx = next((i for i, row in enumerate(rows) if row.get("manifest_path") == manifest_key), None)
    if idx is None:
        row = {
            "run_id": _ledger_id(manifest_path),
            "manifest_path": manifest_key,
            "session_label": data.get("session_label"),
            "runtime": data.get("runtime"),
            "loadout": data.get("loadout"),
            "status": data.get("status"),
            "closeout_status": data.get("closeout_status") or "not_run",
        }
        rows.append(row)
        idx = len(rows) - 1
    delivery_path = delivery_log or ledger_path.with_name("postback-deliveries.jsonl")
    updated = _manage_scan_row(
        rows[idx],
        repo=repo,
        transport=transport,
        delivery_log=delivery_path,
        continuation_profile=continuation_profile,
        dry_run=dry_run,
        auto_answer=auto_answer,
        auto_continue=auto_continue,
    )
    rows[idx] = {k: v for k, v in updated.items() if not k.startswith("_")}
    if not dry_run:
        _write_ledger(ledger_path, rows)
    return {
        "repo": str(repo),
        "ledger_path": str(ledger_path),
        "manifest_path": manifest_key,
        "dry_run": dry_run,
        "result": updated,
    }


def cmd_manage(args: argparse.Namespace) -> dict:
    manage_command = args.manage_command

    # ── manage status ────────────────────────────────────────────────────────
    if manage_command == "status":
        repo = Path(args.repo).resolve() if getattr(args, "repo", None) else Path.cwd().resolve()
        artifact_root = Path(args.artifact_root).resolve() if getattr(args, "artifact_root", None) else None
        ledger_path = _ledger_path_for_repo(repo, artifact_root)
        rows = _read_ledger(ledger_path)
        counts: dict[str, int] = {}
        for row in rows:
            ms = row.get("manager_status") or "not_ready"
            counts[ms] = counts.get(ms, 0) + 1
        asked = [row for row in rows if row.get("manager_status") == "asked_operator"]
        needs_review = [row for row in rows if row.get("manager_status") == "needs_review"]
        return {
            "repo": str(repo),
            "ledger_path": str(ledger_path),
            "manager_counts": counts,
            "total": len(rows),
            "asked_operator": asked,
            "needs_review": needs_review,
        }

    # ── manage classify ──────────────────────────────────────────────────────
    if manage_command == "classify":
        manifest_path = Path(args.manifest).resolve()
        data = read_manifest(manifest_path)
        repo = Path(data.get("repo_path") or Path.cwd()).resolve()
        ledger_path = _ledger_path_for_repo(repo)
        rows = _read_ledger(ledger_path)
        manifest_key = str(manifest_path)
        row = next((r for r in rows if r.get("manifest_path") == manifest_key), {})
        if not row:
            row = {"manifest_path": manifest_key, "run_id": _ledger_id(manifest_path)}
        latest_output = _read_latest_output_for_manage(data)
        report_text = ""
        report_path = row.get("report_path") or data.get("latest_closeout_report") or data.get("latest_report") or ""
        if report_path and Path(report_path).exists():
            try:
                report_text = Path(report_path).read_text(errors="replace")
            except OSError:
                report_text = ""
        result = classify_run(
            data,
            row,
            latest_output=latest_output or None,
            report_text=report_text or None,
        )
        return {
            "manifest_path": manifest_key,
            "manifest_status": data.get("status"),
            "closeout_status": data.get("closeout_status"),
            "has_blockers": data.get("report_has_blockers"),
            **result,
        }

    # ── manage once ──────────────────────────────────────────────────────────
    if manage_command == "once":
        delivery_log = Path(args.delivery_log).resolve() if getattr(args, "delivery_log", None) else None
        return _manage_manifest_once(
            Path(args.manifest),
            transport=getattr(args, "transport", "file_log"),
            delivery_log=delivery_log,
            continuation_profile=getattr(args, "continuation_profile", "session") or "session",
            dry_run=bool(getattr(args, "dry_run", False)),
            auto_answer=bool(getattr(args, "auto_answer", False)),
            auto_continue=bool(getattr(args, "auto_continue", False)),
        )

    # ── manage scan ──────────────────────────────────────────────────────────
    if manage_command == "scan":
        repo = Path(args.repo).resolve() if getattr(args, "repo", None) else Path.cwd().resolve()
        artifact_root = Path(args.artifact_root).resolve() if getattr(args, "artifact_root", None) else None
        ledger_path = _ledger_path_for_repo(repo, artifact_root)
        rows = _read_ledger(ledger_path)
        delivery_log = Path(args.delivery_log).resolve() if getattr(args, "delivery_log", None) else ledger_path.with_name("postback-deliveries.jsonl")
        transport = getattr(args, "transport", "file_log")
        dry_run = bool(getattr(args, "dry_run", False))
        continuation_profile = getattr(args, "continuation_profile", "session") or "session"
        auto_answer = bool(getattr(args, "auto_answer", False))
        auto_continue = bool(getattr(args, "auto_continue", False))
        include_all = bool(getattr(args, "include_all", False))
        include_unowned = bool(getattr(args, "include_unowned", False))

        # Resolve owner — fail closed if no owner scope and --include-all not passed
        owner_launcher, owner_thread_id, owner_session_id = _resolve_scan_owner(args)
        if not owner_launcher and not owner_thread_id and not owner_session_id and not include_all:
            return {
                "repo": str(repo),
                "ledger_path": str(ledger_path),
                "dry_run": dry_run,
                "rows_scanned": 0,
                "total": 0,
                "by_action": {},
                "results": [],
                "warning": (
                    "manage scan requires --owner or HERMES_MANAGED_LAUNCHER / "
                    "HERMES_SESSION_THREAD_ID env; pass --include-all to scan all rows"
                ),
            }

        results: list[dict] = []
        for row in rows:
            if not include_all and not _row_matches_owner(
                row, owner_launcher, owner_thread_id, owner_session_id, include_unowned=include_unowned
            ):
                results.append({**row, "_manage_action": "skipped_owner_filter"})
                continue
            updated = _manage_scan_row(
                row,
                repo=repo,
                transport=transport,
                delivery_log=delivery_log,
                continuation_profile=continuation_profile,
                dry_run=dry_run,
                auto_answer=auto_answer,
                auto_continue=auto_continue,
            )
            results.append(updated)
        if not dry_run and results:
            _write_ledger(ledger_path, [{k: v for k, v in r.items() if not k.startswith("_")} for r in results])
        by_action: dict[str, int] = {}
        for row in results:
            action = row.get("_manage_action", "unknown")
            by_action[action] = by_action.get(action, 0) + 1
        return {
            "repo": str(repo),
            "ledger_path": str(ledger_path),
            "dry_run": dry_run,
            "total": len(results),
            "by_action": by_action,
            "results": results,
        }

    # ── manage answer (Phase 4) ──────────────────────────────────────────────
    if manage_command == "answer":
        manifest_path = Path(args.manifest).resolve()
        data = read_manifest(manifest_path)
        repo = Path(data.get("repo_path") or Path.cwd()).resolve()
        ledger_path = _ledger_path_for_repo(repo)
        rows = _read_ledger(ledger_path)
        manifest_key = str(manifest_path)
        idx = next((i for i, r in enumerate(rows) if r.get("manifest_path") == manifest_key), None)
        row = rows[idx] if idx is not None else {}

        answer_text: str = ""
        if getattr(args, "answer", None):
            answer_text = args.answer
        elif getattr(args, "answer_file", None):
            answer_text = Path(args.answer_file).read_text(encoding="utf-8").strip()
        if not answer_text:
            raise SystemExit("manage answer requires --answer or --answer-file")

        dry_run = bool(getattr(args, "dry_run", False))
        watcher_restart_status: dict = {"attempted": False}
        if not dry_run:
            # Same-session guarantee: resume only the manifest's tmux session; if
            # it no longer exists, fail closed rather than spawning a new one.
            tmux_session = data.get("tmux_session") or ""
            if not tmux_session or not session_exists(tmux_session):
                raise SystemExit(
                    f"manage answer: tmux session {tmux_session!r} does not exist — "
                    "cannot resume (fail closed)"
                )
            original_status = data.get("status")
            original_resumed_at = data.get("continuation_resumed_at")
            transition_manifest_status(
                data, "working",
                reason="operator answer resumed the run", actor="manage.answer",
            )
            data["continuation_resumed_at"] = _now_iso()
            save_manifest(manifest_path, data)
            try:
                send_literal_prompt(tmux_session, answer_text, enter_count=2)
            except Exception:
                transition_manifest_status(
                    data, original_status,
                    reason="answer send failed; restoring paused status", actor="manage.answer",
                )
                if original_resumed_at is None:
                    data.pop("continuation_resumed_at", None)
                else:
                    data["continuation_resumed_at"] = original_resumed_at
                save_manifest(manifest_path, data)
                raise
            # Restart watcher if one was previously configured. The answer has
            # already been sent, so restart failures are surfaced explicitly in
            # the return payload/ledger instead of being swallowed silently.
            existing_watcher = dict(data.get("watcher") or {})
            if existing_watcher:
                watcher_restart_status["attempted"] = True
                try:
                    restart_result = cmd_watch_start(_watcher_restart_namespace(manifest_path, existing_watcher))
                except Exception as exc:
                    watcher_restart_status.update({"ok": False, "error": str(exc)})
                else:
                    watcher_restart_status.update({"ok": True, "result": restart_result})

        if row and idx is not None:
            updated_row = apply_manager_fields(
                row,
                manager_status="answered_runtime",
                message_id="operator_answer" if not dry_run else "dry_run",
                transport="tmux_send" if not dry_run else "dry_run",
                pending_question="",
            )
            updated_row["manager_pending_question"] = ""
            # Clear continuation pending fields so a resumed continuation is not
            # re-detected on the next scan.
            updated_row["manager_continuation_pending"] = False
            for field in (
                "manager_continuation_options",
                "manager_continuation_checkpoint",
                "manager_continuation_recommendation",
                "manager_continuation_confidence",
                "manager_continuation_band",
            ):
                updated_row.pop(field, None)
            rows[idx] = {k: v for k, v in updated_row.items() if not k.startswith("_")}
            if not dry_run:
                _write_ledger(ledger_path, rows)
        return {
            "manifest_path": manifest_key,
            "tmux_session": data.get("tmux_session"),
            "answer_sent": not dry_run,
            "dry_run": dry_run,
            "answer_preview": answer_text[:200],
            "manager_status": "answered_runtime" if not dry_run else "dry_run",
            "watcher_restart_status": watcher_restart_status,
        }

    raise SystemExit(f"manage requires a subcommand: status, classify, scan, answer. Got: {manage_command!r}")


def _canary_report_text(label: str) -> str:
    return "\n".join([
        "## Request",
        f"Synthetic closeout canary run {label}.",
        "",
        "## Changes",
        f"- Touched scripts/synthetic_{label}.py (canary fixture, not real).",
        "",
        "## Verification",
        "- python -m pytest -q (synthetic pass recorded by the canary).",
        "",
        "## Blockers",
        "None.",
        "",
        "## Next Steps",
        "None.",
        "",
    ])


def _canary_create_run(repo: Path, index: int) -> Path:
    """Build one fake completed-clean managed run: manifest + structured report + ledger row."""
    label = f"closeout-canary-{index}"
    manifest = TerminalManifest.create(
        runtime="claude", repo_path=repo, loadout="deep-coding",
        session_label=label, dry_run=True,
    )
    manifest_path = write_manifest(manifest)
    data = read_manifest(manifest_path)
    reports_dir = Path(data["artifacts"]["reports"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "closeout-report.md"
    report_path.write_text(_canary_report_text(label))
    data["status"] = "waiting_for_input"
    data["closeout_status"] = "structured"
    data["report_has_blockers"] = False
    data["latest_closeout_report"] = str(report_path)
    data["conversation_context"] = {
        "session_title": f"Canary session {index}",
        "conversation_goal": "prove closeout response canary",
    }
    data["origin_context"] = {"channel_id": "canary-local"}
    save_manifest(manifest_path, data)
    _upsert_ledger_row(repo, manifest_path, data)
    return manifest_path


def _canary_scan_namespace(repo: Path) -> argparse.Namespace:
    return argparse.Namespace(
        manage_command="scan", repo=str(repo), artifact_root=None,
        delivery_log=None, transport="file_log", dry_run=False,
        continuation_profile="session", auto_answer=False, auto_continue=False,
        include_all=True, include_unowned=False,
        owner=None, thread_id=None, hermes_session_id=None,
    )


def cmd_canary(args: argparse.Namespace) -> dict:
    if getattr(args, "canary_command", None) != "closeout":
        raise SystemExit("canary requires a subcommand: closeout")
    repo = Path(args.repo).resolve()
    runs = max(1, int(getattr(args, "runs", 1)))
    repo.mkdir(parents=True, exist_ok=True)
    manifests = [_canary_create_run(repo, index + 1) for index in range(runs)]

    # Scan twice: the first scan posts one response per run, the second must be
    # fully idempotent (no new response, no duplicate delivery).
    scans = [cmd_manage(_canary_scan_namespace(repo)), cmd_manage(_canary_scan_namespace(repo))]

    ledger_path = _ledger_path_for_repo(repo)
    rows = _read_ledger(ledger_path)
    manifest_keys = {str(path.resolve()) for path in manifests}
    canary_rows = [row for row in rows if row.get("manifest_path") in manifest_keys]
    canary_run_ids = {row.get("run_id") for row in canary_rows}

    posted_rows = [row for row in canary_rows if row.get("manager_response_status") == "posted"]
    message_ids = [row.get("manager_response_message_id", "") for row in posted_rows]
    packet_paths = [row.get("manager_response_packet_path", "") for row in canary_rows if row.get("manager_response_packet_path")]

    # Duplicate proof from the delivery log: count manager deliveries per run.
    delivery_log = ledger_path.with_name("postback-deliveries.jsonl")
    per_run: dict[str, int] = {}
    if delivery_log.exists():
        for line in delivery_log.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if str(record.get("kind", "")).startswith("manager_") and record.get("run_id") in canary_run_ids:
                per_run[record["run_id"]] = per_run.get(record["run_id"], 0) + 1
    duplicates = sum(count - 1 for count in per_run.values() if count > 1)

    try:
        operator = cmd_operator_status(argparse.Namespace(repo=str(repo), artifact_root=None))
        summary = operator.get("summary", {})
    except Exception:
        summary = {}
    operator_status_summary = {
        "manager_response_posted": summary.get("manager_response_posted", 0),
        "manager_response_dry_run": summary.get("manager_response_dry_run", 0),
        "manager_response_missing": summary.get("manager_response_missing", 0),
    }

    ok = (
        len(posted_rows) == runs
        and duplicates == 0
        and len(set(message_ids)) == runs
        and len(packet_paths) == runs
        and all(path and Path(path).exists() for path in packet_paths)
    )
    return {
        "status": "ok" if ok else "failed",
        "repo": str(repo),
        "runs_created": runs,
        "manager_scans": len(scans),
        "responses_posted": len(posted_rows),
        "duplicates": duplicates,
        "message_ids": message_ids,
        "response_packet_paths": packet_paths,
        "operator_status_summary": operator_status_summary,
        "scan_actions": [scan.get("by_action", {}) for scan in scans],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Hermes coding terminals through tmux.")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--runtime", choices=["claude", "codex"], required=True)
    start.add_argument("--repo", required=True)
    start.add_argument("--loadout", default="default")
    start.add_argument("--label", required=True)
    start.add_argument("--artifact-root")
    start.add_argument("--project-slug")
    start.add_argument("--raw-output-root")
    start.add_argument("--project-output-root")
    start.add_argument("--discord-guild-id", help="Discord guild/server id that launched this coding terminal.")
    start.add_argument("--discord-channel-id", help="Discord parent channel id that launched this coding terminal.")
    start.add_argument("--discord-thread-id", help="Discord thread id that launched this coding terminal. Defaults to HERMES_SESSION_THREAD_ID when present.")
    start.add_argument("--discord-thread-name", help="Human-readable Discord thread name resolved by the gateway/operator.")
    start.add_argument("--session-title", help="Human-readable originating session/thread title for session-aware continuation. Falls back to HERMES_SESSION_TITLE then the Discord thread name.")
    start.add_argument("--user-request", help="Bounded summary of the original request that launched this run. Falls back to HERMES_SESSION_REQUEST.")
    start.add_argument("--conversation-goal", help="Bounded summary of the ongoing session goal this run should advance. Falls back to HERMES_SESSION_GOAL.")
    start.add_argument("--previous-work-summary", help="Bounded summary of prior session work for continuation context. Falls back to HERMES_SESSION_PREVIOUS_WORK.")
    start.add_argument("--next-question", help="Optional open operator question present at launch. Falls back to HERMES_SESSION_NEXT_QUESTION.")
    start.add_argument("--context-source", help="Override the recorded provenance for the captured session context (e.g. explicit_cli, prompt_packet).")
    start.add_argument("--managed-launcher", help="Name of the high-level managed launcher that owns this run (e.g. run_loaded_agent.py). Absence marks the start as a manual/diagnostic launch.")
    start.add_argument("--managed-launch-policy-version", help="Managed-launch policy version stamped by the high-level launcher.")
    start.add_argument("--hermes-profile", help="Hermes profile that launched this coding terminal. Falls back to HERMES_PROFILE/HERMES_ACTIVE_PROFILE/HERMES_PROFILE_NAME env.")
    start.add_argument("--hermes-session-id", help="Durable Hermes orchestration session id. Falls back to HERMES_SESSION_ID env. Used for owner-scoped manage scan filtering.")
    start.add_argument("--watcher-required", action="store_true", help="Mark this managed launch as requiring an event-driven watcher; operator surfaces flag it needs-review until watcher metadata is present.")
    start.add_argument("--origin-required", action="store_true", help="Mark this managed launch as requiring verified Discord origin because reportback is expected.")
    start.add_argument("--stop-after-closeout", action="store_true", help="Persist closeout policy: auto-close this terminal after a structured no-blocker closeout with a recorded Hermes response.")
    start.add_argument("--keep-open-after-closeout", action="store_true", help="Persist closeout policy: keep this terminal open after closeout for inspection; overrides auto-close.")
    start.add_argument("--keep-open-reason", help="Recorded reason for --keep-open-after-closeout.")
    start.add_argument("--initial-prompt")
    start.add_argument("--add-dir", dest="add_dirs", action="append", default=[], help="Extra directory Claude should be allowed to access at launch. Repeatable.")
    start.add_argument("--bypass-permissions", action="store_true")
    start.add_argument("--startup-wait", type=float, default=2.0)
    start.add_argument("--visible", action="store_true", help="Open a real desktop terminal attached to the tmux session and verify a client is attached.")
    start.add_argument("--terminal-visibility-reason", default="", help="Record why this run is visible or invisible (default/env/cli).")
    start.add_argument("--visible-wait", type=float, default=1.0)
    start.add_argument("--dry-run", action="store_true")
    start.add_argument("--json", action="store_true")

    send = sub.add_parser("send")
    send.add_argument("--manifest", required=True)
    send.add_argument("--prompt")
    send.add_argument("--prompt-file")
    send.add_argument("--output-contract")
    send.add_argument("--output-type", choices=sorted(OUTPUT_DEFINITIONS), default=None)
    send.add_argument("--raw-prompt", action="store_true", help="Send the prompt without Hermes prompt management/enhancement.")
    send.add_argument("--dry-run", action="store_true")
    send.add_argument("--json", action="store_true")

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--manifest", required=True)
    snapshot.add_argument("--text")
    snapshot.add_argument("--text-file")
    snapshot.add_argument("--start", type=int, default=-200)
    snapshot.add_argument("--json", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("--manifest", required=True)
    status.add_argument("--refresh", action="store_true")
    status.add_argument("--event-only", action="store_true", help="Read only the manifest/events file; do not touch tmux or capture panes.")
    status.add_argument("--json", action="store_true")

    watch = sub.add_parser("watch")
    watch.add_argument("--manifest", required=True)
    watch.add_argument("--timeout", type=float, default=900)
    watch.add_argument("--poll-interval", type=float, default=10.0)
    watch.add_argument("--terminal-state", action="append", default=["finished", "waiting_for_input", "waiting_for_continuation", "blocked", "failed", "stale"])
    watch.add_argument("--event-only", action="store_true", help="Poll only manifest/events written by runtime hooks; no tmux pane capture.")
    watch.add_argument("--event-driven", action="store_true", help="Wait on filesystem events from manifest/events writes instead of sleeping on a timer.")
    watch.add_argument("--closeout-on-complete", action="store_true", help="Run closeout automatically when a terminal runtime event reaches a terminal state.")
    watch.add_argument("--allow-snapshot-fallback", action="store_true", help="Permit closeout snapshot fallback when used with --closeout-on-complete.")
    watch.add_argument("--stop-after-closeout", action="store_true", help="Stop the tmux session after a structured, blocker-free auto-closeout.")
    watch.add_argument("--stop-grace", type=float, default=2.0)
    watch.add_argument("--postback-on-closeout", action="store_true", help="Run an idempotent postback scan after successful closeout.")
    watch.add_argument("--manage-on-closeout", action="store_true", help="After closeout, invoke manage scan scoped to this manifest's owner.")
    watch.add_argument("--postback-transport", choices=["auto", "file_log", "discord"], default="auto", help="Transport for --postback-on-closeout. auto uses Discord when DISCORD_BOT_TOKEN is available, otherwise file_log.")
    watch.add_argument("--no-continuation", action="store_true", help="Skip the second-phase continuation review during the closeout postback scan. Continuation is on by default.")
    watch.add_argument("--continuation-profile", choices=list(CONTINUATION_PROFILES), default="session", help="Continuation review style: session (default, session-aware), minimal (report-only), debug (adds manifest pointer), none (disable).")
    watch.add_argument("--completion-ingress-transport", choices=["auto", "file_log", "webhook"], default="auto", help="Completion ingress transport after the canonical manager/postback response.")
    watch.add_argument("--completion-ingress-url", help="Hermes webhook/API URL for managed-terminal completion events. Falls back to HERMES_TERMINAL_COMPLETION_WEBHOOK_URL.")
    watch.add_argument("--completion-ingress-secret", help="HMAC secret for completion ingress. Falls back to HERMES_TERMINAL_COMPLETION_WEBHOOK_SECRET.")
    watch.add_argument("--completion-ingress-log", help="Local JSONL log for file_log completion ingress. Defaults beside the ledger.")
    watch.add_argument("--cleanup-grace", type=float, default=2.0)
    watch.add_argument("--json", action="store_true")

    watch_start = sub.add_parser("watch-start")
    watch_start.add_argument("--manifest", required=True)
    watch_start.add_argument("--timeout", type=float, default=900)
    watch_start.add_argument("--poll-interval", type=float, default=30.0)
    watch_start.add_argument("--terminal-state", action="append", default=["finished", "waiting_for_input", "waiting_for_continuation", "blocked", "failed", "stale"])
    watch_start.add_argument("--event-only", action="store_true", default=True, help="Watch only manifest/events written by runtime hooks.")
    watch_start.add_argument("--event-driven", action="store_true", default=True, help="Wait on filesystem events from manifest/events writes instead of sleeping on a timer.")
    watch_start.add_argument("--closeout-on-complete", action="store_true", help="Run closeout automatically when a terminal runtime event reaches a terminal state.")
    watch_start.add_argument("--allow-snapshot-fallback", action="store_true", help="Permit closeout snapshot fallback when used with --closeout-on-complete.")
    watch_start.add_argument("--stop-after-closeout", action="store_true", help="Stop the tmux session after a structured, blocker-free auto-closeout.")
    watch_start.add_argument("--stop-grace", type=float, default=2.0)
    watch_start.add_argument("--postback-on-closeout", action="store_true", help="Pass --postback-on-closeout into the managed watcher.")
    watch_start.add_argument("--manage-on-closeout", action="store_true", help="Pass --manage-on-closeout into the managed watcher (owner-scoped manage scan after closeout).")
    watch_start.add_argument("--postback-transport", choices=["auto", "file_log", "discord"], default="auto", help="Transport passed to --postback-on-closeout.")
    watch_start.add_argument("--continuation-profile", choices=list(CONTINUATION_PROFILES), default="session", help="Continuation review style forwarded to the managed watcher. Defaults to session-aware continuation.")
    watch_start.add_argument("--completion-ingress-transport", choices=["auto", "file_log", "webhook"], default="auto", help="Completion ingress transport forwarded to the managed watcher.")
    watch_start.add_argument("--completion-ingress-url", help="Hermes webhook/API URL forwarded to the managed watcher.")
    watch_start.add_argument("--completion-ingress-log", help="Local JSONL completion-ingress log forwarded to the managed watcher.")
    watch_start.add_argument("--json", action="store_true")

    watch_status = sub.add_parser("watch-status")
    watch_status.add_argument("--manifest", required=True)
    watch_status.add_argument("--json", action="store_true")

    closeout = sub.add_parser("closeout")
    closeout.add_argument("--manifest", required=True)
    closeout.add_argument("--wait", action="store_true", help="Wait for the watcher to complete before extracting the final message.")
    closeout.add_argument("--timeout", type=float, default=900)
    closeout.add_argument("--allow-snapshot-fallback", action="store_true", help="Permit a latest-snapshot fallback when no runtime-event message exists.")
    closeout.add_argument("--json", action="store_true")

    stop = sub.add_parser("stop")
    stop.add_argument("--manifest", required=True)
    stop.add_argument("--dry-run", action="store_true")
    stop.add_argument("--grace", type=float, default=2.0)
    stop.add_argument("--json", action="store_true")

    list_cmd = sub.add_parser("list", help="List managed coding-terminal sessions and their manifest/report state.")
    list_cmd.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    list_cmd.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    list_cmd.add_argument("--open-only", action="store_true", help="Only return sessions with a live tmux session.")
    list_cmd.add_argument("--state", choices=["active", "stopped", "needs_attention", "closed", "unknown"], help="Filter by managed lifecycle state.")
    list_cmd.add_argument("--json", action="store_true")

    reports = sub.add_parser("reports", help="Inspect routed closeout reports across local, save-destination/raw, and project mirror destinations.")
    reports_sub = reports.add_subparsers(dest="reports_command", required=True)
    reports_list = reports_sub.add_parser("list", help="List closeout report destinations for managed coding-terminal runs.", epilog="Example: python scripts/coding_terminal_runner.py reports list --repo .", formatter_class=argparse.RawDescriptionHelpFormatter)
    reports_list.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    reports_list.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    reports_list.add_argument("--include-empty", action="store_true", help="Include sessions without any report path.")
    reports_list.add_argument("--limit", type=int, default=None)
    reports_list.add_argument("--json", action="store_true")
    reports_repair = reports_sub.add_parser("repair", help="Backfill missing routed report copies from surviving local/project/raw copies.", epilog="Example: python scripts/coding_terminal_runner.py reports repair --dry-run --repo .", formatter_class=argparse.RawDescriptionHelpFormatter)
    reports_repair.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    reports_repair.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    reports_repair.add_argument("--include-empty", action="store_true", help="Include sessions without any report path.")
    reports_repair.add_argument("--limit", type=int, default=None)
    reports_repair.add_argument("--dry-run", action="store_true")
    reports_repair.add_argument("--json", action="store_true")

    postback = sub.add_parser("postback", help="Scan the durable run ledger and emit idempotent reportback deliveries.")
    postback_sub = postback.add_subparsers(dest="postback_command", required=True)
    postback_scan = postback_sub.add_parser("scan", help="Post completed, verified ledger rows exactly once using the configured local delivery transport.")
    postback_scan.add_argument("--repo", help="Repo whose .hermes/coding-terminals run ledger should be scanned. Defaults to cwd.")
    postback_scan.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    postback_scan.add_argument("--delivery-log", help="Local JSONL delivery log used by the file transport. Defaults beside the ledger.")
    postback_scan.add_argument("--transport", choices=["auto", "file_log", "discord"], default="file_log", help="Delivery transport. file_log is test-safe; discord posts to the verified thread using DISCORD_BOT_TOKEN; auto uses Discord when the token is available.")
    postback_scan.add_argument("--no-continuation", dest="continuation", action="store_false", help="Disable the second-phase continuation review. Alias for --continuation-profile none. Continuation is on by default after a successful postback.")
    postback_scan.set_defaults(continuation=True)
    postback_scan.add_argument("--continuation-profile", choices=list(CONTINUATION_PROFILES), default="session", help="Continuation review style: session (default, session-aware), minimal (report-only), debug (adds manifest pointer), none (disable).")
    postback_scan.add_argument("--owner", help="Only post rows launched by this managed_launcher. Falls back to HERMES_MANAGED_LAUNCHER env.")
    postback_scan.add_argument("--thread-id", help="Only post rows for this discord_thread_id. Falls back to HERMES_SESSION_THREAD_ID env unless --hermes-session-id is explicit.")
    postback_scan.add_argument("--hermes-session-id", help="Only post rows for this Hermes session id. Falls back to HERMES_SESSION_ID env.")
    postback_scan.add_argument("--include-unowned", action="store_true", help="Include manual/unowned rows while owner filtering is active.")
    postback_scan.add_argument("--include-all", action="store_true", help="Disable owner filtering and scan every ledger row; intended for explicit operator sweeps.")
    postback_scan.add_argument("--completion-ingress", action="store_true", help="After a successful postback, emit a signed managed-terminal completion event for Hermes to run a follow-up prompt/skill.")
    postback_scan.add_argument("--completion-ingress-transport", choices=["auto", "file_log", "webhook"], default="auto", help="Completion ingress transport. auto uses webhook when a URL is configured, otherwise file_log.")
    postback_scan.add_argument("--completion-ingress-url", help="Hermes webhook/API URL for managed-terminal completion events. Falls back to HERMES_TERMINAL_COMPLETION_WEBHOOK_URL.")
    postback_scan.add_argument("--completion-ingress-secret", help="HMAC secret for completion ingress. Falls back to HERMES_TERMINAL_COMPLETION_WEBHOOK_SECRET.")
    postback_scan.add_argument("--completion-ingress-log", help="Local JSONL log for file_log completion ingress. Defaults beside the ledger.")
    postback_scan.add_argument("--cleanup-after-response", action="store_true", help="After successful response/postback handling, run safe stopped-terminal cleanup policy.")
    postback_scan.add_argument("--cleanup-dry-run", action="store_true", help="With --cleanup-after-response, report cleanup candidates without closing terminals.")
    postback_scan.add_argument("--cleanup-grace", type=float, default=2.0, help="Grace seconds for terminal cleanup after response.")
    postback_scan.add_argument("--json", action="store_true")

    operator_status = sub.add_parser("operator-status", help="Summarize managed coding terminals, raw tmux sessions, lifecycle state, and report routing health.", epilog="Example: python scripts/coding_terminal_runner.py operator-status --repo .", formatter_class=argparse.RawDescriptionHelpFormatter)
    operator_status.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    operator_status.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    operator_status.add_argument("--json", action="store_true")

    doctor = sub.add_parser("doctor", help="Plain-English health check for coding-terminal sessions, watcher/closeout state, and report routing.", epilog="Example: python scripts/coding_terminal_runner.py doctor --repo .", formatter_class=argparse.RawDescriptionHelpFormatter)
    doctor.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    doctor.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    doctor.add_argument("--json", action="store_true")

    recover_closeouts = sub.add_parser("recover-closeouts", help="Backfill closeout/manager/ingress for finished managed runs that missed the watcher hot path.")
    recover_closeouts.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    recover_closeouts.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    recover_closeouts.add_argument("--limit", type=int, default=20)
    recover_closeouts.add_argument("--dry-run", action="store_true")
    recover_closeouts.add_argument("--allow-snapshot-fallback", action="store_true")
    recover_closeouts.add_argument("--postback-transport", choices=["auto", "file_log", "discord"], default="file_log")
    recover_closeouts.add_argument("--continuation-profile", choices=list(CONTINUATION_PROFILES), default="session")
    recover_closeouts.add_argument("--auto-continue", action="store_true")
    recover_closeouts.add_argument("--completion-ingress-transport", choices=["auto", "file_log", "webhook"], default="auto")
    recover_closeouts.add_argument("--completion-ingress-url")
    recover_closeouts.add_argument("--completion-ingress-secret")
    recover_closeouts.add_argument("--completion-ingress-log")
    recover_closeouts.add_argument("--json", action="store_true")

    orphans = sub.add_parser("orphans", help="Inspect or explicitly close unmanaged hermes-claude/hermes-codex tmux sessions.")
    orphans_sub = orphans.add_subparsers(dest="orphans_command", required=True)
    orphans_list = orphans_sub.add_parser("list", help="List unmanaged coding-agent tmux sessions with attach and cleanup commands.", epilog="Example: python scripts/coding_terminal_runner.py orphans list --repo .", formatter_class=argparse.RawDescriptionHelpFormatter)
    orphans_list.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    orphans_list.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    orphans_list.add_argument("--session", action="append", help="Only show this tmux session name. Can be passed more than once.")
    orphans_list.add_argument("--json", action="store_true")
    orphans_cleanup = orphans_sub.add_parser("cleanup", help="Close selected unmanaged coding-agent tmux sessions after explicit confirmation.")
    orphans_cleanup.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    orphans_cleanup.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    orphans_cleanup.add_argument("--session", action="append", help="Only close this tmux session name. Can be passed more than once.")
    orphans_cleanup.add_argument("--dry-run", action="store_true")
    orphans_cleanup.add_argument("--yes", action="store_true")
    orphans_cleanup.add_argument("--json", action="store_true")

    cleanup_stopped = sub.add_parser("cleanup-stopped", help="Stop only managed tmux sessions that are no longer active; never closes active/running sessions.", epilog="Example: python scripts/coding_terminal_runner.py cleanup-stopped --repo .", formatter_class=argparse.RawDescriptionHelpFormatter)
    cleanup_stopped.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    cleanup_stopped.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    cleanup_stopped.add_argument("--dry-run", action="store_true")
    cleanup_stopped.add_argument("--grace", type=float, default=2.0)
    cleanup_stopped.add_argument("--json", action="store_true")

    cleanup_preflight = sub.add_parser("cleanup-preflight", help="Build a non-invasive activity tally, close only safe stopped managed sessions, and report launch blockers.", epilog="Example: python scripts/coding_terminal_runner.py cleanup-preflight --repo . --runtime claude --json", formatter_class=argparse.RawDescriptionHelpFormatter)
    cleanup_preflight.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    cleanup_preflight.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    cleanup_preflight.add_argument("--runtime", choices=["claude", "codex"], help="Runtime requested for the upcoming launch; used only for per-runtime active-session gates.")
    cleanup_preflight.add_argument("--dry-run", action="store_true")
    cleanup_preflight.add_argument("--grace", type=float, default=2.0)
    cleanup_preflight.add_argument("--json", action="store_true")

    prune = sub.add_parser(
        "prune",
        aliases=["cleanup-closed"],
        help="Prune local derived manifests for closed coding-terminal sessions older than a cutoff; never touches active/problem sessions or routed save-destination artifacts.",
        epilog="Example: python scripts/coding_terminal_runner.py prune --repo . --older-than-days 14 --yes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    prune.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    prune.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    prune.add_argument("--older-than-days", type=int, default=14, help="Only prune closed sessions whose manifest is older than this many days. Default 14.")
    prune.add_argument("--dry-run", action="store_true", help="Report candidates without removing. This is also the default when --yes is absent.")
    prune.add_argument("--yes", action="store_true", help="Actually remove the candidate session directories. Without it, prune only reports candidates.")
    prune.add_argument("--json", action="store_true")

    selftest = sub.add_parser(
        "selftest",
        aliases=["release-check"],
        help="No-model-spend release readiness check: loadout validation, command inventory, route preflight, clean lifecycle, report-repair drift, and runtime hook fixtures.",
        epilog="Example: python scripts/coding_terminal_runner.py selftest --repo .",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    selftest.add_argument("--repo", help="Repo whose .hermes/coding-terminals directory should be scanned. Defaults to cwd.")
    selftest.add_argument("--artifact-root", help="Explicit coding-terminal artifact root to scan instead of <repo>/.hermes/coding-terminals.")
    selftest.add_argument("--json", action="store_true")

    manage = sub.add_parser(
        "manage",
        help="Run-manager: classify, act on, and resume managed coding-terminal runs.",
        epilog="Example: python scripts/coding_terminal_runner.py manage scan --repo . --transport file_log --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    manage_sub = manage.add_subparsers(dest="manage_command", required=True)

    manage_status = manage_sub.add_parser("status", help="Show run-manager state counts from the ledger.")
    manage_status.add_argument("--repo")
    manage_status.add_argument("--artifact-root")
    manage_status.add_argument("--json", action="store_true")

    manage_classify = manage_sub.add_parser("classify", help="Classify a single managed run without acting.")
    manage_classify.add_argument("--manifest", required=True)
    manage_classify.add_argument("--json", action="store_true")

    manage_once = manage_sub.add_parser("once", help="Classify and act on exactly one manifest run (watcher hot path).")
    manage_once.add_argument("--manifest", required=True)
    manage_once.add_argument("--delivery-log")
    manage_once.add_argument("--transport", choices=["auto", "file_log", "discord"], default="file_log")
    manage_once.add_argument("--continuation-profile", choices=list(CONTINUATION_PROFILES), default="session")
    manage_once.add_argument("--auto-answer", action="store_true", help="Enable safe auto-answers for safe pattern questions (default: off — routes to operator).")
    manage_once.add_argument("--auto-continue", action="store_true", help="Enable safe auto-resume for high-confidence safe-operational continuations (default: off — routes to operator).")
    manage_once.add_argument("--dry-run", action="store_true", help="Classify and build messages without sending or updating ledger.")
    manage_once.add_argument("--json", action="store_true")

    manage_scan = manage_sub.add_parser("scan", help="Classify and act on all ledger runs (idempotent).")
    manage_scan.add_argument("--repo")
    manage_scan.add_argument("--artifact-root")
    manage_scan.add_argument("--delivery-log")
    manage_scan.add_argument("--transport", choices=["auto", "file_log", "discord"], default="file_log")
    manage_scan.add_argument("--continuation-profile", choices=list(CONTINUATION_PROFILES), default="session")
    manage_scan.add_argument("--owner", help="Scan only rows owned by this managed_launcher value. Falls back to HERMES_MANAGED_LAUNCHER env.")
    manage_scan.add_argument("--thread-id", help="Narrow owner filter to this discord_thread_id. Falls back to HERMES_SESSION_THREAD_ID env.")
    manage_scan.add_argument("--hermes-session-id", help="Narrow owner filter to rows launched by this Hermes session id. Falls back to HERMES_SESSION_ID env.")
    manage_scan.add_argument("--include-unowned", action="store_true", help="Also process rows with launch_origin=manual or empty managed_launcher.")
    manage_scan.add_argument("--include-all", action="store_true", help="Disable owner filter; scan all rows regardless of ownership (diagnostic only).")
    manage_scan.add_argument("--auto-answer", action="store_true", help="Enable safe auto-answers for safe pattern questions (default: off — routes to operator).")
    manage_scan.add_argument("--auto-continue", action="store_true", help="Enable safe auto-resume for high-confidence safe-operational continuations (default: off — routes to operator).")
    manage_scan.add_argument("--dry-run", action="store_true", help="Classify and build messages without sending or updating ledger.")
    manage_scan.add_argument("--json", action="store_true")

    manage_answer = manage_sub.add_parser("answer", help="Send an operator answer to a pending managed run (Phase 4).")
    manage_answer.add_argument("--manifest", required=True)
    manage_answer.add_argument("--answer", help="Answer text to send directly.")
    manage_answer.add_argument("--answer-file", help="Path to a file whose text is sent as the answer.")
    manage_answer.add_argument("--dry-run", action="store_true")
    manage_answer.add_argument("--json", action="store_true")

    canary = sub.add_parser(
        "canary",
        help="Deterministic local canaries that prove the managed lifecycle without a live runtime.",
        epilog="Example: python scripts/coding_terminal_runner.py canary closeout --repo /tmp/hermes-closeout-canary --runs 2 --json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    canary_sub = canary.add_subparsers(dest="canary_command", required=True)
    canary_closeout = canary_sub.add_parser(
        "closeout",
        help="Create N fake completed-clean runs, scan twice, and prove exactly one closeout response per run.",
    )
    canary_closeout.add_argument("--repo", required=True, help="Throwaway repo dir for the canary's .hermes artifacts (created if missing).")
    canary_closeout.add_argument("--runs", type=int, default=1, help="How many fake completed runs to create (default: 1).")
    canary_closeout.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "send" and not args.prompt and not args.prompt_file:
        raise SystemExit("send requires --prompt or --prompt-file")
    payload = globals()[f"cmd_{args.command.replace('-', '_')}"](args)
    _emit(payload, getattr(args, "json", False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
