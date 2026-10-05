# Scoring engine: domain design (ST-020, ST-021, ST-022)

- **Status:** Accepted for Sprint 1 (principal-engineer, 2026-10-05). Changes go through a PR on this file reviewed by senior-backend-engineer, senior-qa-engineer and pickleball-domain-coach. The seams in `backend/tests/support/contract.py` (ADR 0012) change in the same PR.
- **Contexts:** Sport Plug-in (`racket.sports.pickleball.rules`, Published Language R5) and Match & Scoring (`racket.matches.domain`, `MatchState`). Context map rule 1 allows `matches` to import `racket.sports` (R5).
- **Decisions this rests on:** ADR 0009 (readiness split, Accepted 2026-10-05 by ADR 0023), QD-RE-01..11 and QD §2.2/§2.3 (`docs/requirements/brainstorm-quality-domain.md`), NFR-079, sprint-01 §5, §7.7-§7.10, §14.2.
- **Aligned with:** QA's red-first seams in `backend/tests/support/contract.py` (Sprint 1 block) and helpers in `backend/tests/support/scoring.py`, read on 2026-10-05. Where this file and those seams differ, the seams win and this file is corrected; none differ today.
- **No rulebook claim.** Every rule value lives in `RulesConfig`. Behaviour is specified against explicit configuration values (ADR 0009 part a). The only shipped preset is `PROVISIONAL-UNVERIFIED`; rows from QD §2.2 run `@needs-verification` until the coach records `@rule-<n>` (OQ-01 PDFs still to be supplied).

## 1. Shape

`apply` is a pure function `(GameState, RallyOutcome, RulesConfig) → GameState | DomainError` (QD-RE-01) [EP/ENG-17]. A score is a **projection**: `fold` over the recorded outcomes from a declared start. Nothing is stored that `fold` can recompute (golden replay, NFR-075).

```
racket/sports/pickleball/rules/          # package; pure Python, stdlib only
  __init__.py      re-exports the public names below (the Published Language)
  config.py        Side, ScoringSystem, MatchFormat, FaultKind, RulesConfig, InvalidRulesConfig
  presets.py       PRESETS (the only file allowed to hold rule literals besides config bounds)
  state.py         GameState, new_game, declare_state
  outcome.py       RallyOutcome
  errors.py        DomainError, GameOver, IllegalState, UnknownOutcome
  engine.py        apply, fold
```

**Allowed imports** (IT-01-13, QD-TR-01): `dataclasses`, `enum`, `types`, `typing`, `collections.abc`, `functools`, `__future__`. Nothing from `racket.platform`, SQLAlchemy, FastAPI/Starlette, pydantic, `datetime`, `time`, `random`, `os`, `logging` or any I/O module.

**Literal rule** (IT-01-12, NFR-079): rule values (targets, margins, server numbers as policy, first-service flag) appear only in `presets.py`. `config.py` holds validation bounds only (`>= 1`). The static check allowlists `presets.py`; the engine compares against `config.*` fields only. The server numbers `1` and `2` are the definition of doubles side-out mechanics in this model, not a tunable rule, and live as named constants `FIRST_SERVER`, `SECOND_SERVER` in `state.py` (judgment; QA's check may allowlist that file and those names).

## 2. Value objects

All value objects are `@dataclass(frozen=True, slots=True)` or enums; equality is by value; nothing is mutable.

### 2.1 Enums

| Name | Members | Notes |
|---|---|---|
| `Side` | `A`, `B` (`Enum`, values `"A"`, `"B"`) | `Side.A.other is Side.B`. Indexed by name in tests (`Side["A"]`) |
| `ScoringSystem` | `SIDE_OUT = "side_out"`, `RALLY = "rally"` (`StrEnum`) | `RALLY` exists as a flag from R1 (OQ-04) but is refused by `RulesConfig` in Sprint 1 (§2.2) |
| `MatchFormat` | `DOUBLES = "doubles"`, `SINGLES = "singles"` (`StrEnum`) | `SINGLES` is refused by `RulesConfig` in Sprint 1 (singles scoring is ST-035, Sprint 2) |
| `FaultKind` | `SERVE "serve"`, `FOOT "foot"`, `TWO_BOUNCE "two_bounce"`, `NVZ "nvz"`, `OTHER "other"` (`StrEnum`) | Analytics only; never changes the score (QD-RE-09, P7) |

### 2.2 `RulesConfig`

```python
RulesConfig(*, rules_version: str, scoring_system: str | ScoringSystem, format: str | MatchFormat,
            points_to_win: int, win_by: int, first_service_single_server: bool)
```

- **Keyword-only, no defaults.** A default would be a hidden rule value (NFR-079). Every field must be passed.
- Validation in `__post_init__`; failure **raises** `InvalidRulesConfig` (a `ValueError` subclass, not a `DomainError`). A config is built at the edge (preset load or test setup), never inside `apply`, so raising here does not break QD-RE-05.
- `InvalidRulesConfig` has `field: str` (the Python field name) and `reason: "invalid" | "unknown" | "unsupported"`; `str(exc)` names the field, e.g. `"points_to_win must be an integer >= 1"`.

| Field | Rule | Error (`field`, `reason`) |
|---|---|---|
| `rules_version` | `str`, 1-64 characters after strip, `[A-Za-z0-9._-]` only | `rules_version`, `invalid` |
| `scoring_system` | a `ScoringSystem` value. `"rally"` is known but unsupported in Sprint 1 (FR-043) | `scoring_system`, `unknown` / `unsupported` |
| `format` | a `MatchFormat` value. `"singles"` is known but unsupported in Sprint 1 | `format`, `unknown` / `unsupported` |
| `points_to_win` | `int` (not `bool`), `>= 1` | `points_to_win`, `invalid` |
| `win_by` | `int` (not `bool`), `>= 1` | `win_by`, `invalid` |
| `first_service_single_server` | `bool` | `first_service_single_server`, `invalid` |

Fields arriving later, each with its own story and test, never as a default: `rally_game_point_serving_only` (rally scoring, R2), singles serving-court parity (ST-035).

### 2.3 `PRESETS`

`PRESETS: Mapping[str, RulesConfig]` (a `MappingProxyType`). Sprint 1 ships exactly one entry:

| Key | `rules_version` | `scoring_system` | `format` | `points_to_win` | `win_by` | `first_service_single_server` |
|---|---|---|---|---|---|---|
| `PROVISIONAL-UNVERIFIED` | `PROVISIONAL-UNVERIFIED` | `side_out` | `doubles` | 11 | 2 | `True` |

The values come from QD §2.2 and are **unverified** [DOM G1 R2, R6]. A preset named after a federation (`USAP-2026`) ships only when every row is verified (ADR 0009 rule 4; ST-020b). A match stores `rules_version`; a newer preset never changes an existing match (QD-RE-02; §7.7 "A match keeps the rules version").

### 2.4 `GameState`

```python
GameState(score_a: int, score_b: int, serving_side: Side, server_number: int | None,
          winner: Side | None)
  .is_over -> bool          # winner is not None
  .score_of(side) -> int
```

- Construction checks only what needs no config: scores are non-negative `int`s; `server_number in {1, 2, None}`; `winner` is `None` or a `Side`; if `winner` is set, the winner's score is the higher one. A failure raises `ValueError`: this is a programming error, never reachable through `new_game`, `declare_state` or `apply`.
- Callers do **not** build in-play states by hand. They use `new_game` or `declare_state`, which check the config-dependent rules and return a `DomainError` instead of raising.
- The call ("S-R-n") is **not** a method of `GameState`. Call formatting is a separate pure function (FR-048, ST-029, Sprint 2). Tests parse calls on the test side (`tests/support/scoring.py`).
- Sprint 2 adds `server_player` and `right_court_player` (QD-RE-03, SOD-05/06 positions) as new fields with their own tests; SOD-06 stays `@needs-verification` and is not in the Sprint 1 table.

### 2.5 Constructors of a game

| Function | Returns | Rules |
|---|---|---|
| `new_game(config, first_server: Side)` | `GameState` | 0-0, `first_server` serving, at server 2 when `config.first_service_single_server`, else at server 1. The first server is an **input**, never inferred (QD-RE-11) |
| `declare_state(config, *, serving_side, serving_score, receiving_score, server_number)` | `GameState \| IllegalState` | `IllegalState` when: `server_number` not in {1, 2} (doubles); a score is negative or not an `int`; the scores already meet the game-over condition (§3, P5). A declared `0-0-1` is legal (SOD-13). Used for mid-game starts (QD-RE-06, Sprint 2 UI) and by the golden tables |

### 2.6 `RallyOutcome`

```python
RallyOutcome.won_by(side: Side)                    # rally won outright by `side`
RallyOutcome.fault(by: Side, kind: FaultKind)       # `by` committed a fault, i.e. lost the rally
RallyOutcome.replay()                               # rally replayed; changes nothing (QD-RE-08)
  .kind -> Literal["won", "fault", "replay"]
  .rally_winner -> Side | None                      # fault: by.other; replay: None
  .fault_by -> Side | None; .fault_kind -> FaultKind | None
```

Glossary: "Rally ending" (sprint-01 §14.6). `unforced_error` and `forced_error` endings (FR-050) are analytics labels on a won rally and arrive with tagging (Sprint 2) as optional fields that `apply` ignores. A `gap` outcome (QD-RE-07) arrives in Sprint 2 with resync; P8 covers it then.

### 2.7 Domain errors (returned, never raised)

`DomainError` is a frozen dataclass with `message: str`. It is **not** an `Exception` subclass: `apply` and `fold` return it (QD-RE-05). Subclasses:

| Error | Context | `message` | When |
|---|---|---|---|
| `GameOver` | rules | `"game already over"` | any outcome applied to a finished game (SOD-12, §7.7) |
| `IllegalState` | rules | names the problem, e.g. `"server number must be 1 or 2"`, `"score already meets the game-over condition"` | `declare_state` refusals; `apply` given a state inconsistent with the config (e.g. `server_number is None` under doubles) |
| `UnknownOutcome` | rules | `"unknown rally outcome"` | `apply` given something that is not a `RallyOutcome` (QD-RE-05) |
| `MatchOver` | matches | `"match is over"` | a rally or a new game after the match is decided, or a game number beyond the format (M-05, M-08) |

The API maps them, when they reach HTTP in Sprint 2, to 409 `conflict` with fixed messages; the domain `message` is for tests and logs, never sent.

## 3. `apply` and `fold`

```python
def apply(state: GameState, outcome: RallyOutcome, config: RulesConfig) -> GameState | DomainError
def fold(outcomes: Iterable[RallyOutcome], config: RulesConfig, start: GameState
         ) -> GameState | DomainError
```

`apply`, side-out doubles (the only supported combination in Sprint 1):

1. `outcome` is not a `RallyOutcome` → `UnknownOutcome`. `state` inconsistent with `config` → `IllegalState`.
2. `state.is_over` → `GameOver`.
3. `replay` → return `state` unchanged (identity, P8).
4. `w = outcome.rally_winner` (for a fault, the other side; the subtype is ignored, P7).
5. If `w == state.serving_side`: the serving side gains 1 point; the server number is unchanged. If now `max(score) >= config.points_to_win` and `|score_a - score_b| >= config.win_by`, set `winner = w` (P5).
6. Else, if `server_number == 1`: the same side continues at server 2, no point.
7. Else (`server_number == 2`): side-out; the other side serves at server 1, no point.

`fold` applies left to right from `start`, returns the first `DomainError` it meets, and `fold([], config, start) == start`. A list form `scan(outcomes, config, start) -> tuple[GameState, ...] | DomainError` for the score sheet arrives in Sprint 2 (FR-048, corrections QD-RE-10) and must equal the prefix folds.

Game end uses the configured target and margin only (sprint-01 §7.7): with target 11 and margin 1, 10-10 → 11-10 ends the game; with margin 2 it does not.

## 4. Invariants P1-P9 (QD §2.3) and where they are checked

Stated for **any valid config** (ADR 0009 part a). QA's `check_invariants` and `check_fold` (`tests/support/scoring.py`) are the executable form; ≥ 1,000 sequences per supported scoring system per CI run (NFR-002a).

| # | Invariant | Sprint 1 | Checked by |
|---|---|---|---|
| P1 | Scores never decrease; a rally adds at most 1 point, to one side | Yes | `check_invariants` |
| P2 | Side-out: a side scores only on a rally it won as the serving side | Yes | `check_invariants` |
| P3 | Rally scoring: every counted rally adds exactly 1 to the rally winner (with the game-point flag) | **No**: rally scoring is refused by `RulesConfig` until verified (FR-043) | Sprint 2+ |
| P4 | Doubles `server_number ∈ {1, 2}`; a serving-side loss at server 2 is a side-out to server 1; at server 1 it passes to server 2 | Yes | `check_invariants` |
| P5 | `is_over` ⇔ max ≥ `points_to_win` ∧ diff ≥ `win_by`, first true at the first rally where it holds; `winner` is the leader | Yes | `check_invariants`; `declare_state` refuses a start that already meets it |
| P6 | `fold` equals sequential `apply`; prefix then suffix equals the whole; empty fold is the start | Yes | `check_fold` |
| P7 | For a fixed faulting side, the next state is independent of `FaultKind` and equals "the other side won the rally" | Yes | `check_invariants` |
| P8 | `replay` (and `gap`, Sprint 2) is identity | Yes (replay) | `check_invariants` |
| P9 | An independent QA engine in `backend/tests/oracle/` agrees on 100,000 sequences nightly | Yes (ST-022, ST-024) | nightly job. The oracle author must **not** read `racket/sports/pickleball/rules/` [DPA/AI-08]; this design doc and QD §2 are its only inputs |

Additional guarantees: **purity** (same inputs → equal output, no I/O, clock or randomness; IT-01-13); **totality** (`apply` never raises for any `GameState`, any object as outcome and any valid config, tested with Hypothesis); **performance** (domain suite < 10 s, NFR-073; `apply` is O(1)).

## 5. `MatchState` (ST-021, Match & Scoring)

`racket.matches.domain.MatchState`, a frozen value object. It is the score projection of the `Match` aggregate; Sprint 2 persists rally outcomes on the aggregate and rebuilds `MatchState` by folding them.

```python
MatchState.start(*, best_of: int, config: RulesConfig) -> MatchState        # best_of in {1, 3}
ms.start_game(*, first_server: Side, ends_switched: bool) -> MatchState | DomainError
ms.record_rally(game_number: int, outcome: RallyOutcome) -> MatchState | DomainError
ms.games -> tuple[GameRecord, ...]   # GameRecord(number, first_server, ends_switched, state)
ms.games_won(side) -> int; ms.winner -> Side | None; ms.is_over -> bool; ms.rules_version -> str
```

| Rule | Result | Row |
|---|---|---|
| `best_of` not in {1, 3} | `ValueError` at `start` (edge input; the API validates first) | — |
| The match is decided when a side has won `best_of // 2 + 1` games | `is_over`, `winner` | M-01..M-04 |
| `start_game` while the current game is in play | `IllegalState("current game not finished")` | — |
| `start_game` after the match is decided | `MatchOver` | M-05 |
| `start_game` records `first_server` and `ends_switched` exactly as given; game 2's first server is never inferred | — | M-06, M-07 |
| `record_rally` with the match decided, or `game_number > best_of` | `MatchOver` | M-05, M-08 |
| `record_rally` for a game not yet started | `IllegalState("game not started")` | — |
| `record_rally` for a finished game in an undecided match | the engine's `GameOver` | SOD-12 |
| `rules_version` is `config.rules_version` from `start` and never changes | — | §7.7 |

`MatchOver` subclasses the rules `DomainError`. `MatchState` imports only `racket.sports.pickleball.rules` and the stdlib.

## 6. Test plan alignment (sprint-01 §5, negative first)

| §5 row | Design element |
|---|---|
| `RulesConfig` 1-4 | §2.2 table; frozen dataclass (assigning a field raises `FrozenInstanceError`) |
| `GameState` 1-2 | `declare_state` → `IllegalState` (§2.5); 3: no call method on `GameState` (§2.4) |
| `apply` 1-7 | §3 steps 2, 6, 7, 5, `new_game` (first-service flag), 5 (P5), 3 |
| `Fault` 1-2 | §3 step 4 |
| `fold` 1-3 | §3 `fold` |
| `MatchState` 1-3 | §5 |

## 7. Open items

- The coach confirms or corrects each provisional row once OQ-01 supplies the rulebook; only `PRESETS` and row tags change (ADR 0009).
- `server_player` / positions (SOD-05, SOD-06), singles (ST-035), rally scoring (FR-043), `gap` and corrections (QD-RE-07, QD-RE-10) are later stories; each adds fields or outcomes without changing the signatures above.
