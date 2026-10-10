// The coach's worked example as a stats body (api-sprint-03 §2.1), shared by the ST-048 unit tests.
// Values: web/e2e/sprint-03/worked-example.reference.json; AN-03 B and AN-05 B changed to cover
// one decimal and untagged fault types; AN-07 B n = 0 to cover the empty side.
import type { MetricEntry } from '@/lib/stats/types';

export const MATCH = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
export const entry = (id: string, over: Partial<MetricEntry> = {}): MetricEntry => ({
  id, version: '0.1', name: `Name of ${id}`, definition: `Definition of ${id}.`, unit: 'proportion',
  min_sample: { unit: 'rallies', n: 20 }, status: 'coach-reviewed', ...over,
});

export const WORKED_BODY = {
  match_id: MATCH, sheet_version: 15, rules_version: 'PROVISIONAL-UNVERIFIED', metric_def_version: '0.1',
  unofficial: true, label: 'unofficial scoring (rules not yet verified)', low_sample_rule: { max_interval_width: 0.3 },
  metrics: {
    'AN-01': {
      entry: entry('AN-01', { name: 'Rallies won on serve' }),
      A: { k: 4, n: 7, value: 0.5714, ci_low: 0.2505, ci_high: 0.8418, low_sample: true },
      B: { k: 4, n: 6, value: 0.6667, ci_low: 0.3, ci_high: 0.9032, low_sample: true },
    },
    'AN-03': {
      entry: entry('AN-03', { unit: 'points_per_turn', min_sample: { unit: 'service_turns', n: 10 } }),
      A: { points: 4, turns: 2, value: 2.0, low_sample: true },
      B: { points: 4, turns: 3, value: 1.3333, low_sample: true },
    },
    'AN-04': {
      entry: entry('AN-04', { unit: 'count_per_game', min_sample: { unit: 'games', n: 2 } }),
      A: { count: 2, games: 1, value: 2.0, by_player: { A1: 1, A2: 1 }, player_not_tagged: 0, low_sample: true },
      B: { count: 1, games: 1, value: 1.0, by_player: {}, player_not_tagged: 1, low_sample: true },
    },
    'AN-05': {
      entry: entry('AN-05'),
      A: { k: 2, n: 7, value: 0.2857, ci_low: 0.0822, ci_high: 0.6411, fault_type_not_tagged: 0, low_sample: true },
      B: { k: 0, n: 6, value: 0.0, ci_low: 0.0, ci_high: 0.3903, fault_type_not_tagged: 2, low_sample: true },
    },
    'AN-06': {
      entry: entry('AN-06', { unit: 'points', min_sample: null }),
      A: { longest: 3, longest_by_game: [3], histogram: { '1': 1, '2': 0, '3': 1, '4': 0, '5+': 0 }, n: 4, low_sample: false },
      B: { longest: 2, longest_by_game: [2], histogram: { '1': 0, '2': 2, '3': 0, '4': 0, '5+': 0 }, n: 4, low_sample: false },
    },
    'AN-07': {
      entry: entry('AN-07', { unit: 'proportion_mix' }),
      A: {
        n: 6, counts: { winner: 2, unforced_error: 2, forced_error: 0, fault: 2 }, low_sample: true,
        shares: {
          winner: { k: 2, value: 0.3333, ci_low: 0.0968, ci_high: 0.7 },
          unforced_error: { k: 2, value: 0.3333, ci_low: 0.0968, ci_high: 0.7 },
          forced_error: { k: 0, value: 0, ci_low: 0, ci_high: 0.3903 },
          fault: { k: 2, value: 0.3333, ci_low: 0.0968, ci_high: 0.7 },
        },
      },
      B: { n: 0, counts: { winner: 0, unforced_error: 0, forced_error: 0, fault: 0 }, low_sample: true, shares: {
        winner: { k: 0, value: null, ci_low: null, ci_high: null },
        unforced_error: { k: 0, value: null, ci_low: null, ci_high: null },
        forced_error: { k: 0, value: null, ci_low: null, ci_high: null },
        fault: { k: 0, value: null, ci_low: null, ci_high: null },
      } },
    },
  },
};

