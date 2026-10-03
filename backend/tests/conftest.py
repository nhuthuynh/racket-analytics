"""Root test configuration (ST-004).

* Markers are registered in pyproject.toml (``--strict-markers``) and applied by directory:
  ``unit/`` -> unit, ``integration/`` -> integration, ``regression/`` -> regression +
  integration, ``features/`` -> scenario.
* Gherkin tags map to markers (testing-strategy §4): ``@needs-verification`` ->
  ``needs_verification``, ``@slow`` -> ``slow``, ``@M0`` -> ``milestone("M0")``,
  ``@story-ST-008`` -> ``story("ST-008")``, ``@nfr-051`` -> ``nfr("051")``.
* Hypothesis profiles: ``dev`` (default, 100 examples) and ``ci`` (>= 1,000 examples).
  Select with ``HYPOTHESIS_PROFILE=ci``.
"""

from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from hypothesis import HealthCheck, settings

from tests.support import contract
from tests.support.api import ApiDriver, async_client, lifespan
from tests.support.db import database_url, make_engine, rolled_back_session

# ----------------------------------------------------------------- environment
# The suite always runs as APP_ENV=test, whatever the shell exports (QA-R1-06). Tests that
# need another value set it with monkeypatch.
os.environ["APP_ENV"] = "test"

# ----------------------------------------------------------------- Hypothesis profiles
settings.register_profile("dev", max_examples=100)
settings.register_profile(
    "ci",
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
    print_blob=True,
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

# ----------------------------------------------------------------- markers by directory
_DIR_MARKERS = {
    "unit": ("unit",),
    "tools": ("unit",),
    "integration": ("integration",),
    "regression": ("regression", "integration"),
    "features": ("scenario",),
    "e2e_api": ("integration",),
}
_TESTS_ROOT = Path(__file__).parent


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        try:
            top = Path(str(item.path)).relative_to(_TESTS_ROOT).parts[0]
        except ValueError:
            continue
        for name in _DIR_MARKERS.get(top, ()):
            if item.get_closest_marker(name) is None:
                item.add_marker(getattr(pytest.mark, name))


# ----------------------------------------------------------------- Gherkin tags -> markers
_STORY = re.compile(r"story-(ST-\d{3}|SPIKE-\d{2})")
_NFR = re.compile(r"nfr-(\d{3}[a-z]?)")
_MILESTONE = re.compile(r"M\d+[a-z]?")


def pytest_bdd_apply_tag(tag: str, function: Any) -> bool:
    if tag == "needs-verification":
        marker = pytest.mark.needs_verification
    elif tag == "slow":
        marker = pytest.mark.slow
    elif m := _STORY.fullmatch(tag):
        marker = pytest.mark.story(id=m.group(1))
    elif m := _NFR.fullmatch(tag):
        marker = pytest.mark.nfr(id=m.group(1))
    elif _MILESTONE.fullmatch(tag):
        marker = pytest.mark.milestone(name=tag)
    else:
        marker = pytest.mark.bdd_tag(name=tag)
    marker(function)
    return True


# ----------------------------------------------------------------- database
@pytest.fixture(scope="session")
def raw_db_engine() -> Iterator[Any]:
    """Engine on DATABASE_URL without migrations (harness self-tests)."""
    engine = make_engine(database_url())
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_engine(raw_db_engine: Any) -> Any:
    """Engine on a migrated schema (RED until ST-005 provides the migrations)."""
    contract.DB_MIGRATE.load()(database_url())
    return raw_db_engine


@pytest.fixture
def db_session(db_engine: Any) -> Iterator[Any]:
    """ORM session inside a transaction that is rolled back after the test."""
    with rolled_back_session(db_engine) as session:
        yield session


def _truncate_all(engine: Any) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        tables = (
            conn.execute(
                text(
                    "SELECT quote_ident(tablename) FROM pg_tables "
                    "WHERE schemaname = current_schema() AND tablename <> 'alembic_version'"
                )
            )
            .scalars()
            .all()
        )
        if tables:
            conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def committed_db(db_engine: Any) -> Iterator[Any]:
    """Real commits, for flows that cross processes or connections (worker, queue).
    Every table except alembic_version is truncated afterwards."""
    _truncate_all(db_engine)
    yield db_engine
    _truncate_all(db_engine)


# ----------------------------------------------------------------- application
def _new_app() -> Any:
    return contract.APP_FACTORY.load()()


@pytest.fixture
def app(db_session: Any) -> Iterator[Any]:
    """The FastAPI app wired to the rolled-back session via dependency_overrides (AQS/STACK-01)."""
    application = _new_app()
    get_session = contract.DB_SESSION_DEPENDENCY.load()
    application.dependency_overrides[get_session] = lambda: db_session
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def committed_app(committed_db: Any) -> Iterator[Any]:
    """The FastAPI app on the real, committed database (for API -> queue -> worker flows)."""
    application = _new_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def api_client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    """httpx AsyncClient over ASGITransport: no network, lifespan run (AQS/STACK-01)."""
    async with lifespan(app), async_client(app) as client:
        yield client


@pytest.fixture
def api(committed_app: Any) -> Iterator[ApiDriver]:
    """Synchronous multi-user driver for scenario steps."""
    driver = ApiDriver(committed_app)
    yield driver
    driver.close()


# ----------------------------------------------------------------- tracing
@pytest.fixture(scope="session")
def _session_span_exporter() -> Any:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


@pytest.fixture
def span_exporter(_session_span_exporter: Any) -> Iterator[Any]:
    """In-memory OpenTelemetry exporter on the global provider; cleared around each test.
    Contract: the app and worker use the global tracer provider and never replace one
    that is already set (ST-005)."""
    _session_span_exporter.clear()
    yield _session_span_exporter
    _session_span_exporter.clear()
