#!/usr/bin/env python3
"""Smoke-test clean Hermes onboarding from a public-copy-shaped checkout.

This harness is intentionally sandbox-first. It copies the public tree into a
temporary directory, creates a temporary HERMES_HOME and HOME, installs the
public Hermes bridge-skill snapshot there, then runs the documented loadout
validation/materialization and managed-launch dry-run path.

It does not launch Claude Code or Codex, write live runtime homes, restart
Hermes, or post to external services.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACKED_SKILLS = [
    "coding-terminal-loadout-system",
    "coding-agent-prompt-enhancer",
    "coding-cli-real-home-launch",
    "claude-code-loadout-disclosure",
    "claude-code",
    "codex",
]


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(
            "command failed: " + " ".join(command) +
            f"\nreturncode={completed.returncode}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def _copy_public_shape(destination: Path) -> Path:
    """Copy the public tree while dropping non-public and transient state.

    The public product is everything outside the top-level maintainer
    workspace directory, so the same copy works from a maintainer development
    checkout and from an already-extracted public repo.
    """
    public_copy = destination / "public-copy"

    def ignore(_: str, names: list[str]) -> set[str]:
        ignored = {
            ".git",
            ".pytest_cache",
            "__pycache__",
            "output",
            ".venv",
            "venv",
            "private",
            "local-runtime-artifacts",
            ".hermes",
        }
        return {name for name in names if name in ignored}

    shutil.copytree(ROOT, public_copy, ignore=ignore)
    return public_copy


def _install_bridge_skills(public_copy: Path, hermes_home: Path) -> list[str]:
    src = public_copy / "hermes-gateway-skills" / "autonomous-ai-agents"
    if not src.is_dir():
        raise SystemExit(f"missing Hermes bridge-skill snapshot: {src}")
    dst = hermes_home / "skills" / "autonomous-ai-agents"
    dst.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for skill in TRACKED_SKILLS:
        skill_src = src / skill
        skill_dst = dst / skill
        if not (skill_src / "SKILL.md").is_file():
            raise SystemExit(f"missing bridge skill source: {skill_src / 'SKILL.md'}")
        if skill_dst.exists():
            shutil.rmtree(skill_dst)
        shutil.copytree(skill_src, skill_dst)
        installed.append(str(skill_dst / "SKILL.md"))
    return installed


def _manifest_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "runtime": data.get("runtime"),
        "loadout": data.get("loadout"),
        "inheritance_chain": data.get("inheritance_chain") or [],
        "managed_file_count": len(data.get("managed_files") or []),
    }


def run_smoke(*, keep_tmp: bool = False) -> dict[str, Any]:
    temp_ctx = tempfile.TemporaryDirectory(prefix="terminal-loadout-hermes-smoke-")
    temp_root = Path(temp_ctx.name)
    try:
        public_copy = _copy_public_shape(temp_root)
        hermes_home = temp_root / "hermes-home"
        operator_home = temp_root / "operator-home"
        hermes_home.mkdir(parents=True)
        operator_home.mkdir(parents=True)
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(operator_home),
                "HERMES_HOME": str(hermes_home),
                "HERMES_PROFILE": "clean-onboarding-smoke",
                "SAVE_DESTINATION_PATH": str(temp_root / "save-destination"),
            }
        )
        env.pop("OBSIDIAN_VAULT_PATH", None)
        env.pop("HERMES_DEFAULT_OBSIDIAN_VAULT_PATH", None)

        installed_skills = _install_bridge_skills(public_copy, hermes_home)

        checks: list[dict[str, Any]] = []
        for command in [
            [sys.executable, "scripts/validate_loadouts.py"],
            [sys.executable, "scripts/resolve_route.py", "--runtime", "claude", "--request", "Use Claude for research", "--explicit-loadout", "research"],
            [sys.executable, "scripts/resolve_route.py", "--runtime", "codex", "--request", "Use Codex for research", "--explicit-loadout", "research"],
            [sys.executable, "scripts/apply_loadout.py", "--runtime", "claude", "--loadout", "research", "--output-root", "output"],
            [sys.executable, "scripts/apply_loadout.py", "--runtime", "codex", "--loadout", "research", "--output-root", "output"],
            [sys.executable, "scripts/list_runtime_commands.py", "--compare", "--loadout", "research", "--format", "markdown"],
        ]:
            completed = _run(command, cwd=public_copy, env=env)
            checks.append({"command": command, "stdout": completed.stdout.strip()})

        task_file = public_copy / "output" / "onboarding" / "task.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "Summarize this repo architecture and report verification only. Do not modify files.\n",
            encoding="utf-8",
        )
        dry_run = _run(
            [
                sys.executable,
                "scripts/run_loaded_agent.py",
                "--runtime",
                "claude",
                "--loadout",
                "research",
                "--repo",
                ".",
                "--task-file",
                str(task_file.relative_to(public_copy)),
                "--dry-run",
                "--watch",
                "--json",
            ],
            cwd=public_copy,
            env=env,
        )
        dry_payload = json.loads(dry_run.stdout)
        managed = dry_payload.get("managed_launch") or {}
        if dry_payload.get("mode") != "dry-run":
            raise SystemExit("managed launcher did not stay in dry-run mode")
        if managed.get("watcher_default") is not True or managed.get("closeout_default") is not True:
            raise SystemExit(f"managed launcher did not plan watcher/closeout defaults: {managed}")
        if dry_payload.get("runtime") != "claude" or dry_payload.get("loadout") != "research":
            raise SystemExit(f"managed launcher resolved unexpected route: {dry_payload}")
        steps = "\n".join(dry_payload.get("steps") or [])
        if "close out via runtime-event closeout" not in steps:
            raise SystemExit("managed launcher dry-run did not include runtime-event closeout step")

        git_dir = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=public_copy, env=env, text=True, capture_output=True, check=False)
        if git_dir.returncode == 0:
            diff_check = _run(["git", "diff", "--check"], cwd=public_copy, env=env).stdout.strip()
        else:
            diff_check = "skipped: public copy is not a git checkout"
        result = {
            "status": "PASS",
            "temp_root": str(temp_root),
            "public_copy": str(public_copy),
            "hermes_home": str(hermes_home),
            "operator_home": str(operator_home),
            "installed_bridge_skills": installed_skills,
            "manifests": [
                _manifest_summary(public_copy / "output" / "claude" / "hermes-loadout.json"),
                _manifest_summary(public_copy / "output" / "codex" / "hermes-loadout.json"),
            ],
            "managed_launch": {
                "mode": dry_payload.get("mode"),
                "runtime": dry_payload.get("runtime"),
                "loadout": dry_payload.get("loadout"),
                "watcher_default": managed.get("watcher_default"),
                "closeout_default": managed.get("closeout_default"),
                "classification": managed.get("classification"),
                "steps_include_runtime_event_closeout": True,
            },
            "checks": checks,
            "git_diff_check": diff_check,
            "live_runtime_launched": False,
            "external_reportback_used": False,
        }
        if keep_tmp:
            temp_ctx.cleanup = lambda: None  # type: ignore[method-assign]
        return result
    finally:
        if not keep_tmp:
            temp_ctx.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-tmp", action="store_true", help="Keep the temporary public copy/Hermes home for inspection.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    result = run_smoke(keep_tmp=args.keep_tmp)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("clean_hermes_onboarding_smoke=PASS")
        print(f"public_copy={result['public_copy']}")
        print(f"hermes_home={result['hermes_home']}")
        print(f"installed_bridge_skills={len(result['installed_bridge_skills'])}")
        for manifest in result["manifests"]:
            print(f"manifest={manifest['path']} runtime={manifest['runtime']} loadout={manifest['loadout']} managed_files={manifest['managed_file_count']}")
        print("managed_launch=dry-run watcher_default=true closeout_default=true runtime_event_closeout=true")
        print("live_runtime_launched=false external_reportback_used=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
