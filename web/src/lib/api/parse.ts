// Runtime checks for API responses. The client builds its own objects from an allowlist of
// fields, so anything the contract does not list is dropped (NFR-052, defence in depth).
import {
  MATCH_FORMATS,
  MATCH_STATUSES,
  REJECTION_CODES,
  SLOTS,
  type Participant,
  type Rejection,
  type UploadPolicy,
  type UploadState,
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

export type Obj = Record<string, unknown>;

export function obj(value: unknown, path: string): Obj {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ResponseShapeError(path);
  }
  return value as Obj;
}

export function str(o: Obj, key: string, path: string): string {
  const v = o[key];
  if (typeof v !== 'string') throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

export function num(o: Obj, key: string, path: string): number {
  const v = o[key];
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

export function bool(o: Obj, key: string, path: string): boolean {
  const v = o[key];
  if (typeof v !== 'boolean') throw new ResponseShapeError(`${path}.${key}`);
  return v;
}

export function oneOf<T extends string>(o: Obj, key: string, allowed: readonly T[], path: string): T {
  const v = o[key];
  if (typeof v !== 'string' || !(allowed as readonly string[]).includes(v)) {
    throw new ResponseShapeError(`${path}.${key}`);
  }
  return v as T;
}

export function arr(o: Obj, key: string, path: string): unknown[] {
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

const RESUME_URL_RE = /^\/api\/uploads\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function nullableStr(o: Obj, key: string, path: string): string | null {
  return o[key] === null || o[key] === undefined ? null : str(o, key, path);
}

function parseParticipant(value: unknown, path: string): Participant {
  const o = obj(value, path);
  return {
    slot: oneOf(o, 'slot', SLOTS, path),
    nickname: str(o, 'nickname', path),
    is_me: bool(o, 'is_me', path),
  };
}

function parseUpload(value: unknown, path: string): UploadState {
  const o = obj(value, path);
  const resumeUrl = str(o, 'resume_url', path);
  if (!RESUME_URL_RE.test(resumeUrl)) throw new ResponseShapeError(`${path}.resume_url`);
  const head = nullableStr(o, 'head_sha256', path);
  if (head !== null && !/^[0-9a-f]{64}$/.test(head)) throw new ResponseShapeError(`${path}.head_sha256`);
  return {
    state: oneOf(o, 'state', ['receiving', 'expired'] as const, path),
    offset: num(o, 'offset', path),
    length: num(o, 'length', path),
    expiresAt: str(o, 'expires_at', path),
    resumeUrl,
    fileName: nullableStr(o, 'file_name', path),
    fileLastModifiedMs:
      o.file_last_modified_ms === null || o.file_last_modified_ms === undefined
        ? null
        : num(o, 'file_last_modified_ms', path),
    headSha256: head,
  };
}

function parseRejection(value: unknown, path: string): Rejection {
  const o = obj(value, path);
  return { code: oneOf(o, 'code', REJECTION_CODES, path), at: str(o, 'at', path) };
}

export function parseUploadPolicy(value: unknown): UploadPolicy {
  const o = obj(value, 'policy');
  return {
    maxBytes: num(o, 'max_bytes', 'policy'),
    maxDurationMs: num(o, 'max_duration_ms', 'policy'),
    chunkMinBytes: num(o, 'chunk_min_bytes', 'policy'),
    chunkMaxBytes: num(o, 'chunk_max_bytes', 'policy'),
    expiresAfterS: num(o, 'expires_after_s', 'policy'),
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
    played_on: nullableStr(o, 'played_on', path),
    participants:
      o.participants === undefined
        ? []
        : arr(o, 'participants', path).map((p, i) => parseParticipant(p, `${path}.participants[${i}]`)),
    upload: o.upload === null || o.upload === undefined ? null : parseUpload(o.upload, `${path}.upload`),
    rejection:
      o.rejection === null || o.rejection === undefined ? null : parseRejection(o.rejection, `${path}.rejection`),
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
  return {
    id: str(o, 'id', 'me'),
    display_name: o.display_name === null ? null : str(o, 'display_name', 'me'),
  };
}

export function parseExchange(value: unknown): { newAccount: boolean } {
  const o = obj(value, 'exchange');
  return { newAccount: bool(o, 'new_account', 'exchange') };
}
