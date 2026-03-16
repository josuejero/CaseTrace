# Phase 10 Validation

Phase 10 closes the loop on credibility: the lab now compares every parsed artifact against the known synthetic truth set, records the checks that ran, and surfaces the tool’s boundaries so a recruiter or reviewer sees that the project follows published forensic guidance.

NIST’s Computer Forensics Tool Testing (CFTT) program and SWGDE both frame methodical validation and documented limitations as baseline practice. The new Phase 10 artifacts explicitly reference those programs to signal this discipline.

## Validation script

- `python tools/validate_phase10.py --case-dir cases/CT-2026-001` runs four automated checks:
  1. **Message count** – ensures the parser emits the exact number of seeded messages.
  2. **Deleted rows / recovered rows** – confirms the WAL recovery steps recover the seeded deleted records.
  3. **Timeline locations** – verifies every ground-truth location (GPS or photo) appears in `timeline_events`.
  4. **EXIF timestamps** – compares the parser’s photo timestamps against the actual JPEG EXIF tags.
- The script writes `cases/CT-2026-001/reports/validation.md` (tracked in this repo) so the report can be viewed without re-running the parser.
- Failures print a clear log and exit non-zero, making this script CI-friendly.

## Test coverage summary

- `tests/test_pipeline.py` still exercises the parser pipeline, recovery logic, search index population, and timeline integrity.
- `tests/test_validation_report.py` exercises the new validation helpers and asserts that the locked bundle still passes the Phase 10 checks.
- Run them together with `python -m pytest tests/test_pipeline.py tests/test_validation_report.py` to reproduce the regression guardrail for this phase.

## Documentation & artifacts

- The Phase 10 report lives in `cases/CT-2026-001/reports/validation.md`; regenerate it any time the parser output changes.
- Mention this script/report in the top-level `README.md` and the case-specific `reports/README.md` so reviewers know where to look.
- The React UI also surfaces the same limitations so the investigator experience never overstates what the lab claims.

## Limitations (per NIST/SWGDE expectations)

1. Not a physical acquisition tool—only the seeded emulator files are examined.
2. Does not bypass device protections or modify the target environment.
3. Synthetic artifacts only; CaseTrace does not ingest real user data.
4. Recovery logic is bounded to the seeded WAL content and is documented elsewhere in the repo.
5. Not intended for unsupervised investigative work without external validation.

