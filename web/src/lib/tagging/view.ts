// Display helpers for the tagging screens (ST-027, ST-029, ST-030). Pure.
import type { Match, ParticipantSlot } from '@/lib/api/types';
import { ENDING_LABELS, sideOfSlot, type Ending, type HistoryItem, type ScoreSheet, type SheetRow, type Side } from './types';

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

/** Rally start as "14:32" (or "1:02:05"), floored so the video never starts after the rally. */
export function formatClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const ss = String(total % 60).padStart(2, '0');
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`;
}

const FIELD_WORDS: Readonly<Record<string, string>> = {
  winning_side: 'won by',
  ending: 'ending',
  responsible_player: 'player',
  start_ms: 'start',
  end_ms: 'end',
  fault_kind: 'fault type',
};

function valueWords(field: string, value: HistoryItem['old_value'], names: SideNames): string {
  if (value === null) return field === 'responsible_player' ? 'not tagged' : 'nothing';
  if (field === 'winning_side') return value === names.mySide ? 'your side' : 'the other side';
  if (field === 'ending' && typeof value === 'string' && value in ENDING_LABELS) {
    return ENDING_LABELS[value as Ending].toLowerCase();
  }
  if (field === 'responsible_player') return names.players.find((p) => p.slot === value)?.nickname ?? String(value);
  if ((field === 'start_ms' || field === 'end_ms') && typeof value === 'number') return formatClock(value);
  return String(value);
}

/** One line of the correction history H-01 (FR-052: rally, field, old and new value). */
export function historyText(item: HistoryItem, all: readonly HistoryItem[], names: SideNames): string {
  const rally = item.rally_number ? `Rally ${item.rally_number}` : 'The match';
  switch (item.kind) {
    case 'correction': {
      const field = item.field ?? 'value';
      return `${rally}: ${FIELD_WORDS[field] ?? field} changed from ${valueWords(field, item.old_value, names)} to ${valueWords(field, item.new_value, names)}`;
    }
    case 'withdrawal':
      return item.rally_number ? `${rally} removed` : 'A rally was removed';
    case 'game_started':
      return 'A game was started';
    case 'resolution':
      if (item.field === 'game_number') return `${rally}: moved from game ${item.old_value} to game ${item.new_value}`;
      if (item.field === 'withdrawn') {
        return item.rally_number ? `${rally} removed (your decision)` : 'A rally that needed your decision was removed';
      }
      return `${rally}: your decision was recorded`;
    case 'undo': {
      const target = all.find((i) => i.id === item.undoes);
      return target && target.kind !== 'undo' ? `Undone: ${historyText(target, all, names)}` : 'Undone: an earlier change';
    }
  }
}
