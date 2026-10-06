// Which command a score-sheet correction sends (ST-032; FR-052, FR-053; NFR-036d). One player
// action is one command and one history line. When a change leaves another part of the outcome
// not fitting (a tagged player on the wrong side, a fault type on a non-fault, a winner on a
// replay), the whole outcome goes in one `outcome` command with that part cleared
// (api-sprint-02 §3 "Correctable fields"; PD-S2R1-01). The server still validates everything.
import type { ParticipantSlot } from '@/lib/api/types';
import { otherSide, sideOfSlot, type CorrectableField, type CorrectionValue, type Ending, type OutcomeValue, type SheetRow, type Side } from './types';

export interface Correction {
  field: CorrectableField;
  value: CorrectionValue;
}

/** match-aggregate §2.1 / api-sprint-02 §4.2: the winner's player hit a winner; else the loser's. */
export function playerFits(slot: ParticipantSlot, ending: Ending, winningSide: Side | null): boolean {
  if (ending === 'replay' || winningSide === null) return false;
  const onWinningSide = sideOfSlot(slot) === winningSide;
  return ending === 'winner' ? onWinningSide : !onWinningSide;
}

function outcomeOf(row: SheetRow): OutcomeValue {
  return {
    ending: row.ending,
    winning_side: row.winning_side,
    responsible_player: row.responsible_player,
    fault_kind: row.fault_kind,
  };
}

/** "Switch winner": null on a replay (no winner to switch). */
export function switchWinner(row: SheetRow): Correction | null {
  if (row.winning_side === null || row.ending === 'replay') return null;
  const other = otherSide(row.winning_side);
  if (row.responsible_player === null) return { field: 'winning_side', value: other };
  // The tagged player no longer fits the new winner for the same ending: clear it (the sheet
  // shows "player not tagged" and the player can pick again with "Change player").
  return { field: 'outcome', value: { ...outcomeOf(row), winning_side: other, responsible_player: null } };
}

/**
 * A new ending for a rally. Null when nothing changes, or when the rally is a replay and a scored
 * ending would need a winner first (not offered on S-01).
 */
export function changeEnding(row: SheetRow, ending: Ending): Correction | null {
  if (ending === row.ending) return null;
  if (ending === 'replay') {
    return { field: 'outcome', value: { ending: 'replay', winning_side: null, responsible_player: null, fault_kind: null } };
  }
  if (row.ending === 'replay' || row.winning_side === null) return null;
  const player = row.responsible_player && playerFits(row.responsible_player, ending, row.winning_side) ? row.responsible_player : null;
  const faultKind = ending === 'fault' ? row.fault_kind : null;
  if (player === row.responsible_player && faultKind === row.fault_kind) return { field: 'ending', value: ending };
  return { field: 'outcome', value: { ...outcomeOf(row), ending, responsible_player: player, fault_kind: faultKind } };
}

/** The endings offered on a row: every ending on a scored rally; only "Replay" on a replay. */
export function endingChoices(row: SheetRow, all: readonly Ending[]): Ending[] {
  return row.ending === 'replay' || row.winning_side === null ? all.filter((e) => e === 'replay') : [...all];
}

/** The players offered on a row: only those who fit its winner and ending (HAX: prevent the refusal). */
export function playerChoices<P extends { slot: ParticipantSlot }>(row: SheetRow, players: readonly P[]): P[] {
  return players.filter((p) => playerFits(p.slot, row.ending, row.winning_side));
}

export function changePlayer(row: SheetRow, slot: ParticipantSlot | null): Correction | null {
  return slot === row.responsible_player ? null : { field: 'responsible_player', value: slot };
}
