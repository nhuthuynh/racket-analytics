// ST-048 / ST-047 (FR-100, FR-101, FR-102, FR-103; NFR-034): the stats response parser and the pure
// display helpers of D-01 and E-01 (flows-sprint-03 §0, §2, §3). Negative cases first: a body the
// contract does not describe is refused, unknown ids are dropped, no number is printed without n.
// The numbers are the coach's worked example (web/e2e/sprint-03/worked-example.reference.json).
import { describe, expect, it } from 'vitest';
import { ResponseShapeError } from '@/lib/api/parse';
import { parseEvidence, parseStats } from '@/lib/stats/parse';
import {
  evidenceLabel,
  lowSampleReason,
  pct,
  rate,
  showMeCount,
  showMeText,
  sideHasSample,
  sideSummary,
} from '@/lib/stats/view';
import type { Stats } from '@/lib/stats/types';
import { WORKED_BODY, entry } from './fixtures/stats';

const RALLY = '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a01';
function stats(): Stats {
  return parseStats(structuredClone(WORKED_BODY));
}

describe('parseStats (api-sprint-03 §2.1)', () => {
  it('refuses a body without metrics, a per-side block without n, or a value that is not a number', () => {
    const noMetrics = structuredClone(WORKED_BODY) as Record<string, unknown>;
    delete noMetrics.metrics;
    expect(() => parseStats(noMetrics)).toThrow(ResponseShapeError);
    const noN = structuredClone(WORKED_BODY);
    delete (noN.metrics['AN-01'].A as Partial<typeof noN.metrics['AN-01']['A']>).n;
    expect(() => parseStats(noN)).toThrow(ResponseShapeError);
    const text = structuredClone(WORKED_BODY);
    (text.metrics['AN-01'].A as unknown as { value: string }).value = '57%';
    expect(() => parseStats(text)).toThrow(ResponseShapeError);
  });

  it('drops a metric id it has no layout for and keys outside the contract, and keeps dictionary order', () => {
    const body = structuredClone(WORKED_BODY) as typeof WORKED_BODY & { extra?: string };
    body.extra = 'x';
    (body.metrics as Record<string, unknown>)['AN-99'] = { ...body.metrics['AN-01'], entry: entry('AN-99', { unit: 'elo_rating' }) };
    (body.metrics['AN-01'].A as Record<string, unknown>).nickname = 'Ivy';
    const s = parseStats(body);
    expect(s.metrics.map((m) => m.entry.id)).toEqual(['AN-01', 'AN-03', 'AN-04', 'AN-05', 'AN-06', 'AN-07']);
    expect(JSON.stringify(s)).not.toContain('Ivy');
    expect(JSON.stringify(s)).not.toContain('"extra"');
  });

  it('refuses a metric whose key is not its entry id (one sheet, one dictionary: no guessing)', () => {
    const body = structuredClone(WORKED_BODY);
    (body.metrics as Record<string, unknown>)['AN-02'] = body.metrics['AN-01'];
    expect(() => parseStats(body)).toThrow(ResponseShapeError);
  });

  it('an empty metrics object is a valid answer (nothing published yet), not an error', () => {
    const body = { ...structuredClone(WORKED_BODY), metrics: {} };
    expect(parseStats(body).metrics).toEqual([]);
  });

  it('keeps value and bounds null when n = 0', () => {
    const s = stats();
    const an07 = s.metrics.find((m) => m.entry.id === 'AN-07');
    expect(an07?.kind).toBe('mix');
    if (an07?.kind === 'mix') expect(an07.B.shares.winner.value).toBeNull();
  });
});

describe('parseEvidence (api-sprint-03 §3.1)', () => {
  it('refuses items without a rally id or start, and a total that is not a number', () => {
    const ok = { metric_id: 'AN-01', side: 'A', total: 7, sheet_version: 15, next_cursor: null,
      items: [{ number: 1, rally_id: RALLY, game: 1, start_ms: 1200, end_ms: 9800 }] };
    expect(parseEvidence(ok).items).toHaveLength(1);
    expect(() => parseEvidence({ ...ok, items: [{ number: 1, game: 1, start_ms: 1, end_ms: 2 }] })).toThrow(ResponseShapeError);
    expect(() => parseEvidence({ ...ok, items: [{ number: 1, rally_id: 'not-an-id', game: 1, start_ms: 1, end_ms: 2 }] })).toThrow(ResponseShapeError);
    expect(() => parseEvidence({ ...ok, total: '7' })).toThrow(ResponseShapeError);
  });
});

describe('display helpers (flows-sprint-03 §0, §2)', () => {
  it('prints whole percentages and rates with at most one decimal, no trailing zero, and a dash for no value', () => {
    expect(pct(0.5714)).toBe('57%');
    expect(pct(0)).toBe('0%');
    expect(pct(null)).toBe('—');
    expect(rate(2.0)).toBe('2');
    expect(rate(1.3333)).toBe('1.3');
    expect(rate(1.05)).toBe('1.1');
    expect(rate(null)).toBe('—');
  });

  it('every proportion prints k of n, "n = n" and the range in words (NFR-034: numbers in text)', () => {
    const an01 = stats().metrics[0]!;
    expect(sideSummary(an01, 'A')).toEqual({ main: '57%', lines: ['4 of 7 rallies · n = 7 · range 25% to 84%'] });
  });

  it('n = 0 shows a dash, "No rallies yet · n = 0", no range and no Show me', () => {
    const an07 = stats().metrics.find((m) => m.entry.id === 'AN-07')!;
    expect(sideSummary(an07, 'B', () => '').main).toBe('—');
    expect(sideSummary(an07, 'B', () => '').lines[0]).toBe('No rallies yet · n = 0');
    expect(sideHasSample(an07, 'B')).toBe(false);
  });

  it('AN-03 prints points in service turns; AN-04 per player names from the match, and untagged players', () => {
    const s = stats();
    const an03 = s.metrics.find((m) => m.entry.id === 'AN-03')!;
    expect(sideSummary(an03, 'A')).toEqual({ main: '2', lines: ['4 points in 2 service turns · n = 2'] }); // NFR-038 b: n on every metric
    expect(sideSummary(an03, 'B').main).toBe('1.3');
    const an04 = s.metrics.find((m) => m.entry.id === 'AN-04')!;
    const nick = (slot: string) => ({ A1: 'Ivy', A2: 'Dana', B1: 'Carlos', B2: 'Sam' })[slot] ?? slot;
    expect(sideSummary(an04, 'A', nick)).toEqual({ main: '2', lines: ['2 unforced errors in 1 game', 'Ivy 1 · Dana 1'] });
    expect(sideSummary(an04, 'B', nick)).toEqual({ main: '1', lines: ['1 unforced error in 1 game', 'player not tagged in 1 rally'] });
  });

  it('AN-05 says when fault types were not tagged; AN-06 prints the longest run and n runs', () => {
    const s = stats();
    const an05 = s.metrics.find((m) => m.entry.id === 'AN-05')!;
    expect(sideSummary(an05, 'B').lines).toEqual(['0 of 6 serves · n = 6 · range 0% to 39%', 'fault type not tagged in 2 rallies']);
    const an06 = s.metrics.find((m) => m.entry.id === 'AN-06')!;
    expect(sideSummary(an06, 'A')).toEqual({ main: '3 points', lines: ['n = 4 runs'] });
  });

  it('AN-07 prints n rallies as the main value', () => {
    const an07 = stats().metrics.find((m) => m.entry.id === 'AN-07')!;
    expect(sideSummary(an07, 'A')).toEqual({ main: 'n = 6 rallies', lines: [] });
  });

  it('the low-sample reason comes from the entry and the rule, with the range only where there is one', () => {
    const s = stats();
    expect(lowSampleReason(s.metrics[0]!.entry, s.lowSampleRule)).toBe(
      'Low sample: fewer than 20 rallies, or the range is wider than 30 points. Treat it as a rough guide.',
    );
    const an03 = s.metrics.find((m) => m.entry.id === 'AN-03')!;
    expect(lowSampleReason(an03.entry, s.lowSampleRule)).toBe('Low sample: fewer than 10 service turns. Treat it as a rough guide.');
  });

  it('"Show me" names how many rallies are behind the number, and the runs for AN-06', () => {
    const s = stats();
    const by = (id: string) => s.metrics.find((m) => m.entry.id === id)!;
    expect(showMeCount(by('AN-01'), 'A')).toBe(7);
    expect(showMeText(by('AN-01'), 'A')).toBe('Show me the 7 rallies');
    expect(showMeText(by('AN-03'), 'A')).toBe('Show me the 4 rallies');
    expect(showMeText(by('AN-04'), 'B')).toBe('Show me the 1 rally');
    expect(showMeText(by('AN-05'), 'B')).toBe('Show me the rallies');
    expect(showMeText(by('AN-06'), 'A')).toBe("Show me the runs' rallies");
  });

  it('an evidence item reads "Rally 3 · game 1 · 0:12" (start floored to the second)', () => {
    expect(evidenceLabel({ number: 3, rally_id: RALLY, game: 1, start_ms: 12_999, end_ms: 20_000 })).toBe('Rally 3 · game 1 · 0:12');
  });
});
