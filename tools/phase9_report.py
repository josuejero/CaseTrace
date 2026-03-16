"""Renderer for the Phase 9 investigator report."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Template

from integrity import (
    append_processing_step,
    examiner_name,
    load_manifest,
    load_processing_log,
    sha256_digest,
    utc_timestamp,
    write_manifest,
)
from parser.common import load_json

REPORT_TEMPLATE = Template("""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>CaseTrace Investigator Report</title>
  <style>
    body { font-family: "Inter", "Segoe UI", system-ui, sans-serif; margin: 0; padding: 2rem; background: #f5f5f5; }
    main { background: #ffffff; padding: 2rem; border-radius: 1rem; max-width: 960px; margin: auto; }
    h1, h2, h3 { margin-top: 0; }
    section { margin-top: 1.5rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
    th, td { border: 1px solid #dfe3ea; padding: 0.45rem 0.65rem; text-align: left; }
    th { background: #f0f4ff; }
    .badges { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
    .badge { padding: 0.25rem 0.7rem; border-radius: 999px; background: #e0f2fe; font-size: 0.85rem; }
    ul { padding-left: 1rem; }
    .log-entry { border-left: 3px solid #d1d5db; padding-left: 0.75rem; margin-bottom: 0.5rem; }
    pre { background: #111827; color: #f8fafc; padding: 1rem; border-radius: 0.75rem; overflow-x: auto; }
    footer { text-align: center; margin-top: 2rem; font-size: 0.9rem; color: #475569; }
  </style>
</head>
<body>
  <main>
    <header>
      <p class=\"badge\">Generated {{ generated_at }}</p>
      <h1>CaseTrace Investigator Report · {{ case_id }}</h1>
      <p>Subject: {{ subject or 'N/A' }}</p>
    </header>

    <section>
      <h2>Executive Summary</h2>
      <p>{{ executive_summary }}</p>
      <div class=\"badges\">
        {% for artifact, count in artifact_counts.items() %}
          <span class=\"badge\">{{ artifact }}: {{ count }}</span>
        {% endfor %}
      </div>
    </section>

    <section>
      <h2>Methods</h2>
      <ul>
        <li>Acquisition: {{ acquisition.method }} on {{ acquisition.acquired_at }} by {{ acquisition.operator }}</li>
        <li>Parser version: {{ parser_version }}</li>
        <li>Hash manifest last written: {{ manifest_generated_at }}</li>
      </ul>
    </section>

    <section>
      <h2>Findings</h2>
      <table>
        <thead>
          <tr>
            <th>Record</th>
            <th>Artifact</th>
            <th>Confidence</th>
            <th>Summary</th>
            <th>Raw ref</th>
          </tr>
        </thead>
        <tbody>
          {% for finding in findings %}
          <tr>
            <td>{{ finding.record_id }}</td>
            <td>{{ finding.artifact_type }}</td>
            <td>{{ '%.2f'|format(finding.confidence or 0) }}</td>
            <td>{{ finding.summary }}</td>
            <td>{{ finding.raw_ref or 'n/a' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Integrity / Chain of Custody</h2>
      <table>
        <tbody>
          <tr><th>Operator</th><td>{{ acquisition.operator }}</td></tr>
          <tr><th>Device</th><td>{{ acquisition.device.logical_id }} ({{ acquisition.device.platform }})</td></tr>
          <tr><th>Script</th><td>{{ acquisition.script_version }}</td></tr>
          <tr><th>Manifest</th><td>{{ manifest_generated_at }}</td></tr>
          <tr><th>Report file</th><td>{{ report_path }}</td></tr>
        </tbody>
      </table>
      <div>
        <h3>Processing log</h3>
        {% for step in processing_log.steps %}
        <div class=\"log-entry\">
          <strong>{{ step.stage }} · {{ step.timestamp }}</strong>
          <p>{{ step.description }}</p>
          {% if step.actor %}<p>Actor: {{ step.actor }}</p>{% endif %}
        </div>
        {% endfor %}
      </div>
    </section>

    <section>
      <h2>Validation Results</h2>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Expected</th>
            <th>Actual</th>
            <th>Match</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Total records</td>
            <td>{{ validation.expected_record_count or 'n/a' }}</td>
            <td>{{ validation.actual_record_count }}</td>
            <td>{{ 'pass' if validation.expected_record_count == validation.actual_record_count else 'review' }}</td>
          </tr>
          {% for row in validation.artifact_breakdown %}
          <tr>
            <td>{{ row.artifact_type }}</td>
            <td>{{ row.expected }}</td>
            <td>{{ row.actual }}</td>
            <td>{{ 'pass' if row.expected == row.actual else 'review' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      <p>Minimum cross-artifact correlations required: {{ validation.minimum_correlations or 'n/a' }}</p>
      <p>Validation dataset: {{ validation.validation_dataset or 'n/a' }}</p>
    </section>

    <section>
      <h2>Limitations</h2>
      <ul>
        {% for limitation in limitations %}
        <li>{{ limitation }}</li>
        {% endfor %}
      </ul>
    </section>

    <footer>
      Generated for {{ case_id }} using CaseTrace tooling.
    </footer>
  </main>
</body>
</html>
""")


@dataclass
class ReportGenerationResult:
    html_path: Path
    pdf_path: Path | None
    sha256: str


def generate_report(case_dir: Path, *, output_dir: Path | None = None, generate_pdf: bool = False) -> ReportGenerationResult:
    output_dir = output_dir or (case_dir / "reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir = case_dir / "parsed"
    db_path = parsed_dir / "case.db"
    manifest = load_manifest(case_dir)
    processing_log = load_processing_log(case_dir)
    case_metadata = load_json(case_dir / "case.json")
    artifact_counts = _artifact_counts(db_path)
    total_records = sum(artifact_counts.values())
    findings = _fetch_recovery_findings(db_path)
    expected_metrics = _load_expected_metrics(case_dir)
    validation = _build_validation_summary(total_records, artifact_counts, expected_metrics)
    executive = (
        f"{case_metadata.get('title', 'CaseTrace Synthetic Case')} at {case_dir.name} contains "
        f"{total_records} normalized records. Validation compares {validation.get('expected_record_count')} expected points."
    )
    limitations = [
        "Synthetic, single-case dataset only; do not infer real-world device coverage.",
        "Records derive from seeded artifacts and fixed ground truth; deleted items carry reduced confidence.",
    ]
    methods = (
        f"Acquisition executed via {manifest.get('acquisition', {}).get('method')} with parser {manifest.get('parser_version')}.")
    html_path = output_dir / "phase9-investigator-report.html"
    context = {
        "generated_at": utc_timestamp(),
        "case_id": case_metadata.get("case_id"),
        "subject": case_metadata.get("subject", {}).get("display_name"),
        "acquisition": manifest.get("acquisition", {}),
        "parser_version": manifest.get("parser_version"),
        "artifact_counts": artifact_counts,
        "manifest_generated_at": manifest.get("generated_at"),
        "findings": findings or [],
        "processing_log": processing_log,
        "validation": validation,
        "executive_summary": executive,
        "limitations": limitations,
        "report_path": html_path.relative_to(case_dir).as_posix(),
    }
    html = REPORT_TEMPLATE.render(**context)
    html_path.write_text(html, encoding="utf-8")
    sha = sha256_digest(html_path)
    pdf_path = None
    pdf_generated = False
    if generate_pdf:
        pdf_path = output_dir / "phase9-investigator-report.pdf"
        pdf_generated = _render_pdf(html, pdf_path)
        if not pdf_generated:
            pdf_path = None
    report_entry = {
        "generated_at": utc_timestamp(),
        "path": html_path.relative_to(case_dir).as_posix(),
        "sha256": sha,
        "pdf_path": pdf_path.relative_to(case_dir).as_posix() if pdf_path else None,
        "validation": validation,
    }
    manifest["report"] = report_entry
    write_manifest(case_dir, manifest)
    append_processing_step(
        case_dir,
        case_metadata.get("case_id", ""),
        stage="report_export",
        description="Generated Phase 9 investigator report",
        actor=examiner_name(),
        details={
            "report_path": report_entry["path"],
            "report_sha256": sha,
            "pdf_path": report_entry.get("pdf_path"),
            "validation": validation,
        },
    )
    return ReportGenerationResult(html_path=html_path, pdf_path=pdf_path if pdf_generated else None, sha256=sha)


def _artifact_counts(db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute("SELECT artifact_type, COUNT(*) AS cnt FROM timeline_events GROUP BY artifact_type")
        return {row["artifact_type"]: row["cnt"] for row in cursor.fetchall()}


def _fetch_recovery_findings(db_path: Path) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            "SELECT record_id, artifact_type, summary, raw_ref, confidence FROM recovery_findings ORDER BY confidence DESC LIMIT 10"
        )
        return [dict(row) for row in cursor.fetchall()]


def _load_expected_metrics(case_dir: Path) -> dict[str, Any]:
    metrics_path = case_dir / "validation" / "expected_metrics.json"
    if not metrics_path.exists():
        return {}
    return load_json(metrics_path)


def _build_validation_summary(
    total_records: int, artifact_counts: dict[str, int], expected: dict[str, Any]
) -> dict[str, Any]:
    artifact_breakdown = []
    expected_counts = expected.get("expected_artifact_counts", {})
    for artifact, expected_count in expected_counts.items():
        actual = artifact_counts.get(artifact, 0)
        artifact_breakdown.append(
            {"artifact_type": artifact, "expected": expected_count, "actual": actual}
        )
    return {
        "expected_record_count": expected.get("expected_record_count"),
        "actual_record_count": total_records,
        "artifact_breakdown": artifact_breakdown,
        "minimum_correlations": expected.get("minimum_cross_artifact_correlations"),
        "validation_dataset": expected.get("dataset_file"),
    }


def _render_pdf(html: str, path: Path) -> bool:
    try:
        from weasyprint import HTML
    except ImportError:  # pragma: no cover - optional dependency
        return False
    HTML(string=html).write_pdf(str(path))
    return True


def main() -> None:  # pragma: no cover - CLI entrypoint
    import argparse

    parser = argparse.ArgumentParser(description="Generate the Phase 9 investigator report")
    parser.add_argument("--case-dir", type=Path, default=Path("cases/CT-2026-001"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    result = generate_report(args.case_dir, output_dir=args.output_dir, generate_pdf=args.pdf)
    print(f"Report ready: {result.html_path}")
    if result.pdf_path:
        print(f"PDF ready: {result.pdf_path}")


if __name__ == "__main__":
    main()
