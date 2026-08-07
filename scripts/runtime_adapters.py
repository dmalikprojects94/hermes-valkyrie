from __future__ import annotations

from dataclasses import dataclass
import os
import shlex

from scripts.report_extractor import HEADINGS, heading_pattern
from scripts.runtime_home import resolve_runtime_home


DEFAULT_CLAUDE_MODEL = "claude-fable-5"
MANAGED_BYPASS_POSTURE = "managed_bypass_required"
MANUAL_DIAGNOSTIC_POSTURE = "manual_diagnostic"
RUNTIME_BYPASS_FLAGS = {
    "claude": "--dangerously-skip-permissions",
    "codex": "--dangerously-bypass-approvals-and-sandbox",
}


class ManagedBypassRequiredError(ValueError):
    """Raised when a managed launch attempts to build a no-bypass runtime command."""


def required_bypass_flag(runtime: str) -> str:
    return RUNTIME_BYPASS_FLAGS[runtime]


def permission_posture_metadata(runtime: str, *, bypass_permissions: bool, permission_posture: str) -> dict[str, object]:
    flag = required_bypass_flag(runtime)
    return {
        "permission_posture": permission_posture,
        "bypass_permissions_effective": bool(bypass_permissions),
        "required_runtime_bypass_flag": flag,
        "required_bypass_flag_present": bool(bypass_permissions),
    }


def enforce_permission_posture(runtime: str, *, bypass_permissions: bool, permission_posture: str) -> None:
    if permission_posture == MANAGED_BYPASS_POSTURE and not bypass_permissions:
        raise ManagedBypassRequiredError(
            "Refusing managed launch without bypass permissions: "
            "managed Claude/Codex sessions must launch with bypass-required posture."
        )


def resolve_codex_model() -> str:
    """Return the Codex model pinned for a managed launch, if any."""
    return (
        os.environ.get("HERMES_CODEX_MODEL")
        or os.environ.get("CODEX_MODEL")
        or ""
    ).strip()


def resolve_real_home() -> str:
    return resolve_runtime_home()


def resolve_claude_model() -> str:
    """Return the Claude Code model pinned for managed Hermes launches."""
    return (
        os.environ.get("HERMES_CLAUDE_MODEL")
        or os.environ.get("CLAUDE_CODE_MODEL")
        or DEFAULT_CLAUDE_MODEL
    ).strip()


@dataclass(frozen=True)
class RuntimeAdapter:
    runtime: str
    binary: str

    def launch_command(
        self,
        *,
        repo_path: str,
        prompt: str | None = None,
        bypass_permissions: bool = False,
        permission_posture: str = MANUAL_DIAGNOSTIC_POSTURE,
        add_dirs: list[str] | None = None,
        settings_path: str | None = None,
        extra_env: dict[str, str] | None = None,
        config_overrides: list[str] | None = None,
        model: str | None = None,
    ) -> str:
        raise NotImplementedError

    def _env_prefix(self, extra_env: dict[str, str] | None = None) -> list[str]:
        env = {"HOME": resolve_real_home()}
        if extra_env:
            env.update(extra_env)
        return [f"{key}={shlex.quote(str(value))}" for key, value in env.items()]

    def startup_acceptance_steps(self) -> list[str]:
        return []

    def detect_status(self, captured_text: str) -> str:
        text = captured_text.lower()
        if self.has_completion_report(captured_text):
            return "finished"
        if any(token in text for token in self.working_markers()):
            return "working"
        if any(token in captured_text for token in self.waiting_markers()):
            return "waiting_for_input"
        if any(token in text for token in self.blocked_markers()):
            return "blocked"
        return "blocked"

    def has_completion_report(self, captured_text: str) -> bool:
        return set(heading_pattern().findall(captured_text)) >= set(HEADINGS)

    def completion_markers(self) -> list[str]:
        return ["Request", "Changes", "Verification", "Blockers", "Next Steps"]

    def blocked_markers(self) -> list[str]:
        return [
            "trust this folder",
            "do you trust",
            "permission denied",
            "authentication failed",
            "cannot continue",
            "needs user input",
            "not inside",
        ]

    def working_markers(self) -> list[str]:
        return ["●", "thinking", "running", "reading", "editing", "working"]

    def waiting_markers(self) -> list[str]:
        return ["❯", "›", "> "]

    def default_artifact_subdir(self) -> str:
        return self.runtime


@dataclass(frozen=True)
class ClaudeAdapter(RuntimeAdapter):
    runtime: str = "claude"
    binary: str = "claude"

    def launch_command(
        self,
        *,
        repo_path: str,
        prompt: str | None = None,
        bypass_permissions: bool = False,
        permission_posture: str = MANUAL_DIAGNOSTIC_POSTURE,
        add_dirs: list[str] | None = None,
        settings_path: str | None = None,
        extra_env: dict[str, str] | None = None,
        config_overrides: list[str] | None = None,
        model: str | None = None,
    ) -> str:
        enforce_permission_posture(self.runtime, bypass_permissions=bypass_permissions, permission_posture=permission_posture)
        parts = ["cd", shlex.quote(repo_path), "&&", *self._env_prefix(extra_env), "claude"]
        selected_model = (model or resolve_claude_model()).strip()
        if selected_model:
            parts.extend(["--model", shlex.quote(selected_model)])
        if settings_path:
            parts.extend(["--settings", shlex.quote(settings_path)])
        if bypass_permissions:
            parts.append("--dangerously-skip-permissions")
        for directory in add_dirs or []:
            parts.extend(["--add-dir", shlex.quote(directory)])
        if prompt:
            parts.append(shlex.quote(prompt))
        return " ".join(parts)

    def startup_acceptance_steps(self) -> list[str]:
        return ["trust-folder-enter", "permissions-down-enter-if-present"]

    def blocked_markers(self) -> list[str]:
        return [
            "trust this folder",
            "do you trust",
            "permission denied",
            "no, exit",
            "authentication failed",
            "cannot continue",
            "needs user input",
        ]

    def working_markers(self) -> list[str]:
        return ["esc to interrupt", "running", "reading", "editing", "thinking"]


@dataclass(frozen=True)
class CodexAdapter(RuntimeAdapter):
    runtime: str = "codex"
    binary: str = "codex"

    def launch_command(
        self,
        *,
        repo_path: str,
        prompt: str | None = None,
        bypass_permissions: bool = False,
        permission_posture: str = MANUAL_DIAGNOSTIC_POSTURE,
        add_dirs: list[str] | None = None,
        settings_path: str | None = None,
        extra_env: dict[str, str] | None = None,
        config_overrides: list[str] | None = None,
        model: str | None = None,
    ) -> str:
        enforce_permission_posture(self.runtime, bypass_permissions=bypass_permissions, permission_posture=permission_posture)
        parts = [
            "cd",
            shlex.quote(repo_path),
            "&&",
            *self._env_prefix(extra_env),
            "codex",
            "--no-alt-screen",
        ]
        selected_model = (model or resolve_codex_model()).strip()
        if selected_model:
            parts.extend(["--model", shlex.quote(selected_model)])
        if config_overrides:
            parts.append("--dangerously-bypass-hook-trust")
            for override in config_overrides:
                parts.extend(["-c", shlex.quote(override)])
        if bypass_permissions:
            parts.append("--dangerously-bypass-approvals-and-sandbox")
        if prompt:
            if config_overrides:
                # Codex Stop hooks fire in the interactive/TUI runtime, not in
                # `codex exec`. When Hermes wires runtime-native completion
                # events, keep the session visible and pass the prompt directly.
                parts.append(shlex.quote(prompt))
            else:
                parts.extend(["exec", shlex.quote(prompt)])
        return " ".join(parts)

    def blocked_markers(self) -> list[str]:
        return [
            "not inside a trusted git repository",
            "not a git repository",
            "authentication failed",
            "login required",
            "cannot continue",
            "needs user input",
            "permission denied",
            "command failed and unresolved",
        ]

    def working_markers(self) -> list[str]:
        return ["thinking", "running command", "applying patch", "working", "tokens"]

    def detect_status(self, captured_text: str) -> str:
        if self.has_completion_report(captured_text):
            return "finished"
        text = captured_text.lower()
        press_enter_idx = text.rfind("press enter to continue")
        update_idx = text.rfind("update available")
        ready_idx = max(
            text.rfind("gpt-"),
            text.rfind("/model to change"),
            text.rfind("default ·"),
            text.rfind("directory:"),
        )
        if (press_enter_idx >= 0 or update_idx >= 0) and ready_idx < max(press_enter_idx, update_idx):
            return "blocked"
        return super().detect_status(captured_text)


def get_adapter(runtime: str) -> RuntimeAdapter:
    runtime = runtime.lower()
    if runtime == "claude":
        return ClaudeAdapter()
    if runtime == "codex":
        return CodexAdapter()
    raise KeyError(f"Unknown runtime: {runtime}")
