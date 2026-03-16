"""Entry point exposing the CaseTrace FastAPI application."""
from backend.app import app  # noqa: F401
from backend.settings import get_engine, get_settings  # noqa: F401

__all__ = ["app", "get_engine", "get_settings"]
