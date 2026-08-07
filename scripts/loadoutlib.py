from __future__ import annotations

import json
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from scripts.runtime_home import render_runtime_home_placeholders


RUNTIME_LABELS = {
    "claude": "Claude Code",
    "codex": "Codex",
}

RUNTIME_MAP_REQUIRED_KEYS = {
    "runtime",
    "managed_paths",
}


REQUIRED_FIELDS = {
    "name",
    "description",
    "aliases",
    "supported_runtimes",
    "routing",
    "purpose",
    "when_to_use",
    "when_not_to_use",
    "shared_instructions",
    "shared_skills",
    "packs",
    "session_policy",
    "runtime_overrides",
}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def load_loadouts(repo_root: Path | str) -> dict[str, dict[str, Any]]:
    repo_root = Path(repo_root)
    loadouts_dir = repo_root / "loadouts"
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(loadouts_dir.glob("*/loadout.yaml")):
        data = load_yaml(path)
        data["__path__"] = str(path)
        result[data["name"]] = data
    return result


def _runtime_map(repo_root: Path, runtime: str) -> dict[str, Any]:
    path = repo_root / "adapters" / runtime / "runtime-map.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing runtime map: {path}")
    data = load_yaml(path)
    missing = sorted(RUNTIME_MAP_REQUIRED_KEYS - set(data.keys()))
    if missing:
        raise KeyError(f"Runtime map {path} missing required fields {missing}")
    if data.get("runtime") != runtime:
        raise ValueError(f"Runtime map {path} declares runtime {data.get('runtime')} instead of {runtime}")
    managed_paths = data.get("managed_paths")
    if not isinstance(managed_paths, dict) or not managed_paths:
        raise ValueError(f"Runtime map {path} must define a non-empty managed_paths mapping")
    return data


def _merge_lists(base: list[Any], extra: list[Any]) -> list[Any]:
    merged = list(base)
    for item in extra:
        if item not in merged:
            merged.append(item)
    return merged


def _deep_merge(base: Any, extra: Any) -> Any:
    if isinstance(base, dict) and isinstance(extra, dict):
        merged = deepcopy(base)
        for key, value in extra.items():
            if key not in merged:
                merged[key] = deepcopy(value)
            else:
                merged[key] = _deep_merge(merged[key], value)
        return merged
    if isinstance(base, list) and isinstance(extra, list):
        return _merge_lists(base, extra)
    return deepcopy(extra)


def resolve_loadout(loadouts: dict[str, dict[str, Any]], name: str, _seen: set[str] | None = None) -> dict[str, Any]:
    if name not in loadouts:
        raise KeyError(f"Unknown loadout: {name}")
    seen = _seen or set()
    if name in seen:
        raise ValueError(f"Circular loadout inheritance detected at {name}")
    seen = set(seen)
    seen.add(name)

    current = deepcopy(loadouts[name])
    base_name = current.get("base")
    if not base_name:
        current["resolved_from"] = [current["name"]]
        return current

    base = resolve_loadout(loadouts, base_name, seen)
    merged = deepcopy(base)
    merged = _deep_merge(merged, current)
    merged["name"] = current["name"]
    merged["description"] = current["description"]
    merged["purpose"] = current["purpose"]
    merged["when_to_use"] = current["when_to_use"]
    merged["when_not_to_use"] = current["when_not_to_use"]
    merged["aliases"] = current.get("aliases", [])
    merged["supported_runtimes"] = current.get("supported_runtimes", merged.get("supported_runtimes", []))
    merged["routing"] = deepcopy(current.get("routing", {}))
    merged["session_policy"] = _deep_merge(base.get("session_policy", {}), current.get("session_policy", {}))
    merged["resolved_from"] = base.get("resolved_from", [base_name]) + [current["name"]]
    return merged


def _normalize_request_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(?:~|\.?\.?/)?(?:[\w.-]+/)+[\w.-]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _request_contains_phrase(request: str, phrase: str) -> bool:
    token = _normalize_request_text(phrase)
    if not token:
        return False
    haystack = f" {request} "
    return f" {token} " in haystack


def _find_by_alias(loadouts: dict[str, dict[str, Any]], candidate: str) -> str | None:
    text = candidate.strip().lower()
    for loadout in loadouts.values():
        aliases = [loadout["name"].lower(), *[a.lower() for a in loadout.get("aliases", [])]]
        if text in aliases:
            return loadout["name"]
    return None


def _explicit_loadout_from_request(
    *,
    loadouts: dict[str, dict[str, Any]],
    runtime: str,
    request_text: str,
) -> str | None:
    """Resolve operator phrases that explicitly select the loadout surface.

    These phrases are stronger than ordinary keyword routing. For example,
    "use Claude Code with deep coding, /goal research..." should select the
    deep-coding loadout even though "research" is also a valid routing keyword.
    """
    request = f" {_normalize_request_text(request_text)} "
    matches: list[tuple[int, int, str]] = []
    for raw in loadouts.values():
        resolved = resolve_loadout(loadouts, raw["name"])
        if runtime not in resolved.get("supported_runtimes", []):
            continue
        aliases = [resolved["name"], *resolved.get("aliases", [])]
        for alias in aliases:
            token = _normalize_request_text(alias)
            if not token:
                continue
            explicit_patterns = [
                f" with {token} ",
                f" with the {token} ",
                f" using {token} ",
                f" using the {token} ",
                f" via {token} ",
                f" via the {token} ",
                f" loadout {token} ",
            ]
            if any(pattern in request for pattern in explicit_patterns):
                matches.append((len(token), resolved.get("routing", {}).get("priority", 0), resolved["name"]))
                break
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][2]


def resolve_loadout_name(
    *,
    loadouts: dict[str, dict[str, Any]],
    runtime: str,
    request_text: str,
    explicit_loadout: str | None = None,
) -> str:
    runtime = runtime.lower()
    if explicit_loadout:
        matched = _find_by_alias(loadouts, explicit_loadout)
        if not matched:
            raise KeyError(f"Unknown loadout alias: {explicit_loadout}")
        resolved = resolve_loadout(loadouts, matched)
        if runtime not in resolved.get("supported_runtimes", []):
            raise ValueError(f"Loadout {matched} does not support runtime {runtime}")
        return matched

    explicit_request_loadout = _explicit_loadout_from_request(
        loadouts=loadouts,
        runtime=runtime,
        request_text=request_text,
    )
    if explicit_request_loadout:
        return explicit_request_loadout

    # Default must be sticky. Task keywords like "research", "planning", or
    # "front-end" describe work, not permission to swap in a specialty loadout.
    # Specialty loadouts are selected only by --loadout/alias or explicit
    # operator phrasing handled above ("with deep-coding", "loadout: research").
    defaults = []
    for raw in loadouts.values():
        resolved = resolve_loadout(loadouts, raw["name"])
        if runtime in resolved.get("supported_runtimes", []) and resolved.get("routing", {}).get("default"):
            defaults.append(resolved["name"])
    if not defaults:
        raise ValueError(f"No default loadout found for runtime {runtime}")
    return defaults[0]


def validate_loadouts(*, loadouts: dict[str, dict[str, Any]], repo_root: Path | str) -> list[str]:
    repo_root = Path(repo_root)
    errors: list[str] = []
    registry_path = repo_root / "adapters" / "claude" / "registry.yaml"
    registry = load_yaml(registry_path) if registry_path.exists() else {}
    runtime_maps: dict[str, dict[str, Any]] = {}
    for runtime in sorted(RUNTIME_LABELS):
        try:
            runtime_maps[runtime] = _runtime_map(repo_root, runtime)
        except Exception as exc:
            errors.append(f"runtime-map[{runtime}]: {exc}")
        if not _runtime_folder_start_dirs(repo_root, runtime):
            errors.append(f"Folder-Start[{runtime}]: missing loadouts/{runtime}/Folder-Start baseline surface")
    command_registry = set((registry.get("commands") or {}).keys())
    agent_registry = set((registry.get("agents") or {}).keys())
    command_meta = registry.get("commands") or {}
    agent_meta = registry.get("agents") or {}
    hook_registry = registry.get("hooks") or {}
    mcp_registry = registry.get("mcp_servers") or {}

    for name, loadout in loadouts.items():
        missing = sorted(REQUIRED_FIELDS - set(loadout.keys()))
        if missing:
            errors.append(f"{name}: missing required fields {missing}")
            continue
        base = loadout.get("base")
        if base and base not in loadouts:
            errors.append(f"{name}: unknown base loadout {base}")
        for instruction in loadout.get("shared_instructions", []):
            path = repo_root / "shared" / "instructions" / f"{instruction}.md"
            if not path.exists():
                errors.append(f"{name}: missing shared instruction {instruction}")
        for skill in loadout.get("shared_skills", []):
            path = repo_root / "shared" / "skills" / f"{skill}.md"
            if not path.exists():
                errors.append(f"{name}: missing shared skill {skill}")
        for pack in loadout.get("packs", []):
            path = repo_root / "shared" / "packs" / pack / "PACK.md"
            if not path.exists():
                errors.append(f"{name}: missing pack {pack}")
        overrides = loadout.get("runtime_overrides", {})
        for runtime in loadout.get("supported_runtimes", []):
            if runtime not in overrides:
                errors.append(f"{name}: missing runtime_overrides for {runtime}")
            if runtime not in runtime_maps:
                errors.append(f"{name}: runtime {runtime} has no valid runtime map")
        claude_overrides = overrides.get("claude", {}) or {}
        for command in claude_overrides.get("commands", []) or []:
            if command not in command_registry:
                errors.append(f"{name}: unknown Claude command {command}")
                continue
            source = (command_meta.get(command) or {}).get("source")
            if not source:
                errors.append(f"{name}: command {command} missing registry source")
            elif not (repo_root / source).exists():
                errors.append(f"{name}: command source missing on disk: {source}")
        for agent in claude_overrides.get("agents", []) or []:
            if agent not in agent_registry:
                errors.append(f"{name}: unknown Claude agent {agent}")
                continue
            source = (agent_meta.get(agent) or {}).get("source")
            if not source:
                errors.append(f"{name}: agent {agent} missing registry source")
            elif not (repo_root / source).exists():
                errors.append(f"{name}: agent source missing on disk: {source}")
        for hook in claude_overrides.get("hooks", []) or []:
            if hook not in hook_registry:
                errors.append(f"{name}: unknown Claude hook {hook}")
                continue
            source = (hook_registry.get(hook) or {}).get("source")
            if not source:
                errors.append(f"{name}: hook {hook} missing registry source")
                continue
            if not (repo_root / source).exists():
                errors.append(f"{name}: hook source missing on disk: {source}")
        for server in claude_overrides.get("mcp", []) or []:
            if server not in mcp_registry:
                errors.append(f"{name}: unknown Claude MCP server {server}")
                continue
            source = (mcp_registry.get(server) or {}).get("source")
            if not source:
                errors.append(f"{name}: mcp server {server} missing registry source")
                continue
            if not (repo_root / source).exists():
                errors.append(f"{name}: mcp source missing on disk: {source}")
        try:
            resolve_loadout(loadouts, name)
        except Exception as exc:  # pragma: no cover - defensive branch
            errors.append(f"{name}: {exc}")
    return errors


def _read_text(path: Path) -> str:
    return path.read_text().strip()


def _shared_instruction_text(repo_root: Path, identifiers: list[str]) -> list[str]:
    return [_read_text(repo_root / "shared" / "instructions" / f"{identifier}.md") for identifier in identifiers]


def _shared_skill_map(repo_root: Path, identifiers: list[str]) -> dict[str, str]:
    return {
        identifier: _read_text(repo_root / "shared" / "skills" / f"{identifier}.md")
        for identifier in identifiers
    }


def _pack_text(repo_root: Path, identifiers: list[str]) -> list[str]:
    return [_read_text(repo_root / "shared" / "packs" / identifier / "PACK.md") for identifier in identifiers]


def _claude_registry(repo_root: Path) -> dict[str, Any]:
    return load_yaml(repo_root / "adapters" / "claude" / "registry.yaml")


def _codex_command_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "adapters" / "codex" / "commands.yaml"
    return load_yaml(path) if path.exists() else {"commands": {}}


def _command_inventory(repo_root: Path, loadout: dict[str, Any], runtime: str) -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    if runtime == "claude":
        registry = _claude_registry(repo_root)
        runtime_cfg = loadout["runtime_overrides"].get("claude", {}) or {}
        for command in runtime_cfg.get("commands", []) or []:
            meta = (registry.get("commands") or {}).get(command, {}) or {}
            entries.append(
                {
                    "name": command,
                    "invocation": f"/{command}",
                    "kind": "claude_slash_command",
                    "title": str(meta.get("title") or command),
                    "purpose": str(meta.get("purpose") or ""),
                    "source": str(meta.get("source") or ""),
                    "status": "materialized",
                }
            )
    elif runtime == "codex":
        registry = _codex_command_registry(repo_root)
        for command, meta in sorted((registry.get("commands") or {}).items()):
            entries.append(
                {
                    "name": command,
                    "invocation": f"/{command}",
                    "kind": "codex_native_slash_command",
                    "title": str(meta.get("title") or command),
                    "purpose": str(meta.get("purpose") or ""),
                    "source": str(meta.get("source") or "native"),
                    "status": "tracked_native",
                }
            )
        for skill in loadout.get("shared_skills", []) or []:
            source = f"shared/skills/{skill}.md"
            entries.append(
                {
                    "name": skill,
                    "invocation": f"/{skill}",
                    "kind": "codex_skill_trigger",
                    "title": skill.replace("-", " ").title(),
                    "purpose": "Hermes-managed skill available to Codex; slash form is a command-equivalent trigger when the skill documents it or the operator invokes it by name.",
                    "source": source,
                    "status": "materialized_skill",
                }
            )
    else:
        raise ValueError(f"Unsupported runtime for command inventory: {runtime}")

    return {
        "schema_version": 1,
        "runtime": runtime,
        "runtime_label": RUNTIME_LABELS.get(runtime, runtime),
        "loadout": loadout["name"],
        "resolved_from": loadout.get("resolved_from", [loadout["name"]]),
        "commands": entries,
    }


def _render_command_inventory_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        f"# Command Inventory: {inventory['runtime_label']} / {inventory['loadout']}",
        "",
        "Generated by the Hermes terminal loadout system during `apply_loadout`.",
        "Machine-readable source: `command-inventory.json`.",
        "",
        "| Invocation | Kind | Source | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    for item in inventory.get("commands", []):
        purpose = str(item.get("purpose") or "").replace("\n", " ").replace("|", "\\|")
        source = str(item.get("source") or "").replace("|", "\\|")
        lines.append(f"| `{item['invocation']}` | {item['kind']} | `{source}` | {purpose} |")
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "Run `python scripts/list_runtime_commands.py --runtime <claude|codex> --loadout <name>` from the loadout repo to regenerate this view without launching a terminal agent.",
        ]
    )
    return "\n".join(lines)


def _write_command_inventory(repo_root: Path, root: Path, loadout: dict[str, Any], runtime: str) -> list[str]:
    inventory = _command_inventory(repo_root, loadout, runtime)
    json_path = root / "command-inventory.json"
    md_path = root / "command-inventory.md"
    _write_text(json_path, json.dumps(inventory, indent=2))
    _write_text(md_path, _render_command_inventory_markdown(inventory))
    return [str(json_path), str(md_path)]


def _copy_file(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return str(destination)


def _copy_tree(source: Path, destination: Path) -> list[str]:
    copied: list[str] = []
    if not source.exists():
        return copied
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        try:
            target.chmod(path.stat().st_mode)
        except PermissionError:
            pass
        copied.append(str(target))
    return copied


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _clear_runtime_paths(root: Path, paths: list[str]) -> None:
    for rel in paths:
        _remove_path(root / rel)


def _runtime_folder_start_dirs(repo_root: Path, runtime: str) -> list[Path]:
    """Return baseline runtime surfaces copied into every loadout.

    The canonical layout is runtime-scoped: loadouts/<runtime>/Folder-Start.
    A legacy loadout-scoped fallback is accepted so older branches can still
    validate during migrations.
    """
    candidates = [
        repo_root / "loadouts" / runtime / "Folder-Start",
        repo_root / "loadouts" / "Folder-Start" / runtime,
    ]
    return [path for path in candidates if path.exists() and path.is_dir()]


def _loadout_surface_dirs(repo_root: Path, loadout: dict[str, Any], runtime: str) -> list[Path]:
    surfaces: list[Path] = []
    surfaces.extend(_runtime_folder_start_dirs(repo_root, runtime))
    for name in loadout.get("resolved_from", [loadout["name"]]):
        candidate = repo_root / "loadouts" / name / runtime
        if candidate.exists() and candidate.is_dir():
            surfaces.append(candidate)
    return surfaces


def _ensure_clean_dir(path: Path) -> None:
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")


def _format_cwd_label(cwd: str | None) -> str:
    if not cwd:
        return "n/a"
    path = Path(cwd).expanduser()
    name = path.name.strip()
    if name:
        return name
    return str(path)


def _runtime_launch_metadata(loadout: dict[str, Any], runtime: str) -> dict[str, Any]:
    runtime_block = (loadout.get("runtime_overrides", {}) or {}).get(runtime, {}) or {}
    launch = runtime_block.get("launch", {}) or {}
    return render_runtime_home_placeholders(deepcopy(launch))


def _runtime_doctrine_metadata(runtime_map: dict[str, Any]) -> dict[str, Any]:
    """Return source-accounted runtime bootstrap/tool-map metadata for manifests."""
    return {
        "runtime_bootstrap": deepcopy(runtime_map.get("bootstrap", {})),
        "runtime_tool_map": deepcopy(runtime_map.get("tool_map", {})),
        "runtime_capabilities": deepcopy(runtime_map.get("capabilities", {})),
    }


def _materialize_runtime_doctrine(repo_root: Path, root: Path, runtime_map: dict[str, Any]) -> list[str]:
    """Copy shared runtime bootstrap/tool-map doctrine to runtime-specific surfaces."""
    managed: list[str] = []
    for key in ("bootstrap", "tool_map"):
        block = runtime_map.get(key) or {}
        shared_intent = block.get("shared_intent")
        target = block.get("materialized_to")
        if not shared_intent or not target:
            continue
        source = repo_root / shared_intent
        if not source.exists():
            raise FileNotFoundError(f"Runtime doctrine source missing: {source}")
        managed.append(_copy_file(source, root / target))
    return managed


def _format_launch_section(launch: dict[str, Any]) -> str:
    if not launch:
        return "- No runtime-specific launch metadata"

    lines: list[str] = []
    env = launch.get("env") or {}
    if env:
        lines.append("### Environment")
        lines.extend(f"- `{key}={value}`" for key, value in env.items())

    command_prefix = launch.get("command_prefix")
    if command_prefix:
        lines.append("### Command prefix")
        lines.append(f"- `{command_prefix}`")

    examples = launch.get("examples") or {}
    if examples:
        lines.append("### Examples")
        lines.extend(f"- **{label.replace('_', ' ')}:** `{command}`" for label, command in examples.items())

    notes = launch.get("notes") or []
    if notes:
        lines.append("### Notes")
        lines.extend(f"- {note}" for note in notes)

    return "\n".join(lines)


def format_launch_notice(result: dict[str, Any]) -> str:
    runtime = str(result["runtime"]).lower()
    runtime_label = result.get("runtime_label") or RUNTIME_LABELS.get(runtime, runtime)
    session_policy = result.get("session_policy") or {}
    session_mode = "fresh" if session_policy.get("prefer_fresh_session") else "reuse"
    cwd_label = _format_cwd_label(result.get("cwd"))
    return (
        f"{runtime_label.upper()} | "
        f"loadout: {result['loadout']} | "
        f"session: {session_mode} | "
        f"cwd: {cwd_label}"
    )


def _render_skill_doc(skill_name: str, skill_text: str) -> str:
    body = skill_text.strip()
    return (
        f"---\n"
        f"name: {skill_name}\n"
        f"description: Shared loadout skill materialized by Hermes terminal loadouts\n"
        f"---\n\n"
        f"{body}\n"
    )


def _materialize_hooks(
    repo_root: Path,
    root: Path,
    registry: dict[str, Any],
    hooks_dir_name: str,
    hook_ids: list[str],
) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
    hooks_dir = root / hooks_dir_name
    _ensure_clean_dir(hooks_dir)

    registry_hooks = registry.get("hooks") or {}
    hooks_json: dict[str, list[dict[str, str]]] = {}
    managed: list[str] = []

    for hook_id in hook_ids:
        meta = registry_hooks.get(hook_id)
        if not meta:
            raise KeyError(f"Hook {hook_id} not registered in adapters/claude/registry.yaml")
        source = meta.get("source")
        if not source:
            raise KeyError(f"Hook {hook_id} missing source path in registry")
        source_path = repo_root / source
        if not source_path.exists():
            raise FileNotFoundError(f"Hook source missing: {source_path}")

        target_path = hooks_dir / Path(source).name
        shutil.copyfile(source_path, target_path)
        try:
            target_path.chmod(0o755)
        except PermissionError:
            pass
        managed.append(str(target_path))

        event = meta.get("event", "PreToolUse")
        matcher = meta.get("matcher", "*")
        hooks_json.setdefault(event, []).append(
            {
                "id": hook_id,
                "matcher": matcher,
                "command": f"node hooks/{Path(source).name}",
            }
        )

    hooks_manifest = root / "hooks.json"
    _write_text(hooks_manifest, json.dumps(hooks_json, indent=2))
    managed.append(str(hooks_manifest))
    return managed, hooks_json


def _materialize_mcp(
    repo_root: Path,
    root: Path,
    registry: dict[str, Any],
    mcp_dir_name: str,
    server_ids: list[str],
    loadout_name: str,
) -> list[str]:
    mcp_dir = root / mcp_dir_name
    _ensure_clean_dir(mcp_dir)

    registry_servers = registry.get("mcp_servers") or {}
    merged: dict[str, Any] = {"mcpServers": {}}

    for server_id in server_ids:
        meta = registry_servers.get(server_id)
        if not meta:
            raise KeyError(f"MCP server {server_id} not registered in adapters/claude/registry.yaml")
        source = meta.get("source")
        if not source:
            raise KeyError(f"MCP server {server_id} missing source path in registry")
        source_path = repo_root / source
        if not source_path.exists():
            raise FileNotFoundError(f"MCP server config missing: {source_path}")
        server_data = json.loads(source_path.read_text())
        servers = server_data.get("mcpServers") or {}
        if server_id not in servers:
            raise KeyError(f"MCP server {server_id} missing mcpServers.{server_id} entry in {source_path}")
        merged["mcpServers"][server_id] = servers[server_id]

    servers_file = mcp_dir / "servers.json"
    _write_text(servers_file, json.dumps(merged, indent=2))

    active_file = mcp_dir / "active.mcp.json"
    active_payload = {
        "active_loadout": loadout_name,
        "servers": server_ids,
        "servers_file": "servers.json",
    }
    _write_text(active_file, json.dumps(active_payload, indent=2))

    return [str(servers_file), str(active_file)]


def _materialize_claude(repo_root: Path, root: Path, loadout: dict[str, Any]) -> list[str]:
    registry = _claude_registry(repo_root)
    runtime_map = _runtime_map(repo_root, "claude")
    managed_paths = runtime_map["managed_paths"]
    clear_paths = [
        managed_paths["claude_md"],
        managed_paths["commands_dir"],
        managed_paths["agents_dir"],
        managed_paths["skills_dir"],
        managed_paths.get("rules_dir", "rules"),
        managed_paths.get("templates_dir", "templates"),
        managed_paths.get("bin_dir", "bin"),
        managed_paths["hooks_dir"],
        managed_paths["mcp_dir"],
        managed_paths["metadata_file"],
        "command-inventory.json",
        "command-inventory.md",
        "hooks.json",
    ]
    _clear_runtime_paths(root, clear_paths)

    commands_dir = root / managed_paths["commands_dir"]
    agents_dir = root / managed_paths["agents_dir"]
    skills_dir = root / managed_paths["skills_dir"]
    rules_dir = root / managed_paths.get("rules_dir", "rules")

    commands_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    rules_dir.mkdir(parents=True, exist_ok=True)

    runtime = loadout["runtime_overrides"]["claude"]
    skills = _shared_skill_map(repo_root, loadout.get("shared_skills", []))

    commands = runtime.get("commands", [])
    agents = runtime.get("agents", [])
    hooks = runtime.get("hooks", []) or []
    mcp_servers = runtime.get("mcp", []) or []

    managed: list[str] = []
    managed.extend(_materialize_runtime_doctrine(repo_root, root, runtime_map))
    for surface_dir in _loadout_surface_dirs(repo_root, loadout, "claude"):
        managed.extend(_copy_tree(surface_dir, root))

    for command in commands:
        meta = registry["commands"][command]
        source = meta.get("source")
        if not source:
            raise KeyError(f"Claude command {command} missing registry source")
        source_path = repo_root / source
        if not source_path.exists():
            raise FileNotFoundError(f"Claude command source missing: {source_path}")
        command_path = commands_dir / f"{command}.md"
        managed.append(_copy_file(source_path, command_path))

    for agent in agents:
        meta = registry["agents"][agent]
        source = meta.get("source")
        if not source:
            raise KeyError(f"Claude agent {agent} missing registry source")
        source_path = repo_root / source
        if not source_path.exists():
            raise FileNotFoundError(f"Claude agent source missing: {source_path}")
        agent_path = agents_dir / f"{agent}.md"
        managed.append(_copy_file(source_path, agent_path))

    for idx, identifier in enumerate(loadout.get("shared_instructions", []), start=1):
        source = repo_root / "shared" / "instructions" / f"{identifier}.md"
        target = rules_dir / f"{idx:02d}-instruction-{identifier}.md"
        managed.append(_copy_file(source, target))

    for idx, identifier in enumerate(loadout.get("packs", []), start=90):
        source = repo_root / "shared" / "packs" / identifier / "PACK.md"
        target = rules_dir / f"{idx:02d}-pack-{identifier}.md"
        managed.append(_copy_file(source, target))

    for skill_name, skill_text in skills.items():
        skill_path = skills_dir / skill_name / "SKILL.md"
        _write_text(skill_path, _render_skill_doc(skill_name, skill_text))
        managed.append(str(skill_path))

    hook_files, hooks_json = _materialize_hooks(
        repo_root,
        root,
        registry,
        managed_paths["hooks_dir"],
        hooks,
    )
    mcp_files = _materialize_mcp(
        repo_root,
        root,
        registry,
        managed_paths["mcp_dir"],
        mcp_servers,
        loadout["name"],
    )

    managed.extend(hook_files)
    managed.extend(mcp_files)
    managed.extend(_write_command_inventory(repo_root, root, loadout, "claude"))
    return sorted(set(managed))


MANAGED_CONFIG_START = "# >>> hermes-terminal-loadout >>>"
MANAGED_CONFIG_END = "# <<< hermes-terminal-loadout <<<"


def _render_codex_config(loadout: dict[str, Any]) -> str:
    runtime_cfg = loadout["runtime_overrides"]["codex"].get("config", {})
    lines = [MANAGED_CONFIG_START, "[hermes_terminal_loadout]"]
    lines.append(f'active = "{loadout["name"]}"')
    for key, value in runtime_cfg.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, bool):
            lines.append(f'{key} = {str(value).lower()}')
        else:
            lines.append(f'{key} = {value}')
    lines.append(MANAGED_CONFIG_END)
    return "\n".join(lines)


def _merge_codex_config(existing: str, managed_block: str) -> str:
    existing = existing.strip()
    if MANAGED_CONFIG_START in existing and MANAGED_CONFIG_END in existing:
        before = existing.split(MANAGED_CONFIG_START, 1)[0].rstrip()
        after = existing.split(MANAGED_CONFIG_END, 1)[1].lstrip()
        parts = [part for part in [before, managed_block, after] if part]
        return "\n\n".join(parts) + "\n"
    if existing:
        return existing + "\n\n" + managed_block + "\n"
    return managed_block + "\n"


def _materialize_codex(repo_root: Path, root: Path, loadout: dict[str, Any]) -> list[str]:
    runtime_map = _runtime_map(repo_root, "codex")
    managed_paths = runtime_map["managed_paths"]
    _clear_runtime_paths(
        root,
        [
            managed_paths["skills_dir"],
            managed_paths["memories_dir"],
            managed_paths["metadata_file"],
            "command-inventory.json",
            "command-inventory.md",
        ],
    )
    skills_dir = root / managed_paths["skills_dir"]
    memories_dir = root / managed_paths["memories_dir"]
    skills_dir.mkdir(parents=True, exist_ok=True)
    memories_dir.mkdir(parents=True, exist_ok=True)

    managed: list[str] = []
    managed.extend(_materialize_runtime_doctrine(repo_root, root, runtime_map))
    for surface_dir in _loadout_surface_dirs(repo_root, loadout, "codex"):
        managed.extend(_copy_tree(surface_dir, root))

    instructions = _shared_instruction_text(repo_root, loadout.get("shared_instructions", []))
    packs = _pack_text(repo_root, loadout.get("packs", []))
    skills = _shared_skill_map(repo_root, loadout.get("shared_skills", []))
    runtime_cfg = loadout["runtime_overrides"]["codex"]
    launch = _runtime_launch_metadata(loadout, "codex")
    inventory = _command_inventory(repo_root, loadout, "codex")
    inventory_md = _render_command_inventory_markdown(inventory)

    active_skill = f'''## Active loadout

`{loadout['name']}`

## Purpose

{loadout['purpose']}

## When to use

{chr(10).join(f'- {item}' for item in loadout['when_to_use'])}

## Shared instructions

{chr(10).join(instructions)}

## Active packs

{chr(10).join(packs) if packs else '- None'}

## Runtime launch contract

{_format_launch_section(launch)}

## Command inventory

{inventory_md}

## Reporting expectation

End substantial runs with a concise report covering the request, changes, verification, blockers, and next steps.
'''
    active_skill_path = skills_dir / "hermes-active-loadout" / "SKILL.md"
    _write_text(active_skill_path, _render_skill_doc("hermes-active-loadout", active_skill))
    managed.append(str(active_skill_path))

    command_inventory_skill = f'''## Command inventory

{inventory_md}

## How to use

Use this when the operator asks what slash commands, native commands, or command-equivalent skills are currently available in the active Hermes Codex loadout. The machine-readable source is `command-inventory.json` in the runtime home.
'''
    command_inventory_skill_path = skills_dir / "hermes-command-inventory" / "SKILL.md"
    _write_text(
        command_inventory_skill_path,
        _render_skill_doc("hermes-command-inventory", command_inventory_skill),
    )
    managed.append(str(command_inventory_skill_path))

    for skill_name, skill_text in skills.items():
        skill_path = skills_dir / skill_name / "SKILL.md"
        _write_text(skill_path, _render_skill_doc(skill_name, skill_text))
        managed.append(str(skill_path))

    memory_text = f'''# Active Codex Loadout Memory

- active loadout: {loadout['name']}
- purpose: {loadout['purpose']}
- resolved inheritance: {', '.join(loadout.get('resolved_from', []))}
- session posture: fresh={loadout['session_policy'].get('prefer_fresh_session')}, compact-band={loadout['session_policy'].get('compact_warning_band')}
- launch env: {', '.join(f'{key}={value}' for key, value in (launch.get('env') or {}).items()) or 'none'}
'''
    memory_path = memories_dir / "hermes-loadout.md"
    _write_text(memory_path, memory_text)
    managed.append(str(memory_path))

    config_file = root / managed_paths["config_file"]
    existing = config_file.read_text() if config_file.exists() else ""
    merged = _merge_codex_config(existing, _render_codex_config(loadout))
    _write_text(config_file, merged)
    managed.append(str(config_file))

    managed.extend(_write_command_inventory(repo_root, root, loadout, "codex"))
    return sorted(set(managed))


def apply_loadout(
    *,
    repo_root: Path | str,
    loadouts: dict[str, dict[str, Any]],
    runtime: str,
    loadout_name: str,
    output_root: Path | str,
    target_home: bool = False,
    cwd: str | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    output_root = Path(output_root)
    runtime = runtime.lower()
    runtime_map = _runtime_map(repo_root, runtime)
    managed_paths = deepcopy(runtime_map.get("managed_paths", {}))
    resolved = resolve_loadout(loadouts, loadout_name)
    if runtime not in resolved.get("supported_runtimes", []):
        raise ValueError(f"Loadout {loadout_name} does not support runtime {runtime}")

    root = output_root if target_home else output_root / runtime
    root.mkdir(parents=True, exist_ok=True)

    if runtime == "claude":
        managed_files = _materialize_claude(repo_root, root, resolved)
    elif runtime == "codex":
        managed_files = _materialize_codex(repo_root, root, resolved)
    else:
        raise ValueError(f"Unsupported runtime: {runtime}")

    metadata_filename = managed_paths["metadata_file"]
    manifest_path = root / metadata_filename
    manifest = {
        "runtime": runtime,
        "runtime_label": RUNTIME_LABELS.get(runtime, runtime),
        "loadout": resolved["name"],
        "description": resolved["description"],
        "purpose": resolved["purpose"],
        "resolved_from": resolved.get("resolved_from", [resolved["name"]]),
        "session_policy": resolved.get("session_policy", {}),
        "launch": _runtime_launch_metadata(resolved, runtime),
        **_runtime_doctrine_metadata(runtime_map),
        "target_mode": "live-home" if target_home else "repo-local",
        "runtime_managed_paths": managed_paths,
        "packs": resolved.get("packs", []),
        "shared_skills": resolved.get("shared_skills", []),
        "managed_files": managed_files,
    }
    managed_files = [*managed_files, str(manifest_path)]
    manifest["managed_files"] = managed_files
    _write_text(manifest_path, json.dumps(manifest, indent=2))
    result = {
        "runtime": runtime,
        "runtime_label": RUNTIME_LABELS.get(runtime, runtime),
        "loadout": resolved["name"],
        "description": resolved["description"],
        "purpose": resolved["purpose"],
        "resolved_from": resolved.get("resolved_from", [resolved["name"]]),
        "session_policy": resolved.get("session_policy", {}),
        "launch": manifest.get("launch", {}),
        "runtime_bootstrap": manifest.get("runtime_bootstrap", {}),
        "runtime_tool_map": manifest.get("runtime_tool_map", {}),
        "runtime_capabilities": manifest.get("runtime_capabilities", {}),
        "target_mode": manifest["target_mode"],
        "runtime_managed_paths": managed_paths,
        "output_root": str(root),
        "cwd": cwd,
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "managed_files": managed_files,
    }
    result["launch_notice"] = format_launch_notice(result)
    return result
