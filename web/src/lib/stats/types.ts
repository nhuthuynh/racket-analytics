// Types for the stats and evidence reads (docs/architecture/api-sprint-03.md §2.1, §3.1; ST-046,
// ST-047, ST-048). Field names follow the contract; the client keeps only what it shows.
// The metric layout is chosen by `entry.unit` (the dictionary's unit), so a coach-reviewed metric
// of a known unit needs no web change; an unknown unit is not shown (no guessing a layout).
import type { Side } from '@/lib/tagging/types';

export interface MinSample {
  unit: string;
  n: number;
}

/** `MetricEntry.public()` of the dictionary version the stats used (api-sprint-03 §2.1). */
export interface MetricEntry {
  id: string;
  version: string;
  name: string;
  definition: string;
  unit: string;
  /** null for a descriptive metric (AN-06), which is never flagged. */
  min_sample: MinSample | null;
  status: string;
}

export interface ProportionSide {
  k: number;
  n: number;
  value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  low_sample: boolean;
  /** AN-05 only: the fault type was not tagged in this many rallies (a lower bound). */
  fault_type_not_tagged: number | null;
}

export interface TurnsSide {
  points: number;
  turns: number;
  value: number | null;
  low_sample: boolean;
}

export interface PerGameSide {
  count: number;
  games: number;
  value: number | null;
  /** Slot → count, slots only (never names; the client maps them to the match's nicknames). */
  by_player: Partial<Record<string, number>>;
  player_not_tagged: number;
  low_sample: boolean;
}

export const RUN_BUCKETS = ['1', '2', '3', '4', '5+'] as const;
export type RunBucket = (typeof RUN_BUCKETS)[number];

export interface RunsSide {
  longest: number;
  longest_by_game: number[];
  histogram: Record<RunBucket, number>;
  n: number;
  low_sample: boolean;
}

export const ENDING_ROWS = ['winner', 'unforced_error', 'forced_error', 'fault'] as const;
export type EndingRow = (typeof ENDING_ROWS)[number];

export interface Share {
  k: number;
  value: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface MixSide {
  n: number;
  counts: Record<EndingRow, number>;
  shares: Record<EndingRow, Share>;
  low_sample: boolean;
}

export type Metric =
  | { kind: 'proportion'; entry: MetricEntry; A: ProportionSide; B: ProportionSide }
  | { kind: 'turns'; entry: MetricEntry; A: TurnsSide; B: TurnsSide }
  | { kind: 'perGame'; entry: MetricEntry; A: PerGameSide; B: PerGameSide }
  | { kind: 'runs'; entry: MetricEntry; A: RunsSide; B: RunsSide }
  | { kind: 'mix'; entry: MetricEntry; A: MixSide; B: MixSide };

export type MetricKind = Metric['kind'];

/** The dictionary unit → the card layout (metrics.json `unit`). */
export const KIND_OF_UNIT: Readonly<Record<string, MetricKind>> = {
  proportion: 'proportion',
  points_per_turn: 'turns',
  count_per_game: 'perGame',
  points: 'runs',
  proportion_mix: 'mix',
};

export interface Stats {
  matchId: string;
  sheetVersion: number;
  rulesVersion: string;
  metricDefVersion: string;
  unofficial: boolean;
  label: string;
  lowSampleRule: { maxIntervalWidth: number };
  /** Published entries only (FR-102), in dictionary order. */
  metrics: Metric[];
}

export interface EvidenceItem {
  number: number;
  rally_id: string;
  game: number;
  start_ms: number;
  end_ms: number;
}

export interface Evidence {
  metricId: string;
  side: Side;
  total: number;
  sheetVersion: number;
  items: EvidenceItem[];
  nextCursor: string | null;
}
