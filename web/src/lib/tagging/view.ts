// Display helpers for the tagging screens (ST-027, ST-029, ST-030). Pure.
import type { Match, ParticipantSlot } from '@/lib/api/types';
import { sideOfSlot, type ScoreSheet, type SheetRow, type Side } from './types';

export interface SideNames {
  mySide: Side;
  players: { slot: ParticipantSlot; nickname: string }[];
  /** "Your side (Ivy and Dana)" / "Other side (Carlos and Bo)". */
  label(side: Side): string;
}

export function sideNames(match: Match): SideNames {
  const participants = [...(match.participants ?? [])].sort((a, b) => a.slot.localeCompare(b.slot));
  const me = participants.find((p) => p.is_me);
  const mySide: Side = me ? sideOfSlot(me.slot) : 'A';
  const of = (side: Side) => participants.filter((p) => sideOfSlot(p.slot) === side).map((p) => p.nickname);
  return {
    mySide,
    players: participants.map((p) => ({ slot: p.slot, nickname: p.nickname })),
    label(side) {
      const who = side === mySide ? 'Your side' : 'Other side';
      const n = of(side);
      return n.length ? `${who} (${n.join(' and ')})` : who;
    },
  };
}

/** "us" / "them" for the announcement (FR-048, DES FR-UX-62). */
export function winnerWord(side: Side | null | undefined, mySide: Side): string {
  if (!side) return 'nobody';
  return side === mySide ? 'your side' : 'the other side';
}

/** "Rally 7: them. Score 4-6-1." (FR-048 example; call format provisional, @needs-verification). */
export function tagLine(row: SheetRow, mySide: Side): string {
  const who = row.ending === 'replay' || !row.winning_side ? 'replay' : row.winning_side === mySide ? 'us' : 'them';
  if (row.marker === 'needs_decision' || !row.score_after) return `Rally ${row.number}: ${who}. Needs your decision.`;
  return `Rally ${row.number}: ${who}. Score ${row.score_after}.`;
}

export interface GameStatus {
  /** The number of the newest started game, 0 when none. */
  current: number;
  firstServingSide: Side | null;
  over: boolean;
  lastWinner: Side | null;
  matchOver: boolean;
  matchWinner: Side | null;
}

export function gameStatus(sheet: ScoreSheet): GameStatus {
  const matchWinner = sheet.match_winner ?? null;
  if (sheet.games) {
    const last = sheet.games[sheet.games.length - 1];
    return {
      current: last?.number ?? 0,
      firstServingSide: last?.first_serving_side ?? null,
      over: !!last?.winner,
      lastWinner: last?.winner ?? null,
      matchOver: matchWinner !== null,
      matchWinner,
    };
  }
  const current = sheet.rows.reduce((n, r) => Math.max(n, r.game), 0);
  const first = sheet.rows.find((r) => r.game === current && r.serving_side)?.serving_side ?? null;
  return { current, firstServingSide: first, over: false, lastWinner: null, matchOver: matchWinner !== null, matchWinner };
}
