#!/usr/bin/env python3
"""Repo-aware prompt enhancer for coding-agent terminals.

Usage:
  python enhance_prompt.py --request "fix login bug" --repo /path/to/repo --runtime claude --loadout coding
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""


def detect_repo(start: str | None) -> Path:
    if start:
        p = Path(start).expanduser().resolve()
        if p.is_file():
            p = p.parent
        top = run(["git", "rev-parse", "--show-toplevel"], p)
        return Path(top).resolve() if top else p
    top = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    return Path(top).resolve() if top else Path.cwd().resolve()


def detect_project_name(repo: Path) -> str:
    for filename in ("package.json", "pyproject.toml", "Cargo.toml"):
        path = repo / filename
        if not path.exists():
            continue
        text = path.read_text(errors="ignore")[:4000]
        if filename == "package.json":
            try:
                return json.loads(text).get("name") or repo.name
            except Exception:
                pass
        for line in text.splitlines():
            if line.strip().startswith("name") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"\'') or repo.name
    return repo.name


def detect_commands(repo: Path) -> list[str]:
    cmds: list[str] = []
    package = repo / "package.json"
    if package.exists():
        try:
            scripts = json.loads(package.read_text()).get("scripts", {})
            for key in ("test", "lint", "typecheck", "build"):
                if key in scripts:
                    cmds.append(f"npm run {key}" if key != "test" else "npm test")
        except Exception:
            pass
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        if (repo / "pytest.ini").exists() or "pytest" in pyproject.read_text(errors="ignore"):
            cmds.append("pytest")
        if "ruff" in pyproject.read_text(errors="ignore"):
            cmds.append("ruff check .")
    if (repo / "Makefile").exists():
        makefile = repo.joinpath("Makefile").read_text(errors="ignore")
        for key in ("test", "lint", "build"):
            if f"{key}:" in makefile:
                cmds.append(f"make {key}")
    seen = set()
    return [c for c in cmds if not (c in seen or seen.add(c))]


def infer_scope(request: str) -> str:
    lower = request.lower()
    if any(w in lower for w in ("login", "auth", "session", "oauth")):
        return "auth/login/session routing files and related tests"
    if any(w in lower for w in ("dashboard", "ui", "design", "page", "component")):
        return "relevant frontend pages/components/styles and tests"
    if any(w in lower for w in ("api", "endpoint", "backend", "server")):
        return "relevant API routes/services/models and tests"
    if any(w in lower for w in ("deploy", "vercel", "build")):
        return "build/deploy configuration and affected app code"
    return "the smallest relevant files needed for the task"


def slugify(value: str | None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "unknown-project"


def runtime_raw_subdir(runtime: str | None) -> Path:
    normalized = str(runtime or "").strip().lower()
    if normalized in {"claude", "claude-code"}:
        return Path("agents") / "claude-code" / "raw-runs"
    if normalized == "codex":
        return Path("agents") / "codex" / "raw-runs"
    return Path("agents") / "coding-terminal" / "raw-runs"


def usable_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    if path.exists() and path.is_dir() and os.access(path, os.W_OK):
        return path
    return None


def default_save_path() -> Path | None:
    for key in ("SAVE_DESTINATION_PATH", "OBSIDIAN_VAULT_PATH", "HERMES_DEFAULT_OBSIDIAN_VAULT_PATH"):
        path = usable_path(os.environ.get(key))
        if path:
            return path
    return None


def artifact_paths(*, repo: Path, project: str, runtime: str) -> dict[str, str]:
    default_path = default_save_path()
    artifact_fallback = repo / ".hermes" / "coding-terminals" / "raw"
    project_fallback = repo / ".hermes" / "projects" / slugify(project) / "coding-terminal-runs"
    raw_path = default_path / runtime_raw_subdir(runtime) if default_path else artifact_fallback
    project_path = default_path / "projects" / slugify(project) / "artifacts" / "coding-terminal-runs" if default_path else project_fallback
    return {
        "default_path": str(default_path) if default_path else "",
        "raw_path": str(raw_path),
        "project_path": str(project_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--runtime", default="agent")
    parser.add_argument("--loadout", default="default")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    repo = detect_repo(args.repo)
    project = detect_project_name(repo)
    branch = run(["git", "branch", "--show-current"], repo) or "unknown"
    status = run(["git", "status", "--short"], repo)
    commands = detect_commands(repo) or ["Use the repo's documented test/build command after inspecting README/package files"]
    scope = infer_scope(args.request)
    paths = artifact_paths(repo=repo, project=project, runtime=args.runtime)
    commit_line = "Commit the change" + (" and push it" if args.push else "") + "." if args.commit or args.push else "Do not commit or push unless the operator explicitly instructs it."

    print(f"Context: You are working in {repo} on {project}. Current branch: {branch}.")
    print(f"Runtime/loadout: {args.runtime} / {args.loadout}.")
    print(f"Original request: {args.request}")
    if status:
        print(f"Current git status: there are existing working-tree changes; inspect before editing and do not overwrite unrelated work.")
    else:
        print("Current git status: clean at prompt-enhancement time.")
    print(f"Task: Convert the original request into the smallest correct implementation and complete it in this repo.")
    print(f"Scope: Inspect/modify {scope}. Do not broaden into adjacent refactors or redesigns unless necessary for the requested fix.")
    print("Requirements:")
    print("- Preserve existing behavior outside the requested change.")
    print("- Prefer minimal, maintainable changes over broad rewrites.")
    print("- Add or update tests when the repo has a clear test pattern for the touched area.")
    print("- If this task touches GitHub, branches, PRs, releases, public sharing, or repo publication, check for project update instructions in the repo before editing.")
    print("Artifact routing:")
    print(f"- default_path: {paths['default_path'] or 'not configured; local artifact fallback applies'}")
    print(f"- raw_path: {paths['raw_path']}")
    print(f"- project_path: {paths['project_path']}")
    print("- Treat raw_path as the always-valid capture lane. If the work clearly fits the current project, also use/report project_path as the organized project lane; otherwise leave it in raw_path and say why no project placement fit.")
    print("Verification:")
    for cmd in commands:
        print(f"- {cmd}")
    print(f"Deliverable: Implement the change, run verification, and report changed files plus exact observed output. {commit_line}")


if __name__ == "__main__":
    main()
