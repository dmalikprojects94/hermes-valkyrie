from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping


RUNTIME_HOME_PLACEHOLDERS = ("${RUNTIME_HOME}", "${HOME}")


def resolve_runtime_home(env: Mapping[str, str] | None = None) -> str:
    """Resolve the authenticated runtime home without private hardcoded defaults.

    Precedence is explicit Hermes override, generic real-home override, process
    HOME, then Python's home-directory resolver. The final fallback keeps local
    launches working while avoiding operator-specific literals in tracked source.
    """
    values = env if env is not None else os.environ
    for key in ("HERMES_REAL_HOME", "REAL_HOME", "HOME"):
        value = values.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return str(Path.home())


def render_runtime_home_placeholders(value: Any, *, runtime_home: str | None = None) -> Any:
    """Recursively replace runtime-home placeholders in loadout metadata."""
    resolved_home = runtime_home or resolve_runtime_home()
    if isinstance(value, str):
        rendered = value
        for placeholder in RUNTIME_HOME_PLACEHOLDERS:
            rendered = rendered.replace(placeholder, resolved_home)
        return rendered
    if isinstance(value, list):
        return [render_runtime_home_placeholders(item, runtime_home=resolved_home) for item in value]
    if isinstance(value, dict):
        return {
            key: render_runtime_home_placeholders(item, runtime_home=resolved_home)
            for key, item in value.items()
        }
    return value
