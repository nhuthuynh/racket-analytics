// Runtime checks for the stats and evidence bodies (api-sprint-03 §2.1, §3.1). Like the other
// parsers, every object is rebuilt from an allowlist, so a key the contract does not list never
// reaches the page (NFR-052). A metric of a unit the web has no layout for is dropped.
import { arr, bool, num, obj, oneOf, ResponseShapeError, str, type Obj } from '@/lib/api/parse';
import { isPublicId } from '@/lib/api/types';
import { SIDES, type Side } from '@/lib/tagging/types';
import {
  ENDING_ROWS,
  KIND_OF_UNIT,
  RUN_BUCKETS,
  type EndingRow,
  type Evidence,
  type EvidenceItem,
  type Metric,
  type MetricEntry,
  type MixSide,
  type PerGameSide,
  type ProportionSide,
  type RunBucket,
  type RunsSide,
  type Share,
  type Stats,
  type TurnsSide,
} from './types';

const METRIC_ID_RE = /^AN-\d{2}$/;
const SLOT_RE = /^[AB][12]$/;

function nullableNum(o: Obj, key: string, path: string): number | null {
  return o[key] === null ? null : num(o, key, path);
}

function count(o: Obj, key: string, path: string): number {
  const v = num(o, key, path);
  if (!Number.isInteger(v) || v < 0) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

function parseEntry(value: unknown, path: string): MetricEntry {
  const o = obj(value, path);
  let min: MetricEntry['min_sample'] = null;
  if (o.min_sample !== null) {
    const m = obj(o.min_sample, `${path}.min_sample`);
    min = { unit: str(m, 'unit', `${path}.min_sample`), n: count(m, 'n', `${path}.min_sample`) };
  }
  return {
    id: str(o, 'id', path),
    version: str(o, 'version', path),
    name: str(o, 'name', path),
    definition: str(o, 'definition', path),
    unit: str(o, 'unit', path),
    min_sample: min,
    status: str(o, 'status', path),
  };
}

function proportion(value: unknown, path: string): ProportionSide {
  const o = obj(value, path);
  return {
    k: count(o, 'k', path),
    n: count(o, 'n', path),
    value: nullableNum(o, 'value', path),
    ci_low: nullableNum(o, 'ci_low', path),
    ci_high: nullableNum(o, 'ci_high', path),
    low_sample: bool(o, 'low_sample', path),
    fault_type_not_tagged: o.fault_type_not_tagged === undefined ? null : count(o, 'fault_type_not_tagged', path),
  };
}

function turns(value: unknown, path: string): TurnsSide {
  const o = obj(value, path);
  return {
    points: count(o, 'points', path),
    turns: count(o, 'turns', path),
    value: nullableNum(o, 'value', path),
    low_sample: bool(o, 'low_sample', path),
  };
}

function perGame(value: unknown, path: string): PerGameSide {
  const o = obj(value, path);
  const raw = obj(o.by_player, `${path}.by_player`);
  const byPlayer: Record<string, number> = {};
  for (const slot of Object.keys(raw)) {
    if (!SLOT_RE.test(slot)) throw new ResponseShapeError(`${path}.by_player`);
    byPlayer[slot] = count(raw, slot, `${path}.by_player`);
  }
  return {
    count: count(o, 'count', path),
    games: count(o, 'games', path),
    value: nullableNum(o, 'value', path),
    by_player: byPlayer,
    player_not_tagged: count(o, 'player_not_tagged', path),
    low_sample: bool(o, 'low_sample', path),
  };
}

function runs(value: unknown, path: string): RunsSide {
  const o = obj(value, path);
  const h = obj(o.histogram, `${path}.histogram`);
  const histogram = Object.fromEntries(RUN_BUCKETS.map((b) => [b, count(h, b, `${path}.histogram`)])) as Record<RunBucket, number>;
  return {
    longest: count(o, 'longest', path),
    longest_by_game: arr(o, 'longest_by_game', path).map((v, i) => count({ v }, 'v', `${path}.longest_by_game[${i}]`)),
    histogram,
    n: count(o, 'n', path),
    low_sample: bool(o, 'low_sample', path),
  };
}

function share(value: unknown, path: string): Share {
  const o = obj(value, path);
  return {
    k: count(o, 'k', path),
    value: nullableNum(o, 'value', path),
    ci_low: nullableNum(o, 'ci_low', path),
    ci_high: nullableNum(o, 'ci_high', path),
  };
}

function mix(value: unknown, path: string): MixSide {
  const o = obj(value, path);
  const c = obj(o.counts, `${path}.counts`);
  const s = obj(o.shares, `${path}.shares`);
  const rows = <T>(f: (row: EndingRow) => T) => Object.fromEntries(ENDING_ROWS.map((r) => [r, f(r)])) as Record<EndingRow, T>;
  return {
    n: count(o, 'n', path),
    counts: rows((r) => count(c, r, `${path}.counts`)),
    shares: rows((r) => share(s[r], `${path}.shares.${r}`)),
    low_sample: bool(o, 'low_sample', path),
  };
}

function parseMetric(id: string, value: unknown, path: string): Metric | null {
  const o = obj(value, path);
  const entry = parseEntry(o.entry, `${path}.entry`);
  if (entry.id !== id) throw new ResponseShapeError(`${path}.entry.id`);
  const kind = KIND_OF_UNIT[entry.unit];
  switch (kind) {
    case 'proportion':
      return { kind, entry, A: proportion(o.A, `${path}.A`), B: proportion(o.B, `${path}.B`) };
    case 'turns':
      return { kind, entry, A: turns(o.A, `${path}.A`), B: turns(o.B, `${path}.B`) };
    case 'perGame':
      return { kind, entry, A: perGame(o.A, `${path}.A`), B: perGame(o.B, `${path}.B`) };
    case 'runs':
      return { kind, entry, A: runs(o.A, `${path}.A`), B: runs(o.B, `${path}.B`) };
    case 'mix':
      return { kind, entry, A: mix(o.A, `${path}.A`), B: mix(o.B, `${path}.B`) };
    default:
      return null; // a unit this web version has no card for: not shown
  }
}

export function parseStats(value: unknown): Stats {
  const o = obj(value, 'stats');
  const rule = obj(o.low_sample_rule, 'stats.low_sample_rule');
  const raw = obj(o.metrics, 'stats.metrics');
  const metrics: Metric[] = [];
  for (const id of Object.keys(raw).sort()) {
    if (!METRIC_ID_RE.test(id)) throw new ResponseShapeError('stats.metrics');
    const m = parseMetric(id, raw[id], `stats.metrics.${id}`);
    if (m) metrics.push(m);
  }
  return {
    matchId: str(o, 'match_id', 'stats'),
    sheetVersion: num(o, 'sheet_version', 'stats'),
    rulesVersion: str(o, 'rules_version', 'stats'),
    metricDefVersion: str(o, 'metric_def_version', 'stats'),
    unofficial: bool(o, 'unofficial', 'stats'),
    label: str(o, 'label', 'stats'),
    lowSampleRule: { maxIntervalWidth: num(rule, 'max_interval_width', 'stats.low_sample_rule') },
    metrics,
  };
}

function parseItem(value: unknown, path: string): EvidenceItem {
  const o = obj(value, path);
  const rallyId = str(o, 'rally_id', path);
  if (!isPublicId(rallyId)) throw new ResponseShapeError(`${path}.rally_id`);
  return {
    number: count(o, 'number', path),
    rally_id: rallyId,
    game: count(o, 'game', path),
    start_ms: count(o, 'start_ms', path),
    end_ms: count(o, 'end_ms', path),
  };
}

export function parseEvidence(value: unknown): Evidence {
  const o = obj(value, 'evidence');
  const metricId = str(o, 'metric_id', 'evidence');
  if (!METRIC_ID_RE.test(metricId)) throw new ResponseShapeError('evidence.metric_id');
  const side: Side = oneOf(o, 'side', SIDES, 'evidence');
  return {
    metricId,
    side,
    total: count(o, 'total', 'evidence'),
    sheetVersion: num(o, 'sheet_version', 'evidence'),
    items: arr(o, 'items', 'evidence').map((item, i) => parseItem(item, `evidence.items[${i}]`)),
    nextCursor: o.next_cursor === null ? null : str(o, 'next_cursor', 'evidence'),
  };
}
