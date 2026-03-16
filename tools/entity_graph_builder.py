"""Entity graph builder for CaseTrace Phase 5 analysis."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from parser.common import load_json
from parser.sqlite_utils import sqlite_readonly_connection


def _slugify(value: str) -> str:
    trimmed = value.strip().lower()
    if not trimmed:
        return "node"
    return "".join(ch if ch.isalnum() else "_" for ch in trimmed)


_URL_PATTERN = re.compile(r"https?://[^\s,]+")


def _extract_url_from_summary(summary: str | None) -> str | None:
    if not summary:
        return None
    match = _URL_PATTERN.search(summary)
    if not match:
        return None
    return match.group(0).rstrip(".,)")


def _keyword_label(summary: str | None, fallback: str) -> str:
    if not summary:
        return fallback
    snippet = summary.split(".")[0].strip()
    if not snippet:
        return fallback
    return snippet[:120]


@dataclass
class GraphNode:
    node_id: str
    label: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "type": self.type,
            "metadata": self.metadata,
        }


@dataclass
class GraphEdge:
    edge_id: str
    source: str
    target: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "metadata": self.metadata,
        }


@dataclass
class GraphData:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    generated_at: str
    case_id: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "generated_at": self.generated_at,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


class EntityGraphBuilder:
    """Builds a graph that ties artifacts to traced evidence."""

    def __init__(self, db_path: Path, case_dir: Path):
        self.db_path = db_path
        self.case_dir = case_dir
        self.case_metadata = load_json(case_dir / "case.json")
        self.case_id = self.case_metadata.get("case_id")
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.person_nodes: Dict[str, str] = {}
        self.phone_nodes: Dict[str, str] = {}
        self.location_nodes: Dict[tuple[float, float, str], str] = {}
        self.file_nodes: Dict[str, str] = {}
        self._edge_counter = 0
        self.case_file_node_id: str | None = None
        self.app_account_node_id: str | None = None

    def build(self) -> GraphData:
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        with sqlite_readonly_connection(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            self._load_person_nodes(connection)
            self._ensure_subject_person()
            self._ensure_app_account_node()
            self._ensure_device_node()
            self._build_messages(connection)
            self._build_calls(connection)
            self._build_browser_visits(connection)
            self._build_locations(connection)
            self._build_photos(connection)
            self._build_app_events(connection)
        self._ensure_case_file_node()
        self._link_files_to_case()
        return GraphData(
            case_id=self.case_id,
            generated_at=generated_at,
            nodes=list(self.nodes.values()),
            edges=self.edges,
        )

    def _load_person_nodes(self, connection: sqlite3.Connection) -> None:
        cursor = connection.execute("SELECT entity_id, display_name FROM entities")
        for row in cursor:
            self._ensure_person(row["display_name"], entity_id=row["entity_id"])

    def _ensure_subject_person(self) -> None:
        subject = self.case_metadata.get("subject", {}).get("display_name")
        if subject:
            self._ensure_person(subject)

    def _ensure_app_account_node(self) -> str | None:
        seed_app = self.case_metadata.get("seed_app", {})
        label = seed_app.get("label") or seed_app.get("package_name") or "Waypoint"
        subject = self.case_metadata.get("subject", {}).get("display_name")
        node_label = f"{label} account ({subject})" if subject else f"{label} account"
        metadata = {
            "package": seed_app.get("package_name"),
            "version": seed_app.get("version"),
            "subject": subject,
        }
        node_id = f"app-account-{_slugify(node_label)}"
        node_id = self._register_node_if_missing(node_id, node_label, "app account", metadata)
        self.app_account_node_id = node_id
        if subject:
            person_node = self._ensure_person(subject)
            self._add_edge(
                "references",
                node_id,
                person_node,
                {
                    "record_id": None,
                    "raw_ref": None,
                    "artifact_type": "case_metadata",
                    "source_file": str(self.case_dir / "case.json"),
                },
            )
        return node_id

    def _ensure_device_node(self) -> str | None:
        device = self.case_metadata.get("device", {})
        if not device:
            return None
        logical_id = device.get("logical_id") or device.get("adb_serial")
        if not logical_id:
            return None
        platform = device.get("platform")
        label = f"{logical_id} ({platform})" if platform else logical_id
        metadata = {
            "adb_serial": device.get("adb_serial"),
            "platform": platform,
        }
        node_id = self._register_node_if_missing(f"device-{_slugify(label)}", label, "device", metadata)
        if self.app_account_node_id:
            self._add_edge(
                "references",
                self.app_account_node_id,
                node_id,
                {
                    "record_id": None,
                    "raw_ref": None,
                    "artifact_type": "case_metadata",
                    "source_file": str(self.case_dir / "case.json"),
                },
            )
        return node_id

    def _build_messages(self, connection: sqlite3.Connection) -> None:
        query = """
            SELECT record_id, actor, counterparty, raw_ref, source_file, confidence
            FROM artifacts_messages
        """
        for row in connection.execute(query):
            metadata = self._artifact_metadata(row, "message")
            actor_id = self._ensure_person(row["actor"])
            target_id = self._ensure_person(row["counterparty"])
            file_node = self._ensure_file_node(row["source_file"])
            if actor_id and target_id:
                self._add_edge("messaged", actor_id, target_id, metadata)
            if actor_id and file_node:
                self._add_edge("stored_in", actor_id, file_node, metadata)
            if target_id and file_node:
                self._add_edge("stored_in", target_id, file_node, metadata)

    def _build_calls(self, connection: sqlite3.Connection) -> None:
        query = """
            SELECT record_id, actor, counterparty, raw_ref, source_file, call_type, duration_seconds, confidence
            FROM artifacts_calls
        """
        for row in connection.execute(query):
            metadata = self._artifact_metadata(row, "call")
            actor_id = self._ensure_person(row["actor"])
            phone_id = self._ensure_phone_node(row["record_id"], row["counterparty"], row["call_type"])
            file_node = self._ensure_file_node(row["source_file"])
            if actor_id and phone_id:
                self._add_edge("called", actor_id, phone_id, metadata)
            if phone_id and file_node:
                self._add_edge("stored_in", phone_id, file_node, metadata)
            if actor_id and file_node:
                self._add_edge("stored_in", actor_id, file_node, metadata)

    def _build_browser_visits(self, connection: sqlite3.Connection) -> None:
        query = """
            SELECT record_id, actor, url, content_summary, raw_ref, source_file, confidence
            FROM artifacts_browser
        """
        for row in connection.execute(query):
            metadata = self._artifact_metadata(row, "browser_visit")
            actor_id = self._ensure_person(row["actor"])
            url_id = self._ensure_url_node(
                row["url"],
                record_id=row["record_id"],
                context_summary=row["content_summary"],
            )
            file_node = self._ensure_file_node(row["source_file"])
            if actor_id and url_id:
                self._add_edge("visited", actor_id, url_id, metadata)
            if url_id and file_node:
                self._add_edge("stored_in", url_id, file_node, metadata)

    def _build_locations(self, connection: sqlite3.Connection) -> None:
        query = """
            SELECT record_id, actor, latitude, longitude, label, raw_ref, source_file, confidence
            FROM artifacts_locations
        """
        for row in connection.execute(query):
            metadata = self._artifact_metadata(row, "location_point")
            actor_id = self._ensure_person(row["actor"])
            location_id = self._ensure_location_node(row["latitude"], row["longitude"], row["label"])
            file_node = self._ensure_file_node(row["source_file"])
            if actor_id and location_id:
                self._add_edge("located_at", actor_id, location_id, metadata)
            if location_id and file_node:
                self._add_edge("stored_in", location_id, file_node, metadata)

    def _build_photos(self, connection: sqlite3.Connection) -> None:
        query = """
            SELECT record_id, actor, counterparty, file_name, latitude, longitude, location_label,
                   raw_ref, source_file, confidence
            FROM artifacts_media
        """
        for row in connection.execute(query):
            metadata = self._artifact_metadata(row, "photo")
            photo_node = self._ensure_photo_node(row["record_id"], row["file_name"], row["counterparty"])
            location_id = self._ensure_location_node(row["latitude"], row["longitude"], row["location_label"])
            actor_id = self._ensure_person(row["actor"])
            file_node = self._ensure_file_node(row["source_file"])
            if photo_node and location_id:
                self._add_edge("captured_at", photo_node, location_id, metadata)
            if actor_id and location_id:
                self._add_edge("located_at", actor_id, location_id, metadata)
            if photo_node and file_node:
                self._add_edge("stored_in", photo_node, file_node, metadata)

    def _build_app_events(self, connection: sqlite3.Connection) -> None:
        query = """
            SELECT record_id, actor, content_summary, raw_ref, source_file, confidence
            FROM artifacts_events
        """
        for row in connection.execute(query):
            metadata = self._artifact_metadata(row, "app_event")
            keyword_label = _keyword_label(row["content_summary"], row["record_id"])
            keyword_id = self._ensure_keyword_node(keyword_label, row["record_id"], row["content_summary"])
            actor_id = self._ensure_person(row["actor"])
            file_node = self._ensure_file_node(row["source_file"])
            if keyword_id and actor_id:
                self._add_edge("references", keyword_id, actor_id, metadata)
            if keyword_id and file_node:
                self._add_edge("stored_in", keyword_id, file_node, metadata)

    def _link_files_to_case(self) -> None:
        self._ensure_case_file_node()
        if not self.case_file_node_id:
            return
        for path, file_node_id in self.file_nodes.items():
            if file_node_id == self.case_file_node_id:
                continue
            self._add_edge(
                "linked_to_case",
                file_node_id,
                self.case_file_node_id,
                {
                    "record_id": None,
                    "raw_ref": None,
                    "artifact_type": "case_metadata",
                    "source_file": str(self.case_dir / "case.json"),
                    "file_path": path,
                },
            )

    def _artifact_metadata(self, row: sqlite3.Row, artifact_type: str) -> Dict[str, Any]:
        return {
            "record_id": row["record_id"],
            "raw_ref": row["raw_ref"],
            "artifact_type": artifact_type,
            "confidence": row["confidence"],
            "source_file": row["source_file"],
        }

    def _ensure_person(self, name: str | None, entity_id: str | None = None) -> str | None:
        if not name:
            return None
        normalized = name.strip()
        if not normalized:
            return None
        key = normalized.lower()
        if key in self.person_nodes:
            return self.person_nodes[key]
        node_id = entity_id or f"person-{_slugify(normalized)}"
        self._register_node_if_missing(node_id, normalized, "person", {"source": "parsed_entities"})
        self.person_nodes[key] = node_id
        return node_id

    def _ensure_phone_node(self, record_id: str, label: str | None, call_type: str | None) -> str:
        title = f"{record_id} line to {label}" if label else record_id
        node_id = f"phone-{_slugify(title)}"
        metadata = {"call_type": call_type, "counterparty": label}
        self.phone_nodes[record_id] = node_id
        return self._register_node_if_missing(node_id, title, "phone number", metadata)

    def _ensure_url_node(
        self,
        raw_url: str | None,
        *,
        record_id: str | None = None,
        context_summary: str | None = None,
    ) -> str | None:
        actual = raw_url or _extract_url_from_summary(context_summary)
        if not actual:
            return None
        node_id = f"url-{_slugify(actual)}"
        parsed = urlparse(actual)
        metadata = {
            "domain": parsed.netloc or None,
            "scheme": parsed.scheme or None,
            "record_id": record_id,
        }
        if context_summary:
            metadata["context_summary"] = context_summary
        return self._register_node_if_missing(node_id, actual, "URL", metadata)

    def _ensure_keyword_node(self, label: str | None, record_id: str | None, summary: str | None) -> str | None:
        if not label:
            return None
        node_id = f"keyword-{_slugify(label)}"
        if node_id not in self.nodes:
            self._register_node_if_missing(node_id, label, "keyword", {"records": [], "summaries": []})
        node = self.nodes[node_id]
        if record_id:
            node.metadata.setdefault("records", []).append(record_id)
        if summary:
            node.metadata.setdefault("summaries", []).append(summary)
        return node_id

    def _ensure_location_node(self, latitude: float | None, longitude: float | None, label: str | None) -> str | None:
        if latitude is None or longitude is None:
            return None
        normalized_label = label or f"{latitude},{longitude}"
        key = (round(latitude, 5), round(longitude, 5), normalized_label)
        if key in self.location_nodes:
            return self.location_nodes[key]
        node_id = f"location-{_slugify(normalized_label)}"
        metadata = {
            "label": normalized_label,
            "latitude": latitude,
            "longitude": longitude,
        }
        self.location_nodes[key] = node_id
        return self._register_node_if_missing(node_id, normalized_label, "location", metadata)

    def _ensure_photo_node(self, record_id: str, file_name: str | None, counterparty: str | None) -> str:
        label = file_name or record_id
        node_id = f"photo-{_slugify(label)}"
        metadata = {"file_name": file_name, "counterparty": counterparty}
        return self._register_node_if_missing(node_id, label, "photo", metadata)

    def _ensure_file_node(self, path: str | None) -> str | None:
        if not path:
            return None
        normalized = path.strip()
        if not normalized:
            return None
        node_id = f"file-{_slugify(normalized)}"
        self.file_nodes[normalized] = node_id
        return self._register_node_if_missing(node_id, normalized, "file", {"path": normalized})

    def _ensure_case_file_node(self) -> str | None:
        if self.case_file_node_id:
            return self.case_file_node_id
        case_file = self.case_dir / "case.json"
        if not case_file.exists():
            return None
        node_id = self._ensure_file_node(str(case_file))
        self.case_file_node_id = node_id
        return node_id

    def _register_node_if_missing(
        self, node_id: str, label: str, node_type: str, metadata: Dict[str, Any] | None = None
    ) -> str:
        if node_id in self.nodes:
            node = self.nodes[node_id]
            for key, value in (metadata or {}).items():
                if value is not None:
                    if key in node.metadata and isinstance(node.metadata[key], list):
                        node.metadata[key].append(value)
                    else:
                        node.metadata[key] = value
            return node_id
        node_metadata = {k: v for k, v in (metadata or {}).items() if v is not None}
        self.nodes[node_id] = GraphNode(node_id=node_id, label=label, type=node_type, metadata=node_metadata)
        return node_id

    def _add_edge(self, edge_type: str, source: str, target: str, metadata: Dict[str, Any]) -> None:
        if not source or not target:
            return
        data = metadata.copy()
        data.setdefault("record_id", None)
        data.setdefault("raw_ref", None)
        data.setdefault("artifact_type", None)
        data.setdefault("confidence", None)
        data.setdefault("source_file", None)
        edge_id = f"edge-{self._edge_counter + 1:04d}"
        self._edge_counter += 1
        self.edges.append(GraphEdge(edge_id=edge_id, source=source, target=target, type=edge_type, metadata=data))
