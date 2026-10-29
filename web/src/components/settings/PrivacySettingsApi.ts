// R-01's calls (ST-071; api-sprint-04 §1 rule 3, §5, §6): the flags from `GET /config/public`,
// `GET/PUT /me/retention`, `GET/PUT /me/training-consent` and the review video deletion dates of
// `GET /matches`. Every answer becomes an outcome the page can show; nothing throws. Authorisation
// is the API's: `/me/*` is the session's own account [AQS/SEC-03].
import { apiInternalUrl } from '@/lib/api/config';
import type { PrivacyFeatures, RetentionDays, RetentionSetting, ReviewVideo, TrainingConsent } from './PrivacySettingsModel';

export type Outcome<T> = { kind: 'ok'; value: T } | { kind: 'signed_out' } | { kind: 'error'; supportRef: string | null };

export interface PrivacySettingsApi {
  retention(): Promise<Outcome<RetentionSetting>>;
  saveRetention(days: RetentionDays): Promise<Outcome<RetentionSetting>>;
  reviewVideos(): Promise<Outcome<ReviewVideo[]>>;
  consent(): Promise<Outcome<TrainingConsent>>;
  saveConsent(optIn: boolean): Promise<Outcome<TrainingConsent>>;
}

const SUPPORT_REF_RE = /^ref_[0-9a-f]{16}$/;
type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);
const isDays = (v: unknown): v is RetentionDays => v === null || (typeof v === 'number' && Number.isInteger(v) && v > 0);

function retentionFrom(b: unknown): RetentionSetting | null {
  if (!isObj(b) || !Array.isArray(b.choices) || !b.choices.every(isDays) || !b.choices.includes(b.review_video_days as RetentionDays)) return null;
  return { days: b.review_video_days as RetentionDays, choices: b.choices };
}

function consentFrom(b: unknown): TrainingConsent | null {
  return isObj(b) && typeof b.opt_in === 'boolean' ? { optIn: b.opt_in } : null;
}

function reviewVideosFrom(b: unknown): ReviewVideo[] | null {
  if (!isObj(b) || !Array.isArray(b.items)) return null;
  const out: ReviewVideo[] = [];
  for (const m of b.items) {
    if (!isObj(m) || typeof m.id !== 'string' || typeof m.title !== 'string') return null;
    const at = m.review_video_delete_at ?? null;
    if (at !== null && typeof at !== 'string') return null;
    if (m.media !== null) out.push({ matchId: m.id, title: m.title, deleteAt: at });
  }
  return out;
}

export function createPrivacySettingsApi(options: { baseUrl: string; fetch?: typeof fetch }) {
  const fetchFn: typeof fetch = (input, init) => (options.fetch ?? globalThis.fetch)(input, init);
  const base = options.baseUrl.replace(/\/+$/, '');

  async function call<T>(method: string, path: string, parse: (b: unknown) => T | null, body?: unknown): Promise<Outcome<T>> {
    let response: Response;
    try {
      response = await fetchFn(`${base}${path}`, {
        method,
        headers: body === undefined ? { accept: 'application/json' } : { accept: 'application/json', 'content-type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
      });
    } catch {
      return { kind: 'error', supportRef: null };
    }
    if (response.status === 401) return { kind: 'signed_out' };
    let json: unknown = null;
    try {
      json = await response.json();
    } catch {
      // not JSON (a proxy page, an empty body)
    }
    if (response.ok) {
      const value = parse(json);
      return value === null ? { kind: 'error', supportRef: null } : { kind: 'ok', value };
    }
    const e = isObj(json) && isObj(json.error) ? json.error : {};
    const ref = typeof e.support_ref === 'string' && SUPPORT_REF_RE.test(e.support_ref) ? e.support_ref : null;
    return { kind: 'error', supportRef: ref };
  }

  return {
    /** Any failure reads as both flags off: the page then does not exist (the API still guards). */
    async features(): Promise<PrivacyFeatures> {
      const r = await call('GET', '/config/public', (b) => (isObj(b) && isObj(b.features) ? b.features : null));
      if (r.kind !== 'ok') return { retention: false, consent: false };
      return { retention: r.value.retention_setting === true, consent: r.value.training_consent === true };
    },
    retention: () => call('GET', '/me/retention', retentionFrom),
    saveRetention: (days: RetentionDays) => call('PUT', '/me/retention', retentionFrom, { review_video_days: days }),
    reviewVideos: () => call('GET', '/matches?limit=50', reviewVideosFrom),
    consent: () => call('GET', '/me/training-consent', consentFrom),
    saveConsent: (optIn: boolean) => call('PUT', '/me/training-consent', consentFrom, { opt_in: optIn }),
  } satisfies PrivacySettingsApi & { features(): Promise<PrivacyFeatures> };
}

export const privacySettingsApi = createPrivacySettingsApi({ baseUrl: '/api' });

/** For the server page: the flags, read directly from the API (no session needed). */
export async function serverFeatures(): Promise<PrivacyFeatures> {
  return createPrivacySettingsApi({ baseUrl: apiInternalUrl() }).features();
}
