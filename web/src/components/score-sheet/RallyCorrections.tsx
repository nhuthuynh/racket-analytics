'use client';

// Correct a rally where it is seen (ST-032; FR-052, FR-053; NFR-036d ≤ 2 taps or keys): one
// button switches the winner, and the ending and player lists save on change. The server
// replays the score and answers with the whole sheet; nothing is computed here. Controls are
// never disabled while a command runs, so focus stays where the player is (the screen ignores a
// second command until the first one is answered).
import type { ParticipantSlot } from '@/lib/api/types';
import { ENDING_LABELS, ENDINGS, otherSide, type CorrectableField, type Ending, type SheetRow } from '@/lib/tagging/types';
import type { SideNames } from '@/lib/tagging/view';

export function RallyCorrections({
  row,
  names,
  onCorrect,
}: {
  row: SheetRow;
  names: SideNames;
  onCorrect: (row: SheetRow, field: CorrectableField, value: string | null) => void;
}) {
  const other = row.winning_side ? otherSide(row.winning_side) : null;
  return (
    <div className="rally-fix">
      {other ? (
        <button
          type="button"
          className="button button--secondary rally-fix__button"
          aria-label={`Rally ${row.number}: change the winner to ${other === names.mySide ? 'your side' : 'the other side'}`}
          onClick={() => onCorrect(row, 'winning_side', other)}
        >
          Switch winner
        </button>
      ) : null}
      <select
        className="input rally-fix__select"
        aria-label={`Rally ${row.number} ending`}
        value={row.ending}
        onChange={(e) => onCorrect(row, 'ending', e.target.value as Ending)}
      >
        {ENDINGS.map((ending) => (
          <option key={ending} value={ending}>
            {ENDING_LABELS[ending]}
          </option>
        ))}
      </select>
      {names.players.length > 0 && row.ending !== 'replay' ? (
        <select
          className="input rally-fix__select"
          aria-label={`Rally ${row.number} player`}
          value={row.responsible_player ?? ''}
          onChange={(e) => onCorrect(row, 'responsible_player', (e.target.value || null) as ParticipantSlot | null)}
        >
          <option value="">Not tagged</option>
          {names.players.map((p) => (
            <option key={p.slot} value={p.slot}>
              {p.nickname}
            </option>
          ))}
        </select>
      ) : null}
    </div>
  );
}
