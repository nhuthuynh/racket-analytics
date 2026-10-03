// Runtime checks for API responses. The client builds its own objects from an allowlist of
// fields, so anything the contract does not list is dropped (NFR-052, defence in depth).
import {
  MATCH_FORMATS,
  MATCH_STATUSES,
  type DevUser,
  type Match,
  type MatchFormat,
  type MatchStatus,
  type Me,
  type MediaFacts,
} from './types';

export class ResponseShapeError extends Error {
  constructor(path: string) {
    super(`unexpected response shape at ${path}`);
    this.name = 'ResponseShapeError';
  }
}

type Obj = Record<string, unknown>;

function obj(value: unknown, path: string): Obj {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ResponseShapeError(path);
  }
  return value as Obj;
}

function str(o: Obj, key: string, path: string): string {
  const v = o[key];
  if (typeof v !== 'string') throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

function num(o: Obj, key: string, path: string): number {
  const v = o[key];
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

function bool(o: Obj, key: string, path: string): boolean {
  const v = o[key];
  if (typeof v !== 'boolean') throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

function oneOf<T extends string>(o: Obj, key: string, allowed: readonly T[], path: string): T {
  const v = o[key];
  if (typeof v !== 'string' || !(allowed as readonly string[]).includes(v)) {
    throw new ResponseShapeError(`${path}.${key}`);
  }
  return v as T;
}

function arr(o: Obj, key: string, path: string): unknown[] {
  const v = o[key];
  if (!Array.isArray(v)) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

export function parseMedia(value: unknown, path = 'media'): MediaFacts {
  const o = obj(value, path);
  return {
    duration_ms: num(o, 'duration_ms', path),
    fps: num(o, 'fps', path),
    width: num(o, 'width', path),
    height: num(o, 'height', path),
    has_audio: bool(o, 'has_audio', path),
    vfr: bool(o, 'vfr', path),
    container: str(o, 'container', path),
    video_codec: str(o, 'video_codec', path),
  };
}

export function parseMatch(value: unknown, path = 'match'): Match {
  const o = obj(value, path);
  return {
    id: str(o, 'id', path),
    title: str(o, 'title', path),
    format: oneOf<MatchFormat>(o, 'format', MATCH_FORMATS, path),
    status: oneOf<MatchStatus>(o, 'status', MATCH_STATUSES, path),
    media: o.media === null || o.media === undefined ? null : parseMedia(o.media, `${path}.media`),
    created_at: str(o, 'created_at', path),
    updated_at: str(o, 'updated_at', path),
  };
}

export function parseMatchList(value: unknown): Match[] {
  const o = obj(value, 'list');
  return arr(o, 'items', 'list').map((item, i) => parseMatch(item, `list.items[${i}]`));
}

export function parseDevUsers(value: unknown): DevUser[] {
  const o = obj(value, 'users');
  return arr(o, 'items', 'users').map((item, i) => {
    const u = obj(item, `users.items[${i}]`);
    return {
      username: str(u, 'username', `users.items[${i}]`),
      display_name: str(u, 'display_name', `users.items[${i}]`),
    };
  });
}

export function parseMe(value: unknown): Me {
  const o = obj(value, 'me');
  return { id: str(o, 'id', 'me'), display_name: str(o, 'display_name', 'me') };
}
