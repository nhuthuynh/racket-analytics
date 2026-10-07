"""Account deletion erases every personal column at once (ST-051; FR-007; deletion-and-purge.md
§3.2 step 5; NFR-057). A new column on ``accounts`` must be named here: erased, or kept with a
reason, so personal data cannot outlive the deletion by accident."""

from __future__ import annotations

import pytest

from racket.players.deletion import ERASED, KEPT
from racket.players.models import accounts

pytestmark = [pytest.mark.unit]


def test_every_accounts_column_is_either_erased_or_kept_for_a_reason() -> None:
    columns = {c.name for c in accounts.columns}
    assert set(ERASED) | set(KEPT) == columns
    assert set(ERASED) & set(KEPT) == set()


def test_the_address_its_key_and_the_names_are_erased() -> None:
    assert {"email", "email_key", "username", "display_name"} <= set(ERASED)
    assert all(value is None for value in ERASED.values())


def test_only_the_id_and_times_are_kept() -> None:
    assert set(KEPT) == {"id", "created_at", "deleted_at"}
    assert all(KEPT.values()), "each kept column needs its reason"
