// Runtime checks for the Full Tag reads (api-sprint-03 §5.2, §5.3). Objects are rebuilt from the
// schema's fields only (NFR-052), so the export file holds exactly `full-tag-labels/v1`.
import { arr, bool, num, obj, oneOf, ResponseShapeError, str, type Obj } from '@/lib/api/parse';
import { ENDINGS, SIDES } from '@/lib/tagging/types';
import {
  FAULT_KINDS,
  type EventLabel,
  type LabelDocument,
  type LabelOutcome,
  type LabelSaved,
  type LabelSession,
  type SavedRally,
} from './types';

const SLOT_RE = /^[AB][12]$/;

function frame(o: Obj, key: string, path: string): number {
  const v = num(o, key, path);
  if (!Number.isInteger(v) || v < 0) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

function slot(value: unknown, path: string): string {
  if (typeof value !== 'string' || !SLOT_RE.test(value)) throw new ResponseShapeError(path);
  return value;
}

function outcome(value: unknown, path: string): LabelOutcome {
  const o = obj(value, path);
  return {
    ending: oneOf(o, 'ending', ENDINGS, path),
    winning_side: o.winning_side === null ? null : oneOf(o, 'winning_side', SIDES, path),
    responsible_player: o.responsible_player === null || o.responsible_player === undefined ? null : slot(o.responsible_player, `${path}.responsible_player`),
    fault_kind: o.fault_kind === null || o.fault_kind === undefined ? null : oneOf(o, 'fault_kind', FAULT_KINDS, path),
  };
}

function event(value: unknown, path: string): EventLabel {
  const o = obj(value, path);
  const type = oneOf(o, 'type', ['hit', 'bounce'] as const, path);
  if (type === 'hit') {
    const f = o.facets === undefined ? {} : obj(o.facets, `${path}.facets`);
    const facets: Record<string, string> = {};
    for (const k of Object.keys(f)) facets[k] = str(f, k, `${path}.facets`);
    return { type, frame: frame(o, 'frame', path), hitter: slot(o.hitter, `${path}.hitter`), facets };
  }
  let xy: [number, number] | null = null;
  if (o.court_xy_m !== null && o.court_xy_m !== undefined) {
    const v = arr(o, 'court_xy_m', path);
    if (v.length !== 2 || !v.every((n) => typeof n === 'number' && Number.isFinite(n))) throw new ResponseShapeError(`${path}.court_xy_m`);
    xy = [v[0] as number, v[1] as number];
  }
  return { type, frame: frame(o, 'frame', path), visible: bool(o, 'visible', path), court_xy_m: xy };
}

function rally(value: unknown, path: string): SavedRally {
  const o = obj(value, path);
  return {
    id: str(o, 'id', path),
    start_frame: frame(o, 'start_frame', path),
    end_frame: frame(o, 'end_frame', path),
    outcome: outcome(o.outcome, `${path}.outcome`),
    events: arr(o, 'events', path).map((e, i) => event(e, `${path}.events[${i}]`)),
  };
}

export function parseLabelDocument(value: unknown, path = 'document'): LabelDocument {
  const o = obj(value, path);
  if (o.schema !== 'full-tag-labels/v1') throw new ResponseShapeError(`${path}.schema`);
  return {
    schema: 'full-tag-labels/v1',
    clip: str(o, 'clip', path),
    fps: num(o, 'fps', path),
    frame_count: frame(o, 'frame_count', path),
    players: arr(o, 'players', path).map((p, i) => slot(p, `${path}.players[${i}]`)),
    rallies: arr(o, 'rallies', path).map((r, i) => rally(r, `${path}.rallies[${i}]`)),
  };
}

export function parseLabelSession(value: unknown): LabelSession {
  const o = obj(value, 'label');
  const fps = num(o, 'fps', 'label');
  if (fps <= 0) throw new ResponseShapeError('label.fps');
  return {
    matchId: str(o, 'match_id', 'label'),
    fps,
    frameCount: frame(o, 'frame_count', 'label'),
    players: arr(o, 'players', 'label').map((p, i) => slot(p, `label.players[${i}]`)),
    version: frame(o, 'version', 'label'),
    document: parseLabelDocument(o.document, 'label.document'),
  };
}

export function parseLabelSaved(value: unknown): LabelSaved {
  const o = obj(value, 'saved');
  return { version: frame(o, 'version', 'saved'), rallies: frame(o, 'rallies', 'saved'), events: frame(o, 'events', 'saved') };
}
