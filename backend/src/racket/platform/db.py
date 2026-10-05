"""Postgres access: engine, sessions, migrations and shared column types (ST-005; ADR 0008).

Domain classes stay framework-free; each context maps its aggregates imperatively onto the
tables declared here (``mapper_registry``), so persistence never leaks into ``domain`` modules.
"""

from __future__ import annotations

import enum
import json
import uuid
from collections.abc import Callable, Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi import Request
from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect, make_url
from sqlalchemy.orm import Session, registry, sessionmaker
from sqlalchemy.types import String, TypeDecorator, Uuid

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_MIGRATION_LOCK = 0x5241434B  # pg_advisory_lock key ("RACK"): one migrator at a time

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)
mapper_registry = registry(metadata=metadata)


def sqlalchemy_url(url: str) -> str:
    """Use the psycopg 3 driver for plain ``postgresql://`` URLs."""
    parsed = make_url(url)
    if parsed.drivername in ("postgresql", "postgres"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


@lru_cache(maxsize=8)
def engine_for(url: str) -> Engine:
    return create_engine(sqlalchemy_url(url), pool_pre_ping=True, pool_size=5, max_overflow=10)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def upgrade_to_head(database_url: str) -> None:
    """Apply the Alembic migrations. Serialised with an advisory lock (API and CI may race)."""
    engine = create_engine(sqlalchemy_url(database_url))
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _MIGRATION_LOCK})
            try:
                config = Config()
                config.set_main_option("script_location", str(MIGRATIONS_DIR))
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                connection.commit()
            except BaseException:
                connection.rollback()  # a half-applied migration leaves nothing (BE-PL-01)
                raise
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _MIGRATION_LOCK})
                connection.commit()
    finally:
        engine.dispose()


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one Session per request. Tests override it (ADR 0012)."""
    factory: Callable[[], Session] = request.app.state.session_factory
    session = factory()
    try:
        yield session
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


# ------------------------------------------------------------------ column types
class IdType(TypeDecorator[Any]):
    """A UUID column that loads into a value-object class taking a UUID (e.g. ``MatchId``)."""

    impl = Uuid
    cache_ok = True

    def __init__(self, id_class: type[Any]) -> None:
        super().__init__(as_uuid=True)
        self.id_class = id_class

    def process_bind_param(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        return value.value if isinstance(value, self.id_class) else uuid.UUID(str(value))

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return None if value is None else self.id_class(value)


class StrEnumType(TypeDecorator[Any]):
    """Stores a ``StrEnum`` as text and loads it back as the enum member."""

    impl = String(32)
    cache_ok = True

    def __init__(self, enum_class: type[enum.Enum]) -> None:
        super().__init__()
        self.enum_class = enum_class

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        return None if value is None else self.enum_class(value).value

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return None if value is None else self.enum_class(value)


class DataclassListType(TypeDecorator[Any]):
    """A JSONB list of frozen dataclasses (e.g. upload parts). Assign new lists to change it."""

    impl = JSONB
    cache_ok = True

    def __init__(self, item_class: type[Any]) -> None:
        super().__init__()
        self.item_class = item_class

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return []
        return [dict(vars(item)) for item in value]

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return [self.item_class(**item) for item in (value or [])]


def to_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
