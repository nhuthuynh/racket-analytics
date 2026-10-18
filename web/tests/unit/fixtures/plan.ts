// A GET /me/plan 200 body (api-sprint-04 §2.3, as `plan_body` renders it: evidence links carry
// `side`; ST-061b decisions). One match, one week; the warm-up and two targeted drills.
export const MATCH_ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
export const RALLY_ID = '7c1d0e2f-3a4b-4c5d-8e6f-0a1b2c3d4e5f';
const uuid = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;

function citation(metricId: string, value: number, n: number, lowSample = false) {
  return {
    metric_id: metricId, metric_version: '0.1', side: 'A', value, n, k: Math.round(value * n),
    low_sample: lowSample, rally_ids: [RALLY_ID], evidence: [{ match_id: MATCH_ID, side: 'A', n }],
  };
}

function assignment(id: number, position: number, extra: Record<string, unknown>) {
  return { id: uuid(id), position, ...extra };
}

export function planBody(): Record<string, unknown> {
  return {
    id: uuid(1), version: 1, created_at: '2026-10-17T09:00:00Z', content_digest: 'sha256:ab',
    library_version: 'lib-1', regenerated: null,
    unofficial: true, label: 'unofficial scoring (rules not yet verified)', drills_verified: false,
    preferences: {
      minutes_per_session: 30, sessions_per_week: 3, weekly_minutes: 90, players_available: 1,
      equipment: ['wall'], level: 'intermediate',
    },
    ranking: {
      unit: 'rallies_lost_per_game', side_out_verified: false, games: 1, rallies: 14, skipped_matches: 0,
      weaknesses: [
        { id: 'unforced_errors', name: 'Unforced errors', metric_id: 'AN-04', rank: 1, per_game: 2.0,
          on_serve_per_game: 1.0, on_receive_per_game: 1.0, conceded_per_game: 1.0 },
        { id: 'serve_faults', name: 'Serve faults', metric_id: 'AN-05', rank: 2, per_game: 1.0,
          on_serve_per_game: 1.0, on_receive_per_game: 0.0, conceded_per_game: 1.0 },
      ],
    },
    limited_data: { rallies: 14 },
    unfitted: [],
    sessions: [
      {
        id: uuid(10), week: 1, index: 1, minutes_budget: 30, done: false, done_at: null,
        assignments: [
          // Out of position order on purpose: the page orders by `position`.
          assignment(102, 2, {
            drill: { id: 'pb.wall.serve-target', version: 1, name: 'Serve to a target', players: 1,
              needs: ['wall'], skills: ['serve'] },
            minutes: 12, weakness_id: 'serve_faults', warm_up: false,
            citation: citation('AN-05', 0.2857, 7, true), why: 'Serve faults: 29% of 7 serves',
          }),
          assignment(101, 1, {
            drill: { id: 'pb.warm-up.dinks', version: 1, name: 'Wall dinks warm-up', players: 1,
              needs: [], skills: ['warm-up'] },
            minutes: 8, weakness_id: null, warm_up: true,
            citation: citation('AN-01', 0.5714, 7), why: 'Rallies won on serve: 57% of 7 serves',
          }),
        ],
      },
      {
        id: uuid(11), week: 1, index: 2, minutes_budget: 30, done: false, done_at: null,
        assignments: [
          assignment(103, 1, {
            drill: { id: 'pb.wall.reset', version: 1, name: 'Wall resets', players: 2,
              needs: ['wall', 'ball_machine'], skills: ['reset'] },
            minutes: 20, weakness_id: 'unforced_errors', warm_up: false,
            citation: citation('AN-04', 2.0, 1), why: 'Unforced errors: 2.0 over 1 game',
          }),
        ],
      },
    ],
  };
}

type Body = Record<string, unknown>;

/** The body with one change made to its first session's first assignment (in body order). */
export function withFirstAssignment(change: (a: Body) => void): Body {
  const body = planBody();
  const sessions = body.sessions as { assignments: Body[] }[];
  change(sessions[0]!.assignments[0]!);
  return body;
}
