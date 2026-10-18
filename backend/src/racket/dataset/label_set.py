"""Which matches a label set may hold (ST-070; FR-009, FR-150; OQ-06, ADR 0023; context map R9;
SEC-4 T4-CS-1, T4-CS-2, T4-CS-4).

Pure domain code (ddd-guidelines §4.5): no I/O and no framework. The build adapter
(``racket.dataset.build_label_set``) hands in the candidate matches and the consent port.

* **Owner opt-in** (``FEATURE_TRAINING_CONSENT`` on): a match is in the set only when its
  **owner** has opted in at build time. No consent row is "no"; another account's opt-in, a
  labeller's included, never counts; a team-held record alone does not include a match. The
  port is asked once, about the candidates' owners only; an id it was not asked about adds
  nothing. A failing lookup raises ``ConsentUnavailable``: the build fails closed, no partial
  set (T4-CS-1).
* **Team record** (flag off): the FR-150 rule as it stands, a match with a team-held consent
  record (``label_consents``), and the opt-in is never read.
* A built set is a new version: it never edits an earlier one. A revoke therefore excludes the
  owner's matches from the **next** build; frozen versions retire at their next scheduled
  refresh (OQ-06, accepted 2026-10-05).
* A match with neither a standing rally nor a Full Tag label has nothing to train on and is
  left out. The manifest names matches and counts only, never an owner (data minimisation).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

LABEL_SET_SCHEMA = "label-set/v1"

# The consent port: the owners (of those asked) who opted in to training use now.
OptedIn = Callable[[frozenset[uuid.UUID]], Collection[uuid.UUID]]


class ConsentRule(Enum):
    TEAM_RECORD = "team_record"  # FR-150 as built in Sprint 3 (flag off)
    OWNER_OPT_IN = "owner_opt_in"  # FR-009 (flag on)

    @classmethod
    def for_flag(cls, training_consent_on: bool) -> ConsentRule:
        return cls.OWNER_OPT_IN if training_consent_on else cls.TEAM_RECORD


class ConsentUnavailable(RuntimeError):
    """The consent lookup failed; the build must stop without writing anything (T4-CS-1)."""


@dataclass(frozen=True)
class Candidate:
    """A live match that may enter the set: its owner, its standing Quick Tag rallies (the
    player's corrections), its Full Tag label count and whether the team holds a consent
    record for it."""

    match_id: uuid.UUID
    owner_id: uuid.UUID
    rallies: int
    full_tag_labels: int
    team_consent: bool

    @property
    def has_labels(self) -> bool:
        return self.rallies > 0 or self.full_tag_labels > 0


@dataclass(frozen=True)
class LabelSet:
    rule: ConsentRule
    built_at: datetime
    matches: tuple[Candidate, ...]

    def manifest(self) -> dict[str, Any]:
        built = self.built_at.astimezone(UTC).isoformat(timespec="milliseconds")
        return {
            "schema": LABEL_SET_SCHEMA,
            "built_at": built.replace("+00:00", "Z"),
            "consent_rule": self.rule.value,
            "matches": [
                {
                    "match_id": str(c.match_id),
                    "rallies": c.rallies,
                    "full_tag_labels": c.full_tag_labels,
                }
                for c in self.matches
            ],
        }


def _consented_owners(candidates: tuple[Candidate, ...], opted_in: OptedIn) -> frozenset[uuid.UUID]:
    owners = frozenset(c.owner_id for c in candidates)
    if not owners:
        return frozenset()
    try:
        answered = opted_in(owners)
    except Exception as exc:  # any failure is "unknown", never "yes" (fail closed)
        raise ConsentUnavailable("training consent lookup failed") from exc
    return owners & frozenset(answered)


def select_label_set(
    candidates: Iterable[Candidate], rule: ConsentRule, opted_in: OptedIn, built_at: datetime
) -> LabelSet:
    """The next label set under ``rule``, its matches in match-id order."""
    labelled = tuple(c for c in candidates if c.has_labels)
    ids = [c.match_id for c in labelled]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate match among the label-set candidates")
    if rule is ConsentRule.TEAM_RECORD:
        chosen = tuple(c for c in labelled if c.team_consent)
    else:
        owners = _consented_owners(labelled, opted_in)
        chosen = tuple(c for c in labelled if c.owner_id in owners)
    return LabelSet(rule, built_at, tuple(sorted(chosen, key=lambda c: c.match_id)))
