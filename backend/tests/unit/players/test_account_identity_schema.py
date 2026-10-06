"""ST-013b (ADR 0032; SEC-R3-S1-01 / SEC-R4-S1-01): the account identity is the stored
normalised address; ``email_key`` is only the log and rate-limit pseudonym.

No I/O: the table definitions and the link value. The behaviour (rotation keeps the account,
a forced key collision gives two accounts, links lose the address) is IT-02-12 (QA lane).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from racket.players.domain import MagicLinkToken
from racket.players.models import accounts, sign_in_links

NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)


def _unique_column_sets(table: sa.Table) -> set[frozenset[str]]:
    sets = {frozenset(c.name for c in u.columns) for u in table.constraints
            if isinstance(u, sa.UniqueConstraint)}  # fmt: skip
    sets |= {frozenset([c.name]) for c in table.columns if c.unique}
    return sets


def test_email_key_is_no_longer_unique_on_accounts() -> None:
    assert frozenset(["email_key"]) not in _unique_column_sets(accounts)


def test_the_address_is_the_unique_identity_of_an_account() -> None:
    assert "email" in accounts.c
    assert accounts.c.email.nullable  # legacy dev accounts and dev-provider users have none
    assert accounts.c.email.type.length == 254
    assert frozenset(["email"]) in _unique_column_sets(accounts)


def test_a_link_row_carries_the_address_until_used_or_refused() -> None:
    assert "email" in sign_in_links.c
    assert sign_in_links.c.email.nullable
    assert sign_in_links.c.email.type.length == 254


def test_a_link_value_is_built_from_its_row_without_the_address() -> None:
    row = {
        "token_sha256": "a" * 64, "email_key": "b" * 16, "email": "ivy@example.test",
        "created_at": NOW, "expires_at": NOW + timedelta(minutes=15), "used_at": None,
    }  # fmt: skip
    link = MagicLinkToken.from_row(row)
    assert link == MagicLinkToken("a" * 64, "b" * 16, NOW, NOW + timedelta(minutes=15))
    assert "ivy@example.test" not in repr(link)
