// Types for docs/architecture/api-sprint-00.md (Sprint 0 contract). Field names follow the
// contract exactly; changes go through a PR on that file (principal-engineer).

export const MATCH_STATUSES = [
  'awaiting_upload',
  'uploading',
  'video_received',
  'probe_failed',
] as const;
export type MatchStatus = (typeof MATCH_STATUSES)[number];

/** UI labels: the QA contract's STATUS_LABELS (backend/tests/support/contract.py). */
export const STATUS_LABELS: Readonly<Record<MatchStatus, string>> = {
  awaiting_upload: 'Awaiting upload',
  uploading: 'Uploading',
  video_received: 'Video received',
  probe_failed: 'We could not read this video',
};

export const MATCH_FORMATS = ['singles', 'doubles'] as const;
export type MatchFormat = (typeof MATCH_FORMATS)[number];

export const FORMAT_LABELS: Readonly<Record<MatchFormat, string>> = {
  singles: 'Singles',
  doubles: 'Doubles',
};

export interface MediaFacts {
  duration_ms: number;
  fps: number;
  width: number;
  height: number;
  has_audio: boolean;
  vfr: boolean;
  container: string;
  video_codec: string;
}

export const SLOTS = ['A1', 'A2', 'B1', 'B2'] as const;
export type ParticipantSlot = (typeof SLOTS)[number];

export interface Participant {
  slot: ParticipantSlot;
  nickname: string;
  is_me: boolean;
}

/** The resume source of truth while an upload session exists (api-sprint-01 §5.2, flows D-3). */
export interface UploadState {
  state: 'receiving' | 'expired';
  offset: number;
  length: number;
  expiresAt: string;
  /** Same-origin tus URL, `/api/uploads/<uuid>`. */
  resumeUrl: string;
  fileName: string | null;
  fileLastModifiedMs: number | null;
  headSha256: string | null;
}

export const REJECTION_CODES = ['not_a_video', 'too_large', 'too_long', 'unsupported_video'] as const;
export type RejectionCode = (typeof REJECTION_CODES)[number];

export interface Rejection {
  code: RejectionCode;
  at: string;
}

export interface Match {
  id: string;
  title: string;
  format: MatchFormat;
  status: MatchStatus;
  media: MediaFacts | null;
  created_at: string;
  updated_at: string;
  /** Sprint 1 fields (api-sprint-01 §5.2). The parser always sets them (empty defaults when an
   * older API omits them); optional so Sprint 0 fixtures stay valid. */
  played_on?: string | null;
  participants?: Participant[];
  upload?: UploadState | null;
  rejection?: Rejection | null;
}

export interface NewMatch {
  format: MatchFormat;
  title?: string;
  scoring_system?: 'side_out';
  played_on?: string;
  participants?: Participant[];
}

/** GET /upload-policy (api-sprint-01 §6.1). Caps are provisional until ST-025 (R-05). */
export interface UploadPolicy {
  maxBytes: number;
  maxDurationMs: number;
  chunkMinBytes: number;
  chunkMaxBytes: number;
  expiresAfterS: number;
}

/** The provisional caps (K12, R-05), used only when the policy cannot be read. */
export const FALLBACK_UPLOAD_POLICY: UploadPolicy = {
  maxBytes: 10_000_000_000,
  maxDurationMs: 9_000_000,
  chunkMinBytes: 5 * 1024 * 1024,
  chunkMaxBytes: 8 * 1024 * 1024,
  expiresAfterS: 86_400,
};

export interface DevUser {
  username: string;
  display_name: string;
}

export interface Me {
  id: string;
  /** null for magic-link accounts until a later story sets it (api-sprint-01 §2.3). */
  display_name: string | null;
}

/** Error codes from api-sprint-00 §3, plus client-side codes. */
export const API_ERROR_CODES = [
  'bad_request',
  'unauthenticated',
  'forbidden_origin',
  'not_found',
  'method_not_allowed',
  'conflict',
  'upload_offset_mismatch',
  'length_required',
  'tus_version_unsupported',
  'payload_too_large',
  'unsupported_media_type',
  'validation_failed',
  'rate_limited',
  'internal_error',
  'unavailable',
  // api-sprint-01 §4.1
  'link_expired',
  'checksum_invalid',
  'upload_expired',
  'video_too_large',
  'not_a_video',
  'upload_quota_exceeded',
  'checksum_mismatch',
  // api-sprint-02 §4.1
  'stale_match',
  'match_not_ready',
  'invalid_outcome',
  'invalid_rally',
  'game_over',
  'match_over',
  'nothing_to_undo',
  'illegal_start',
  'game_not_started',
  'game_not_over',
  'decision_needed',
  'rules_unavailable',
  'scorebook_full',
] as const;
export type ServerErrorCode = (typeof API_ERROR_CODES)[number];
export type ApiErrorCode = ServerErrorCode | 'network_error' | 'invalid_response' | 'unknown';

/** Title rules from api-sprint-00 §5.1: 1-120 characters after trimming. */
export const TITLE_MAX_LENGTH = 120;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** Public IDs are canonical lowercase UUIDs (api-sprint-00 §1). */
export function isPublicId(value: string): boolean {
  return UUID_RE.test(value);
}

/** Closed field codes of api-sprint-01 §4.2 and api-sprint-02 §4.2. */
export const FIELD_ERROR_CODES = [
  'email_invalid',
  'format_required',
  'format_invalid',
  'scoring_system_invalid',
  'scoring_system_unavailable',
  'played_on_invalid',
  'played_on_in_future',
  'title_invalid',
  'side_needs_two_players',
  'side_needs_one_player',
  'invalid_slot',
  'choose_one_me',
  'nickname_required',
  'nickname_too_long',
  'nickname_invalid',
  'participants_without_format',
  'unknown_field',
  'invalid',
  // api-sprint-02 §4.2
  'time_invalid',
  'end_before_start',
  'overlaps_rally',
  'out_of_game_order',
  'time_after_video',
  'ending_invalid',
  'side_invalid',
  'side_required',
  'replay_has_no_side',
  'player_invalid',
  'replay_has_no_player',
  'must_be_on_winning_side',
  'must_be_on_losing_side',
  'fault_kind_invalid',
  'only_for_fault',
  'field_invalid',
  'unchanged',
  'decision_invalid',
  'not_needed',
  'no_previous_game',
  'previous_game_over',
  'not_first_in_game',
  // api-sprint-02 §4.2 amendment (C3-02, PE-S2-R3-02): only the latest kept rally moves forward
  'not_last_in_game',
  'too_many_rallies',
  'too_many_changes',
] as const;
export type FieldErrorCode = (typeof FIELD_ERROR_CODES)[number];

export interface ApiFieldError {
  /** A path from the route's closed list, or null (api-sprint-01 §1.1). */
  field: string | null;
  code: FieldErrorCode;
}

/** The magic-link token: 43 base64url characters (api-sprint-01 §2.2). */
export function isLinkToken(value: string): boolean {
  return /^[A-Za-z0-9_-]{43}$/.test(value);
}
