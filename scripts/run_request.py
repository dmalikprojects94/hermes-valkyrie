#!/usr/bin/env python3
"""
Managed run request contract (Slice 1).

A ``RunRequest`` is the deterministic launch-intent object Hermes builds
*before* any terminal is launched. It captures the original user request
verbatim, structural origin/routing metadata, and the resolved runtime/
loadout choice with the reason it was chosen.

This module does not launch Claude/Codex and does not mutate runtime homes.
It only builds, validates, and (de)serializes the request packet.
"""
from __future__ import annotations

import os
import hashlib
import json
from dataclasses import asdict, dataclass
from collections.abc import Mapping
from typing import Any

DEFAULT_RUNTIME = "claude"
DEFAULT_LOADOUT = "default"
DEFAULT_EXPECTED_RETURN = "result_packet"
DEFAULT_TERMINAL_VISIBLE = True
TERMINAL_VISIBLE_ENV = "HERMES_CODING_TERMINAL_VISIBLE"

SUPPORTED_RUNTIMES = ("claude", "codex")
# Claude Code permission modes plus codex's coarse gate. Fixed set so bad
# input fails loudly at request-build time rather than at launch.
APPROVAL_MODES = ("default", "acceptEdits", "plan", "bypassPermissions")

EXPLICIT_LOADOUT_REASON = "explicit"
DEFAULT_LOADOUT_REASON = "default"

_TRUE_VALUES = ("1", "true", "yes", "on", "visible")
_FALSE_VALUES = ("0", "false", "no", "off", "hidden", "invisible")


@dataclass(frozen=True)
class RunRequest:
    request_id: str
    original_user_request: str
    origin: dict[str, str]
    repo_path: str
    branch: str | None
    runtime: str
    loadout: str
    loadout_selection_reason: str
    slash_command: str | None
    slash_command_source: str | None
    approval_mode: str
    terminal_visible: bool
    terminal_visibility_reason: str
    created_prompt_path: str | None
    expected_return: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, **kwargs)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRequest":
        return cls(**data)

    @classmethod
    def from_json(cls, text: str) -> "RunRequest":
        return cls.from_dict(json.loads(text))


def _request_id(original_user_request: str, repo_path: str,
                origin: dict[str, str], nonce: str) -> str:
    # Canonical, order-independent digest so the same intent + nonce is stable
    # and any change to request/repo/origin/nonce changes the id.
    payload = json.dumps(
        {
            "request": original_user_request,
            "repo": repo_path,
            "origin": origin,
            "nonce": nonce,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"req_{digest[:16]}"


def resolve_terminal_visibility(
    terminal_visible: bool | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[bool, str]:
    """Resolve terminal visibility for the run request.

    Visible is the safe/default behavior. Operators can override it per launch
    with ``terminal_visible`` or by setting ``HERMES_CODING_TERMINAL_VISIBLE``.
    """
    if terminal_visible is not None:
        return bool(terminal_visible), "explicit"

    visibility_env: Mapping[str, str] = os.environ if env is None else env
    raw = visibility_env.get(TERMINAL_VISIBLE_ENV)
    if raw is None or not raw.strip():
        return DEFAULT_TERMINAL_VISIBLE, "default_visible"

    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True, f"env:{TERMINAL_VISIBLE_ENV}"
    if normalized in _FALSE_VALUES:
        return False, f"env:{TERMINAL_VISIBLE_ENV}"
    raise ValueError(
        f"unsupported {TERMINAL_VISIBLE_ENV}={raw!r}; "
        f"expected one of {_TRUE_VALUES + _FALSE_VALUES}"
    )


def build_run_request(
    *,
    original_user_request: str,
    repo_path: str,
    nonce: str,
    origin: dict[str, str] | None = None,
    branch: str | None = None,
    runtime: str | None = None,
    loadout: str | None = None,
    slash_command: str | None = None,
    slash_command_source: str | None = None,
    approval_mode: str = "default",
    terminal_visible: bool | None = None,
    env: Mapping[str, str] | None = None,
    created_prompt_path: str | None = None,
    expected_return: str = DEFAULT_EXPECTED_RETURN,
) -> RunRequest:
    """Build a deterministic ``RunRequest`` without launching anything.

    ``nonce`` is caller-supplied (a timestamp or unique token) so request ids
    are stable in tests and unique in production.
    """
    if not original_user_request or not original_user_request.strip():
        raise ValueError("original_user_request must be non-empty")
    if not repo_path or not repo_path.strip():
        raise ValueError("repo_path must be non-empty")
    if not nonce or not str(nonce).strip():
        raise ValueError("nonce must be non-empty")

    runtime = runtime or DEFAULT_RUNTIME
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(
            f"unsupported runtime {runtime!r}; expected one of {SUPPORTED_RUNTIMES}"
        )
    if approval_mode not in APPROVAL_MODES:
        raise ValueError(
            f"unsupported approval_mode {approval_mode!r}; expected one of {APPROVAL_MODES}"
        )

    if loadout:
        loadout_selection_reason = EXPLICIT_LOADOUT_REASON
    else:
        loadout = DEFAULT_LOADOUT
        loadout_selection_reason = DEFAULT_LOADOUT_REASON

    origin = dict(origin or {})
    resolved_visible, visibility_reason = resolve_terminal_visibility(
        terminal_visible=terminal_visible,
        env=env,
    )

    return RunRequest(
        request_id=_request_id(original_user_request, repo_path, origin, str(nonce)),
        original_user_request=original_user_request,
        origin=origin,
        repo_path=repo_path,
        branch=branch,
        runtime=runtime,
        loadout=loadout,
        loadout_selection_reason=loadout_selection_reason,
        slash_command=slash_command,
        slash_command_source=slash_command_source,
        approval_mode=approval_mode,
        terminal_visible=resolved_visible,
        terminal_visibility_reason=visibility_reason,
        created_prompt_path=created_prompt_path,
        expected_return=expected_return,
    )
