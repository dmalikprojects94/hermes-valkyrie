from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

HEADINGS = ["Request", "Changes", "Verification", "Blockers", "Next Steps"]
OPTIONAL_HEADINGS = ["Qualifying Questions"]
HEADING_ALIASES = {"Non-ambiguous Work Completed": "Changes"}
RECOGNIZED_HEADINGS = HEADINGS + OPTIONAL_HEADINGS + list(HEADING_ALIASES)
VALID_ORIGINS = {"closeout", "snapshot", "status"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def heading_pattern() -> re.Pattern[str]:
    heading_alt = "|".join(re.escape(heading) for heading in RECOGNIZED_HEADINGS)
    # TUI panes often prefix assistant output with bullets like `●` or `•`,
    # then render markdown headings after that prefix. Accept those UI markers
    # while still requiring a real heading line, so prompt contracts mentioning
    # the heading names do not count as a finished report.
    return re.compile(rf"^\s*(?:[●•]\s*)?(?:#{{1,3}}\s+)?({heading_alt})\s*$", re.MULTILINE)


def _parse_sections(text: str) -> dict[str, str]:
    pattern = heading_pattern()
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = HEADING_ALIASES.get(match.group(1), match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body_lines = [line.strip() for line in text[start:end].splitlines()]
        body = "\n".join(line for line in body_lines).strip()
        sections[heading] = body
    return sections


def _has_blockers(sections: dict[str, str]) -> bool | None:
    blockers = sections.get("Blockers")
    if blockers is None:
        return None
    normalized = blockers.strip().lower().strip(".!")
    # Treat explanatory no-blocker prose as clean. Claude often writes e.g.
    # "None. (One open decision, not a blocker: ...)"; the current lifecycle
    # must not mark that as finished_blocked just because useful follow-up text
    # follows the explicit `None` marker.
    if re.match(r"^(?:none|no blockers?|no known blockers?)\b", normalized):
        return False
    return normalized not in {
        "",
        "none",
        "no",
        "no blockers",
        "no known blockers",
        "n/a",
        "not applicable",
        "nothing blocking",
    }


def extract_report_from_text(
    *,
    text: str,
    reports_dir: Path,
    source_label: str,
    source_path: Path | None = None,
    origin: str = "status",
) -> dict[str, Any]:
    """Parse the five-heading report contract from raw text and write artifacts.

    `source_label` distinguishes provenance (e.g. `runtime_event` vs `snapshot`)
    so callers can trace where the closeout text came from without reparsing.
    `origin` distinguishes a final `closeout` report from a `snapshot` fallback
    or a generic `status` report so operator surfaces can track them separately.
    """
    if origin not in VALID_ORIGINS:
        raise ValueError(f"Invalid report origin: {origin}")
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    sections = _parse_sections(text)
    structured = all(heading in sections for heading in HEADINGS)
    status = "structured" if structured else "unstructured"
    stamp = _timestamp()
    report_path = reports_dir / f"{stamp}-report.md"
    summary_path = reports_dir / f"{stamp}-summary.json"

    front = [f"status: {status}", f"origin: {origin}", f"source: {source_label}"]
    if source_path is not None:
        front.append(f"source_path: {source_path}")
    front_matter = "---\n" + "\n".join(front) + "\n---\n"

    if structured:
        report = [front_matter]
        for heading in HEADINGS:
            report.append(f"## {heading}\n{sections.get(heading, '').strip()}\n")
        for heading in OPTIONAL_HEADINGS:
            if heading in sections:
                report.append(f"## {heading}\n{sections.get(heading, '').strip()}\n")
        report_path.write_text("\n".join(report))
    else:
        reference = f"`{source_path}`" if source_path is not None else f"source `{source_label}`"
        report_path.write_text(
            f"{front_matter}\n"
            "# Unstructured Coding Terminal Output\n\n"
            f"The terminal output did not include the full reporting contract. Review raw {reference}\n"
        )

    summary = {
        "status": status,
        "origin": origin,
        "source": source_label,
        "source_path": str(source_path) if source_path is not None else None,
        "report_path": str(report_path),
        "summary_path": str(summary_path),
        "heading_presence": {heading: heading in sections for heading in HEADINGS + OPTIONAL_HEADINGS},
        "sections": sections if structured else {},
        "has_blockers": _has_blockers(sections),
        "verification": sections.get("Verification", ""),
    }
    summary_path.write_text(json.dumps(summary, indent=2))
    return summary


def extract_report(*, snapshot_path: Path, reports_dir: Path) -> dict[str, Any]:
    snapshot_path = Path(snapshot_path)
    summary = extract_report_from_text(
        text=snapshot_path.read_text(),
        reports_dir=reports_dir,
        source_label="snapshot",
        source_path=snapshot_path,
        origin="snapshot",
    )
    summary.setdefault("snapshot_path", str(snapshot_path))
    return summary
