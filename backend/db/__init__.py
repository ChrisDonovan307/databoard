"""Database engine / session wiring.

Framework-agnostic: a plain SQLAlchemy 2.0 engine + sessionmaker, no Flask-SQLAlchemy,
so the same layer works under Flask now and FastAPI later.

Connection string comes from the ``DATABASE_URL`` env var, e.g.
``mysql+pymysql://user:pass@127.0.0.1:3306/databoard``. On a laptop this points at an
SSH tunnel to the Silk MySQL; on Silk it points at localhost.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Lazily build the process-wide engine from ``DATABASE_URL``."""
    global _engine, _SessionLocal
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to backend/.env "
                "(mysql+pymysql://user:pass@127.0.0.1:3306/databoard)."
            )
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def get_session() -> Iterator[Session]:
    """Session scope with commit/rollback handling."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
