// Typed client for docs/architecture/api-sprint-00.md (ST-010).
// Browser: baseUrl "/api" (same origin, rewritten to the API; the HttpOnly session cookie goes
// along automatically). Server components: baseUrl API_INTERNAL_URL plus the incoming cookie.
// Authorisation is enforced by the API only; nothing here decides access [AQS/SEC-03].
import {
  parseDevUsers,
  parseMatch,
  parseMatchList,
  parseMe,
  ResponseShapeError,
} from './parse';
import {
  API_ERROR_CODES,
  isPublicId,
  type ApiErrorCode,
  type DevUser,
  type Match,
  type Me,
  type NewMatch,
} from './types';

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly supportRef: string | null;

  constructor(status: number, code: ApiErrorCode, supportRef: string | null = null) {
    super(`API error ${status} ${code}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.supportRef = supportRef;
  }
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
  try {
    const body: unknown = await response.json();
    const error = (body as { error?: { code?: unknown; support_ref?: unknown } } | null)?.error;
    if (typeof error?.code === 'string' && (API_ERROR_CODES as readonly string[]).includes(error.code)) {
      code = error.code as ApiErrorCode;
    }
    if (typeof error?.support_ref === 'string' && SUPPORT_REF_RE.test(error.support_ref)) {
      supportRef = error.support_ref;
    }
  } catch {
    // Not JSON (a proxy error page, an empty body): keep "unknown".
  }
  return new ApiError(response.status, code, supportRef);
}

export function createApiClient(options: ApiClientOptions) {
  const fetchFn = options.fetch ?? globalThis.fetch.bind(globalThis);
  const base = options.baseUrl.replace(/\/+$/, '');

  async function request(method: string, path: string, body?: unknown): Promise<Response> {
    const headers = new Headers(options.headers);
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
      const body: NewMatch = { title: input.title, format: input.format };
      return parsed(await request('POST', '/matches', body), parseMatch);
    },
    async getMatch(id: string): Promise<Match> {
      return parsed(await request('GET', matchPath(id)), parseMatch);
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
