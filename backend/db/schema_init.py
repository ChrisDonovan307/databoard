"""Greenfield schema creation. Alembic is deferred until the first post-deploy
schema change (ADR-0001 / plan)."""

from __future__ import annotations

from sqlalchemy import Engine

from db import get_engine
from db.models import Base


def create_all(engine: Engine | None = None) -> None:
    Base.metadata.create_all(engine or get_engine())
