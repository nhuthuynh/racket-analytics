// P-02's two calls (ST-063b; api-sprint-04 §2.1, §2.2): `POST /me/plan` with the player's
// PlanPreferences, and `GET /me/plan` for the last preferences on a regenerate visit. Every answer
// becomes an outcome the page can show; nothing throws. Authorisation is the API's: `/me/plan` is
// the session's own plan [AQS/SEC-03].
import type { FieldError } from '@/components/ErrorSummary';
import { fieldErrorsFrom422, preferencesFrom, toRequestBody, type PlanPreferences } from './PlanPreferencesModel';

export type GenerateOutcome =
  | { kind: 'created' }
  | { kind: 'invalid'; errors: FieldError[] }
  | { kind: 'no_tagged_match' }
  | { kind: 'no_plan_fits' }
  | { kind: 'plan_conflict' }
  | { kind: 'signed_out' }
  | { kind: 'error'; supportRef: string | null };

export type LastPreferencesRead =
  | { kind: 'preferences'; preferences: PlanPreferences }
  | { kind: 'none' }
  | { kind: 'signed_out' }
  | { kind: 'error' };

export interface PlanPreferencesApi {
  generatePlan(preferences: PlanPreferences): Promise<GenerateOutcome>;
  lastPreferences(): Promise<LastPreferencesRead>;
}

const REFUSALS = ['no_tagged_match', 'no_plan_fits', 'plan_conflict'] as const;
const SUPPORT_REF_RE = /^ref_[0-9a-f]{16}$/;

interface Envelope {
  code: string | null;
  supportRef: string | null;
  fields: { field: string | null; code: string }[];
}

async function envelopeOf(response: Response): Promise<Envelope> {
  try {
    const body = (await response.json()) as { error?: Record<string, unknown> } & Record<string, unknown>;
    const e = (body?.error ?? body) as Record<string, unknown>;
    const fields = Array.isArray(e.fields)
      ? e.fields.flatMap((f: { field?: unknown; code?: unknown }) =>
          typeof f?.code === 'string' ? [{ field: typeof f.field === 'string' ? f.field : null, code: f.code }] : [])
      : [];
    return {
      code: typeof e.code === 'string' ? e.code : null,
      supportRef: typeof e.support_ref === 'string' && SUPPORT_REF_RE.test(e.support_ref) ? e.support_ref : null,
      fields,
    };
  } catch {
    return { code: null, supportRef: null, fields: [] };
  }
}

export function createPlanPreferencesApi(options: {
  baseUrl: string;
  fetch?: typeof fetch;
}): PlanPreferencesApi {
  const fetchFn = options.fetch ?? globalThis.fetch.bind(globalThis);
  const url = `${options.baseUrl.replace(/\/+$/, '')}/me/plan`;
  const init = (method: string, body?: unknown): RequestInit => ({
    method,
    headers: body === undefined ? { accept: 'application/json' } : { accept: 'application/json', 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
    cache: 'no-store',
    redirect: 'error',
  });

  return {
    async generatePlan(preferences) {
      let response: Response;
      try {
        response = await fetchFn(url, init('POST', toRequestBody(preferences)));
      } catch {
        return { kind: 'error', supportRef: null };
      }
      if (response.status === 201) return { kind: 'created' };
      if (response.status === 401) return { kind: 'signed_out' };
      const e = await envelopeOf(response);
      const refusal = REFUSALS.find((r) => r === e.code);
      if (response.status === 409 && refusal) return { kind: refusal };
      if (response.status === 422) {
        const errors = fieldErrorsFrom422(e.fields);
        if (errors.length > 0) return { kind: 'invalid', errors };
      }
      return { kind: 'error', supportRef: e.supportRef };
    },

    async lastPreferences() {
      try {
        const response = await fetchFn(url, init('GET'));
        if (response.status === 404) return { kind: 'none' };
        if (response.status === 401) return { kind: 'signed_out' };
        if (response.status !== 200) return { kind: 'error' };
        const body = (await response.json()) as { preferences?: unknown } | null;
        const preferences = preferencesFrom(body?.preferences);
        return preferences ? { kind: 'preferences', preferences } : { kind: 'error' };
      } catch {
        return { kind: 'error' };
      }
    },
  };
}
