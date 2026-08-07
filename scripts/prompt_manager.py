from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REPORT_HEADINGS = ["Request", "Changes", "Verification", "Blockers", "Next Steps"]

OUTPUT_DEFINITIONS: dict[str, str] = {
    "structured-report": """Default completion report. Use this when no more specific output was requested. Keep the response concise and operational.""",
    "implementation-log": """Implementation log. In Changes, include files created/modified and commands run. In Verification, include exact verification results. This is the default when code or project files may change.""",
    "project-plan": """Project plan. In Changes, list plan artifacts created or updated. In Next Steps, provide ordered implementation tasks that can be assigned or executed later.""",
    "verification-report": """Verification report. In Verification, emphasize commands, checks, observed outputs, pass/fail status, and any unverified assumptions.""",
    "decision-record": """Decision record. In Request, restate the decision being made. In Changes, record the chosen option and rejected alternatives. In Verification, explain the evidence used.""",
    "handoff-note": """Handoff note. In Changes, summarize completed work and artifact locations. In Blockers and Next Steps, make continuation state explicit for the next agent/session.""",
}

DEFAULT_OUTPUT_TYPE = "implementation-log"

DEFAULT_OUTPUT_CONTRACT = """End the run with level-2 markdown headings using these exact names, in this exact order: `Request`, `Changes`, `Verification`, `Blockers`, `Next Steps`.

Section requirements:
- Request: Restate the task actually performed.
- Changes: List concrete files, commands, or artifacts changed.
- Verification: List the real verification commands/results. If not verified, say exactly why.
- Blockers: Use `None` if there are no blockers. Otherwise name the blocker and what is needed.
- Next Steps: Use `None` if no follow-up is needed. Otherwise list only actionable next steps.

Important: only emit the actual markdown heading lines in your final answer, not while discussing or restating this contract.
"""


CANONICAL_GROUNDING_DOCS = (
    "README.md",
    "docs/README.md",
    "docs/DOCUMENTATION-OVERVIEW.md",
    "docs/integrations/hermes.md",
    "docs/architecture/runtime-adapters.md",
    "docs/guides/managed-visible-launch-contract.md",
)


@dataclass(frozen=True)
class PreparedPrompt:
    original_request: str
    prompt: str
    output_contract: str
    project_slug: str
    output_type: str


def slugify(value: str, *, fallback: str = "project") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def infer_project_slug(repo_path: Path | str, explicit: str | None = None) -> str:
    if explicit:
        return slugify(explicit)
    return slugify(Path(repo_path).resolve().name)


def normalize_output_type(output_type: str | None) -> str:
    if not output_type:
        return DEFAULT_OUTPUT_TYPE
    normalized = slugify(output_type, fallback=DEFAULT_OUTPUT_TYPE)
    if normalized not in OUTPUT_DEFINITIONS:
        known = ", ".join(sorted(OUTPUT_DEFINITIONS))
        raise ValueError(f"unknown output type {output_type!r}; known output types: {known}")
    return normalized


def build_output_contract(*, output_type: str | None = None, output_contract: str | None = None) -> str:
    if output_contract:
        return output_contract.strip()
    normalized_type = normalize_output_type(output_type)
    type_instructions = OUTPUT_DEFINITIONS[normalized_type].strip()
    return f"""Output document type: {normalized_type}

{type_instructions}

{DEFAULT_OUTPUT_CONTRACT.strip()}
""".strip()


def build_grounding_context(
    *,
    repo_path: Path | str,
    project_slug: str,
    vault_path: Path | str | None = None,
) -> str:
    repo_root = Path(repo_path).resolve()
    doc_lines = "\n".join(f"  - {doc}" for doc in CANONICAL_GROUNDING_DOCS)
    if vault_path:
        vault_line = f"- Save destination project context: {Path(vault_path) / 'projects' / project_slug}"
    else:
        vault_line = "- Save destination project context: (unset — no SAVE_DESTINATION_PATH configured)"
    return f"""Grounding context (read these before acting; do not continue from terminal state alone):
- Repo root: {repo_root}
- Canonical repo docs to read first:
{doc_lines}
{vault_line}"""


def prepare_prompt(
    *,
    request: str,
    runtime: str,
    loadout: str,
    repo_path: Path | str,
    project_slug: str | None = None,
    output_contract: str | None = None,
    output_type: str | None = None,
    vault_path: Path | str | None = None,
) -> PreparedPrompt:
    original = request.strip()
    if not original:
        raise ValueError("request cannot be empty")
    slug = infer_project_slug(repo_path, project_slug)
    normalized_output_type = normalize_output_type(output_type)
    contract = build_output_contract(output_type=normalized_output_type, output_contract=output_contract)
    grounding = build_grounding_context(repo_path=repo_path, project_slug=slug, vault_path=vault_path)
    prompt = f"""You are being launched by Hermes through the managed tmux coding-terminal runner.

Restated task:
{original}

Runtime: {runtime}
Loadout: {loadout}
Project slug: {slug}
Output type: {normalized_output_type}

{grounding}

Execution rules:
- Before acting, read the grounding context above: the canonical repo docs and the save-destination project context, not just terminal state.
- Treat the restated task as the scope. Do not drift into adjacent work unless necessary to finish it.
- If the task is broad, first tighten it internally into a concrete implementation plan, then execute.
- Save any code/file changes in the current repo/workspace, not only in the chat transcript.
- Keep a concise log of what you did in the final structured output.
- Run the most relevant verification available before reporting done.
- If a command, install, auth step, or permission blocks you, stop and report the blocker clearly.

Output contract:
{contract}
""".strip() + "\n"
    return PreparedPrompt(
        original_request=original,
        prompt=prompt,
        output_contract=contract,
        project_slug=slug,
        output_type=normalized_output_type,
    )
