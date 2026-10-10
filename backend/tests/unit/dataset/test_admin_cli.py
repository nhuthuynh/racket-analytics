"""The labeller-admin CLI refuses bad input before it touches the database (ST-052b;
api-sprint-03 §5.5): usage errors exit 2, an invalid id or consent reference exits 1."""

from __future__ import annotations

import uuid

import pytest

from racket.dataset import admin

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse() -> None:
        raise AssertionError("the database must not be opened")

    monkeypatch.setattr(admin, "_session", refuse)


@pytest.mark.parametrize(
    "argv",
    [[], ["grant-labeller"], ["consent", "--match", str(uuid.uuid4())], ["unknown"],
     ["grant-labeller", "--account"]],
)  # fmt: skip
def test_usage_errors_exit_2(argv: list[str]) -> None:
    assert admin.main(argv) == 2


@pytest.mark.parametrize(
    "argv",
    [["grant-labeller", "--account", "not-a-uuid"],
     ["revoke-labeller", "--account", "x"],
     ["consent", "--match", "nope", "--record", "CONSENT-1"],
     ["consent", "--match", str(uuid.uuid4()), "--record", "Ivy Example <ivy@example.com>"],
     ["consent", "--match", str(uuid.uuid4()), "--record", ""],
     ["consent", "--match", str(uuid.uuid4()), "--record", "R1", "--by", "x y"]],
)  # fmt: skip
def test_an_invalid_id_or_reference_exits_1(argv: list[str]) -> None:
    assert admin.main(argv) == 1


class _FakeSession:
    """Stands in for the database session so the CLI's refusals are checked without Postgres."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_consent_for_a_match_that_is_not_live_exits_1_and_stores_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    saved: list[object] = []
    monkeypatch.setattr(admin, "_session", lambda: session)
    monkeypatch.setattr(admin.matches, "lock_live_match", lambda s, m: False)
    monkeypatch.setattr(admin.LabelRepository, "save_consent", lambda self, r: saved.append(r))
    assert admin.main(["consent", "--match", str(uuid.uuid4()), "--record", "CONSENT-1"]) == 1
    assert saved == []
    assert not session.committed


def test_consent_for_a_live_match_is_saved_under_its_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    calls: list[str] = []
    monkeypatch.setattr(admin, "_session", lambda: session)
    monkeypatch.setattr(admin.matches, "lock_live_match", lambda s, m: calls.append("lock") or True)
    monkeypatch.setattr(admin.LabelRepository, "save_consent", lambda self, r: calls.append("save"))
    assert admin.main(["consent", "--match", str(uuid.uuid4()), "--record", "CONSENT-1"]) == 0
    assert calls == ["lock", "save"]
    assert session.committed


def test_revoke_on_an_unknown_account_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(admin, "_session", lambda: session)
    monkeypatch.setattr(admin.players, "revoke_role", lambda s, a, r: False)
    assert admin.main(["revoke-labeller", "--account", str(uuid.uuid4())]) == 1
    assert session.rolled_back
    assert not session.committed
