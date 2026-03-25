"""
Report generation for Aletheia evaluation results.

Output formats:
- JSON: the canonical output (SCOPE.md §3.3 schema)
- Markdown: human-readable summary (Phase 1 stub, full in Phase 2)

Hegel's Aufhebung at session closure: the raw eval data is negated
(individual probe details compressed), preserved (scores retained),
and elevated (aggregated into the Aletheia Index). The report is the
sublation of the eval run.

Eliade's consecration: the report is the ritual act that selects what
mattered from the eval run — what survives the dissolution of runtime.

Security: reports undergo secret scanning before output. Report signing
ensures tamper detection (Phase 1: SHA-256 stub, Phase 2: Ed25519).

Ref: SCOPE.md §3.3 (Output Format)
"""

from __future__ import annotations

from pathlib import Path

import structlog

from aletheia.models import EvalReport
from aletheia.security import scan_for_secrets, set_restrictive_permissions

logger = structlog.get_logger()


def report_to_json(report: EvalReport, pretty: bool = True) -> str:
    """Serialize report to JSON string.

    This is the canonical output format matching SCOPE.md §3.3.
    """
    indent = 2 if pretty else None
    return report.model_dump_json(indent=indent)


def write_json_report(report: EvalReport, output_path: Path) -> Path:
    """Write JSON report to disk with security checks.

    1. Serialize to JSON
    2. Scan for accidentally included secrets
    3. Sign the report
    4. Write with restrictive permissions (0600)

    Returns the path written to.
    """
    json_str = report_to_json(report)

    # Security: scan for leaked secrets
    findings = scan_for_secrets(json_str)
    if findings:
        logger.error("secret_leak_detected", findings=findings)
        msg = f"Report contains potential secrets: {findings}. Refusing to write."
        raise SecurityError(msg)

    # Write atomically: write to temp, then rename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json_str, encoding="utf-8")
    set_restrictive_permissions(output_path)

    logger.info("report_written", path=str(output_path), size_bytes=len(json_str))
    return output_path


def report_to_markdown(report: EvalReport) -> str:
    """Generate a human-readable markdown summary.

    Phase 1: basic summary with scores and key findings.
    Phase 2: full report with probe details, charts, and philosophical commentary.
    """
    lines: list[str] = []

    lines.append("# Aletheia Evaluation Report")
    lines.append("")
    lines.append(f"**Model:** {report.model}")
    lines.append(f"**Suite:** {report.suite}")
    lines.append(f"**Timestamp:** {report.timestamp}")
    lines.append(f"**Run ID:** {report.run_id}")
    lines.append("")

    # Aletheia Index
    lines.append("## Aletheia Index")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    lines.append(f"| **Final Aletheia Index** | **{report.aletheia_index:.4f}** |")
    lines.append(f"| Raw Index (before UCI) | {report.raw_aletheia_index:.4f} |")
    lines.append(f"| Unhappy Consciousness Index | {report.unhappy_consciousness_index:.4f} |")
    lines.append("")
    lines.append(
        f"*Final = Raw x (1 - UCI) = {report.raw_aletheia_index:.4f} "
        f"x (1 - {report.unhappy_consciousness_index:.4f}) "
        f"= {report.aletheia_index:.4f}*"
    )
    lines.append("")

    # Dimension scores
    lines.append("## Dimension Scores")
    lines.append("")
    lines.append("| Dimension | Score | Passed | Total |")
    lines.append("|-----------|-------|--------|-------|")

    for dim_name, dim_result in report.dimensions.items():
        lines.append(
            f"| {dim_name} | {dim_result.score:.4f} | "
            f"{dim_result.tests_passed} | {dim_result.tests_total} |"
        )
    lines.append("")

    # UCI Detail
    if report.unhappy_consciousness_detail:
        lines.append("## Unhappy Consciousness Detail (Hegel)")
        lines.append("")
        lines.append("*The gap between what the agent can articulate and what it can perform.*")
        lines.append("")
        lines.append("| Dimension | Articulation | Performance | Gap |")
        lines.append("|-----------|-------------|-------------|-----|")

        for dim_name, uci_d in report.unhappy_consciousness_detail.items():
            lines.append(
                f"| {dim_name} | {uci_d.articulation:.4f} | "
                f"{uci_d.performance:.4f} | {uci_d.gap:.4f} |"
            )
        lines.append("")

    # Notable findings
    if report.notable_findings:
        lines.append("## Notable Findings")
        lines.append("")
        lines.extend(f"- {finding}" for finding in report.notable_findings)
        lines.append("")

    # Kantian boundaries
    if report.kantian_boundaries_triggered:
        lines.extend([
            "## Kantian Boundaries Triggered",
            "",
            "*Points where measurement ends and metaphysics begins.*",
            "",
        ])
        lines.extend(f"- {trigger}" for trigger in report.kantian_boundaries_triggered)
        lines.append("")

    # Footer
    lines.extend([
        "---",
        "",
        "*Generated by [Aletheia](https://github.com/Shwha/aletheia) — ",
        "ontological evaluation for AI agents.*",
    ])
    lines.append("")
    lines.append('*"Does your AI know what it is?"*')

    return "\n".join(lines)


def write_markdown_report(report: EvalReport, output_path: Path) -> Path:
    """Write markdown summary to disk."""
    md = report_to_markdown(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    set_restrictive_permissions(output_path)
    logger.info("markdown_report_written", path=str(output_path))
    return output_path


class SecurityError(Exception):
    """Raised when a security check prevents an operation."""
