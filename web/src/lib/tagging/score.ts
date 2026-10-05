// Optimistic score display (NFR-012a ≤ 200 ms): the next call shown at once, before the server
// answers. It is never stored or sent; the server sheet replaces it (FR-049, match-aggregate §4
// "the client never computes a score itself beyond the optimistic display").
// Provisional side-out doubles (PROVISIONAL-UNVERIFIED, ADR 0009; 0-0-2 first-service rule).
// A call it cannot read gives null, and the screen then shows "Saving…" instead of a guess.
import type { SheetRow, Side } from './types';
import { otherSide } from './types';

export interface CallState {
  servingSide: Side;
  /** "serving-receiving-server", e.g. "4-6-1". */
  call: string;
}

const CALL_RE = /^(\d{1,2})-(\d{1,2})-([12])$/;

/** The call after one rally won by `winner` (null = replay). Game end is the server's job. */
export function nextCall(state: CallState, winner: Side | null): CallState | null {
  const m = CALL_RE.exec(state.call);
  if (!m) return null;
  const serving = Number(m[1]);
  const receiving = Number(m[2]);
  const server = Number(m[3]);
  if (winner === null) return { ...state };
  if (winner === state.servingSide) {
    return { servingSide: state.servingSide, call: `${serving + 1}-${receiving}-${server}` };
  }
  if (server === 1) return { servingSide: state.servingSide, call: `${serving}-${receiving}-2` };
  return { servingSide: otherSide(state.servingSide), call: `${receiving}-${serving}-1` };
}

/** The call before the next rally of `game`, from the last scored row of that game. */
export function currentCall(rows: readonly SheetRow[], game: number, firstServingSide: Side): CallState | null {
  const scored = rows.filter((r) => r.game === game && r.marker === null && r.serving_side && r.score_before);
  const last = scored[scored.length - 1];
  if (!last) return { servingSide: firstServingSide, call: '0-0-2' };
  return nextCall({ servingSide: last.serving_side as Side, call: last.score_before as string }, last.winning_side);
}
