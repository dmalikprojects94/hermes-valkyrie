from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import Any

from scripts.runtime_adapters import resolve_real_home

VALID_STATUSES = {"starting", "ready", "working", "waiting_for_input", "blocked", "finished", "failed", "stale", "needs_attention"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, *, fallback: str = "session") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def make_tmux_session_name(runtime: str, session_label: str) -> str:
    base = f"hermes-{slugify(runtime)}-{slugify(session_label)}"
    return base[:80].rstrip("-")


def artifact_paths(root: Path) -> dict[str, str]:
    root = Path(root)
    return {
        "root": str(root),
        "inputs": str(root / "inputs"),
        "snapshots": str(root / "snapshots"),
        "reports": str(root / "reports"),
        "events": str(root / "events.jsonl"),
        "runtime_settings": str(root / "runtime-settings.json"),
        "manifest": str(root / "manifest.json"),
        "watcher_result": str(root / "watcher-result.json"),
        "watcher_log": str(root / "watcher.log"),
        "watcher_pid": str(root / "watcher.pid"),
        "latest_snapshot": str(root / "latest-snapshot.txt"),
        "last_snapshot": "",
        "latest_report": "",
    }


@dataclass
class TerminalManifest:
    schema_version: int
    runtime: str
    repo_path: str
    loadout: str
    session_label: str
    tmux_session: str
    created_at: str
    updated_at: str
    status: str
    artifacts: dict[str, str]
    launch_env: dict[str, str]
    last_prompt_id: str | None = None
    dry_run: bool = False

    @classmethod
    def create(
        cls,
        *,
        runtime: str,
        repo_path: Path,
        loadout: str = "default",
        session_label: str,
        launch_env: dict[str, str] | None = None,
        artifact_root: Path | None = None,
        dry_run: bool = False,
    ) -> "TerminalManifest":
        label_slug = slugify(session_label)
        root = artifact_root or (Path(repo_path) / ".hermes" / "coding-terminals" / label_slug)
        now = utc_now()
        return cls(
            schema_version=1,
            runtime=runtime,
            repo_path=str(Path(repo_path)),
            loadout=loadout,
            session_label=session_label,
            tmux_session=make_tmux_session_name(runtime, session_label),
            created_at=now,
            updated_at=now,
            status="starting",
            artifacts=artifact_paths(root),
            launch_env=launch_env or {},
            dry_run=dry_run,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ensure_artifact_dirs(manifest: TerminalManifest | dict[str, Any]) -> None:
    data = manifest.to_dict() if isinstance(manifest, TerminalManifest) else manifest
    artifacts = data["artifacts"]
    for key in ("root", "inputs", "snapshots", "reports"):
        Path(artifacts[key]).mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def write_manifest(manifest: TerminalManifest) -> Path:
    ensure_artifact_dirs(manifest)
    path = Path(manifest.artifacts["manifest"])
    _atomic_write_json(path, manifest.to_dict())
    return path


def read_manifest(path: Path) -> dict[str, Any]:
    path = Path(path)
    last_error: Exception | None = None
    for _ in range(5):
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            last_error = exc
            time.sleep(0.02)
    assert last_error is not None
    raise last_error


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = utc_now()
    _atomic_write_json(Path(path), data)


def update_manifest_status(
    path: Path,
    status: str,
    *,
    reason: str = "status update",
    actor: str = "runner",
    **artifact_updates: str,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    from scripts.terminal_lifecycle import transition_manifest_status

    data = read_manifest(path)
    transition_manifest_status(data, status, reason=reason, actor=actor)
    data.setdefault("artifacts", {}).update({k: v for k, v in artifact_updates.items() if v is not None})
    save_manifest(path, data)
    return data


def build_paste_prompt_commands(tmux_session: str, prompt: str) -> list[list[str]]:
    return [
        ["tmux", "load-buffer", "-", prompt],
        ["tmux", "paste-buffer", "-t", tmux_session],
        ["tmux", "send-keys", "-t", tmux_session, "Enter"],
    ]


def run_tmux(argv: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, input=input_text, capture_output=True, text=True, check=check)


def create_tmux_session(session_name: str, command: str, *, width: int = 140, height: int = 40, environment: dict[str, str] | None = None) -> None:
    run_tmux(["tmux", "new-session", "-d", "-s", session_name, "-x", str(width), "-y", str(height), command])
    for key, value in (environment or {}).items():
        run_tmux(["tmux", "set-environment", "-t", session_name, key, value])


def desktop_attach_command(session_name: str, *, title: str) -> list[str]:
    shell_command = f"export HOME={shlex.quote(resolve_real_home())}; tmux attach-session -t {session_name}"
    if shutil.which("xterm"):
        return ["xterm", "-T", title, "-e", "bash", "-lc", shell_command]
    terminal = shutil.which("x-terminal-emulator")
    if terminal:
        return [terminal, "-T", title, "-e", "bash", "-lc", shell_command]
    raise RuntimeError("No supported desktop terminal found for visible tmux attach")


def desktop_attach_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return env suitable for opening a desktop terminal from Hermes.

    Hermes gateway/tool subprocesses can have a stripped shell env even while
    the user session has DISPLAY/WAYLAND/XAUTHORITY registered with systemd.
    Pull those values from `systemctl --user show-environment` so visible
    launches do not silently degrade into tmux-only sessions.
    """
    env = dict(base or os.environ)
    wanted = {"DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "XAUTHORITY"}
    if all(env.get(key) for key in ("DISPLAY", "XDG_RUNTIME_DIR")):
        return env
    completed = subprocess.run(
        ["systemctl", "--user", "show-environment"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        for line in completed.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in wanted and value and not env.get(key):
                env[key] = value
    return env


def open_desktop_client(session_name: str, *, title: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        desktop_attach_command(session_name, title=title),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=desktop_attach_environment(),
        text=True,
    )


def desktop_window_ids_for_title(title: str) -> list[str]:
    """Return desktop window ids matching a visible terminal title.

    tmux ``list-clients`` only proves a PTY client attached to the session. It
    does not prove a GUI window opened on the operator's desktop. On this GNOME/XWayland
    setup, xterm windows are discoverable through xdotool; use that as the
    extra desktop-window proof when available.
    """
    if not shutil.which("xdotool"):
        return []
    completed = subprocess.run(
        ["xdotool", "search", "--name", title],
        capture_output=True,
        text=True,
        check=False,
        env=desktop_attach_environment(),
    )
    if completed.returncode != 0:
        return []
    window_ids = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if window_ids:
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", window_ids[-1]],
            capture_output=True,
            text=True,
            check=False,
            env=desktop_attach_environment(),
        )
    return window_ids


def list_clients(session_name: str) -> str:
    completed = subprocess.run(["tmux", "list-clients", "-t", session_name], capture_output=True, text=True, check=False)
    return completed.stdout.strip()


def send_literal_prompt(session_name: str, prompt: str, *, enter_count: int = 1, enter_delay: float = 0.35) -> None:
    run_tmux(["tmux", "load-buffer", "-"], input_text=prompt)
    run_tmux(["tmux", "paste-buffer", "-t", session_name])
    import time
    time.sleep(enter_delay)
    for _ in range(enter_count):
        run_tmux(["tmux", "send-keys", "-t", session_name, "Enter"])
        if enter_count > 1:
            time.sleep(enter_delay)


def capture_pane(session_name: str, *, start: int = -200) -> str:
    completed = run_tmux(["tmux", "capture-pane", "-t", session_name, "-p", "-S", str(start)])
    return completed.stdout


def kill_session(session_name: str) -> None:
    subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True, text=True, check=False)


def session_exists(session_name: str) -> bool:
    return subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True, text=True).returncode == 0
