#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.tmux_terminal import read_manifest, save_manifest


def _read_stdin() -> str:
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def _safe_json(raw: str) -> Any:
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_runtime_fields(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    fields: dict[str, Any] = {}
    for source, target in (
        ("session_id", "runtime_session_id"),
        ("turn_id", "runtime_turn_id"),
        ("transcript_path", "runtime_transcript_path"),
        ("last_assistant_message", "last_assistant_message"),
        ("hook_event_name", "hook_event_name"),
    ):
        value = payload.get(source)
        if value is not None:
            fields[target] = value
    return fields


def _manifest_status_after_event(current_status: str | None, event_status: str) -> str:
    """Return the manifest lifecycle status for a newly recorded runtime event.

    Claude's generic Stop hook records ``waiting_for_input`` after every turn.
    A deliberate continuation checkpoint can record ``waiting_for_continuation``
    from inside the turn immediately before that generic Stop hook fires.  The
    generic hook must not downgrade the first-class continuation state before
    the watcher/manager can see it.
    """
    if current_status == "waiting_for_continuation" and event_status == "waiting_for_input":
        return "waiting_for_continuation"
    return event_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Claude/Codex runtime lifecycle events into a Hermes coding-terminal manifest.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--status", default="waiting_for_input")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    raw = _read_stdin()
    payload = _safe_json(raw)
    try:
        manifest = read_manifest(manifest_path)
        artifacts = manifest.setdefault("artifacts", {})
        events_path = Path(artifacts.get("events") or Path(artifacts["root"]) / "events.jsonl")
        events_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": _stamp(),
            "runtime": args.runtime,
            "event": args.event,
            "status": args.status,
            "prompt_id": manifest.get("current_prompt_id") or manifest.get("last_prompt_id"),
            "prompt_started_at": manifest.get("current_prompt_started_at"),
            "payload": payload,
            "raw": raw if payload is None else None,
        }
        record.update(_normalized_runtime_fields(payload))
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        manifest["status"] = _manifest_status_after_event(manifest.get("status"), args.status)
        manifest["last_runtime_event"] = record
        artifacts["events"] = str(events_path)
        save_manifest(manifest_path, manifest)
        print("{}")
    except Exception as exc:
        fallback = {
            "timestamp": _stamp(),
            "runtime": args.runtime,
            "event": args.event,
            "status": "failed",
            "error": str(exc),
            "raw": raw,
        }
        try:
            fallback_path = manifest_path.with_suffix(".events.failed.jsonl")
            with fallback_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(fallback, ensure_ascii=False) + "\n")
        except Exception:
            pass
        print(f"record_runtime_event: failed to update manifest {manifest_path}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
