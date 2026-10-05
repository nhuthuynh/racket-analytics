// Wire → typed values for the Sprint 2 routes (ST-027..ST-037). Fails closed: any unexpected
// shape is a ResponseShapeError, which the client turns into `invalid_response` (ADR 0014).
import { ResponseShapeError } from '@/lib/api/parse';
import { isPublicId, SLOTS, type ParticipantSlot } from '@/lib/api/types';
import {
  ENDINGS,
  HISTORY_KINDS,
  MAX_MEDIA_TTL_S,
  SIDES,
  type Ending,
  type HistoryItem,
  type RallyMedia,
  type ScoreSheet,
  type SheetGame,
  type SheetRow,
  type Side,
  type Versioned,
} from './types';

type Obj = Record<string, unknown>;
const CALL_RE = /^\d{1,2}-\d{1,2}(-[12])?$/;

function obj(value: unknown, path: string): Obj {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new ResponseShapeError(path);
  return value as Obj;
}
function str(o: Obj, key: string, path: string): string {
  const v = o[key];
  if (typeof v !== 'string') throw new ResponseShapeError(`${path}.${key}`);
  return v;
}
function int(o: Obj, key: string, path: string, min = 0): number {
  const v = o[key];
  if (typeof v !== 'number' || !Number.isInteger(v) || v < min) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}
function oneOrNull<T extends string>(o: Obj, key: string, allowed: readonly T[], path: string): T | null {
  const v = o[key] ?? null;
  if (v === null) return null;
  if (typeof v !== 'string' || !(allowed as readonly string[]).includes(v)) throw new ResponseShapeError(`${path}.${key}`);
  return v as T;
}
function one<T extends string>(o: Obj, key: string, allowed: readonly T[], path: string): T {
  const v = oneOrNull(o, key, allowed, path);
  if (v === null) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}
function callOrNull(o: Obj, key: string, path: string): string | null {
  const v = o[key] ?? null;
  if (v === null) return null;
  if (typeof v !== 'string' || !CALL_RE.test(v)) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}
function publicId(o: Obj, key: string, path: string): string {
  const v = str(o, key, path);
  if (!isPublicId(v)) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}
function nullablePublicId(o: Obj, key: string, path: string): string | null {
  return (o[key] ?? null) === null ? null : publicId(o, key, path);
}

function parseRow(value: unknown, path: string): SheetRow {
  const o = obj(value, path);
  const marker = o.marker ?? null;
  if (marker !== null && marker !== 'needs_decision') throw new ResponseShapeError(`${path}.marker`);
  const corrected = o.corrected_by_user;
  if (typeof corrected !== 'boolean') throw new ResponseShapeError(`${path}.corrected_by_user`);
  const fault = o.fault_kind ?? null;
  if (fault !== null && (typeof fault !== 'string' || !/^[a-z_]{1,32}$/.test(fault))) {
    throw new ResponseShapeError(`${path}.fault_kind`);
  }
  return {
    rally_id: publicId(o, 'rally_id', path),
    number: int(o, 'number', path, 1),
    game: int(o, 'game', path, 1),
    start_ms: int(o, 'start_ms', path),
    end_ms: int(o, 'end_ms', path),
    serving_side: oneOrNull<Side>(o, 'serving_side', SIDES, path),
    score_before: callOrNull(o, 'score_before', path),
    score_after: callOrNull(o, 'score_after', path),
    winning_side: oneOrNull<Side>(o, 'winning_side', SIDES, path),
    ending: one<Ending>(o, 'ending', ENDINGS, path),
    responsible_player: oneOrNull<ParticipantSlot>(o, 'responsible_player', SLOTS, path),
    fault_kind: fault as string | null,
    marker: marker as SheetRow['marker'],
    corrected_by_user: corrected,
  };
}

function parseGame(value: unknown, path: string): SheetGame {
  const o = obj(value, path);
  return {
    number: int(o, 'number', path, 1),
    first_serving_side: oneOrNull<Side>(o, 'first_serving_side', SIDES, path),
    winner: oneOrNull<Side>(o, 'winner', SIDES, path),
  };
}

export function parseSheet(value: unknown, path = 'sheet'): ScoreSheet {
  const o = obj(value, path);
  if (typeof o.unofficial !== 'boolean') throw new ResponseShapeError(`${path}.unofficial`);
  const rows = o.rows;
  if (!Array.isArray(rows)) throw new ResponseShapeError(`${path}.rows`);
  const sheet: ScoreSheet = {
    rules_version: str(o, 'rules_version', path),
    unofficial: o.unofficial,
    label: str(o, 'label', path),
    rows: rows.map((r, i) => parseRow(r, `${path}.rows[${i}]`)),
  };
  if (Array.isArray(o.games)) sheet.games = o.games.map((g, i) => parseGame(g, `${path}.games[${i}]`));
  if ('match_winner' in o) sheet.match_winner = oneOrNull<Side>(o, 'match_winner', SIDES, path);
  return sheet;
}

/** GET sheet: the version comes from the body, else the ETag, else it is unknown (null). */
export function parseSheetResponse(value: unknown, etag: string | null): { version: number | null; sheet: ScoreSheet } {
  const o = obj(value, 'sheet');
  const sheet = parseSheet(o);
  if (typeof o.version === 'number' && Number.isInteger(o.version) && o.version >= 0) return { version: o.version, sheet };
  const m = etag ? /^(?:W\/)?"?(\d{1,9})"?$/.exec(etag.trim()) : null;
  return { version: m ? Number(m[1]) : null, sheet };
}

export function parseVersioned(value: unknown): Versioned {
  const o = obj(value, 'command');
  return { version: int(o, 'version', 'command'), sheet: parseSheet(o.sheet) };
}

export function parseTagged(value: unknown): Versioned & { rallyId: string } {
  const o = obj(value, 'tag');
  return { ...parseVersioned(o), rallyId: publicId(o, 'rally_id', 'tag') };
}

function scalarOrNull(o: Obj, key: string, path: string): string | number | boolean | null {
  const v = o[key] ?? null;
  if (v === null || typeof v === 'boolean' || (typeof v === 'number' && Number.isInteger(v))) return v as never;
  if (typeof v === 'string' && /^[A-Za-z0-9_-]{1,32}$/.test(v)) return v;
  throw new ResponseShapeError(`${path}.${key}`);
}

export function parseHistory(value: unknown): HistoryItem[] {
  const o = obj(value, 'history');
  const items = o.items;
  if (!Array.isArray(items)) throw new ResponseShapeError('history.items');
  return items.map((raw, i) => {
    const path = `history.items[${i}]`;
    const it = obj(raw, path);
    const field = it.field ?? null;
    if (field !== null && (typeof field !== 'string' || !/^[a-z_]{1,32}$/.test(field))) {
      throw new ResponseShapeError(`${path}.field`);
    }
    const num = it.rally_number ?? null;
    return {
      id: publicId(it, 'id', path),
      kind: one(it, 'kind', HISTORY_KINDS, path),
      rally_id: nullablePublicId(it, 'rally_id', path),
      rally_number: num === null ? null : int(it, 'rally_number', path, 1),
      field: field as string | null,
      old_value: scalarOrNull(it, 'old_value', path),
      new_value: scalarOrNull(it, 'new_value', path),
      undoes: nullablePublicId(it, 'undoes', path),
      at: str(it, 'at', path),
    };
  });
}

const LOOPBACK = new Set(['localhost', '127.0.0.1', '[::1]']);

/** A media URL is a same-origin path or https (http only on loopback, the native dev stack). */
export function isSafeMediaUrl(url: string): boolean {
  if (url.startsWith('/') && !url.startsWith('//')) return true;
  try {
    const u = new URL(url);
    return u.protocol === 'https:' || (u.protocol === 'http:' && LOOPBACK.has(u.hostname));
  } catch {
    return false;
  }
}

export function parseRallyMedia(value: unknown): RallyMedia {
  const o = obj(value, 'media');
  const url = str(o, 'url', 'media');
  if (!isSafeMediaUrl(url)) throw new ResponseShapeError('media.url');
  const ttl = int(o, 'expires_in_s', 'media', 1);
  if (ttl > MAX_MEDIA_TTL_S) throw new ResponseShapeError('media.expires_in_s');
  return { url, expiresInS: ttl, startMs: int(o, 'start_ms', 'media') };
}
