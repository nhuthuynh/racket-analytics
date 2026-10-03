"""Test-data builders (ST-004; QD-TR-03: one builder per aggregate).

Builders are immutable and fluent: every ``with_*``/``titled``/``owned_by`` call returns a new
builder, so a shared base builder can never leak state between tests.

``an_owner()`` and ``a_match()`` can render themselves three ways:

* ``.as_create_payload()``: the JSON body for ``POST /matches`` (API tests and scenarios);
* ``.build()``: the domain object, through the seams in ``tests.support.contract``
  (RED until ST-006 provides ``racket.matches.domain``);
* plain attribute access for assertions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from tests.support.contract import Seam

MATCH = Seam("racket.matches.domain:Match", "ST-006", "Match.create(owner_id=, title=, format=)")
MATCH_ID = Seam("racket.matches.domain:MatchId", "ST-006")
OWNER_ID = Seam("racket.matches.domain:OwnerId", "ST-006")

DEV_USERS = ("ivy", "carlos", "dana")  # api-sprint-00 §2 (R2-01)
MATCH_FORMATS = ("singles", "doubles")


@dataclass(frozen=True)
class OwnerBuilder:
    username: str = "ivy"
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def named(self, username: str) -> OwnerBuilder:
        return replace(self, username=username)

    def with_id(self, value: uuid.UUID) -> OwnerBuilder:
        return replace(self, id=value)

    def build(self) -> Any:
        """The domain ``OwnerId`` value object."""
        return OWNER_ID.load()(str(self.id))


@dataclass(frozen=True)
class MatchBuilder:
    title: str = "Skeleton test"
    format: str = "doubles"
    owner: OwnerBuilder = field(default_factory=OwnerBuilder)

    def titled(self, title: str) -> MatchBuilder:
        return replace(self, title=title)

    def with_format(self, fmt: str) -> MatchBuilder:
        return replace(self, format=fmt)

    def owned_by(self, owner: OwnerBuilder) -> MatchBuilder:
        return replace(self, owner=owner)

    def as_create_payload(self) -> dict[str, str]:
        return {"title": self.title, "format": self.format}

    def build(self) -> Any:
        """The domain ``Match`` aggregate in its initial state (status ``awaiting_upload``)."""
        return MATCH.load().create(
            owner_id=self.owner.build(), title=self.title, format=self.format
        )


def an_owner() -> OwnerBuilder:
    return OwnerBuilder()


def a_match() -> MatchBuilder:
    return MatchBuilder()
