// Display helpers for D-01 and E-01 (flows-sprint-03 §0, §2, §3; ST-048, ST-047). Pure.
// Every number a card shows is printed in words next to its sample size (NFR-034); a value
// without n is never printed. Metric names and definitions come from the API (FR-102); the
// words here are the design's card lines (flows-sprint-03 §2 table, accepted by the coach, R3-2).
import { formatClock } from '@/lib/tagging/view';
import type { Side } from '@/lib/tagging/types';
import {
  ENDING_ROWS,
  RUN_BUCKETS,
  type EndingRow,
  type EvidenceItem,
  type Metric,
  type MetricEntry,
  type MixSide,
  type RunsSide,
} from './types';

export const DASH = '—';

/** "57%": whole percentages (flows-sprint-03 §0). */
export function pct(v: number | null): string {
  return v === null ? DASH : `${Math.round(v * 100)}%`;
}

/** Rates with at most one decimal and no trailing zero: "2", "1.3". */
export function rate(v: number | null): string {
  if (v === null) return DASH;
  return String(Math.round(v * 10) / 10);
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

function range(lo: number | null, hi: number | null): string | null {
  return lo === null || hi === null ? null : `range ${pct(lo)} to ${pct(hi)}`;
}

export interface SideSummary {
  /** The big value: "57%", "2", "3 points", "n = 6 rallies", or "—" when n = 0. */
  main: string;
  /** Supporting lines, always shown. */
  lines: string[];
}

const identity = (slot: string): string => slot;

/** What one side block prints (flows-sprint-03 §2 "What each side block prints"). */
export function sideSummary(metric: Metric, side: Side, nickname: (slot: string) => string = identity): SideSummary {
  switch (metric.kind) {
    case 'proportion': {
      const s = metric[side];
      if (s.n === 0) return { main: DASH, lines: ['No rallies yet · n = 0'] };
      // fault_type_not_tagged is the serve-fault metric's own field (api-sprint-03 §2.1, AN-05).
      const noun = s.fault_type_not_tagged === null ? 'rallies' : 'serves';
      const parts = [`${s.k} of ${s.n} ${noun}`, `n = ${s.n}`, range(s.ci_low, s.ci_high)].filter(Boolean);
      const lines = [parts.join(' · ')];
      if (s.fault_type_not_tagged) lines.push(`fault type not tagged in ${plural(s.fault_type_not_tagged, 'rally', 'rallies')}`);
      return { main: pct(s.value), lines };
    }
    case 'turns': {
      const s = metric[side];
      if (s.turns === 0) return { main: DASH, lines: ['No service turns yet · n = 0'] };
      return { main: rate(s.value), lines: [`${plural(s.points, 'point', 'points')} in ${plural(s.turns, 'service turn', 'service turns')} · n = ${s.turns}`] };
    }
    case 'perGame': {
      const s = metric[side];
      if (s.games === 0) return { main: DASH, lines: ['No games yet · n = 0'] };
      const lines = [`${plural(s.count, 'unforced error', 'unforced errors')} in ${plural(s.games, 'game', 'games')}`];
      const players = Object.keys(s.by_player)
        .sort()
        .map((slot) => `${nickname(slot)} ${s.by_player[slot] ?? 0}`);
      if (players.length) lines.push(players.join(' · '));
      if (s.player_not_tagged > 0) lines.push(`player not tagged in ${plural(s.player_not_tagged, 'rally', 'rallies')}`);
      return { main: rate(s.value), lines };
    }
    case 'runs': {
      const s = metric[side];
      if (s.n === 0) return { main: DASH, lines: ['No runs yet · n = 0'] };
      return { main: plural(s.longest, 'point', 'points'), lines: [`n = ${plural(s.n, 'run', 'runs')}`] };
    }
    case 'mix': {
      const s = metric[side];
      if (s.n === 0) return { main: DASH, lines: ['No rallies yet · n = 0'] };
      return { main: `n = ${plural(s.n, 'rally', 'rallies')}`, lines: [] };
    }
  }
}

/** Whether a side has anything behind its number (n > 0); no "Show me" otherwise (§2). */
export function sideHasSample(metric: Metric, side: Side): boolean {
  switch (metric.kind) {
    case 'proportion':
    case 'runs':
    case 'mix':
      return metric[side].n > 0;
    case 'turns':
      return metric[side].turns > 0;
    case 'perGame':
      return metric[side].games > 0;
  }
}

export function lowSample(metric: Metric, side: Side): boolean {
  return metric[side].low_sample;
}

/** How many rallies "Show me" lists (the snapshot's rallies behind the number), or null (AN-06 runs). */
export function showMeCount(metric: Metric, side: Side): number | null {
  switch (metric.kind) {
    case 'proportion': {
      const s = metric[side];
      return s.fault_type_not_tagged === null ? s.n : s.k;
    }
    case 'turns':
      return metric[side].points;
    case 'perGame':
      return metric[side].count;
    case 'runs':
      return null;
    case 'mix':
      return metric[side].n;
  }
}

/** The visible words of "Show me" (flows-sprint-03 §2): "Show me the 7 rallies". */
export function showMeText(metric: Metric, side: Side): string {
  const c = showMeCount(metric, side);
  if (c === null) return "Show me the runs' rallies";
  if (c === 0) return 'Show me the rallies';
  return `Show me the ${plural(c, 'rally', 'rallies')}`;
}

const UNIT_WORDS: Readonly<Record<string, string>> = {
  rallies: 'rallies',
  service_turns: 'service turns',
  games: 'games',
};

/** Units whose values carry a Wilson range (so the range half of rule 0.3 applies). */
const RANGED_UNITS = new Set(['proportion', 'proportion_mix']);

/** "Low sample: fewer than 20 rallies, or the range is wider than 30 points. Treat it as a rough guide." */
export function lowSampleReason(entry: MetricEntry, rule: { maxIntervalWidth: number }): string {
  const min = entry.min_sample;
  if (!min) return '';
  const unit = UNIT_WORDS[min.unit] ?? min.unit.replace(/_/g, ' ');
  const ranged = RANGED_UNITS.has(entry.unit)
    ? `, or the range is wider than ${Math.round(rule.maxIntervalWidth * 100)} points`
    : '';
  return `Low sample: fewer than ${min.n} ${unit}${ranged}. Treat it as a rough guide.`;
}

/** "Smallest sample we trust: 20 rallies." or, for a descriptive metric, why it is not flagged. */
export function minSampleLine(entry: MetricEntry): string {
  const min = entry.min_sample;
  if (!min) return 'Not flagged: this describes the match, it is not an estimate.';
  return `Smallest sample we trust: ${min.n} ${UNIT_WORDS[min.unit] ?? min.unit.replace(/_/g, ' ')}.`;
}

export function versionLine(entry: MetricEntry): string {
  return entry.status === 'verified'
    ? `Definition version ${entry.version}, checked by our coach and verified.`
    : `Definition version ${entry.version}, checked by our coach.`;
}

const ROW_WORDS: Readonly<Record<EndingRow, string>> = {
  winner: 'Winners',
  unforced_error: 'Unforced errors',
  forced_error: 'Forced errors',
  fault: 'Faults',
};

export interface BarRow {
  key: string;
  text: string;
  /** 0..1, for the bar's width only; the text carries the number. */
  fraction: number;
}

/** AN-07 rows: "Winners: 2 (33%, range 10% to 70%)". */
export function mixRows(s: MixSide): BarRow[] {
  return ENDING_ROWS.map((row) => {
    const share = s.shares[row];
    const r = range(share.ci_low, share.ci_high);
    const detail = share.value === null ? '' : ` (${pct(share.value)}${r ? `, ${r}` : ''})`;
    return { key: row, text: `${ROW_WORDS[row]}: ${s.counts[row]}${detail}`, fraction: s.n ? s.counts[row] / s.n : 0 };
  });
}

/** AN-06 histogram rows: "1 point: 1 run" … "5 or more: 0 runs". */
export function runRows(s: RunsSide): BarRow[] {
  const most = Math.max(1, ...RUN_BUCKETS.map((b) => s.histogram[b]));
  return RUN_BUCKETS.map((b) => {
    const label = b === '5+' ? '5 or more' : b === '1' ? '1 point' : `${b} points`;
    const n = s.histogram[b];
    return { key: b, text: `${label}: ${plural(n, 'run', 'runs')}`, fraction: n / most };
  });
}

/** "Rally 3 · game 1 · 0:12" (flows-sprint-03 §3). */
export function evidenceLabel(item: EvidenceItem): string {
  return `Rally ${item.number} · game ${item.game} · ${formatClock(item.start_ms)}`;
}
