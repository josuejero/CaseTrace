"""WAL-aware recovery helpers for CaseTrace Phase 6."""
from __future__ import annotations

import logging
import re
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .common import load_json
from .models import ArtifactRecordModel, PARSER_VERSION, ParsedArtifact

logger = logging.getLogger(__name__)

AcquisitionRoot = "/data/user/0/com.casetrace.waypoint"

FindingLabel = Literal["observed", "recovered", "inferred"]

RECOVERY_RECORD_IDS: dict[str, str] = {
    "messages": "rec-001",
    "browser_history": "rec-002",
}

CONFIDENCE_MAP: dict[str, float] = {
    "messages": 0.58,
    "browser_history": 0.55,
}

TABLE_HANDLERS: dict[str, str] = {
    "messages": "_build_messages_recovery",
    "browser_history": "_build_browser_history_recovery",
}

TABLE_ARTIFACT_TYPES: dict[str, str] = {
    "messages": "message",
    "browser_history": "browser_visit",
}

ASCII_PATTERN = re.compile(
    r"(?P<title>[\x20-\x7e]{4,120}?)(?P<url>https?://[^\x00]{10,256}?)(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:]+Z)",
    flags=re.DOTALL,
)

OBSERVED_CONFIDENCE = 0.92


@dataclass
class RecoveryFinding:
    record_id: str
    artifact_type: str
    raw_ref: str
    confidence: float
    summary: str
    label: FindingLabel
    database_file: str
    wal_file: str | None
    parser_method: str
    parser_version: str


@dataclass
class WalRecoveryResult:
    artifacts: list[ParsedArtifact]
    findings: list[RecoveryFinding]


@dataclass
class _Candidate:
    rowid: int | str
    row: dict[str, object]
    label: FindingLabel


def parse_wal_recovery(case_dir: Path) -> WalRecoveryResult:
    db_dir = case_dir / "files" / "databases"
    if not db_dir.exists():
        return WalRecoveryResult([], [])

    bundle_path = _bundle_path(case_dir)
    findings: list[RecoveryFinding] = []
    artifacts: list[ParsedArtifact] = []

    for db_path in sorted(db_dir.glob("*.db")):
        logger.debug("evaluating WAL for %s", db_path.name)
        result = _recover_from_db(db_path, bundle_path)
        artifacts.extend(result.artifacts)
        findings.extend(result.findings)

    return WalRecoveryResult(artifacts=artifacts, findings=findings)


def _bundle_path(case_dir: Path) -> Path | None:
    case_json = case_dir / "case.json"
    if not case_json.exists():
        return None
    try:
        metadata = load_json(case_json)
    except FileNotFoundError:
        return None
    case_id = metadata.get("case_id")
    if not case_id:
        return None
    candidate = case_dir / f"{case_id}-evidence-bundle.zip"
    if candidate.exists():
        return candidate
    return None


@dataclass
class _CopySet:
    observed_db: Path
    wal_db: Path
    wal_file: Path


class _WalCopier:
    def __init__(self, db_path: Path, bundle: Path | None):
        self.db_path = db_path
        self.bundle = bundle
        self.temp_dir = Path(tempfile.mkdtemp(prefix="casetrace-wal-"))
        self.observed_dir = self.temp_dir / "observed"
        self.wal_dir = self.temp_dir / "wal"
        self.observed_dir.mkdir(parents=True)
        self.wal_dir.mkdir(parents=True)
        self.observed_db = self.observed_dir / db_path.name
        self.wal_db = self.wal_dir / db_path.name
        self.wal_file = self.wal_dir / f"{db_path.name}-wal"
        self.shm_file = self.wal_dir / f"{db_path.name}-shm"

    def __enter__(self) -> _CopySet:
        shutil.copy(self.db_path, self.observed_db)
        shutil.copy(self.db_path, self.wal_db)
        wal_source = self._auxiliary_path("-wal")
        shm_source = self._auxiliary_path("-shm")
        if wal_source:
            shutil.copy(wal_source, self.wal_file)
        if shm_source:
            shutil.copy(shm_source, self.shm_file)
        return _CopySet(observed_db=self.observed_db, wal_db=self.wal_db, wal_file=self.wal_file)

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _auxiliary_path(self, suffix: str) -> Path | None:
        candidate = self.db_path.with_name(self.db_path.name + suffix)
        if candidate.exists():
            return candidate
        if self.bundle:
            entry = f"files/databases/{self.db_path.name}{suffix}"
            try:
                with zipfile.ZipFile(self.bundle) as bundle:
                    with bundle.open(entry) as source, (self.temp_dir / "tmp.bin").open("wb") as sink:
                        shutil.copyfileobj(source, sink)
                    temp_path = self.temp_dir / "tmp.bin"
                    result = self.temp_dir / f"{self.db_path.name}{suffix}"
                    shutil.move(str(temp_path), result)
                    return result
            except KeyError:
                return None
        return None


def _recover_from_db(db_path: Path, bundle: Path | None) -> WalRecoveryResult:
    try:
        with _WalCopier(db_path, bundle) as copies:
            if not copies.wal_file.exists():
                logger.debug("missing WAL file for %s", db_path.name)
                return WalRecoveryResult([], [])
            observed_conn = sqlite3.connect(copies.observed_db)
            wal_conn = sqlite3.connect(copies.wal_db)
            try:
                journal = observed_conn.execute("PRAGMA journal_mode").fetchone()
                if not journal or journal[0].lower() != "wal":
                    logger.debug("skipping %s with journal_mode=%s", db_path.name, journal[0] if journal else None)
                    return WalRecoveryResult([], [])
                try:
                    tables = [
                        row[0]
                        for row in wal_conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                        )
                    ]
                except sqlite3.DatabaseError as exc:
                    logger.warning("failed to list tables for %s: %s", db_path.name, exc)
                    return WalRecoveryResult([], [])

                findings: list[RecoveryFinding] = []
                artifacts: list[ParsedArtifact] = []
                for table in tables:
                    handler_name = TABLE_HANDLERS.get(table)
                    if not handler_name:
                        continue
                    observed_rows = _rows_by_rowid(observed_conn, table)
                    if observed_rows:
                        first_rowid = next(iter(observed_rows))
                        findings.append(
                            _build_observed_finding(
                                table,
                                first_rowid,
                                observed_rows[first_rowid],
                                db_path,
                                copies.wal_file,
                            )
                        )
                    wal_rows = _rows_by_rowid(wal_conn, table)
                    candidates = _collect_candidates(table, observed_rows, wal_rows, copies.wal_file)
                    if not candidates:
                        continue
                    candidate = candidates[0]
                    handler = globals()[handler_name]
                    artifact, finding = handler(
                        candidate.rowid,
                        candidate.row,
                        db_path,
                        label=candidate.label,
                    )
                    artifacts.append(artifact)
                    findings.append(finding)
                return WalRecoveryResult(artifacts=artifacts, findings=findings)
            finally:
                observed_conn.close()
                wal_conn.close()
    except sqlite3.DatabaseError as exc:
        logger.warning("WAL recovery failed for %s: %s", db_path.name, exc)
        return WalRecoveryResult([], [])


def _collect_candidates(
    table: str,
    observed_rows: dict[int | str, dict[str, object]],
    wal_rows: dict[int | str, dict[str, object]],
    wal_file: Path,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    seen: set[int | str] = set()
    for rowid in sorted(set(wal_rows) - set(observed_rows)):
        candidates.append(_Candidate(rowid=rowid, row=wal_rows[rowid], label="recovered"))
        seen.add(rowid)
    if table == "messages":
        for rowid, row in observed_rows.items():
            if row.get("deleted_flag") and rowid not in seen:
                candidates.append(_Candidate(rowid=rowid, row=row, label="inferred"))
                seen.add(rowid)
    if table == "browser_history" and not candidates:
        fallback = _browser_candidate_from_wal(
            wal_file,
            {row.get("url") for row in observed_rows.values() if row.get("url")},
            {row.get("title") for row in observed_rows.values() if row.get("title")},
            {row.get("timestamp") for row in observed_rows.values() if row.get("timestamp")},
        )
        if fallback:
            rowid, data = fallback
            candidates.append(_Candidate(rowid=rowid, row=data, label="inferred"))
    return candidates


def _rows_by_rowid(connection: sqlite3.Connection, table: str) -> dict[int | str, dict[str, object]]:
    cursor = connection.execute(f"SELECT rowid, * FROM {table}")
    cols = [desc[0] for desc in cursor.description][1:]
    result: dict[int | str, dict[str, object]] = {}
    for row in cursor:
        data = {col: row[idx + 1] for idx, col in enumerate(cols)}
        result[row[0]] = data
    return result


def _browser_candidate_from_wal(
    wal_path: Path,
    seen_urls: set[str],
    seen_titles: set[str],
    seen_timestamps: set[str],
) -> tuple[str, dict[str, object]] | None:
    try:
        data = wal_path.read_bytes()
    except OSError as exc:
        logger.warning("unable to read WAL file %s: %s", wal_path, exc)
        return None
    text = data.decode("latin-1", errors="ignore")
    for match in ASCII_PATTERN.finditer(text):
        url = match.group("url")
        if url in seen_urls:
            continue
        title = match.group("title").strip()
        title = re.sub(r"^[^A-Za-z0-9]+", "", title)
        if not title or title in seen_titles:
            continue
        timestamp = match.group("timestamp")
        if timestamp in seen_timestamps:
            continue
        row = {
            "title": title,
            "url": url,
            "typed_url": 1,
            "referrer": None,
            "timestamp": timestamp,
        }
        return (f"wal-browser-{url}", row)
    return None


def _build_observed_finding(
    table: str,
    rowid: int | str,
    row: dict[str, object],
    db_path: Path,
    wal_file: Path,
) -> RecoveryFinding:
    raw_ref = f"db://files/databases/{db_path.name}#table={table}&rowid={rowid}"
    database_file = f"{AcquisitionRoot}/databases/{db_path.name}"
    wal_file_uri = f"{AcquisitionRoot}/databases/{db_path.name}-wal" if wal_file.exists() else None
    summary = (
        f"Observed row {rowid} in {table} within the main database (timestamp={row.get('timestamp')})."
    )
    artifact_type = TABLE_ARTIFACT_TYPES.get(table, "recovered_record")
    return RecoveryFinding(
        record_id=f"obs-{table}-{rowid}",
        artifact_type=artifact_type,
        raw_ref=raw_ref,
        confidence=OBSERVED_CONFIDENCE,
        summary=summary,
        label="observed",
        database_file=database_file,
        wal_file=wal_file_uri,
        parser_method="wal_recovery",
        parser_version=PARSER_VERSION,
    )


def _finding_confidence(table: str, label: FindingLabel) -> float:
    base = CONFIDENCE_MAP.get(table, 0.5)
    if label == "inferred":
        return max(base - 0.05, 0.1)
    return base


def _build_messages_recovery(
    rowid: int | str,
    row: dict[str, object],
    db_path: Path,
    label: FindingLabel,
) -> tuple[ParsedArtifact, RecoveryFinding]:
    record_id = RECOVERY_RECORD_IDS["messages"]
    timestamp = row.get("timestamp")
    raw_ref = f"db://files/databases/{db_path.name}-wal#table=messages&rowid={rowid}"
    source_file = f"{AcquisitionRoot}/databases/{db_path.name}-wal"
    database_file = f"{AcquisitionRoot}/databases/{db_path.name}"
    content = row.get("body") or "Recovered deleted message from WAL"
    prefix = "Inferred" if label == "inferred" else "Recovered"
    summary = f"{prefix} deleted message from WAL: {content}"
    confidence = _finding_confidence("messages", label)
    artifact = ParsedArtifact(
        record=ArtifactRecordModel(
            artifact_type="recovered_record",
            source_file=source_file,
            record_id=record_id,
            event_time_start=timestamp,
            event_time_end=timestamp,
            actor=row.get("sender"),
            counterparty=row.get("recipient"),
            location=None,
            content_summary=content,
            raw_ref=raw_ref,
            deleted_flag=True,
            confidence=confidence,
            parser_version=PARSER_VERSION,
        ),
        metadata={"table": "messages", "source_rowid": rowid},
    )
    finding = RecoveryFinding(
        record_id=record_id,
        artifact_type="recovered_record",
        raw_ref=raw_ref,
        confidence=confidence,
        summary=summary,
        label=label,
        database_file=database_file,
        wal_file=source_file,
        parser_method="wal_recovery",
        parser_version=PARSER_VERSION,
    )
    return artifact, finding


def _build_browser_history_recovery(
    rowid: int | str,
    row: dict[str, object],
    db_path: Path,
    label: FindingLabel,
) -> tuple[ParsedArtifact, RecoveryFinding]:
    record_id = RECOVERY_RECORD_IDS["browser_history"]
    timestamp = row.get("timestamp")
    raw_ref = f"db://files/databases/{db_path.name}-wal#table=browser_history&rowid={rowid}"
    source_file = f"{AcquisitionRoot}/databases/{db_path.name}-wal"
    database_file = f"{AcquisitionRoot}/databases/{db_path.name}"
    url = row.get("url")
    typed_url = row.get("typed_url", 1)
    summary = f"{'Inferred' if label == 'inferred' else 'Recovered'} deleted browser lookup for {url} from WAL."
    confidence = _finding_confidence("browser_history", label)
    artifact = ParsedArtifact(
        record=ArtifactRecordModel(
            artifact_type="recovered_record",
            source_file=source_file,
            record_id=record_id,
            event_time_start=timestamp,
            event_time_end=timestamp,
            actor=None,
            counterparty=None,
            location=None,
            content_summary=summary,
            raw_ref=raw_ref,
            deleted_flag=True,
            confidence=confidence,
            parser_version=PARSER_VERSION,
        ),
        metadata={"table": "browser_history", "raw_url": url, "typed_url": typed_url},
    )
    finding = RecoveryFinding(
        record_id=record_id,
        artifact_type="recovered_record",
        raw_ref=raw_ref,
        confidence=confidence,
        summary=summary,
        label=label,
        database_file=database_file,
        wal_file=source_file,
        parser_method="wal_recovery",
        parser_version=PARSER_VERSION,
    )
    return artifact, finding
