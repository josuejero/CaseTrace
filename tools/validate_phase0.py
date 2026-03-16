from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "cases" / "CT-2026-001"
FILES_DIR = CASE_DIR / "files"
SCHEMAS_DIR = ROOT / "schemas"
EXAMPLES_DIR = SCHEMAS_DIR / "examples"
ACQUISITION_ROOT = "/data/user/0/com.casetrace.waypoint/"
ALLOWED_NAMES = {
    "Jordan Vega",
    "Mira Chen",
    "Riley Brooks",
    "Noah Bennett",
    "Alex Mercer",
}
RESERVED_HOST_RE = re.compile(r"https://([A-Za-z0-9.-]+)")
BANNED_LOCATION_WORDS = {
    "home",
    "residence",
    "apartment",
    "office",
    "workplace",
    "classroom",
    "campus",
    "dorm",
    "headquarters",
}


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validator_for(schema_name: str) -> Draft202012Validator:
    schema = load_json(SCHEMAS_DIR / schema_name)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_instance(name: str, schema_name: str, instance: object) -> None:
    validator = validator_for(schema_name)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(error.message for error in errors)
        raise AssertionError(f"{name} failed schema validation: {details}")



def validate_example_fixtures() -> None:
    valid_examples = [
        "valid-message.json",
        "valid-call.json",
        "valid-browser-visit.json",
        "valid-location-point.json",
        "valid-photo.json",
        "valid-app-event.json",
        "valid-recovered-record.json",
    ]
    invalid_examples = [
        "invalid-missing-content-summary.json",
        "invalid-artifact-type.json",
        "invalid-bad-timestamp.json",
        "invalid-confidence.json",
    ]

    validator = validator_for("artifact-record.schema.json")
    for fixture in valid_examples:
        instance = load_json(EXAMPLES_DIR / fixture)
        errors = list(validator.iter_errors(instance))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise AssertionError(f"{fixture} should be valid: {details}")

    for fixture in invalid_examples:
        instance = load_json(EXAMPLES_DIR / fixture)
        errors = list(validator.iter_errors(instance))
        if not errors:
            raise AssertionError(f"{fixture} should be invalid but passed validation")


def raw_ref_target(raw_ref: str) -> Path:
    _, remainder = raw_ref.split("://", 1)
    target = remainder.split("#", 1)[0]
    return CASE_DIR / target


def bundle_path_from_source_file(source_file: str) -> Path:
    if not source_file.startswith(ACQUISITION_ROOT):
        raise AssertionError(f"source_file outside locked acquisition root: {source_file}")
    relative = source_file.removeprefix(ACQUISITION_ROOT)
    return FILES_DIR / relative


def sha256_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_reserved_hosts(text: str) -> None:
    hosts = RESERVED_HOST_RE.findall(text)
    for host in hosts:
        if not (
            host.endswith(".example")
            or host.endswith(".test")
            or host.endswith(".invalid")
            or host in {"example.com", "example.org", "example.net", "localhost"}
        ):
            raise AssertionError(f"non-reserved host detected: {host}")


def verify_docs_consistency() -> None:
    docs = [
        ROOT / "README.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "parser-schema-spec.md",
    ]
    required_strings = [
        "com.casetrace.waypoint",
        "pixel7-api34-emulator",
        "emulator-5554",
        "Jordan Vega",
        "America/New_York",
        "/data/user/0/com.casetrace.waypoint/",
        "HTML",
        "case_ct_2026_001_ground_truth.json",
        "42",
        "message",
        "call",
        "browser_visit",
        "location_point",
        "photo",
        "app_event",
        "recovered_record",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for needle in required_strings:
            if needle not in text:
                raise AssertionError(f"{doc} is missing required value: {needle}")


def verify_hash_manifest() -> None:
    manifest = load_json(CASE_DIR / "hash_manifest.json")
    validate_instance("hash_manifest.json", "hash-manifest.schema.json", manifest)
    assert isinstance(manifest, dict)
    entries = manifest["files"]
    actual_files = sorted(path for path in FILES_DIR.rglob("*") if path.is_file())
    manifest_paths = {entry["path"] for entry in entries}
    actual_paths = {
        file_path.relative_to(CASE_DIR).as_posix()
        for file_path in actual_files
    }
    if manifest_paths != actual_paths:
        raise AssertionError("hash_manifest.json paths do not match files/ contents")
    for entry in entries:
        file_path = CASE_DIR / entry["path"]
        actual_hash = sha256_digest(file_path)
        actual_size = file_path.stat().st_size
        if actual_hash != entry["sha256"]:
            raise AssertionError(f"hash mismatch for {entry['path']}")
        if actual_size != entry["size_bytes"]:
            raise AssertionError(f"size mismatch for {entry['path']}")


def verify_processing_log() -> None:
    log = load_json(CASE_DIR / "processing_log.json")
    validate_instance("processing_log.json", "processing-log.schema.json", log)
    steps = log.get("steps", [])
    required_stages = {"acquisition", "analysis", "report_export"}
    seen_stages = {step.get("stage") for step in steps}
    missing = required_stages - seen_stages
    if missing:
        raise AssertionError(f"processing_log.json missing stages: {sorted(missing)}")


def verify_case_bundle() -> None:
    case_metadata = load_json(CASE_DIR / "case.json")
    expected_metrics = load_json(CASE_DIR / "validation" / "expected_metrics.json")
    dataset = load_json(CASE_DIR / "validation" / "case_ct_2026_001_ground_truth.json")

    validate_instance("case.json", "case-metadata.schema.json", case_metadata)
    validate_instance("expected_metrics.json", "expected-metrics.schema.json", expected_metrics)
    validate_instance(
        "case_ct_2026_001_ground_truth.json",
        "ground-truth-dataset.schema.json",
        dataset,
    )

    artifact_validator = validator_for("artifact-record.schema.json")
    records = dataset["records"]
    correlations = dataset["cross_artifact_correlations"]
    counts = Counter()

    intact_confidences = []
    recovered_confidences = []

    for record in records:
        errors = list(artifact_validator.iter_errors(record))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise AssertionError(f"record {record.get('record_id')} failed artifact validation: {details}")

        counts[record["artifact_type"]] += 1
        bundle_source = bundle_path_from_source_file(record["source_file"])
        if not bundle_source.exists():
            raise AssertionError(f"source_file does not map to a bundle file: {record['source_file']}")

        raw_target = raw_ref_target(record["raw_ref"])
        if not raw_target.exists():
            raise AssertionError(f"raw_ref target does not exist: {record['raw_ref']}")

        if record["actor"] is not None and record["actor"] not in ALLOWED_NAMES:
            raise AssertionError(f"unexpected actor name: {record['actor']}")
        if record["counterparty"] is not None and record["counterparty"] not in ALLOWED_NAMES:
            raise AssertionError(f"unexpected counterparty name: {record['counterparty']}")

        assert_reserved_hosts(record["content_summary"])

        location = record["location"]
        if location is not None:
            lowered = location["label"].lower()
            if any(word in lowered for word in BANNED_LOCATION_WORDS):
                raise AssertionError(f"banned location label detected: {location['label']}")

        if record["deleted_flag"]:
            if record["artifact_type"] != "recovered_record":
                raise AssertionError("deleted_flag is only allowed on recovered_record items")
            if not record["source_file"].endswith(".db-wal"):
                raise AssertionError("deleted records must originate from WAL sources")
            recovered_confidences.append(record["confidence"])
        else:
            intact_confidences.append(record["confidence"])

    if len(records) != expected_metrics["expected_record_count"]:
        raise AssertionError("ground-truth record count does not match expected_metrics.json")
    if counts != Counter(expected_metrics["expected_artifact_counts"]):
        raise AssertionError("artifact counts do not match expected_metrics.json")

    deleted_count = sum(1 for record in records if record["deleted_flag"])
    if deleted_count != expected_metrics["expected_deleted_record_count"]:
        raise AssertionError("deleted record total does not match expected_metrics.json")

    if max(recovered_confidences) >= min(intact_confidences):
        raise AssertionError("recovered record confidence must remain below intact record confidence")

    record_index = {record["record_id"]: record for record in records}
    if len(correlations) < expected_metrics["minimum_cross_artifact_correlations"]:
        raise AssertionError("cross-artifact correlation count is below the minimum")
    for correlation in correlations:
        types = set()
        for record_id in correlation["linked_record_ids"]:
            if record_id not in record_index:
                raise AssertionError(f"correlation references unknown record_id: {record_id}")
            types.add(record_index[record_id]["artifact_type"])
        if len(types) < 2:
            raise AssertionError(f"correlation {correlation['correlation_id']} is not cross-artifact")


def main() -> None:
    validate_example_fixtures()
    verify_case_bundle()
    verify_hash_manifest()
    verify_processing_log()
    verify_docs_consistency()
    print("Phase 0 verification passed.")


if __name__ == "__main__":
    main()
