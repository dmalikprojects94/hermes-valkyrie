#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAX_ACTIVE_SESSIONS_PER_RUNTIME = 10
DEFAULT_AUTO_WATCH_SECONDS = 28800
sys.path.insert(0, str(ROOT))

from scripts.loadoutlib import load_loadouts, resolve_loadout_name, validate_loadouts
from scripts.prompt_manager import prepare_prompt
from scripts.runtime_adapters import resolve_real_home
from scripts.artifact_router import resolve_obsidian_vault_path

TERMINAL_STATUSES = {"finished", "waiting_for_input", "blocked", "failed", "stale"}
MANAGED_LAUNCH_POLICY_VERSION = "1.0"
_VISIBLE_FALSE_VALUES = {"0", "false", "no", "off", "hidden", "invisible"}
_VISIBLE_TRUE_VALUES = {"1", "true", "yes", "on", "visible"}


def _cli_origin_ids(args: argparse.Namespace) -> list[str | None]:
    return [
        getattr(args, "discord_guild_id", None),
        getattr(args, "discord_channel_id", None),
        getattr(args, "discord_thread_id", None),
    ]


def _origin_verification(args: argparse.Namespace, origin_context: dict[str, str]) -> dict[str, Any]:
    """Classify managed-launch origin. Explicit CLI ids win over env fallback.

    A fully explicit Discord origin is verified. Origin present only via env fallback is
    audit-only (`needs_origin_review`). A partial *explicit* origin is a misconfiguration
    (`incomplete_cli_origin`) the launcher can refuse in live mode. No origin at all means
    reportback is not expected and the run is a local/managed launch with no Discord target.
    """
    cli_ids = _cli_origin_ids(args)
    cli_present = any(_first_nonempty(value) for value in cli_ids)
    cli_complete = all(_first_nonempty(value) for value in cli_ids)
    if not origin_context or origin_context.get("platform") != "discord":
        return {"origin_verified": False, "origin_verification": "no_origin", "reportback_expected": False, "needs_origin_review": False, "cli_origin_present": cli_present, "origin_complete": False}
    origin_complete = all(origin_context.get(key) for key in ("guild_id", "channel_id", "thread_id"))
    if cli_complete:
        return {"origin_verified": True, "origin_verification": "explicit_discord_origin", "reportback_expected": True, "needs_origin_review": False, "cli_origin_present": True, "origin_complete": True}
    verification = "incomplete_cli_origin" if cli_present else "env_fallback_audit_only"
    return {"origin_verified": False, "origin_verification": verification, "reportback_expected": True, "needs_origin_review": True, "cli_origin_present": cli_present, "origin_complete": origin_complete}


def _terminal_visibility(args: argparse.Namespace) -> tuple[bool, str]:
    if args.no_visible:
        return False, "cli:--no-visible"
    raw = (os.environ.get("HERMES_CODING_TERMINAL_VISIBLE") or "").strip()
    if raw:
        normalized = raw.lower()
        if normalized in _VISIBLE_FALSE_VALUES:
            return False, f"env:HERMES_CODING_TERMINAL_VISIBLE={raw}"
        if normalized in _VISIBLE_TRUE_VALUES:
            return True, f"env:HERMES_CODING_TERMINAL_VISIBLE={raw}"
    return True, "default_visible"


def _managed_launch_contract(args: argparse.Namespace, *, runtime: str, loadout: str, origin_verification: dict[str, Any]) -> dict[str, Any]:
    auto_watch = not args.no_auto_watch
    visible, visibility_reason = _terminal_visibility(args)
    closeout = bool(args.closeout)
    diagnostics: list[str] = []
    if not auto_watch:
        diagnostics.append("watcher disabled via --no-auto-watch")
    if not visible:
        diagnostics.append("visible viewer disabled via --no-visible")
    if not closeout:
        diagnostics.append("closeout disabled via --no-closeout")
    reportback_expected = bool(origin_verification.get("reportback_expected"))
    if reportback_expected and origin_verification.get("needs_origin_review"):
        classification = "needs_origin_review"
    elif diagnostics:
        classification = "diagnostic_incomplete"
    else:
        classification = "managed"
    return {
        "managed_launcher": "run_loaded_agent.py",
        "managed_launch_policy_version": MANAGED_LAUNCH_POLICY_VERSION,
        "runtime": runtime,
        "loadout": loadout,
        "visible_default": visible,
        "terminal_visible": visible,
        "terminal_visibility_reason": visibility_reason,
        "watcher_default": auto_watch,
        "closeout_default": closeout,
        "reportback_default": auto_watch,
        "reportback_expected": reportback_expected,
        "origin_verification": origin_verification.get("origin_verification"),
        "origin_verified": bool(origin_verification.get("origin_verified")),
        "origin_behavior": "explicit_discord_origin_wins_over_env_fallback",
        "classification": classification,
        "diagnostic_notes": diagnostics,
    }


def _watcher_fields_present(payload: dict[str, Any]) -> bool:
    watcher = payload.get("watcher") or {}
    status = payload.get("watcher_status") or {}
    return bool(watcher.get("pid") or watcher.get("watcher_status") or status.get("watcher_status"))


def _launch_health(payload: dict[str, Any], *, auto_watch: bool) -> str:
    """Reject the prior failure shape: runtime/loadout present but no watcher metadata."""
    if not (payload.get("runtime") and payload.get("loadout")):
        return "incomplete"
    if auto_watch and not _watcher_fields_present(payload):
        return "watcher_missing"
    return "healthy"


def _build_goal_command(goal: str | None) -> str:
    """Construct the `/goal <condition>` first raw command. Never returns a bare `/goal`."""
    condition = _first_nonempty(goal)
    if condition.startswith("/goal"):
        condition = condition[len("/goal"):].strip()
    if not condition:
        raise SystemExit("Refusing to send a bare /goal handoff: pass a non-empty --goal <condition>.")
    return f"/goal {condition}"


def _tmux_session_exists(session_name: str) -> bool:
    return subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True, text=True).returncode == 0


def _first_nonempty(*values: str | None) -> str:
    for value in values:
        if value:
            stripped = str(value).strip()
            if stripped:
                return stripped
    return ""


def _candidate_access_dirs(task: str, repo: Path) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"(/[^\s'\"`]+)", task):
        raw = match.group(1).rstrip(".,:;!?)]}")
        try:
            path = Path(raw).expanduser().resolve()
        except OSError:
            continue
        target = path if path.is_dir() else path.parent
        if not target.exists() or not target.is_dir():
            continue
        target = _git_root_for_path(target) or target
        try:
            target.relative_to(repo)
            continue
        except ValueError:
            pass
        candidate = str(target)
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates


def _additional_dirs(args: argparse.Namespace, *, task: str, repo: Path, resume_data: dict[str, Any] | None) -> list[str]:
    if resume_data:
        return []
    explicit = [str(Path(value).expanduser().resolve()) for value in getattr(args, "add_dir", []) or []]
    auto = [] if getattr(args, "no_auto_add_dirs", False) else _candidate_access_dirs(task, repo)
    combined: list[str] = []
    seen: set[str] = set()
    for candidate in [*explicit, *auto]:
        if candidate == str(repo) or candidate in seen:
            continue
        seen.add(candidate)
        combined.append(candidate)
    return combined


def _git_root_for_path(path: Path) -> Path | None:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    root = completed.stdout.strip()
    return Path(root).resolve() if root else None


def _discord_session_env() -> dict[str, str]:
    """Map the vars Hermes actually bridges (session contextvars) to Discord origin fields.

    Gated on HERMES_SESSION_PLATFORM=discord so Telegram/CLI sessions never
    masquerade as Discord origin. `HERMES_SESSION_CHAT_ID` is the thread itself for
    thread messages, so it only counts as the parent channel when it differs from
    the thread id.
    """
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


def _origin_context_from_args(args: argparse.Namespace) -> dict[str, str]:
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


CONTEXT_FIELD_MAX_CHARS = 280


def _bounded_context_text(value: str | None, *, max_chars: int = CONTEXT_FIELD_MAX_CHARS) -> str:
    text = _first_nonempty(value)
    if not text:
        return ""
    flattened = " ".join(text.split())
    if len(flattened) > max_chars:
        flattened = flattened[: max_chars - 1].rstrip() + "…"
    return flattened


def _request_summary_from_task(task: str) -> str:
    for line in task.splitlines():
        stripped = line.strip().lstrip("#").strip("-* ").strip()
        if stripped:
            return _bounded_context_text(stripped)
    return ""


def _conversation_context_from_args(args: argparse.Namespace, *, task: str, origin_context: dict[str, str], label: str) -> dict[str, str]:
    session_title = _bounded_context_text(_first_nonempty(getattr(args, "session_title", None), os.environ.get("HERMES_SESSION_TITLE"), origin_context.get("thread_name"), label))
    user_request = _bounded_context_text(_first_nonempty(getattr(args, "user_request", None), os.environ.get("HERMES_SESSION_REQUEST"))) or _request_summary_from_task(task)
    conversation_goal = _bounded_context_text(_first_nonempty(getattr(args, "conversation_goal", None), os.environ.get("HERMES_SESSION_GOAL")))
    previous_work = _bounded_context_text(_first_nonempty(getattr(args, "previous_work_summary", None), os.environ.get("HERMES_SESSION_PREVIOUS_WORK")))
    next_question = _bounded_context_text(_first_nonempty(getattr(args, "next_question", None), os.environ.get("HERMES_SESSION_NEXT_QUESTION")))
    packet = {
        "session_title": session_title,
        "user_request": user_request,
        "conversation_goal": conversation_goal,
        "previous_work_summary": previous_work,
        "next_question": next_question,
    }
    return {key: value for key, value in packet.items() if value}


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SystemExit(f"Resume manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Resume manifest is not valid JSON: {path}") from exc


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(command, cwd=cwd, env=merged_env, capture_output=True, text=True, check=check)


def _json_command(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = _run(command, cwd=cwd, env=env)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Command did not return JSON: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}") from exc


def _managed_child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {"HOME": resolve_real_home()}
    passthrough_keys = (
        "SAVE_DESTINATION_PATH",
        "OBSIDIAN_VAULT_PATH",
        "PATH",
        "PYTHONPATH",
        "DISCORD_BOT_TOKEN",
        "HERMES_PROFILE",
        "HERMES_SESSION_PROFILE",
        "HERMES_ACTIVE_PROFILE",
        "HERMES_PROFILE_NAME",
        "HERMES_TERMINAL_COMPLETION_WEBHOOK_URL",
        "HERMES_TERMINAL_COMPLETION_WEBHOOK_SECRET",
    )
    for key in passthrough_keys:
        value = os.environ.get(key)
        if value:
            env[key] = value
    if "SAVE_DESTINATION_PATH" not in env and "OBSIDIAN_VAULT_PATH" not in env:
        vault_path = resolve_obsidian_vault_path()
        if vault_path:
            env["SAVE_DESTINATION_PATH"] = str(vault_path)
    if extra:
        env.update(extra)
    return env


def _is_git_work_tree(repo: Path) -> bool:
    completed = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _git_clean() -> bool:
    completed = _run(["git", "status", "--porcelain"], check=False)
    return completed.returncode == 0 and completed.stdout.strip() == ""


def _sync_loadout_repo(*, require_clean: bool) -> dict[str, Any]:
    before = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if require_clean and not _git_clean():
        raise SystemExit("Refusing to sync loadout repo with local source changes. Commit/stash first or pass --allow-dirty-loadout-repo.")
    _run(["git", "fetch", "origin", "main"])
    local = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    remote = _run(["git", "rev-parse", "origin/main"]).stdout.strip()
    if local != remote:
        _run(["git", "pull", "--ff-only", "origin", "main"])
    after = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    return {"before": before, "after": after, "changed": before != after}


def _validate_or_exit(loadouts: dict[str, dict[str, Any]]) -> None:
    errors = validate_loadouts(loadouts=loadouts, repo_root=ROOT)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"Loadout validation failed:\n{joined}")


def _apply_codex_session_home(*, repo: Path, loadout: str) -> dict[str, Any]:
    return _json_command([
        sys.executable,
        str(ROOT / "scripts" / "apply_loadout.py"),
        "--runtime",
        "codex",
        "--loadout",
        loadout,
        "--output-root",
        str(repo / ".codex"),
        "--target-home",
        "--format",
        "json",
    ])


def _task_text(args: argparse.Namespace) -> str:
    if args.task_file:
        return Path(args.task_file).read_text()
    if args.task:
        return args.task
    raise SystemExit("Pass --task or --task-file")


def _label(args: argparse.Namespace, repo: Path, loadout: str) -> str:
    if args.label:
        return args.label
    return f"{repo.name}-{args.runtime}-{loadout}-{_stamp()}"


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"runtime: {payload['runtime']}")
    print(f"loadout: {payload['loadout']}")
    print(f"repo: {payload['repo']}")
    print(f"mode: {payload['mode']}")
    managed = payload.get("managed_launch") or {}
    if managed:
        print(f"managed launcher: {managed.get('managed_launcher')} (policy v{managed.get('managed_launch_policy_version')})")
        print(f"managed launch: classification={managed.get('classification')} visible={managed.get('visible_default')} watcher={managed.get('watcher_default')} closeout={managed.get('closeout_default')} reportback_expected={managed.get('reportback_expected')}")
        print(f"origin: {managed.get('origin_verification')} verified={managed.get('origin_verified')} ({managed.get('origin_behavior')})")
        if managed.get("goal_command"):
            print(f"goal: {managed['goal_command']}")
        if managed.get("launch_health"):
            print(f"launch health: {managed['launch_health']}")
    if payload.get("manifest_path"):
        print(f"manifest: {payload['manifest_path']}")
    if payload.get("tmux_attach"):
        print(f"attach: {payload['tmux_attach']}")
    if payload.get("latest_report"):
        print(f"report: {payload['latest_report']}")
    route = payload.get("artifact_route_preflight") or {}
    if route:
        print(f"raw route: {route.get('raw_root', '')} ({route.get('raw_root_source', '')})")
        for warning in route.get("warnings") or []:
            print(f"route warning: {warning}")
    watcher = payload.get("watcher") or {}
    if watcher:
        print(f"watcher: {watcher.get('watcher_status')} pid={watcher.get('pid')} result={watcher.get('result_path')}")


def _active_sessions_for_runtime(status: dict[str, Any], runtime: str | None) -> list[dict[str, Any]]:
    if not runtime:
        return []
    return [
        session for session in status.get("open_sessions") or []
        if session.get("lifecycle_state") == "active" and session.get("runtime") == runtime
    ]


def _operator_status_blocks_launch(status: dict[str, Any], *, requested_runtime: str | None = None) -> list[str]:
    summary = status.get("summary") or {}
    blockers: list[str] = []
    if summary.get("orphan_tmux", 0):
        blockers.append(f"{summary['orphan_tmux']} orphan hermes-claude/hermes-codex tmux session(s)")
    active_same_runtime = _active_sessions_for_runtime(status, requested_runtime)
    active_sessions = [
        session for session in status.get("open_sessions") or []
        if session.get("lifecycle_state") == "active"
    ]
    active_count = int(summary.get("active", 0) or 0)
    unclassified_active_count = max(0, active_count - len(active_sessions))
    if requested_runtime and len(active_same_runtime) >= MAX_ACTIVE_SESSIONS_PER_RUNTIME:
        blockers.append(
            f"{len(active_same_runtime)} active {requested_runtime} managed coding-terminal session(s); "
            f"limit is {MAX_ACTIVE_SESSIONS_PER_RUNTIME}"
        )
    elif unclassified_active_count:
        blockers.append(f"{unclassified_active_count} active managed coding-terminal session(s) with unknown runtime")
    elif active_count and not requested_runtime:
        blockers.append(f"{active_count} active managed coding-terminal session(s)")
    if summary.get("needs_attention", 0):
        blockers.append(f"{summary['needs_attention']} managed session(s) need attention")
    if summary.get("runtime_event_recording_failed", 0):
        blockers.append(f"{summary['runtime_event_recording_failed']} run(s) have failed runtime-event recording")
    return blockers


def _prepare_managed_prompt(*, task: str, runtime: str, loadout: str, repo: Path, project_slug: str) -> str:
    prepared = prepare_prompt(
        request=task,
        runtime=runtime,
        loadout=loadout,
        repo_path=str(repo),
        project_slug=project_slug,
        vault_path=resolve_obsidian_vault_path(),
    )
    return prepared.prompt


def _record_initial_prompt_artifact(*, manifest_path: str, raw_task: str, prompt_text: str) -> dict[str, Any]:
    manifest = Path(manifest_path)
    data = _read_json_file(manifest)
    inputs = Path(data["artifacts"]["inputs"])
    inputs.mkdir(parents=True, exist_ok=True)
    existing_prompts = [path for path in inputs.glob("*.md") if not path.name.endswith("-original.md")]
    prompt_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{len(existing_prompts) + 1:03d}"
    prompt_path = inputs / f"{prompt_id}.md"
    original_path = inputs / f"{prompt_id}-original.md"
    original_path.write_text(raw_task)
    prompt_path.write_text(prompt_text)
    data["last_prompt_id"] = prompt_id
    data["current_prompt_id"] = prompt_id
    data["current_prompt_started_at"] = datetime.now(timezone.utc).isoformat()
    for key in ("last_runtime_event", "latest_closeout_report", "latest_closeout_summary", "latest_routed_report", "latest_raw_report", "latest_project_report", "closeout_status", "closeout_source", "closeout_routed"):
        data.pop(key, None)
    artifacts = data.setdefault("artifacts", {})
    for key in ("latest_report", "latest_routed_report", "latest_raw_report", "latest_project_report"):
        artifacts[key] = ""
    data["input_transport"] = "initial_prompt"
    data["status"] = "working"
    manifest.write_text(json.dumps(data, indent=2))
    return {
        "status": data["status"],
        "prompt_id": prompt_id,
        "prompt_path": str(prompt_path),
        "original_prompt_path": str(original_path),
        "manifest_path": str(manifest),
        "input_transport": "initial_prompt",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync/validate/apply local loadouts, then start and send a Claude/Codex tmux task.",
        epilog=(
            "Managed runs are visible by default: the runner opens a real desktop terminal "
            "viewer attached to the managed tmux session. Pass --no-visible to opt out of the "
            "desktop viewer.\n"
            "Example: python scripts/run_loaded_agent.py --runtime claude --loadout default "
            "--repo . --task-file /tmp/task.md --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--runtime", choices=["claude", "codex"], help="Runtime to start. Required unless --resume-manifest supplies one.")
    parser.add_argument("--loadout", help="Explicit loadout name or alias. If omitted, resolve from task text or resume manifest.")
    parser.add_argument("--repo", help="Target project repository for the coding agent. Required unless --resume-manifest supplies one.")
    parser.add_argument("--task", help="Task text to send.")
    parser.add_argument("--task-file", help="Markdown/text file containing task text.")
    parser.add_argument("--label", help="Optional tmux/session label.")
    parser.add_argument("--resume-manifest", help="Explicitly resume an existing coding-terminal manifest instead of starting the default fresh tmux session.")
    parser.add_argument("--project-slug", help="Optional artifact project slug. Defaults to target repo name.")
    parser.add_argument("--discord-guild-id", help="Discord guild/server id to persist on the managed run manifest.")
    parser.add_argument("--discord-channel-id", help="Discord parent channel id to persist on the managed run manifest.")
    parser.add_argument("--discord-thread-id", help="Discord thread id to persist on the managed run manifest. Defaults to HERMES_SESSION_THREAD_ID when present.")
    parser.add_argument("--discord-thread-name", help="Human-readable Discord thread name to persist on the managed run manifest.")
    parser.add_argument("--session-title", help="Originating session/thread title for session-aware continuation. Defaults to the Discord thread name or run label.")
    parser.add_argument("--user-request", help="Original request summary for session-aware continuation. Defaults to a bounded summary of the task text.")
    parser.add_argument("--conversation-goal", help="Ongoing session goal this run should advance, for session-aware continuation.")
    parser.add_argument("--previous-work-summary", help="Short summary of prior session work, for session-aware continuation context.")
    parser.add_argument("--next-question", help="Optional open operator question present at launch, surfaced in the continuation review.")
    parser.add_argument("--sync-loadouts", action="store_true", help="Fast-forward this local loadout repo from origin/main before the run.")
    parser.add_argument("--allow-dirty-loadout-repo", action="store_true", help="Allow git sync even if this loadout repo has local source changes.")
    parser.add_argument("--apply-live", action="store_true", help="Apply the selected loadout to the live runtime home before starting.")
    parser.add_argument("--codex-session-home", action="store_true", help="Advanced: materialize Codex loadout into <repo>/.codex and launch with that session home only if the auth strategy supports it.")
    parser.add_argument("--skip-codex-session-home", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--bypass-permissions", action="store_true", help="Pass through to coding_terminal_runner start.")
    parser.add_argument("--add-dir", action="append", default=[], help="Extra directory Claude should be allowed to access at launch. Repeatable.")
    parser.add_argument("--no-auto-add-dirs", action="store_true", help="Disable automatic --add-dir inference from absolute paths mentioned in the task.")
    parser.add_argument("--no-visible", action="store_true", help="Opt out of opening a real desktop terminal viewer for this run.")
    parser.add_argument("--no-auto-watch", action="store_true", help="Do not start the default event-driven completion watcher after sending the task. Reported as a diagnostic/incomplete managed launch.")
    parser.add_argument("--no-postback-on-closeout", dest="postback_on_closeout", action="store_false", default=True, help="Disable the Discord/Hermes completion postback on closeout. Postback is enabled by default; pass this to run silently without a completion message.")
    parser.add_argument("--goal", help="Claude Code /goal handoff condition. Sends `/goal <condition>` as the first raw command, then the detailed task as a follow-up. Never sends a bare /goal.")
    parser.add_argument("--allow-unverified-origin", action="store_true", help="Allow a live managed launch to proceed when an explicit but incomplete Discord origin was supplied. Env-only origin is always audit-only and never auto-posts.")
    parser.add_argument("--no-cleanup-stopped", action="store_true", help="Skip the default preflight that closes only safe stopped sessions before starting a new coding terminal.")
    parser.add_argument("--allow-open-sessions", action="store_true", help=f"Allow launch even when operator-status still sees the per-runtime concurrency limit, needs-attention, or orphan coding-terminal tmux sessions after safe cleanup. Default per-runtime active limit is {MAX_ACTIVE_SESSIONS_PER_RUNTIME}.")
    parser.add_argument("--hermes-profile", help="Hermes profile that launched this managed coding terminal. Falls back to HERMES_PROFILE/HERMES_ACTIVE_PROFILE/HERMES_PROFILE_NAME env.")
    parser.add_argument("--hermes-session-id", help="Durable Hermes orchestration session id stamped on the manifest. Falls back to HERMES_SESSION_ID env. Used to scope manage scan to runs launched by this session.")
    parser.add_argument("--watch", action="store_true", help="Block here until the run closes out. Uses runtime-event closeout, not pane polling.")
    parser.add_argument("--closeout", dest="closeout", action="store_true", default=True, help="When blocking, close out via runtime-event closeout (default).")
    parser.add_argument("--no-closeout", dest="closeout", action="store_false", help="Opt out of closeout and use the legacy diagnostic pane/status poll for blocking waits.")
    parser.add_argument("--closeout-timeout", type=int, default=None, help="Closeout wait timeout in seconds. Defaults to --watch-seconds.")
    parser.add_argument("--stop-after-closeout", action="store_true", help="After a successful structured closeout with no blockers, stop the interactive tmux session. Keeps failed/blocked/no-final-message sessions open for diagnosis.")
    parser.add_argument("--keep-open-after-closeout", action="store_true", help="For watched one-shot runs, keep the visible terminal open after successful structured closeout instead of using the default safe auto-stop policy.")
    parser.add_argument("--watch-seconds", type=int, default=900)
    parser.add_argument(
        "--auto-watch-seconds",
        type=int,
        default=DEFAULT_AUTO_WATCH_SECONDS,
        help=(
            "Timeout in seconds for the background auto watcher that handles closeout/reportback/continuation. "
            "Defaults to a long-lived lease so short foreground waits do not silently disable Discord follow-up."
        ),
    )
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true", help="Resolve, validate, and show the planned run without writing homes or starting tmux.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    task = _task_text(args)
    resume_data: dict[str, Any] | None = None
    resume_manifest: Path | None = None
    if args.resume_manifest:
        resume_manifest = Path(args.resume_manifest).expanduser().resolve()
        resume_data = _read_json_file(resume_manifest)

    runtime = args.runtime or (resume_data or {}).get("runtime")
    if not runtime:
        raise SystemExit("Pass --runtime or --resume-manifest with a runtime")
    if runtime not in {"claude", "codex"}:
        raise SystemExit(f"Unsupported runtime: {runtime}")

    repo_value = args.repo or (resume_data or {}).get("repo_path")
    if not repo_value:
        raise SystemExit("Pass --repo or --resume-manifest with a repo_path")
    repo = Path(repo_value).expanduser().resolve()
    if runtime == "codex" and not args.dry_run and not resume_data and not _is_git_work_tree(repo):
        raise SystemExit(f"Codex requires --repo to be inside a git work tree before launch: {repo}")

    sync_result = None
    if args.sync_loadouts and not args.dry_run:
        sync_result = _sync_loadout_repo(require_clean=not args.allow_dirty_loadout_repo)

    loadouts = load_loadouts(ROOT)
    _validate_or_exit(loadouts)
    manifest_loadout = (resume_data or {}).get("loadout")
    requested_loadout = args.loadout or manifest_loadout
    if requested_loadout and str(requested_loadout).startswith("/"):
        raise SystemExit(
            f"'{requested_loadout}' is a slash command, not a loadout. Slash commands like /goal are launch "
            "metadata (use --goal); pick a real loadout name or omit --loadout."
        )
    try:
        loadout = resolve_loadout_name(loadouts=loadouts, runtime=runtime, request_text=task, explicit_loadout=requested_loadout)
    except KeyError as exc:
        raise SystemExit(f"Unknown loadout alias: {requested_loadout}. It was not treated as a loadout or slash command; pass a name from loadouts/.") from exc
    label = (resume_data or {}).get("session_label") if resume_data else _label(args, repo, loadout)
    project_slug = args.project_slug or repo.name
    origin_context = (resume_data or {}).get("origin_context") if resume_data else _origin_context_from_args(args)
    conversation_context = (resume_data or {}).get("conversation_context", {}) if resume_data else _conversation_context_from_args(args, task=task, origin_context=origin_context or {}, label=label)
    origin_verification = _origin_verification(args, origin_context or {})
    hermes_session_id = _first_nonempty(getattr(args, "hermes_session_id", None), os.environ.get("HERMES_SESSION_ID"))
    hermes_profile = _hermes_profile_from_args(args)
    managed_launch = _managed_launch_contract(args, runtime=runtime, loadout=loadout, origin_verification=origin_verification)
    additional_dirs = _additional_dirs(args, task=task, repo=repo, resume_data=resume_data)
    if args.goal:
        managed_launch["goal_command"] = _build_goal_command(args.goal)
    # Launcher-side mirror of resolve_terminal_closeout_policy for dry-run and
    # resume paths; live launches read the authoritative persisted policy back
    # from the start result below.
    watcher_planned = bool(args.watch or not args.no_auto_watch)
    if args.keep_open_after_closeout:
        effective_stop_after_closeout = False
    elif args.stop_after_closeout:
        effective_stop_after_closeout = True
    else:
        effective_stop_after_closeout = bool(watcher_planned and not resume_data)

    payload: dict[str, Any] = {
        "mode": "dry-run" if args.dry_run else ("resume" if resume_data else "run"),
        "runtime": runtime,
        "loadout": loadout,
        "repo": str(repo),
        "label": label,
        "project_slug": project_slug,
        "origin_context": origin_context or {},
        "hermes_profile": hermes_profile,
        "conversation_context": conversation_context or {},
        "managed_launch": managed_launch,
        "loadout_repo": str(ROOT),
        "sync": sync_result,
        "apply_live": bool(args.apply_live),
        "apply_codex_session_home": bool(runtime == "codex" and args.codex_session_home and not args.skip_codex_session_home),
        "stop_after_closeout": effective_stop_after_closeout,
        "postback_on_closeout": bool(args.postback_on_closeout),
        "cleanup_stopped_before_start": bool(not args.no_cleanup_stopped),
        "task_chars": len(task),
        "resume_manifest": str(resume_manifest) if resume_manifest else None,
        "session_policy": "resume_explicit_only" if resume_data else "fresh_by_default",
        "resume_requires_explicit_manifest": True,
        "additional_dirs": additional_dirs,
        "permission_posture": "managed_bypass_required" if not resume_data else resume_data.get("permission_posture", ""),
        "bypass_permissions_effective": True if not resume_data else bool(resume_data.get("bypass_permissions_effective", False)),
    }

    codex_initial_prompt = runtime == "codex" and not resume_data
    if args.goal and codex_initial_prompt:
        raise SystemExit("--goal is a Claude post-start slash command and is not supported for Codex startup-prompt runs.")

    if args.dry_run:
        payload["input_transport"] = "initial_prompt" if codex_initial_prompt else "post_start_send"
        payload["steps"] = [
            "optionally fast-forward local loadout repo",
            "validate local loadout repo",
            "resolve runtime/loadout: default unless --loadout or explicit loadout phrasing selects a specialty loadout",
            "optionally apply selected loadout to live runtime home",
            "materialize Codex session home at <repo>/.codex" if runtime == "codex" and args.codex_session_home and not args.skip_codex_session_home else ("use live Codex home/auth surface" if runtime == "codex" else "use live Claude home/auth surface with Stop-hook completion events"),
            "resume the explicitly requested tmux coding terminal from --resume-manifest" if resume_data else "start a fresh tmux coding terminal by default; only resume when --resume-manifest is passed explicitly",
            None if resume_data else "build cleanup-preflight/operator-status-compatible non-invasive tally before launch: count active sessions without pane capture/refresh, close only safe stopped sessions, and report orphan Claude/Codex tmux sessions for explicit operator action",
            "start tmux coding terminal with a real desktop viewer unless --no-visible was passed",
            f"grant Claude access to extra dirs at launch: {', '.join(additional_dirs)}" if additional_dirs else None,
            f"submit '{managed_launch['goal_command']}' as the first raw command, then send the detailed prompt follow-up" if args.goal and not codex_initial_prompt else None,
            "pass managed prompt as Codex startup prompt" if codex_initial_prompt else "send managed prompt after terminal startup",
            "start event-only, event-driven watcher with closeout, postback, and manage-on-closeout (owner-scoped manage scan after closeout)" if not args.no_auto_watch else "skip automatic watcher because --no-auto-watch was passed",
            "cleanup-preflight closes only safe stopped sessions before starting; active sessions are only tallied, never refreshed/captured; orphan Claude/Codex tmux sessions are reported for explicit operator action" if not args.no_cleanup_stopped else "skip stopped-session cleanup preflight",
            "close out via runtime-event closeout when blocking, not pane/status polling" if args.closeout else "block on legacy diagnostic pane/status polling when --watch is set",
            "stop the tmux session after successful no-blocker closeout" if effective_stop_after_closeout else "leave the tmux session open after closeout for inspection/resume",
        ]
        payload["steps"] = [step for step in payload["steps"] if step]
        _emit(payload, args.json)
        return 0

    if (
        not resume_data
        and origin_verification.get("reportback_expected")
        and origin_verification.get("needs_origin_review")
        and (origin_verification.get("cli_origin_present") or not origin_verification.get("origin_complete"))
        and not args.allow_unverified_origin
    ):
        missing = [name for name, key in (("guild id", "guild_id"), ("channel id", "channel_id"), ("thread id", "thread_id")) if not (origin_context or {}).get(key)]
        raise SystemExit(
            "Refusing managed launch: Discord origin is incomplete "
            f"({origin_verification.get('origin_verification')}; missing: {', '.join(missing) or 'none'}). "
            "Provide --discord-guild-id, --discord-channel-id, and --discord-thread-id together "
            "(or a complete Hermes Discord session env), or pass --allow-unverified-origin "
            "to launch without verified reportback origin."
        )

    if args.apply_live:
        payload["apply_result"] = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "apply_live_system.py"),
            "--runtime",
            runtime,
            "--loadout",
            loadout,
            "--yes",
            "--format",
            "json",
        ])

    if runtime == "codex" and args.codex_session_home and not args.skip_codex_session_home and not resume_data:
        payload["codex_session_home_result"] = _apply_codex_session_home(repo=repo, loadout=loadout)

    if not resume_data:
        payload["preflight_operator_status"] = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "operator-status",
            "--repo",
            str(repo),
            "--json",
        ], env=_managed_child_env())

    if not resume_data and not args.no_cleanup_stopped:
        payload["preflight_cleanup"] = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "cleanup-preflight",
            "--repo",
            str(repo),
            "--runtime",
            runtime,
            "--json",
        ], env=_managed_child_env())
        launch_blockers = payload["preflight_cleanup"].get("blockers") or []
        payload["launch_blockers"] = launch_blockers
        if launch_blockers and not args.allow_open_sessions:
            joined = "; ".join(launch_blockers)
            raise SystemExit(f"Refusing to launch while coding-terminal cleanup preflight is not clean: {joined}. Run doctor/orphans/cleanup-stopped or pass --allow-open-sessions intentionally.")

    if not resume_data:
        payload["post_cleanup_operator_status"] = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "operator-status",
            "--repo",
            str(repo),
            "--json",
        ], env=_managed_child_env())
        launch_blockers = _operator_status_blocks_launch(payload["post_cleanup_operator_status"], requested_runtime=runtime)
        payload["post_cleanup_launch_blockers"] = launch_blockers
        if launch_blockers and not args.allow_open_sessions:
            joined = "; ".join(launch_blockers)
            raise SystemExit(f"Refusing to launch while coding-terminal lifecycle is not clean after cleanup preflight: {joined}. Run doctor/orphans/cleanup-stopped or pass --allow-open-sessions intentionally.")

        reports_state = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "reports",
            "list",
            "--repo",
            str(repo),
            "--json",
        ], env=_managed_child_env())
        drifted = [report for report in (reports_state.get("reports") or []) if report.get("missing")]
        if drifted:
            payload["report_drift"] = {
                "count": len(drifted),
                "sessions": [report.get("session_label") for report in drifted],
                "hint": "Routed report copies are missing or drifted. Inspect with `python scripts/coding_terminal_runner.py reports repair --dry-run` before relying on routed reports; v1.0 does not auto-repair.",
            }

    initial_prompt_text = None
    if resume_data:
        manifest = str(resume_manifest)
        tmux_session = resume_data.get("tmux_session")
        if not tmux_session:
            raise SystemExit(f"Resume manifest is missing tmux_session: {resume_manifest}")
        if not args.dry_run and not resume_data.get("dry_run") and not _tmux_session_exists(tmux_session):
            raise SystemExit(f"Cannot resume; tmux session is not running: {tmux_session}")
        start_result = {
            "status": resume_data.get("status"),
            "manifest_path": manifest,
            "tmux_session": tmux_session,
            "resumed": True,
        }
    else:
        start_command = [
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "start",
            "--runtime",
            runtime,
            "--repo",
            str(repo),
            "--loadout",
            loadout,
            "--label",
            label,
            "--project-slug",
            project_slug,
            "--managed-launcher",
            "run_loaded_agent.py",
            "--managed-launch-policy-version",
            MANAGED_LAUNCH_POLICY_VERSION,
            "--json",
        ]
        if not args.no_auto_watch:
            start_command.append("--watcher-required")
        if origin_verification.get("reportback_expected"):
            start_command.append("--origin-required")
        if origin_context:
            if origin_context.get("guild_id"):
                start_command.extend(["--discord-guild-id", origin_context["guild_id"]])
            if origin_context.get("channel_id"):
                start_command.extend(["--discord-channel-id", origin_context["channel_id"]])
            if origin_context.get("thread_id"):
                start_command.extend(["--discord-thread-id", origin_context["thread_id"]])
            if origin_context.get("thread_name"):
                start_command.extend(["--discord-thread-name", origin_context["thread_name"]])
        context_flag = {
            "session_title": "--session-title",
            "user_request": "--user-request",
            "conversation_goal": "--conversation-goal",
            "previous_work_summary": "--previous-work-summary",
            "next_question": "--next-question",
        }
        for key, flag in context_flag.items():
            if conversation_context.get(key):
                start_command.extend([flag, conversation_context[key]])
        if hermes_session_id:
            start_command.extend(["--hermes-session-id", hermes_session_id])
        if hermes_profile:
            start_command.extend(["--hermes-profile", hermes_profile])
        # Standard managed launches always require bypass posture.  The lower
        # start layer independently refuses managed launches without this flag.
        start_command.append("--bypass-permissions")
        # Persist the effective closeout policy into the manifest.  The
        # launcher default is safe auto-stop for fresh watched runs, so do not
        # only forward the raw CLI flag; otherwise direct run_loaded_agent
        # launches can advertise auto-stop in the payload while the manifest
        # records a manual/keep-open policy and leaves completed terminals up.
        if effective_stop_after_closeout:
            start_command.append("--stop-after-closeout")
        if args.keep_open_after_closeout:
            start_command.append("--keep-open-after-closeout")
            start_command.extend(["--keep-open-reason", "cli:--keep-open-after-closeout"])
        for directory in additional_dirs:
            start_command.extend(["--add-dir", directory])
        initial_prompt_text = None
        if codex_initial_prompt:
            initial_prompt_text = _prepare_managed_prompt(
                task=task,
                runtime=runtime,
                loadout=loadout,
                repo=repo,
                project_slug=project_slug,
            )
            start_command.extend(["--initial-prompt", initial_prompt_text])
        if managed_launch["terminal_visible"]:
            start_command.append("--visible")
        start_command.extend(["--terminal-visibility-reason", managed_launch["terminal_visibility_reason"]])
        start_result = _json_command(start_command, env=_managed_child_env())
        manifest = start_result["manifest_path"]
        if not args.no_visible and start_result.get("status") == "blocked" and not start_result.get("clients"):
            raise SystemExit(
                "Refusing to continue hidden: visible terminal launch was requested but no desktop/tmux client attached. "
                f"Manifest: {manifest}. Attach manually with: tmux attach -t {start_result['tmux_session']}"
            )
    payload.update(start_result)
    payload["tmux_attach"] = f"tmux attach -t {start_result['tmux_session']}"
    closeout_policy = start_result.get("terminal_closeout_policy") or {}
    if closeout_policy:
        # The persisted policy is authoritative for both foreground and
        # detached watcher close behavior.
        effective_stop_after_closeout = bool(
            closeout_policy.get("auto_close_finished_terminals")
        ) and not closeout_policy.get("keep_open_after_closeout")
        payload["terminal_closeout_policy"] = closeout_policy
        payload["stop_after_closeout"] = effective_stop_after_closeout

    if codex_initial_prompt:
        payload["send_result"] = _record_initial_prompt_artifact(
            manifest_path=manifest,
            raw_task=task,
            prompt_text=initial_prompt_text or task,
        )
    else:
        if args.goal:
            goal_command = _build_goal_command(args.goal)
            payload["goal_command"] = goal_command
            payload["goal_send_result"] = _json_command([
                sys.executable,
                str(ROOT / "scripts" / "coding_terminal_runner.py"),
                "send",
                "--manifest",
                manifest,
                "--prompt",
                goal_command,
                "--raw-prompt",
                "--json",
            ], env=_managed_child_env())
            payload["goal_sent_at"] = datetime.now(timezone.utc).isoformat()
        send_result = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "send",
            "--manifest",
            manifest,
            "--prompt",
            task,
            "--json",
        ], env=_managed_child_env())
        payload["send_result"] = send_result
        payload["task_sent_at"] = datetime.now(timezone.utc).isoformat()
        if args.goal:
            managed_launch["goal_sent_at"] = payload["goal_sent_at"]
            managed_launch["task_sent_at"] = payload["task_sent_at"]
            managed_launch["goal_task_order"] = "goal_first"

    if not args.no_auto_watch:
        watch_start_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "watch-start",
            "--manifest",
            manifest,
            "--timeout",
            str(args.auto_watch_seconds),
            "--event-only",
            "--event-driven",
            "--closeout-on-complete",
            "--manage-on-closeout",
            "--postback-transport",
            "auto",
            "--json",
        ]
        if args.postback_on_closeout:
            watch_start_cmd.append("--postback-on-closeout")
        completion_ingress_url = os.environ.get("HERMES_TERMINAL_COMPLETION_WEBHOOK_URL")
        if completion_ingress_url:
            # Pass URL explicitly so detached watcher processes do not depend on
            # ambient Hermes env inheritance. Secret stays env-only/redacted.
            watch_start_cmd.extend(["--completion-ingress-url", completion_ingress_url])
        if effective_stop_after_closeout:
            watch_start_cmd.append("--stop-after-closeout")
        payload["watcher"] = _json_command(watch_start_cmd, env=_managed_child_env())
        payload["watcher_status"] = _json_command([
            sys.executable,
            str(ROOT / "scripts" / "coding_terminal_runner.py"),
            "watch-status",
            "--manifest",
            manifest,
            "--json",
        ], env=_managed_child_env())

    launch_health = _launch_health(payload, auto_watch=not args.no_auto_watch)
    managed_launch["watcher_attached"] = _watcher_fields_present(payload)
    managed_launch["launch_health"] = launch_health
    payload["launch_health"] = launch_health

    if args.watch:
        timeout = args.closeout_timeout if args.closeout_timeout is not None else args.watch_seconds
        if args.closeout:
            closeout = _json_command([
                sys.executable,
                str(ROOT / "scripts" / "coding_terminal_runner.py"),
                "closeout",
                "--manifest",
                manifest,
                "--wait",
                "--timeout",
                str(timeout),
                "--json",
            ], env=_managed_child_env())
            payload["closeout"] = closeout
            if args.postback_on_closeout:
                postback_cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "coding_terminal_runner.py"),
                    "postback",
                    "scan",
                    "--repo",
                    str(repo),
                    "--transport",
                    "auto",
                    "--completion-ingress",
                    "--completion-ingress-transport",
                    "auto",
                    "--json",
                ]
                manifest_scope: dict[str, Any] = {}
                try:
                    manifest_scope = json.loads(Path(manifest).read_text(encoding="utf-8"))
                except OSError:
                    manifest_scope = {}
                managed_launcher = manifest_scope.get("managed_launcher") or payload.get("managed_launcher") or "run_loaded_agent.py"
                thread_id = manifest_scope.get("discord_thread_id") or (origin_context or {}).get("thread_id")
                session_id = manifest_scope.get("hermes_session_id") or hermes_session_id
                if managed_launcher:
                    postback_cmd.extend(["--owner", managed_launcher])
                if thread_id:
                    postback_cmd.extend(["--thread-id", thread_id])
                if session_id:
                    postback_cmd.extend(["--hermes-session-id", session_id])
                payload["postback"] = _json_command(postback_cmd, env=_managed_child_env())
            else:
                payload["postback"] = {"status": "disabled", "reason": "postback_on_closeout=false"}
            payload["latest_report"] = (
                closeout.get("project_report")
                or closeout.get("raw_report")
                or closeout.get("report_path")
            )
            should_stop = effective_stop_after_closeout and closeout.get("status") == "structured"
            payload["stop_after_closeout_applied"] = bool(should_stop)
            if should_stop:
                payload["stop_result"] = _json_command([
                    sys.executable,
                    str(ROOT / "scripts" / "coding_terminal_runner.py"),
                    "stop",
                    "--manifest",
                    manifest,
                    "--json",
                ], env=_managed_child_env())
        else:
            deadline = time.time() + timeout
            last_status: dict[str, Any] = {}
            while time.time() < deadline:
                last_status = _json_command([
                    sys.executable,
                    str(ROOT / "scripts" / "coding_terminal_runner.py"),
                    "status",
                    "--manifest",
                    manifest,
                    "--refresh",
                    "--json",
                ], env=_managed_child_env())
                if last_status.get("status") in TERMINAL_STATUSES:
                    break
                time.sleep(args.poll_interval)
            payload["last_status"] = last_status
            artifacts = last_status.get("artifacts") or {}
            payload["latest_report"] = last_status.get("latest_routed_report") or artifacts.get("latest_report")

    _emit(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
