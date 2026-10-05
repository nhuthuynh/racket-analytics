// Quick Tag state (ST-027; FR-050; sprint-02 §5 front-end TDD plan). Pure: the screen dispatches
// what the player did and what the server answered. One tag at a time; while it is pending the
// optimistic call is shown, and a server error rolls it back and gives the draft back (NFR-012a).
import type { ParticipantSlot } from '@/lib/api/types';
import { currentCall, nextCall } from './score';
import { sideOfSlot, type Ending, type ScoreSheet, type Side, type TagInput } from './types';

export interface Draft {
  start_ms?: number;
  end_ms?: number;
  winning_side?: Side;
  responsible_player?: ParticipantSlot;
}

export interface Pending {
  tag: TagInput;
  number: number;
  /** The provisional call shown until the server answers; null when it cannot be derived. */
  optimisticCall: string | null;
  baseVersion: number;
}

export interface TaggingState {
  sheet: ScoreSheet;
  version: number;
  game: number;
  firstServingSide: Side;
  draft: Draft;
  pending: Pending | null;
  /** A short message about the last thing that could not be done, or null. */
  notice: string | null;
}

export type TaggingAction =
  | { type: 'mark_start'; ms: number }
  | { type: 'mark_end'; ms: number }
  | { type: 'choose_winner'; side: Side }
  | { type: 'choose_player'; slot: ParticipantSlot | null }
  | { type: 'choose_ending'; ending: Ending }
  | { type: 'clear' }
  | { type: 'confirmed'; sheet: ScoreSheet; version: number }
  | { type: 'stale'; sheet: ScoreSheet; version: number }
  | { type: 'failed'; message: string }
  | { type: 'game_started'; sheet: ScoreSheet; version: number; game: number; firstServingSide: Side };

export function initialTagging(input: {
  sheet: ScoreSheet;
  version: number;
  firstServingSide: Side;
  game?: number;
}): TaggingState {
  const game = input.game ?? Math.max(1, ...input.sheet.rows.map((r) => r.game));
  return { sheet: input.sheet, version: input.version, game, firstServingSide: input.firstServingSide, draft: {}, pending: null, notice: null };
}

const ERROR_ENDINGS: readonly Ending[] = ['unforced_error', 'forced_error', 'fault'];

/** I6 as the client can check it (match-aggregate §2.1; coach to confirm, §8 Q2). */
function playerProblem(ending: Ending, side: Side | undefined, slot: ParticipantSlot | undefined): string | null {
  if (!slot || !side || ending === 'replay') return null;
  const onWinning = sideOfSlot(slot) === side;
  if (ending === 'winner' && !onWinning) return 'The player who hit the winner must be on the side that won the rally.';
  if (ERROR_ENDINGS.includes(ending) && onWinning) {
    return 'The player who made the error must be on the side that lost the rally.';
  }
  return null;
}

function lastEndMs(state: TaggingState): { number: number; end: number } | null {
  const rows = state.sheet.rows;
  const last = rows[rows.length - 1];
  return last ? { number: last.number, end: last.end_ms } : null;
}

export function taggingReducer(state: TaggingState, action: TaggingAction): TaggingState {
  const busy = state.pending !== null;
  switch (action.type) {
    case 'mark_start': {
      if (busy) return state;
      const ms = Math.floor(action.ms);
      const last = lastEndMs(state);
      if (last && ms < last.end) {
        return {
          ...state,
          notice: `This rally starts before the end of rally ${last.number}. Play on to the next rally, then mark its start.`,
        };
      }
      return { ...state, draft: { ...state.draft, start_ms: ms, end_ms: undefined }, notice: null };
    }
    case 'mark_end': {
      if (busy) return state;
      const ms = Math.floor(action.ms);
      if (state.draft.start_ms === undefined) return { ...state, notice: 'Mark the rally start first.' };
      if (ms <= state.draft.start_ms) return { ...state, notice: 'The rally end must be after its start.' };
      return { ...state, draft: { ...state.draft, end_ms: ms }, notice: null };
    }
    case 'choose_winner':
      if (busy) return state;
      return { ...state, draft: { ...state.draft, winning_side: action.side }, notice: null };
    case 'choose_player': {
      if (busy) return state;
      const draft = { ...state.draft };
      if (action.slot) draft.responsible_player = action.slot;
      else delete draft.responsible_player;
      return { ...state, draft, notice: null };
    }
    case 'choose_ending': {
      if (busy) return state;
      const d = state.draft;
      if (d.start_ms === undefined) return { ...state, notice: 'Mark the rally start first.' };
      if (d.end_ms === undefined) return { ...state, notice: 'Mark the rally end first.' };
      const replay = action.ending === 'replay';
      if (!replay && !d.winning_side) return { ...state, notice: 'Choose which side won the rally first.' };
      const problem = playerProblem(action.ending, d.winning_side, d.responsible_player);
      if (problem) return { ...state, notice: problem };
      const winning = replay ? null : (d.winning_side ?? null);
      const before = currentCall(state.sheet.rows, state.game, state.firstServingSide);
      const after = before ? (replay ? before : nextCall(before, winning)) : null;
      const tag: TagInput = {
        start_ms: d.start_ms,
        end_ms: d.end_ms,
        winning_side: winning,
        ending: action.ending,
        responsible_player: replay ? null : (d.responsible_player ?? null),
        fault_kind: null,
      };
      const number = (state.sheet.rows[state.sheet.rows.length - 1]?.number ?? 0) + 1;
      return {
        ...state,
        draft: {},
        notice: null,
        pending: { tag, number, optimisticCall: after?.call ?? null, baseVersion: state.version },
      };
    }
    case 'clear':
      return busy ? state : { ...state, draft: {}, notice: null };
    case 'confirmed':
      return { ...state, sheet: action.sheet, version: action.version, pending: null, notice: null };
    case 'stale':
      return {
        ...state,
        sheet: action.sheet,
        version: action.version,
        pending: null,
        notice: 'This match was changed on another device. The latest score is shown; your rally was not saved.',
      };
    case 'failed': {
      if (!state.pending) return { ...state, notice: action.message };
      const t = state.pending.tag;
      const draft: Draft = { start_ms: t.start_ms, end_ms: t.end_ms };
      if (t.winning_side) draft.winning_side = t.winning_side;
      if (t.responsible_player) draft.responsible_player = t.responsible_player;
      return { ...state, pending: null, draft, notice: action.message };
    }
    case 'game_started':
      return {
        ...state,
        sheet: action.sheet,
        version: action.version,
        game: action.game,
        firstServingSide: action.firstServingSide,
        draft: {},
        notice: null,
      };
  }
}

