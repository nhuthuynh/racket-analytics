"""Test-side helpers for the scoring scenarios and properties (ST-020, ST-022, ST-023).

Everything that touches the production engine goes through the seams in
``tests.support.contract`` (ADR 0012), so a missing engine makes each test RED with the story
name instead of breaking collection.

Notation used by the golden tables (QD §2.2): a doubles call ``"S-R-n"`` is the serving side's
score, the receiving side's score and the server number. It is parsed here, on the test side;
the engine's own call formatting is FR-048 (Sprint 2).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from tests.support import contract

# ------------------------------------------------------------------ calls


@dataclass(frozen=True)
class Call:
    serving: int
    receiving: int
    server_number: int


def parse_call(text: str) -> Call:
    parts = [p.strip() for p in text.split("-")]
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"not a doubles call 'S-R-n': {text!r}")
    serving, receiving, number = (int(p) for p in parts)
    return Call(serving, receiving, number)


def side(letter: str) -> Any:
    sides = contract.RULES_SIDE.load()
    return sides[letter.strip().upper()]


def score_of(state: Any, side_obj: Any) -> int:
    return int(state.score_a if side_obj == side("A") else state.score_b)


def call_of(state: Any) -> Call:
    """The doubles call of ``state`` from the serving side's point of view."""
    serving = state.serving_side
    return Call(score_of(state, serving), score_of(state, serving.other), state.server_number)


# ------------------------------------------------------------------ configurations


def mechanics_config(points_to_win: int, win_by: int, *, first_service: bool = False) -> Any:
    """An explicit side-out doubles configuration: no rulebook claim (ADR 0009 part a)."""
    return contract.RULES_CONFIG.load()(
        rules_version="TEST-MECHANICS",
        scoring_system="side_out",
        format="doubles",
        points_to_win=points_to_win,
        win_by=win_by,
        first_service_single_server=first_service,
    )


def provisional_preset() -> Any:
    presets = contract.RULES_PRESETS.load()
    assert contract.PROVISIONAL_PRESET in presets, sorted(presets)
    return presets[contract.PROVISIONAL_PRESET]


# ------------------------------------------------------------------ states and outcomes


def is_domain_error(value: Any) -> bool:
    return isinstance(value, contract.DOMAIN_ERROR.load())


def state_from_call(config: Any, call: Call, serving_letter: str) -> Any:
    """A declared in-play state. Raises AssertionError if the engine refuses it."""
    result = contract.DECLARE_STATE.load()(
        config,
        serving_side=side(serving_letter),
        serving_score=call.serving,
        receiving_score=call.receiving,
        server_number=call.server_number,
    )
    assert not is_domain_error(result), f"engine refused the declared state {call}: {result!r}"
    return result


def outcome_for(word: str, state: Any) -> Any:
    """``serving`` / ``receiving`` / ``replay`` relative to the state's serving side."""
    outcome = contract.RALLY_OUTCOME.load()
    if word == "replay":
        return outcome.replay()
    if word == "serving":
        return outcome.won_by(state.serving_side)
    if word == "receiving":
        return outcome.won_by(state.serving_side.other)
    raise ValueError(f"unknown rally winner {word!r}")


FAULT_WORDS = {
    "serve": "SERVE",
    "foot fault on serve": "FOOT",
    "two-bounce": "TWO_BOUNCE",
    "nvz": "NVZ",
    "other": "OTHER",
}


def fault_kind(word: str) -> Any:
    kinds = contract.FAULT_KIND.load()
    return kinds[FAULT_WORDS[word.strip().lower()]]


def fault_outcome(by_word: str, fault_word: str, state: Any) -> Any:
    by = state.serving_side if by_word == "serving" else state.serving_side.other
    return contract.RALLY_OUTCOME.load().fault(by=by, kind=fault_kind(fault_word))


def apply(state: Any, outcome: Any, config: Any) -> Any:
    return contract.RULES_APPLY.load()(state, outcome, config)


def all_outcomes() -> list[Any]:
    """One outcome of every kind, for 'any rally' steps (SOD-12)."""
    outcome = contract.RALLY_OUTCOME.load()
    a, b = side("A"), side("B")
    kinds = list(contract.FAULT_KIND.load())
    return [
        outcome.won_by(a),
        outcome.won_by(b),
        outcome.replay(),
        *(outcome.fault(by=s, kind=k) for s in (a, b) for k in kinds),
    ]


def play_until_over(state: Any, winner: Any, config: Any, limit: int = 500) -> Any:
    """``winner`` wins every rally until the game ends (mechanics only, no rule claim)."""
    outcome = contract.RALLY_OUTCOME.load().won_by(winner)
    for _ in range(limit):
        if state.is_over:
            return state
        state = apply(state, outcome, config)
        assert not is_domain_error(state), state
    raise AssertionError(f"game did not end within {limit} rallies")


# ------------------------------------------------------------------ random sequences (P1-P8)

# A rally outcome as plain data, so sequences can be generated without the engine and shrunk.
#   ("won", "A"|"B") | ("fault", "A"|"B", kind_name) | ("replay",)
RawOutcome = tuple[str, ...]


def to_outcome(raw: RawOutcome) -> Any:
    outcome = contract.RALLY_OUTCOME.load()
    if raw[0] == "won":
        return outcome.won_by(side(raw[1]))
    if raw[0] == "fault":
        return outcome.fault(by=side(raw[1]), kind=contract.FAULT_KIND.load()[raw[2]])
    if raw[0] == "replay":
        return outcome.replay()
    raise ValueError(raw)


FAULT_NAMES = ("SERVE", "FOOT", "TWO_BOUNCE", "NVZ", "OTHER")


def random_sequence(rng: random.Random, length: int) -> list[RawOutcome]:
    seq: list[RawOutcome] = []
    for _ in range(length):
        roll = rng.random()
        who = rng.choice("AB")
        if roll < 0.75:
            seq.append(("won", who))
        elif roll < 0.95:
            seq.append(("fault", who, rng.choice(FAULT_NAMES)))
        else:
            seq.append(("replay",))
    return seq


def random_sequences(seed: int, count: int, max_length: int = 120) -> Iterator[list[RawOutcome]]:
    rng = random.Random(seed)  # noqa: S311  (seeded test data, not security)
    for _ in range(count):
        yield random_sequence(rng, rng.randint(0, max_length))


# ------------------------------------------------------------------ invariants (QD §2.3)


def game_over_condition(state: Any, config: Any) -> bool:
    a, b = int(state.score_a), int(state.score_b)
    return max(a, b) >= config.points_to_win and abs(a - b) >= config.win_by


STEP_PROPERTIES = frozenset({"P1", "P2", "P4", "P5", "P7", "P8"})


def check_invariants(
    raw: Sequence[RawOutcome],
    config: Any,
    first_server_letter: str = "A",
    props: frozenset[str] = STEP_PROPERTIES,
) -> list[Any]:
    """Score ``raw`` rally by rally and assert the properties in ``props`` (default: P1, P2,
    P4, P5, P7 and P8) on every step. Returns the states (start included) up to and including
    the end of the game, so callers can check P6 against ``fold``. Raises AssertionError naming
    the property that broke."""
    start = contract.NEW_GAME.load()(config, side(first_server_letter))
    assert not start.is_over, "P5: a new game is not over"
    states = [start]
    state = start
    outcome_type = contract.RALLY_OUTCOME.load()
    for i, item in enumerate(raw):
        outcome = to_outcome(item)
        nxt = apply(state, outcome, config)
        where = f"rally {i + 1} {item} from {state!r}"
        if state.is_over:
            assert isinstance(nxt, contract.GAME_OVER.load()), f"SOD-12/QD-RE-05 at {where}"
            break
        assert not is_domain_error(nxt), f"QD-RE-05: unexpected {nxt!r} at {where}"
        da, db = nxt.score_a - state.score_a, nxt.score_b - state.score_b
        # P1: never decreases; at most +1 to exactly one side
        if "P1" in props:
            assert da >= 0, f"P1 decrease at {where}"
            assert db >= 0, f"P1 decrease at {where}"
            assert da + db <= 1, f"P1 more than one point at {where}"
        # P2: side-out scoring: only a rally won as the serving side scores
        if "P2" in props and da + db == 1:
            scorer = side("A") if da == 1 else side("B")
            assert scorer == state.serving_side, f"P2 receiving side scored at {where}"
            assert _rally_winner(item, state) == scorer, f"P2 loser scored at {where}"
        # P4: server number in {1, 2}; a serving-side loss at server 2 is a side-out
        winner = _rally_winner(item, state)
        if "P4" in props:
            assert nxt.server_number in (1, 2), f"P4 server number at {where}"
        if "P4" in props and winner is not None and winner != state.serving_side:
            if state.server_number == 2:
                assert nxt.serving_side == state.serving_side.other, f"P4 no side-out at {where}"
                assert nxt.server_number == 1, f"P4 side-out not at server 1 at {where}"
            else:
                assert nxt.serving_side == state.serving_side, f"P4 early side-out at {where}"
                assert nxt.server_number == 2, f"P4 partner not serving at {where}"
        # P5: game over exactly when the condition first holds
        if "P5" in props:
            assert nxt.is_over == game_over_condition(nxt, config), f"P5 at {where}"
            if nxt.is_over:
                leader = side("A") if nxt.score_a > nxt.score_b else side("B")
                assert nxt.winner == leader, f"P5 wrong winner at {where}"
            else:
                assert nxt.winner is None, f"P5 winner before game over at {where}"
        # P7: the fault subtype never changes the next state
        if "P7" in props and item[0] == "fault":
            generic = apply(state, outcome_type.won_by(side(item[1]).other), config)
            assert nxt == generic, f"P7 fault subtype {item[2]} changed the state at {where}"
        # P8: replay is identity
        if "P8" in props and item[0] == "replay":
            assert nxt == state, f"P8 replay changed the state at {where}"
        states.append(nxt)
        state = nxt
    return states


def _rally_winner(item: RawOutcome, state: Any) -> Any:
    if item[0] == "won":
        return side(item[1])
    if item[0] == "fault":
        return side(item[1]).other
    return None


def check_fold(raw: Sequence[RawOutcome], config: Any, states: Sequence[Any]) -> None:
    """P6: fold equals sequential apply, and prefix-then-suffix equals the whole."""
    fold: Callable[..., Any] = contract.RULES_FOLD.load()
    played = [to_outcome(r) for r in raw[: len(states) - 1]]
    start = states[0]
    assert fold([], config, start) == start, "P6 empty fold is not the start state"
    assert fold(played, config, start) == states[-1], "P6 fold differs from sequential apply"
    cut = len(played) // 2
    middle = fold(played[:cut], config, start)
    assert middle == states[cut], "P6 prefix fold differs"
    assert fold(played[cut:], config, middle) == states[-1], "P6 prefix-then-suffix differs"
