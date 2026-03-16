"""Settings and cached engine accessors for the backend API."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from backend.engine import CaseDataEngine


class CaseSearchSettings(BaseSettings):
    case_db_path: Path = Field(default=Path("cases/CT-2026-001/parsed/case.db"), env="CASE_DB_PATH")
    context_window_minutes: int = Field(default=3, ge=1, le=15, env="CONTEXT_WINDOW_MINUTES")


@lru_cache(maxsize=1)
def get_settings() -> CaseSearchSettings:
    return CaseSearchSettings()


@lru_cache(maxsize=1)
def get_engine() -> CaseDataEngine:
    settings = get_settings()
    return CaseDataEngine(settings.case_db_path)
