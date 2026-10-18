"""The label-set selection rule (ST-070; FR-009; FR-150; OQ-06, ADR 0023; context map R9;
SEC-4 T4-CS-1, T4-CS-2, T4-CS-4).

Negative cases first: under the owner opt-in rule a match whose owner has no consent row is
out, another owner's opt-in never brings it in, a team-held record alone does not either, and a
consent lookup that fails aborts the build (no partial set). Then the team-record rule of FR-150
(flag off) and the included matches, in a fixed order, with no owner id in the manifest."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import UTC, datetime

import pytest

from racket.dataset.label_set import (
    LABEL_SET_SCHEMA,
    Candidate,
    ConsentRule,
    ConsentUnavailable,
    select_label_set,
)

pytestmark = [pytest.mark.unit]

AT = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
IVY = uuid.UUID(int=1)
CARLOS = uuid.UUID(int=2)


def _match(n: int, owner: uuid.UUID, *, team: bool = False, rallies: int = 14,
           labels: int = 0) -> Candidate:  # fmt: skip
    return Candidate(uuid.UUID(int=100 + n), owner, rallies, labels, team)


class Port:
    """A consent port double: records what it was asked."""

    def __init__(self, opted_in: Collection[uuid.UUID] = ()) -> None:
        self.opted_in = set(opted_in)
        self.asked: list[frozenset[uuid.UUID]] = []

    def __call__(self, owners: frozenset[uuid.UUID]) -> Collection[uuid.UUID]:
        self.asked.append(owners)
        return self.opted_in


def _ids(candidates: list[Candidate], rule: ConsentRule, port: Port) -> list[uuid.UUID]:
    built = select_label_set(candidates, rule, port, AT)
    return [c.match_id for c in built.matches]


# ------------------------------------------------------------------ owner opt-in (negative first)
def test_an_owner_with_no_consent_row_is_excluded() -> None:
    assert _ids([_match(1, IVY)], ConsentRule.OWNER_OPT_IN, Port()) == []


def test_another_owners_opt_in_does_not_include_my_match() -> None:
    ivy, carlos = _match(1, IVY), _match(2, CARLOS)
    assert _ids([ivy, carlos], ConsentRule.OWNER_OPT_IN, Port({CARLOS})) == [carlos.match_id]


def test_a_team_held_record_alone_does_not_include_a_match_while_the_flag_is_on() -> None:
    assert _ids([_match(1, IVY, team=True)], ConsentRule.OWNER_OPT_IN, Port()) == []


@pytest.mark.parametrize("error", [ConnectionError("db down"), RuntimeError("x"), KeyError("k")])
def test_a_failing_consent_lookup_aborts_the_build(error: Exception) -> None:
    def failing(_: frozenset[uuid.UUID]) -> Collection[uuid.UUID]:
        raise error

    with pytest.raises(ConsentUnavailable):
        select_label_set([_match(1, IVY)], ConsentRule.OWNER_OPT_IN, failing, AT)


def test_an_id_the_port_was_not_asked_about_never_adds_a_match() -> None:
    stranger = uuid.UUID(int=99)
    port = Port({stranger})
    assert _ids([_match(1, IVY)], ConsentRule.OWNER_OPT_IN, port) == []
    assert port.asked == [frozenset({IVY})]


def test_the_port_is_asked_once_with_every_owner() -> None:
    port = Port({IVY})
    _ids([_match(1, IVY), _match(2, CARLOS), _match(3, IVY)], ConsentRule.OWNER_OPT_IN, port)
    assert port.asked == [frozenset({IVY, CARLOS})]


def test_a_match_with_nothing_labelled_is_not_training_data() -> None:
    empty = _match(1, IVY, rallies=0, labels=0)
    labelled = _match(2, IVY, rallies=0, labels=3)
    assert _ids([empty, labelled], ConsentRule.OWNER_OPT_IN, Port({IVY})) == [labelled.match_id]


def test_a_duplicate_match_is_refused() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        select_label_set([_match(1, IVY), _match(1, IVY)], ConsentRule.OWNER_OPT_IN, Port(), AT)


def test_no_candidates_build_an_empty_set_without_a_lookup() -> None:
    port = Port()
    assert _ids([], ConsentRule.OWNER_OPT_IN, port) == []
    assert port.asked == []


def test_opted_in_owners_matches_are_included_in_match_id_order() -> None:
    later, first = _match(9, IVY), _match(3, CARLOS)
    got = _ids([later, first], ConsentRule.OWNER_OPT_IN, Port({IVY, CARLOS}))
    assert got == [first.match_id, later.match_id]


# ------------------------------------------------------------------ team record (flag off)
def test_flag_off_keeps_the_team_record_rule_and_never_reads_the_opt_in() -> None:
    port = Port({IVY, CARLOS})
    recorded, plain = _match(1, CARLOS, team=True), _match(2, IVY)
    assert _ids([recorded, plain], ConsentRule.TEAM_RECORD, port) == [recorded.match_id]
    assert port.asked == []


@pytest.mark.parametrize(
    ("flag", "rule"), [(False, ConsentRule.TEAM_RECORD), (True, ConsentRule.OWNER_OPT_IN)]
)
def test_the_rule_follows_the_flag(flag: bool, rule: ConsentRule) -> None:
    assert ConsentRule.for_flag(flag) is rule


# ------------------------------------------------------------------ manifest
def test_the_manifest_names_the_rule_and_the_matches_but_no_owner() -> None:
    built = select_label_set([_match(1, IVY, labels=2)], ConsentRule.OWNER_OPT_IN, Port({IVY}), AT)
    manifest = built.manifest()
    assert manifest == {
        "schema": LABEL_SET_SCHEMA,
        "built_at": "2026-10-18T12:00:00.000Z",
        "consent_rule": "owner_opt_in",
        "matches": [{"match_id": str(uuid.UUID(int=101)), "rallies": 14, "full_tag_labels": 2}],
    }
    assert str(IVY) not in repr(manifest)
