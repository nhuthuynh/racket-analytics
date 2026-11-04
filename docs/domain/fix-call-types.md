# Call types for "fix a call in ≤ 2" (NFR-036.4)

- **Owner:** pickleball-domain-coach (COACH-5, 2026-11-03). **Used by:** ST-080 (`web/e2e/sprint-05/fix-call-taps.spec.ts` (planned)), which counts the taps or keys for each call type below. This file confirms and refines assumption A7 in `docs/sprints/05/requirements-breakdown.md` §5 ("rally winner, fault, rally ending").
- **Basis:** FR-050 (Quick Tag inputs), FR-051 (keys), FR-052 (corrections), FR-044 (fault subtype is for analytics only). The R1 correction controls are in `web/src/components/score-sheet/RallyCorrections.tsx`: "Switch winner", "Change ending" and "Change player". Endings are listed in `web/src/lib/tagging/types.ts` (`ENDINGS`). **No pickleball rule is claimed here.** A call type is a field that the player sets on a rally. The scoring consequences are listed for test data only. They follow the `PROVISIONAL-UNVERIFIED` preset and are **UNVERIFIED** (`docs/domain/rules-verified.md`).

## 1. What a "call" is

A call is one value the player gave a rally that a coach would want fixed when it is wrong. Fixing a call changes only that field. The score then replays (FR-053), but the replay is a consequence and not another call, so it costs no tap.

## 2. Call types that ST-080 counts (all must be ≤ 2 taps or keys)

| Id | Call type (A7 name) | Field | Fix in R1 | Example fix for the test (from → to) | Score effect (UNVERIFIED, preset) |
|---|---|---|---|---|---|
| CT-1 | Rally winner | `winning_side` | "Switch winner" | won by side A → won by side B (ending `unforced_error`) | yes: the side-out or point changes |
| CT-2 | Rally ending, other than fault | `ending` among winner, unforced error, forced error, replay | "Change ending" → option | `winner` → `unforced_error`; and `unforced_error` → `replay` | none between winner and the errors; **replay removes the rally from the score** |
| CT-3 | Fault | `ending` to or from `fault` | "Change ending" → "Fault" (or away from it) | `unforced_error` → `fault`; and `fault` → `forced_error` | none: a fault and an error both lose the rally for that side (FR-044, queue row 5) |
| CT-4 | Responsible player (added by COACH-5) | `responsible_player` | "Change player" → name, or "Not tagged" | on a rally ending `unforced_error`: the tagged player → their partner; and the tagged player → "Not tagged" | none on the score; it changes the per-player error stats |

- **Why CT-4 is added (judgment):** per-player error stats are player-facing (FR-050 "per-player error stats"; K9 in `docs/requirements/functional-requirements.md`). A wrong player tag is the call a doubles partner disputes most often. It is the same 2-tap control as CT-2. So the test costs one more parametrised case.
- **Why CT-2 and CT-3 are split:** a fault and an error have the same score effect, but they feed different analytics (AN-07 fault share against forced-error share). Players mix them up most often (judgment). The counter must prove both directions: into "Fault" and out of it.
- **Where the call is seen:** each row of the score sheet (FR-049), and the last tagged rally in Quick Tag. ST-080 and the principal-designer choose the screens the counter starts from (NFR-036.4: "score sheet and Quick Tag review"). Opening the screen is not counted. The count starts on the screen where the wrong value is visible.

## 3. Not call types in R1 (not counted)

| Field | Why it is not counted |
|---|---|
| Fault subtype (serve, foot, two bounce, kitchen, other) | Quick Tag and the score sheet do not set or correct it in R1. Only Full Tag (labeller role) sets it. It never changes the score (FR-044). If R2 adds it to the player's controls, it becomes CT-5 |
| Rally start and end time | A time boundary, not a call. Fixing it is a video-editing task. No ending, winner or score depends on it (judgment) |
| Server, score or server number | Never typed. They are replayed from the calls (FR-049: "never stored as an editable value") |
| Game start (first server, start score) | Declared once per game (FR-046), not per rally. Fixing it is a setup task |

## 4. Negative case for ST-080

The planted 3-step path (sprint-05 §3.7 ST-080) should be a CT-3 fix that goes through a confirmation step. This is the path most likely to grow an extra step: confirming that the score will change (FR-054) does not apply to CT-3, because the score does not change (judgment).
