"""Command-line entry point for the CaseTrace parser pipeline."""
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from parser import run_pipeline


def main() -> None:
    parser = ArgumentParser(description="Run the CaseTrace Phase 3 parser pipeline.")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=Path("cases/CT-2026-001"),
        help="Path to the case folder containing the evidence bundle.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where parsed outputs (case.db, artifact_records.json) will be written.",
    )
    args = parser.parse_args()
    output_dir = args.output_dir or args.case_dir / "parsed"
    run_pipeline(args.case_dir, output_dir)


if __name__ == "__main__":
    main()
