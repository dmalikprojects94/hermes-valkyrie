from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
from typing import Any


RAW_OBSIDIAN_SUBDIR = Path("agents") / "coding-terminal" / "raw-runs"
RAW_OBSIDIAN_AGENT_SUBDIRS = {
    "claude": Path("agents") / "claude-code" / "raw-runs",
    "claude-code": Path("agents") / "claude-code" / "raw-runs",
    "codex": Path("agents") / "codex" / "raw-runs",
}
CANONICAL_VAULT_PROJECT_SLUG = "local-vault"
VAULT_PROJECT_ALIASES = frozenset({
    "local-vault",
    "local-vault-project",
    "obsidian-vault",
    "claudevault",
    "claude-vault",
})

# Conservative patterns for obvious credential material. Intentionally narrow so
# normal report prose is never mangled; this is a safety net, not a full scanner.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[oprsu]_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{20,}"),
]
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd)(\s*[:=]\s*)(['\"]?)([A-Za-z0-9._\-/+]{8,})(['\"]?)"
)


def redact_secrets(text: str) -> str:
    """Replace obvious tokens/keys/credentials with `[REDACTED]`.

    Kept deliberately conservative: keyed assignments preserve the key name and
    a small set of well-known token shapes are masked outright.
    """
    if not text:
        return text
    redacted = _SECRET_ASSIGNMENT.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[REDACTED]{m.group(5)}", text
    )
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def raw_obsidian_subdir(runtime: str | None = None) -> Path:
    if not runtime:
        return RAW_OBSIDIAN_SUBDIR
    return RAW_OBSIDIAN_AGENT_SUBDIRS.get(str(runtime).lower(), RAW_OBSIDIAN_SUBDIR)


def _usable_vault_path(vault: Path | str | None) -> Path | None:
    if not vault:
        return None
    vault_path = Path(vault).expanduser().resolve()
    if not vault_path.exists() or not vault_path.is_dir() or not os.access(vault_path, os.W_OK):
        return None
    return vault_path


def resolve_obsidian_vault_path() -> Path | None:
    """Return the configured or local-default save destination for reports."""
    explicit_save = os.environ.get("SAVE_DESTINATION_PATH")
    if explicit_save:
        return _usable_vault_path(explicit_save)
    explicit_obsidian = os.environ.get("OBSIDIAN_VAULT_PATH")
    if explicit_obsidian:
        return _usable_vault_path(explicit_obsidian)
    configured_default = os.environ.get("HERMES_DEFAULT_OBSIDIAN_VAULT_PATH")
    if configured_default:
        return _usable_vault_path(configured_default)
    return None


def raw_obsidian_root(runtime: str | None = None) -> Path | None:
    vault_path = resolve_obsidian_vault_path()
    if not vault_path:
        return None
    return vault_path / raw_obsidian_subdir(runtime)


def slugify_project_slug(project_slug: str | None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(project_slug or "").strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        return "unknown-project"
    if slug in VAULT_PROJECT_ALIASES:
        return CANONICAL_VAULT_PROJECT_SLUG
    return slug


def project_obsidian_root(project_slug: str) -> Path | None:
    vault_path = resolve_obsidian_vault_path()
    if not vault_path:
        return None
    safe_slug = slugify_project_slug(project_slug)
    return vault_path / "projects" / safe_slug / "artifacts" / "coding-terminal-runs"


def default_routes(*, artifact_root: Path, repo_path: Path, project_slug: str, runtime: str | None = None) -> dict[str, str]:
    artifact_root = Path(artifact_root)
    repo_path = Path(repo_path)
    default_root = resolve_obsidian_vault_path()
    raw_root = (default_root / raw_obsidian_subdir(runtime)) if default_root else (artifact_root / "raw")
    safe_slug = slugify_project_slug(project_slug)
    project_root = (
        default_root / "projects" / safe_slug / "artifacts" / "coding-terminal-runs"
        if default_root
        else repo_path / ".hermes" / "projects" / project_slug / "coding-terminal-runs"
    )
    source = "save_destination" if default_root else "artifact_fallback"
    return {
        "default_path": str(default_root) if default_root else "",
        "default_path_source": source,
        "raw_path": str(raw_root),
        "raw_root": str(raw_root),
        "raw_root_source": source,
        "project_path": str(project_root),
        "sorted_path": str(project_root),
        "project_root": str(project_root),
        "project_root_source": source,
    }


def ensure_routes(routes: dict[str, str]) -> None:
    Path(routes["raw_root"]).mkdir(parents=True, exist_ok=True)
    Path(routes["project_root"]).mkdir(parents=True, exist_ok=True)


def _copy_redacted_text(src: Path, dst: Path) -> None:
    dst.write_text(redact_secrets(Path(src).read_text()))


def _root_writable(root: str) -> bool:
    probe = Path(root)
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            return False
        probe = parent
    return os.access(probe, os.W_OK)


def _copy_redacted_verified(src: Path, dst: Path) -> bool:
    """Copy redacted text and confirm the destination holds the full payload.

    Redaction can shrink the text, so the integrity check compares the written
    destination size against the redacted content actually emitted rather than
    against the raw source size.
    """
    content = redact_secrets(Path(src).read_text())
    Path(dst).write_text(content)
    return Path(dst).exists() and Path(dst).stat().st_size == len(content.encode("utf-8"))


def route_report_artifacts(
    *,
    manifest: dict[str, Any],
    report_path: Path,
    summary_path: Path,
    provenance_path: Path | None = None,
    provenance_label: str = "snapshot",
    snapshot_path: Path | None = None,
) -> dict[str, Any]:
    provenance = provenance_path if provenance_path is not None else snapshot_path
    routes = manifest.get("artifact_routes") or {}
    if not routes:
        routes = default_routes(
            artifact_root=Path(manifest["artifacts"]["root"]),
            repo_path=Path(manifest["repo_path"]),
            project_slug=manifest.get("project_slug") or Path(manifest["repo_path"]).name,
            runtime=manifest.get("runtime"),
        )

    try:
        summary = json.loads(Path(summary_path).read_text())
    except (json.JSONDecodeError, OSError):
        # A malformed/unreadable summary must not abort the raw archive; treat
        # the run as unstructured so the raw report copy still proceeds.
        summary = {}
    structured = summary.get("status") == "structured"

    # Fail closed before touching any destination: if the routing roots are not
    # writable, keep the local report and report a failed routing status rather
    # than crashing the runtime hook or losing the artifact silently.
    errors: list[str] = []
    if not _root_writable(routes["raw_root"]):
        errors.append(f"raw routing root not writable: {routes['raw_root']}")
    if structured and not _root_writable(routes["project_root"]):
        errors.append(f"project routing root not writable: {routes['project_root']}")
    if errors:
        return {
            "mode": "local_only",
            "structured": structured,
            "routing_status": "failed",
            "routing_error": "; ".join(errors),
            "raw_root": routes["raw_root"],
            "raw_root_source": routes.get("raw_root_source", "configured"),
            "project_root": routes["project_root"],
            "provenance_label": provenance_label,
            "raw_provenance": "",
            "raw_snapshot": "",
            "raw_report": "",
            "raw_summary": "",
            "project_report": "",
            "project_summary": "",
            "local_report": str(report_path),
        }

    ensure_routes(routes)
    stamp = _stamp()
    runtime = manifest.get("runtime", "runtime")
    label = manifest.get("session_label", "session")
    safe_label = "-".join(label.lower().replace("/", " ").split()) or "session"
    stem = f"{stamp}-{runtime}-{safe_label}"

    raw_report = Path(routes["raw_root"]) / f"{stem}-report.md"
    raw_summary = Path(routes["raw_root"]) / f"{stem}-summary.json"
    if not _copy_redacted_verified(Path(report_path), raw_report):
        errors.append(f"raw report copy verification failed: {raw_report}")
    if not _copy_redacted_verified(Path(summary_path), raw_summary):
        errors.append(f"raw summary copy verification failed: {raw_summary}")

    raw_provenance = ""
    if provenance is not None:
        provenance = Path(provenance)
        suffix = provenance.suffix or ".txt"
        raw_provenance_path = Path(routes["raw_root"]) / f"{stem}-{provenance_label}{suffix}"
        # Provenance text is copied verbatim from runtime output, so redact it
        # rather than blindly shutil.copyfile-ing any secrets it may contain.
        if not _copy_redacted_verified(provenance, raw_provenance_path):
            errors.append(f"raw provenance copy verification failed: {raw_provenance_path}")
        raw_provenance = str(raw_provenance_path)

    routed: dict[str, Any] = {
        "mode": "project" if structured else "raw",
        "structured": structured,
        "raw_root": routes["raw_root"],
        "raw_root_source": routes.get("raw_root_source", "configured"),
        "project_root": routes["project_root"],
        "provenance_label": provenance_label,
        "raw_provenance": raw_provenance,
        # Back-compatible alias for older snapshot-shaped callers.
        "raw_snapshot": raw_provenance,
        "raw_report": str(raw_report),
        "raw_summary": str(raw_summary),
        "project_report": "",
        "project_summary": "",
        "local_report": str(report_path),
    }

    if structured:
        project_report = Path(routes["project_root"]) / f"{stem}-report.md"
        project_summary = Path(routes["project_root"]) / f"{stem}-summary.json"
        if not _copy_redacted_verified(Path(report_path), project_report):
            errors.append(f"project report copy verification failed: {project_report}")
        if not _copy_redacted_verified(Path(summary_path), project_summary):
            errors.append(f"project summary copy verification failed: {project_summary}")
        routed["project_report"] = str(project_report)
        routed["project_summary"] = str(project_summary)

    routed["routing_status"] = "failed" if errors else "ok"
    routed["routing_error"] = "; ".join(errors)
    return routed
