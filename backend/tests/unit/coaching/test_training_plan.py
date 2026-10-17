"""ST-056 (FR-121; QD-PL-01..03): the ``TrainingPlan`` aggregate and the rules-only assembly.

Negative cases first: each invariant of coaching-plan §5 is broken on its own in a hand-built
plan and must be refused on creation and on a change; the hand-built plan itself is the positive
control. Then ``assemble``: infeasible inputs, unfitted weaknesses, the 3:2:1 spread, rotation,
determinism, and a property over >= 1,000 generated (preferences, library, weaknesses) inputs
checked by the independent ``plan_problems`` (0 violations).
"""

from __future__ import annotations

import dataclasses
import random
from collections import Counter
from typing import Any

import pytest
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from racket.coaching.plan.domain import (
    NO_DRILL_FITS,
    Drill,
    DrillAssignment,
    Infeasible,
    InvalidPreferences,
    PlanInvariantBroken,
    PlanWeakness,
    Preferences,
    Session,
    TrainingPlan,
    Unfitted,
    assemble,
)
from tests.unit.coaching.plan_helpers import (
    TOP_3,
    drill,
    drill_doc,
    plan_problems,
    reviewed_test_library,
    solo_wall,
    warm_up,
)

LIB = {d.id: d for d in reviewed_test_library()}
WARM = LIB["pb.test.shadow-warm-up"]
DINKS = LIB["pb.test.wall-dinks"]
SERVE = LIB["pb.test.serve-target"]


def a(position: int, d: Drill, minutes: int, weakness: str | None) -> DrillAssignment:
    return DrillAssignment(position=position, drill=d, minutes=minutes, weakness_id=weakness)


def standard_session(week: int, index: int, budget: int = 30) -> Session:
    return Session(
        week=week,
        index=index,
        minutes_budget=budget,
        assignments=(
            a(1, WARM, 10, None),
            a(2, DINKS, 12, "unforced_errors"),
            a(3, SERVE, 8, "serve_faults"),
        ),
    )


def sessions(**replace: Session) -> tuple[Session, ...]:
    """The 6 standard sessions; ``s1_2=...`` replaces week 1 session 2."""
    out = []
    for week in (1, 2):
        for index in (1, 2, 3):
            out.append(replace.get(f"s{week}_{index}", standard_session(week, index)))
    return tuple(out)


def with_assignments(*assignments: DrillAssignment, budget: int = 30) -> Session:
    return Session(week=1, index=1, minutes_budget=budget, assignments=tuple(assignments))


def plan(
    sessions_: tuple[Session, ...] | None = None,
    prefs: Preferences | None = None,
    unfitted: tuple[Unfitted, ...] = (Unfitted("errors_under_pressure"),),
    weaknesses: tuple[PlanWeakness, ...] = TOP_3,
) -> TrainingPlan:
    return TrainingPlan(
        preferences=prefs or solo_wall(),
        weaknesses=weaknesses,
        unfitted=unfitted,
        sessions=sessions() if sessions_ is None else sessions_,
    )


def broken(code: str, **kw: Any) -> list[str]:
    with pytest.raises(PlanInvariantBroken) as err:
        plan(**kw)
    assert any(v.startswith(code) for v in err.value.violations), err.value.violations
    return err.value.violations


# ------------------------------------------------------------------ preferences (negative first)
@pytest.mark.parametrize(
    "over",
    [
        {"minutes_per_session": 14},
        {"minutes_per_session": 181},
        {"sessions_per_week": 0},
        {"sessions_per_week": 8},
        {"players_available": 0},
        {"players_available": 5},
        {"equipment": frozenset({"trampoline"})},
        {"level": "pro"},
        {"weekly_minutes": 44},  # < 3 sessions x 15 minutes
    ],
)
def test_preferences_out_of_range_are_refused(over: dict[str, Any]) -> None:
    fields: dict[str, Any] = {
        "minutes_per_session": 30,
        "sessions_per_week": 3,
        "players_available": 1,
        "equipment": frozenset({"wall"}),
        "level": "beginner",
    }
    with pytest.raises(InvalidPreferences):
        Preferences(**{**fields, **over})


def test_preferences_budget_is_the_smaller_of_session_and_weekly_share() -> None:
    assert solo_wall(30, 3).minutes_budget == 30
    assert solo_wall(30, 3).weekly_total == 90
    prefs = dataclasses.replace(solo_wall(60, 3), weekly_minutes=150)
    assert (prefs.minutes_budget, prefs.weekly_total, prefs.drill_cap) == (50, 150, 20)
    assert solo_wall(15, 1).drill_cap == 6  # floor(0.4 x 15)


# ------------------------------------------------------------------ drills
def test_drill_from_document_reads_the_schema_fields() -> None:
    doc = drill_doc("pb.test.x", needs=("wall",), players=2, deprecated_by="pb.test.y@1")
    d = Drill.from_document(doc)
    assert (d.ref, d.players, d.needs, d.deprecated) == (
        "pb.test.x@1",
        2,
        frozenset({"wall"}),
        True,
    )
    assert not d.is_warm_up
    assert d.is_reviewed


def test_an_07_drill_hits_only_its_named_share() -> None:
    """weakness-catalogue §5: AN-07 is split by share; without a share skill it fills no slot."""
    assert drill("pb.t.a", targets=("AN-07",)).plan_targets == frozenset()
    fault = drill("pb.t.b", targets=("AN-07", "AN-04"), skills=("share:fault",))
    assert fault.plan_targets == frozenset({"AN-07:fault", "AN-04"})


# ------------------------------------------------------------------ aggregate: negative first
def test_session_over_its_minutes_is_refused() -> None:
    over = with_assignments(
        a(1, WARM, 10, None), a(2, DINKS, 12, "unforced_errors"), a(3, SERVE, 10, "serve_faults")
    )
    broken("QD-PL-01", sessions_=sessions(s1_1=over))


def test_week_over_the_weekly_minutes_is_refused() -> None:
    prefs = dataclasses.replace(solo_wall(30, 3), weekly_minutes=60)  # budget 20 per session
    violations = broken("QD-PL-01", prefs=prefs)
    assert any("week 1" in v for v in violations)


def test_minutes_outside_the_drills_duration_are_refused() -> None:
    short = with_assignments(
        a(1, WARM, 10, None), a(2, DINKS, 7, "unforced_errors"), a(3, SERVE, 8, "serve_faults")
    )
    broken("QD-PL-01", sessions_=sessions(s1_1=short))


@pytest.mark.parametrize(
    "bad",
    [
        LIB["pb.test.machine-drops"],  # needs a ball machine
        LIB["pb.test.four-player-drops"],  # 4 players
        LIB["pb.test.draft-drops"],  # draft
        LIB["pb.test.old-drops"],  # deprecated
        drill("pb.test.advanced-drops", levels=("advanced", "advanced")),  # level
    ],
    ids=["ball-machine", "four-players", "draft", "deprecated", "level"],
)
def test_drill_that_does_not_fit_the_setup_is_refused(bad: Drill) -> None:
    s = with_assignments(
        a(1, WARM, 10, None), a(2, bad, 12, "unforced_errors"), a(3, SERVE, 8, "serve_faults")
    )
    broken("QD-PL-02", sessions_=sessions(s1_1=s))


def test_session_not_starting_with_a_warm_up_is_refused() -> None:
    s = with_assignments(
        a(1, DINKS, 12, "unforced_errors"), a(2, WARM, 10, None), a(3, SERVE, 8, "serve_faults")
    )
    broken("QD-PL-03", sessions_=sessions(s1_1=s))


def test_warm_up_longer_than_10_minutes_is_refused() -> None:
    long_warm = warm_up("pb.test.long-warm-up", minutes=(5, 12))
    s = with_assignments(
        a(1, long_warm, 11, None),
        a(2, DINKS, 12, "unforced_errors"),
        a(3, SERVE, 7, "serve_faults"),
    )
    broken("QD-PL-03", sessions_=sessions(s1_1=s))


def test_drill_over_40_percent_of_its_session_is_refused() -> None:
    s = with_assignments(
        a(1, WARM, 10, None), a(2, DINKS, 13, "unforced_errors"), a(3, SERVE, 7, "serve_faults")
    )
    broken("QD-PL-03", sessions_=sessions(s1_1=s))


def test_second_warm_up_in_a_session_is_refused() -> None:
    other = LIB["pb.test.wall-warm-up"]
    s = with_assignments(a(1, WARM, 10, None), a(2, other, 8, "unforced_errors"))
    broken("QD-PL-03", sessions_=sessions(s1_1=s))


def test_same_drill_twice_in_a_session_is_refused() -> None:
    s = with_assignments(
        a(1, WARM, 10, None), a(2, DINKS, 12, "unforced_errors"), a(3, DINKS, 8, "unforced_errors")
    )
    broken("plan", sessions_=sessions(s1_1=s))


def test_wrong_number_of_sessions_is_refused() -> None:
    broken("plan", sessions_=sessions()[:5])


def test_positions_must_run_from_1() -> None:
    s = with_assignments(a(1, WARM, 10, None), a(3, DINKS, 12, "unforced_errors"))
    broken("plan", sessions_=sessions(s1_1=s))


@pytest.mark.parametrize(
    ("d", "weakness"),
    [
        (DINKS, "serve_faults"),  # trains AN-04, not AN-05
        (DINKS, "unknown"),
        (DINKS, None),
        (LIB["pb.test.pressure-volleys"], "errors_under_pressure"),  # an unfitted weakness
    ],
    ids=["other-target", "unknown-weakness", "no-weakness", "unfitted-weakness"],
)
def test_assignment_must_train_a_fitted_weakness(d: Drill, weakness: str | None) -> None:
    prefs = dataclasses.replace(
        solo_wall(), players_available=2, equipment=frozenset({"wall", "partner_feeder"})
    )
    s = with_assignments(a(1, WARM, 10, None), a(2, d, 12, weakness))
    broken("plan", sessions_=sessions(s1_1=s), prefs=prefs)


def test_warm_up_with_a_weakness_is_refused() -> None:
    s = with_assignments(a(1, WARM, 10, "unforced_errors"), a(2, DINKS, 12, "unforced_errors"))
    broken("plan", sessions_=sessions(s1_1=s))


def test_session_budget_must_match_the_preferences() -> None:
    broken("plan", sessions_=sessions(s1_1=standard_session(1, 1, budget=45)))


def test_more_than_3_weaknesses_or_duplicate_ranks_are_refused() -> None:
    extra = (*TOP_3, PlanWeakness("other_faults", "AN-07:fault", 4))
    broken("plan", weaknesses=extra)
    broken("plan", weaknesses=(TOP_3[0], dataclasses.replace(TOP_3[1], rank=1), TOP_3[2]))


def test_unfitted_weakness_must_be_a_plan_weakness() -> None:
    broken("plan", unfitted=(Unfitted("nobody"),))


def test_hand_built_plan_keeps_every_invariant() -> None:
    """Positive control for every refusal above."""
    p = plan()
    assert (p.version, len(p.sessions), p.sessions[0].total_minutes) == (1, 6, 30)
    assert p.unfitted[0].text == NO_DRILL_FITS == "no drill fits your setup"


# ------------------------------------------------------------------ aggregate: every change
def test_change_that_breaks_an_invariant_is_refused_and_changes_nothing() -> None:
    p = plan()
    before = p.content()
    with pytest.raises(PlanInvariantBroken):
        p.replace_drill(week=1, index=1, position=2, drill=LIB["pb.test.machine-drops"], minutes=12)
    with pytest.raises(PlanInvariantBroken):
        p.replace_drill(week=1, index=1, position=2, drill=DINKS, minutes=13)  # over 40%
    assert (p.content(), p.version) == (before, 1)


def test_change_to_an_unknown_assignment_is_refused() -> None:
    p = plan()
    with pytest.raises(KeyError):
        p.replace_drill(week=3, index=1, position=2, drill=DINKS, minutes=12)


def test_valid_change_is_applied_and_bumps_the_version() -> None:
    p = plan()
    other = drill("pb.test.wall-volleys", needs=("wall",), minutes=(8, 12))
    p.replace_drill(week=2, index=3, position=2, drill=other, minutes=12)
    assert p.version == 2
    assert p.sessions[-1].assignments[1].drill == other
    assert p.sessions[-1].assignments[1].weakness_id == "unforced_errors"
    assert p.sessions[0].assignments[1].drill == DINKS


# ------------------------------------------------------------------ assembly: negative first
def test_no_weakness_gives_no_plan() -> None:
    assert assemble([], solo_wall(), reviewed_test_library()) == Infeasible("no_weakness")


def test_no_warm_up_that_fits_gives_no_plan() -> None:
    library = [d for d in reviewed_test_library() if not d.is_warm_up]
    assert assemble(TOP_3, solo_wall(), library) == Infeasible("no_plan_fits")
    # a warm-up of at least 7 minutes does not fit under the 6-minute cap of a 15-minute budget
    long_warm = warm_up("pb.test.long-warm-up", minutes=(7, 10))
    assert assemble(TOP_3, solo_wall(15, 1), [long_warm, DINKS]) == Infeasible("no_plan_fits")


def test_no_weakness_drill_that_fits_gives_no_plan() -> None:
    library = [WARM, LIB["pb.test.machine-drops"], LIB["pb.test.four-player-drops"]]
    assert assemble(TOP_3, solo_wall(), library) == Infeasible("no_plan_fits")


def test_weakness_with_no_fitting_drill_is_named_and_others_take_its_share() -> None:
    weaknesses = (
        PlanWeakness("errors_under_pressure", "AN-07:forced-error", 1),
        PlanWeakness("unforced_errors", "AN-04", 2),
    )
    result = assemble(weaknesses, solo_wall(), reviewed_test_library())
    assert isinstance(result, TrainingPlan)
    assert [u.weakness_id for u in result.unfitted] == ["errors_under_pressure"]
    used = Counter(x.weakness_id for s in result.sessions for x in s.assignments[1:])
    assert set(used) == {"unforced_errors"}


def test_only_the_top_3_weaknesses_are_planned() -> None:
    fourth = PlanWeakness("opponent_winners", "AN-01", 4)
    result = assemble((*TOP_3, fourth), solo_wall(), reviewed_test_library())
    assert isinstance(result, TrainingPlan)
    assert [w.id for w in result.weaknesses] == [w.id for w in TOP_3]
    assert all(x.weakness_id != "opponent_winners" for s in result.sessions for x in s.assignments)


# ------------------------------------------------------------------ assembly: positive
def test_solo_wall_plan_matches_the_worked_example() -> None:
    """coaching-plan §6 by hand: warm-ups rotate (shadow, wall), weaknesses 3:2 in smooth
    round-robin (A B A B A ...), drills at min(duration_max, 40% cap, remaining)."""
    result = assemble(TOP_3, solo_wall(), reviewed_test_library())
    assert isinstance(result, TrainingPlan)
    rows = [
        [(x.drill.id[8:], x.minutes, x.weakness_id) for x in s.assignments]
        for s in result.sessions[:2]
    ]
    assert rows == [
        [
            ("shadow-warm-up", 10, None),
            ("wall-dinks", 12, "unforced_errors"),
            ("serve-target", 8, "serve_faults"),
        ],
        [
            ("wall-warm-up", 8, None),
            ("wall-dinks", 12, "unforced_errors"),
            ("serve-target", 10, "serve_faults"),
        ],
    ]


def test_weaknesses_are_spread_by_rank() -> None:
    rich = [WARM] + [
        drill(
            f"pb.test.{t.replace(':', '-').lower()}-{i}",
            targets=(t[:5],),
            skills=(f"share:{t[6:]}",) if ":" in t else (),
            minutes=(5, 10),
        )
        for t in ("AN-04", "AN-05", "AN-07:forced-error")
        for i in range(4)
    ]
    prefs = dataclasses.replace(solo_wall(60, 3))
    result = assemble(TOP_3, prefs, rich)
    assert isinstance(result, TrainingPlan)
    used = Counter(x.weakness_id for s in result.sessions for x in s.assignments[1:])
    ranks = [used[w.id] for w in TOP_3]
    assert ranks[0] > ranks[1] > ranks[2] > 0, used
    assert result.sessions[0].assignments[1].weakness_id == "unforced_errors"


def test_drills_of_a_weakness_rotate() -> None:
    second = drill("pb.test.wall-volleys", needs=("wall",), minutes=(8, 12))
    result = assemble(TOP_3, solo_wall(), [*reviewed_test_library(), second])
    assert isinstance(result, TrainingPlan)
    used = {x.drill.id for s in result.sessions for x in s.assignments if x.weakness_id}
    assert {"pb.test.wall-dinks", "pb.test.wall-volleys"} <= used


def test_same_input_gives_the_same_plan_whatever_the_input_order() -> None:
    first = assemble(TOP_3, solo_wall(), reviewed_test_library())
    assert isinstance(first, TrainingPlan)
    for seed in range(5):
        library = reviewed_test_library()
        random.Random(seed).shuffle(library)  # noqa: S311 - a fixed shuffle, not crypto
        again = assemble(tuple(reversed(TOP_3)), solo_wall(), library)
        assert isinstance(again, TrainingPlan)
        assert again.content() == first.content()
        assert again.content_digest() == first.content_digest()
    other = assemble(TOP_3, solo_wall(45, 3), reviewed_test_library())
    assert isinstance(other, TrainingPlan)
    assert other.content_digest() != first.content_digest()
    assert first.content_digest().startswith("sha256:")


# ------------------------------------------------------------------ property (>= 1,000 inputs)
TARGETS = ("AN-01", "AN-02", "AN-04", "AN-05", "AN-07:fault", "AN-07:forced-error")
NEEDS = ("wall", "half_court", "full_court", "ball_machine", "partner_feeder")
LEVELS = ("beginner", "intermediate", "advanced")


@st.composite
def drills(draw: st.DrawFn, i: int) -> Drill:
    dmin = draw(st.integers(1, 45))
    lo, hi = sorted(
        draw(st.lists(st.sampled_from(LEVELS), min_size=2, max_size=2)), key=LEVELS.index
    )
    skills = draw(
        st.lists(
            st.sampled_from(["warm-up", "share:fault", "share:forced-error", "x"]), unique=True
        )
    )
    return drill(
        f"pb.gen.d{i}",
        targets=draw(
            st.lists(
                st.sampled_from(["AN-01", "AN-02", "AN-04", "AN-05", "AN-07"]),
                min_size=1,
                max_size=3,
                unique=True,
            )
        ),
        skills=skills,
        players=draw(st.integers(1, 4)),
        needs=draw(st.lists(st.sampled_from(NEEDS), max_size=2, unique=True)),
        minutes=(dmin, draw(st.integers(dmin, 45))),
        levels=(lo, hi),
        status=draw(st.sampled_from(["draft", "coach-reviewed", "verified"])),
        deprecated_by=draw(st.sampled_from([None, None, None, "pb.gen.old@1"])),
    )


@st.composite
def inputs(draw: st.DrawFn) -> tuple[list[PlanWeakness], Preferences, list[Drill]]:
    n = draw(st.integers(0, 14))
    library = [draw(drills(i)) for i in range(n)]
    # an empty ranking is covered by test_no_weakness_gives_no_plan; here 1-4 weaknesses
    targets = draw(st.lists(st.sampled_from(TARGETS), min_size=1, max_size=4, unique=True))
    if draw(st.booleans()):  # often give the generator a chance to build a plan
        metric, _, share = targets[0].partition(":")
        library.append(warm_up("pb.gen.warm"))
        skills = (f"share:{share}",) if share else ()
        library.append(drill("pb.gen.easy", targets=(metric,), skills=skills, minutes=(5, 6)))
    weaknesses = [PlanWeakness(f"w{r}", t, r) for r, t in enumerate(targets, start=1)]
    spw = draw(st.integers(1, 7))
    mps = draw(st.integers(15, 180))
    weekly = draw(st.one_of(st.none(), st.integers(spw * 15, 1260)))
    prefs = Preferences(
        minutes_per_session=mps,
        sessions_per_week=spw,
        players_available=draw(st.integers(1, 4)),
        equipment=frozenset(draw(st.lists(st.sampled_from(NEEDS), unique=True))),
        level=draw(st.sampled_from(LEVELS)),
        weekly_minutes=weekly,
    )
    return weaknesses, prefs, library


@pytest.mark.plan_property
@settings(max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(inputs(), st.randoms(use_true_random=False))
def test_property_assembled_plans_keep_every_rule(
    case: tuple[list[PlanWeakness], Preferences, list[Drill]], rnd: random.Random
) -> None:
    weaknesses, prefs, library = case
    result = assemble(weaknesses, prefs, library)
    event("plan" if isinstance(result, TrainingPlan) else f"infeasible:{result.reason}")
    assert plan_problems(result, prefs, weaknesses, library) == []
    shuffled = list(library)
    rnd.shuffle(shuffled)
    again = assemble(list(reversed(weaknesses)), prefs, shuffled)
    if isinstance(result, TrainingPlan):
        assert isinstance(again, TrainingPlan)
        assert again.content_digest() == result.content_digest()
    else:
        assert again == result
