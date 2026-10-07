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
