"""An independent side-out doubles engine: the differential oracle P9 (ST-022, NFR-002b).

Written by the senior-qa-engineer from QD §2.1-§2.3 and the golden tables only, WITHOUT reading
the production engine (writer/reviewer split [DPA/AI-08]). Do not refactor it towards the
production code: its value is that it was derived separately. It encodes the PROVISIONAL rules
(ADR 0009, @needs-verification); when the coach verifies the rules, only the parameters and
the golden tables change.

Representation is deliberately different from production: plain tuples and strings.
Outcomes are raw tuples (same shape as tests.support.scoring.RawOutcome):
    ("won", "A"|"B")  |  ("fault", "A"|"B", kind)  |  ("replay",)
A fault by X is "X lost the rally" (QD-RE-09), whatever the kind.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

PARTNER = {"A1": "A2", "A2": "A1", "B1": "B2", "B2": "B1"}
OTHER = {"A": "B", "B": "A"}


@dataclass(frozen=True)
class Rules:
    points_to_win: int
    win_by: int
    first_service_single_server: bool


@dataclass(frozen=True)
class OracleState:
    a: int
    b: int
    serving: str  # "A" | "B"
    server_number: int  # 1 | 2
    server: str  # slot "A1".."B2"
    right_a: str  # slot of side A standing in the right-hand court
    right_b: str
    winner: str | None = None

    @property
    def over(self) -> bool:
        return self.winner is not None

    def right(self, side_: str) -> str:
        return self.right_a if side_ == "A" else self.right_b


class GameAlreadyOver(Exception):
    pass


def start(rules: Rules, first: str) -> OracleState:
    right_a, right_b = "A1", "B1"
    server = right_a if first == "A" else right_b
    number = 2 if rules.first_service_single_server else 1
    return OracleState(0, 0, first, number, server, right_a, right_b)


def _rally_winner(raw: tuple[str, ...]) -> str | None:
    kind = raw[0]
    if kind == "won":
        return raw[1]
    if kind == "fault":
        return OTHER[raw[1]]
    if kind == "replay":
        return None
    raise ValueError(f"unknown outcome {raw!r}")


def step(s: OracleState, raw: tuple[str, ...], rules: Rules) -> OracleState:
    if s.over:
        raise GameAlreadyOver
    won = _rally_winner(raw)
    if won is None:
        return s
    if won == s.serving:
        a = s.a + (1 if won == "A" else 0)
        b = s.b + (1 if won == "B" else 0)
        # the server's side swaps courts after a point (UNVERIFIED, SOD-05/06)
        if won == "A":
            moved = replace(s, a=a, b=b, right_a=PARTNER[s.right_a])
        else:
            moved = replace(s, a=a, b=b, right_b=PARTNER[s.right_b])
        lead = abs(a - b)
        if max(a, b) >= rules.points_to_win and lead >= rules.win_by:
            return replace(moved, winner="A" if a > b else "B")
        return moved
    if s.server_number == 1:
        return replace(s, server_number=2, server=PARTNER[s.server])
    new = OTHER[s.serving]
    return replace(s, serving=new, server_number=1, server=s.right(new))


def run(raws: list[tuple[str, ...]], rules: Rules, first: str = "A") -> list[OracleState]:
    """States from the start up to the end of the game (rallies after it are ignored)."""
    states = [start(rules, first)]
    for raw in raws:
        if states[-1].over:
            break
        states.append(step(states[-1], raw, rules))
    return states
