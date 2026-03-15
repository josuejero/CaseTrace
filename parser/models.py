"""Pydantic models for normalized CaseTrace records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, StrictBool, StrictFloat, StrictStr


PARSER_VERSION = "phase0-spec/1.0.0"


ArtifactType = Literal[
    "message",
    "call",
    "browser_visit",
    "location_point",
    "photo",
    "app_event",
    "recovered_record",
]


class LocationModel(BaseModel):
    latitude: StrictFloat
    longitude: StrictFloat
    accuracy_m: StrictFloat = Field(ge=0)
    label: StrictStr


class ArtifactRecordModel(BaseModel):
    artifact_type: ArtifactType
    source_file: StrictStr
    record_id: StrictStr
    event_time_start: StrictStr
    event_time_end: StrictStr
    actor: Optional[StrictStr] = None
    counterparty: Optional[StrictStr] = None
    location: Optional[LocationModel] = None
    content_summary: StrictStr
    raw_ref: StrictStr
    deleted_flag: StrictBool
    confidence: StrictFloat = Field(ge=0.0, le=1.0)
    parser_version: StrictStr = PARSER_VERSION

    class Config:
        frozen = True
        validate_assignment = True


@dataclass
class ParsedArtifact:
    """Parsed artifact plus the raw metadata needed for the case database."""

    record: ArtifactRecordModel
    metadata: dict[str, Any] = field(default_factory=dict)
