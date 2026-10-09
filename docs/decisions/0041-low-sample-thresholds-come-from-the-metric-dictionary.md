# 0041. The low-sample thresholds have one source: the versioned metric dictionary

- **Status:** Accepted (principal-engineer, 2026-10-07, Sprint 3 review round 1, PE-R1S3-03). Amends the "thresholds live in config" clause of ADR 0005 (Proposed) and FR-101 by naming which config: the dictionary file, not environment settings. The values of ADR 0005 do not change.
- **Date:** 2026-10-07
- **Deciders:** principal-engineer
- **Consulted:** pickleball-domain-coach (metric owner; confirms the `low_sample` field restates rule 0.3), senior-backend-engineer (ST-046), business-analyst (FR-101 wording)
- **Related:** ADR 0005; FR-101, FR-102; NFR-075; `docs/domain/metric-dictionary.md` rule 0.3; `backend/src/racket/sports/pickleball/metrics.py`; `backend/src/racket/analytics/uncertainty.py`; analytics-snapshots.md §5.2

## Context and problem statement

The minimum sample exists twice. `metrics.json` holds `min_sample` per entry; it is versioned, covered by the definition digest (`metrics.lock.json`) and shown to players by `MetricEntry.public()`. `LowSamplePolicy` holds `min_proportion_n=20`, `min_service_turns=10`, `min_games=2`, `max_interval_width=0.30` and its docstring says they "come from settings"; nothing reads them from the dictionary. If an operator changed the policy, a card would show "n below 20" while the flag used another number, and two snapshots with the same `metric_def_version` could carry different flags (NFR-075). The policy also has one `min_proportion_n` for four metrics, so a per-metric change by the coach could not be expressed.

## Decision drivers

- What the player reads must be what the system applied (FR-101, FR-102; [DPA/DESIGN-11] G2).
- A changed interpretation changes a version (NFR-075, ddd-guidelines §4.7).
- The coach owns thresholds (metric owner); operators do not.

## Considered options

1. **The dictionary is the only source** (chosen): each metric's flag uses its own entry's `min_sample.n`; the interval-width rule becomes a digested top-level dictionary field `low_sample.max_interval_width`; no environment setting; `LowSamplePolicy.from_dictionary()` at the composition root; a unit test pins it to ADR 0005's values for the shipped file.
2. **Environment settings are the source; the card reads them too.** Good: an operator can tune without a release. Bad: no version changes when the meaning changes (NFR-075); the coach-reviewed dictionary would no longer state its own rule; dev/CI/prod could disagree silently.
3. **Keep both, add a start-up check that they agree.** Good: small change. Bad: still two places to edit; the check only turns a silent drift into a refused start, and per-metric thresholds remain impossible.

## Decision outcome

Option 1.

### Consequences

- `metrics.json` gains `"low_sample": {"max_interval_width": 0.30}` (covered by the lock; changing it bumps the dictionary version). `MetricDictionary.parse` validates it (0 < width ≤ 1).
- `LowSamplePolicy.from_dictionary(dictionary)` builds per-metric thresholds and refuses a `min_sample.unit` that does not fit the metric; `starter_stats` takes that policy. The `LowSamplePolicy()` defaults remain for pure unit calls only.
- The stats response shows `entry.min_sample` and `low_sample_rule` (api-sprint-03 §2.1).
- No `LOW_SAMPLE_*` environment variable exists or may be added; `infra/env.example` stays without one.
- Owner: senior-backend-engineer in ST-046, red test first (negative: a dictionary with AN-05 `n = 30` flags AN-05 at n = 25 and not AN-01).

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Two sources today | `metrics.py` `public()` returns `min_sample`; `uncertainty.py` `LowSamplePolicy` defaults; `grep -rn "LowSamplePolicy" backend/src` → only `uncertainty.py` and `starter_stats.py` | code |
| No threshold env setting exists yet | `grep -rn "LOW_SAMPLE\|min_proportion" backend/src/racket/platform/settings.py infra/env.example` → no match | code |
| Snapshots must keep their meaning per version | NFR-075; ddd-guidelines §4.7 | requirement |
| Choice of option 1 | (judgment) | judgment |
