"""Unit tests for the shared integrity helpers."""
from pathlib import Path

from integrity import (
    append_processing_step,
    collect_file_entries,
    gather_file_summary,
    load_manifest,
    load_processing_log,
    write_manifest,
)


def test_collect_entries_and_processing_log(tmp_path: Path) -> None:
    case_dir = tmp_path
    files_dir = case_dir / "files"
    (files_dir / "media").mkdir(parents=True, exist_ok=True)
    sample = files_dir / "media" / "artifact.txt"
    sample.write_text("trace data")

    entries = collect_file_entries(files_dir, case_dir)
    assert len(entries) == 1
    assert entries[0]["path"].endswith("media/artifact.txt")

    summary = gather_file_summary(entries)
    assert summary["file_count"] == 1
    assert summary["total_size_bytes"] == sample.stat().st_size

    manifest = {
        "case_id": "CT-2026-001",
        "algorithm": "sha256",
        "generated_at": "2026-03-15T22:21:10Z",
        "acquisition": {
            "acquired_at": "2026-03-13T01:15:00Z",
            "operator": "CaseTrace Lab Analyst",
            "script_version": "phase2-acquisition/1.0.0",
            "device": {
                "logical_id": "pixel7-api34-emulator",
                "adb_serial": "emulator-5554",
                "platform": "Android 14 (API 34)",
            },
            "method": "adb exec-out run-as com.casetrace.waypoint tar -cf - .",
        },
        "app": {
            "package": "com.casetrace.waypoint",
            "label": "Waypoint",
            "version": "0.1.0-phase0",
        },
        "environment": {
            "git_commit": "abc123",
            "container_image_digest": None,
        },
        "parser_version": "phase0-spec/1.0.0",
        "files": entries,
    }

    write_manifest(case_dir, manifest)
    loaded = load_manifest(case_dir)
    assert loaded["case_id"] == "CT-2026-001"
    assert loaded["files"] == entries

    append_processing_step(
        case_dir,
        manifest["case_id"],
        stage="acquisition",
        description="seed acquisition",
        actor="Codex",
        details={"hash_summary": summary},
    )

    log = load_processing_log(case_dir)
    assert log["case_id"] == "CT-2026-001"
    assert log["steps"][-1]["stage"] == "acquisition"
