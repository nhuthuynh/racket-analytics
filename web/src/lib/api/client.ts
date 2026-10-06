// Typed client for docs/architecture/api-sprint-00.md (ST-010).
// Browser: baseUrl "/api" (same origin, rewritten to the API; the HttpOnly session cookie goes
// along automatically). Server components: baseUrl API_INTERNAL_URL plus the incoming cookie.
// Authorisation is enforced by the API only; nothing here decides access [AQS/SEC-03].
import {
  parseDevUsers,
  parseExchange,
  parseMatch,
  parseMatchList,
  parseMe,
  parseUploadPolicy,
  ResponseShapeError,
} from './parse';
import {
  parseHistory,
  parseRallyMedia,
  parseSheetResponse,
  parseTagged,
  parseVersioned,
} from '@/lib/tagging/parse';
import type {
  CorrectableField,
  CorrectionValue,
  HistoryItem,
  RallyMedia,
  ScoreSheet,
  Side,
  TagInput,
  Versioned,
} from '@/lib/tagging/types';
import {
  API_ERROR_CODES,
  FIELD_ERROR_CODES,
  isLinkToken,
  isPublicId,
  type ApiErrorCode,
  type ApiFieldError,
  type FieldErrorCode,
  type DevUser,
  type Match,
  type Me,
  type NewMatch,
  type UploadPolicy,
} from './types';

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly supportRef: string | null;
  /** Field errors of a 422, from the closed code list (api-sprint-01 §1.1). */
  readonly fields: readonly ApiFieldError[];
  /** RFC 3339 UTC time after which a 429 can be retried, or null. */
  readonly retryAt: string | null;

  constructor(
    status: number,
    code: ApiErrorCode,
    supportRef: string | null = null,
    extra: { fields?: readonly ApiFieldError[]; retryAt?: string | null } = {},
  ) {
    super(`API error ${status} ${code}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.supportRef = supportRef;
    this.fields = extra.fields ?? [];
    this.retryAt = extra.retryAt ?? null;
  }
}

const RETRY_AT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const FIELD_PATH_RE = /^[a-z_]+(\.[A-Za-z0-9_]+)*$/;

function fieldErrorsFrom(raw: unknown): ApiFieldError[] {
  if (!Array.isArray(raw)) return [];
  const out: ApiFieldError[] = [];
  for (const item of raw) {
    const f = item as { field?: unknown; code?: unknown } | null;
    if (typeof f?.code !== 'string' || !(FIELD_ERROR_CODES as readonly string[]).includes(f.code)) continue;
    const field = typeof f.field === 'string' && FIELD_PATH_RE.test(f.field) ? f.field : null;
    out.push({ field, code: f.code as FieldErrorCode });
  }
  return out;
}

export interface ApiClientOptions {
  /** "/api" in the browser; the internal API origin on the server. No trailing slash. */
  baseUrl: string;
  fetch?: typeof fetch;
  /** Extra request headers, e.g. the forwarded `cookie` on the server. */
  headers?: Record<string, string>;
}

const SUPPORT_REF_RE = /^ref_[0-9a-f]{16}$/;

async function toApiError(response: Response): Promise<ApiError> {
  let code: ApiErrorCode = 'unknown';
  let supportRef: string | null = null;
  let fields: ApiFieldError[] = [];
  let retryAt: string | null = null;
  try {
    const body: unknown = await response.json();
    type Envelope = { code?: unknown; support_ref?: unknown; fields?: unknown; retry_at?: unknown };
    // api-sprint-00 §3 envelope {"error": {...}}; the Sprint 2 harness also reads a top-level
    // {"code": ...} (tagcontract.py), so both are accepted until api-sprint-02.md decides.
    const outer = body as ({ error?: Envelope } & Envelope) | null;
    const error = outer?.error ?? outer;
    if (typeof error?.code === 'string' && (API_ERROR_CODES as readonly string[]).includes(error.code)) {
      code = error.code as ApiErrorCode;
    }
    if (typeof error?.support_ref === 'string' && SUPPORT_REF_RE.test(error.support_ref)) {
      supportRef = error.support_ref;
    }
    if (response.status === 422) fields = fieldErrorsFrom(error?.fields);
    if (typeof error?.retry_at === 'string' && RETRY_AT_RE.test(error.retry_at)) {
      retryAt = error.retry_at;
    }
  } catch {
    // Not JSON (a proxy error page, an empty body): keep "unknown".
  }
  return new ApiError(response.status, code, supportRef, { fields, retryAt });
}

export function createApiClient(options: ApiClientOptions) {
  const fetchFn = options.fetch ?? globalThis.fetch.bind(globalThis);
  const base = options.baseUrl.replace(/\/+$/, '');

  async function request(
    method: string,
    path: string,
    body?: unknown,
    extra: Record<string, string> = {},
  ): Promise<Response> {
    const headers = new Headers(options.headers);
    for (const [k, v] of Object.entries(extra)) headers.set(k, v);
    headers.set('accept', 'application/json');
    if (body !== undefined) headers.set('content-type', 'application/json');
    let response: Response;
    try {
      response = await fetchFn(`${base}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
      });
    } catch {
      throw new ApiError(0, 'network_error');
    }
    if (!response.ok) throw await toApiError(response);
    return response;
  }

  async function parsed<T>(response: Response, parse: (value: unknown) => T): Promise<T> {
    try {
      return parse(await response.json());
    } catch (e) {
      if (e instanceof ResponseShapeError || e instanceof SyntaxError) {
        throw new ApiError(response.status, 'invalid_response');
      }
      throw e;
    }
  }

  function ifMatch(version: number): Record<string, string> {
    return { 'if-match': String(version) };
  }

  function rallyPath(id: string): string {
    if (!isPublicId(id)) throw new ApiError(404, 'not_found');
    return id;
  }

  function matchPath(id: string): string {
    if (!isPublicId(id)) throw new ApiError(404, 'not_found');
    return `/matches/${id}`;
  }

  return {
    async listDevUsers(): Promise<DevUser[]> {
      return parsed(await request('GET', '/dev/users'), parseDevUsers);
    },
    async signIn(username: string): Promise<void> {
      await request('POST', '/dev/sign-in', { username });
    },
    /** A-01: 202 whether or not an account exists (api-sprint-01 §2.1). */
    async requestLink(email: string): Promise<void> {
      await request('POST', '/auth/links', { email });
    },
    /** A-03: exchange the link's token for a session cookie (api-sprint-01 §2.2). */
    async exchangeLink(token: string): Promise<{ newAccount: boolean }> {
      if (!isLinkToken(token)) throw new ApiError(401, 'link_expired');
      return parsed(await request('POST', '/auth/exchange', { token }), parseExchange);
    },
    async signOut(): Promise<void> {
      await request('POST', '/auth/sign-out');
    },
    async me(): Promise<Me> {
      return parsed(await request('GET', '/me'), parseMe);
    },
    async listMatches(): Promise<Match[]> {
      return parsed(await request('GET', '/matches?limit=50'), parseMatchList);
    },
    async createMatch(input: NewMatch): Promise<Match> {
      // Closed body: only the contract's keys, and only when given (api-sprint-01 §5.1).
      const body: Record<string, unknown> = {};
      for (const key of ['title', 'format', 'scoring_system', 'played_on', 'participants'] as const) {
        if (input[key] !== undefined) body[key] = input[key];
      }
      return parsed(await request('POST', '/matches', body), parseMatch);
    },
    async uploadPolicy(): Promise<UploadPolicy> {
      return parsed(await request('GET', '/upload-policy'), parseUploadPolicy);
    },
    async getMatch(id: string): Promise<Match> {
      return parsed(await request('GET', matchPath(id)), parseMatch);
    },
    // Sprint 2 (ST-027..ST-037). Routes from tagcontract.py until api-sprint-02.md exists.
    async getScoreSheet(id: string): Promise<{ version: number | null; sheet: ScoreSheet }> {
      const response = await request('GET', `${matchPath(id)}/score-sheet`);
      const etag = response.headers.get('etag');
      return parsed(response, (v) => parseSheetResponse(v, etag));
    },
    async startGame(
      id: string,
      version: number,
      start: { first_serving_side: Side; ends_switched: boolean },
    ): Promise<Versioned> {
      return parsed(await request('POST', `${matchPath(id)}/games`, start, ifMatch(version)), parseVersioned);
    },
    async tagRally(id: string, version: number, tag: TagInput): Promise<Versioned & { rallyId: string }> {
      return parsed(await request('POST', `${matchPath(id)}/rallies`, tag, ifMatch(version)), parseTagged);
    },
    async correctRally(
      id: string,
      version: number,
      rallyId: string,
      field: CorrectableField,
      value: CorrectionValue,
    ): Promise<Versioned> {
      const path = `${matchPath(id)}/rallies/${rallyPath(rallyId)}`;
      return parsed(await request('PATCH', path, { field, value }, ifMatch(version)), parseVersioned);
    },
    /** FR-053 (a), provisional: decide a "needs your decision" rally. */
    async resolveRally(
      id: string,
      version: number,
      rallyId: string,
      decision: 'withdraw' | 'move_to_next_game',
    ): Promise<Versioned> {
      const path = `${matchPath(id)}/rallies/${rallyPath(rallyId)}/resolution`;
      return parsed(await request('POST', path, { decision }, ifMatch(version)), parseVersioned);
    },
    async undo(id: string, version: number): Promise<Versioned> {
      return parsed(await request('POST', `${matchPath(id)}/undo`, undefined, ifMatch(version)), parseVersioned);
    },
    async corrections(id: string): Promise<HistoryItem[]> {
      return parsed(await request('GET', `${matchPath(id)}/corrections`), parseHistory);
    },
    /**
     * The whole match video for the tagging screen: `GET /matches/{id}/video` (BE `ac5ca2c`, same
     * rules as the rally link). `GET /matches/{id}/media` stays the probed facts.
     */
    async matchMedia(id: string): Promise<RallyMedia> {
      return parsed(await request('GET', `${matchPath(id)}/video`), parseRallyMedia);
    },
    async rallyMedia(id: string, rallyId: string): Promise<RallyMedia> {
      return parsed(await request('GET', `${matchPath(id)}/rallies/${rallyPath(rallyId)}/media`), parseRallyMedia);
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
