// Sprint 2 tagging and score-sheet shapes (ST-027, ST-030; match-aggregate §2, §5).
// ASSUMPTION until docs/architecture/api-sprint-02.md exists: names follow
// scripts/measure/tagcontract.py and taglib.ROW_FIELDS (decision-log 2026-10-05). The parser in
// ./parse.ts is the one place that maps the wire format; nothing else reads raw JSON.
import type { ParticipantSlot } from '@/lib/api/types';

export const SIDES = ['A', 'B'] as const;
export type Side = (typeof SIDES)[number];

export const ENDINGS = ['winner', 'unforced_error', 'forced_error', 'fault', 'replay'] as const;
export type Ending = (typeof ENDINGS)[number];

export const ENDING_LABELS: Readonly<Record<Ending, string>> = {
  winner: 'Winner',
  unforced_error: 'Unforced error',
  forced_error: 'Forced error',
  fault: 'Fault',
  replay: 'Replay',
};

/** The outcome input the player tags (match-aggregate §2 `OutcomeInput`, plus the times). */
export interface TagInput {
  start_ms: number;
  end_ms: number;
  winning_side: Side | null;
  ending: Ending;
  responsible_player: ParticipantSlot | null;
  fault_kind: string | null;
}

/** One projected row of the score sheet (match-aggregate §2 `ScoreSheet`). */
export interface SheetRow {
  rally_id: string;
  number: number;
  game: number;
  start_ms: number;
  end_ms: number;
  serving_side: Side | null;
  /** Three-number call, serving side first (FR-048, provisional), or null on a conflict row. */
  score_before: string | null;
  score_after: string | null;
  winning_side: Side | null;
  ending: Ending;
  responsible_player: ParticipantSlot | null;
  fault_kind: string | null;
  marker: 'needs_decision' | null;
  corrected_by_user: boolean;
}

export interface SheetGame {
  number: number;
  first_serving_side: Side | null;
  winner: Side | null;
}

export interface ScoreSheet {
  rules_version: string;
  /** FR-055: true while any rule in the scoring path is unverified (today always). */
  unofficial: boolean;
  label: string;
  rows: SheetRow[];
  games?: SheetGame[];
  match_winner?: Side | null;
}

export const UNOFFICIAL_LABEL = 'unofficial scoring (rules not yet verified)';

export function otherSide(side: Side): Side {
  return side === 'A' ? 'B' : 'A';
}

export function sideOfSlot(slot: ParticipantSlot): Side {
  return slot[0] as Side;
}

export const HISTORY_KINDS = ['game_started', 'correction', 'withdrawal', 'undo', 'resolution'] as const;
export type HistoryKind = (typeof HISTORY_KINDS)[number];

/**
 * The whole outcome input of one rally, as `{"field": "outcome", "value": …}` sends it and as an
 * outcome correction's old and new values hold it (api-sprint-02 §2, §3 "Correctable fields").
 */
export interface OutcomeValue {
  ending: Ending;
  winning_side: Side | null;
  responsible_player: ParticipantSlot | null;
  fault_kind: string | null;
}

/** A history value: a tag value, or for `field = "outcome"` an outcome object of tag values. */
export type HistoryValue = string | number | boolean | null | OutcomeValue;

/** One audit row of GET /matches/{id}/corrections (FR-052; match-aggregate §2 `Correction`). */
export interface HistoryItem {
  id: string;
  kind: HistoryKind;
  rally_id: string | null;
  rally_number: number | null;
  field: string | null;
  /** Tag values only (sides, slots, enums, integers): never names or free text (§6). */
  old_value: HistoryValue;
  new_value: HistoryValue;
  undoes: string | null;
  at: string;
}

/** GET /matches/{id}/rallies/{rally_id}/media (ST-037; NFR-055 TTL ≤ 15 min). */
export interface RallyMedia {
  url: string;
  expiresInS: number;
  startMs: number;
}

export const MAX_MEDIA_TTL_S = 900;

/** Correctable fields (ST-031/ST-032; match-aggregate §4 `correct_rally`). */
export type CorrectableField = 'winning_side' | 'ending' | 'responsible_player' | 'start_ms' | 'end_ms' | 'fault_kind' | 'outcome';

/** The value sent with a correction: a tag value, or the whole outcome for `outcome`. */
export type CorrectionValue = string | number | null | OutcomeValue;

export interface Versioned {
  version: number;
  sheet: ScoreSheet;
}
