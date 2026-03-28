from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def clear_engine_cache() -> None:
    get_engine.cache_clear()
    _session_factory.cache_clear()


def open_session() -> Session:
    """Synchronous session for startup scripts and one-off use."""
    return _session_factory()()


def get_db() -> Generator[Session, None, None]:
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
