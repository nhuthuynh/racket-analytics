'use client';

// Correct a rally where it is seen (ST-032; FR-052, FR-053; NFR-036d ≤ 2 taps or keys;
// flows-sprint-02 §5 S-01). "Switch winner" is 1 tap. "Change ending" and "Change player" are
// disclosures with one button per option: open, then press the option (2 taps). Nothing is saved
// by moving through the options (PD-S2R1-02, SC 3.2.2); one press is one command and one
// history line. A change that leaves the tagged player not fitting clears it in the same command
// (PD-S2R1-01; lib/tagging/corrections.ts). The server replays the score and answers with the
// whole sheet; nothing is computed here. Controls are never disabled while a command runs, so
// focus stays where the player is (the screen ignores a second command until the first one is
// answered).
import { useRef, useState, type KeyboardEvent } from 'react';
import { changeEnding, changePlayer, endingChoices, playerChoices, switchWinner, type Correction } from '@/lib/tagging/corrections';
import { ENDING_LABELS, ENDINGS, otherSide, type CorrectableField, type CorrectionValue, type SheetRow } from '@/lib/tagging/types';
import type { SideNames } from '@/lib/tagging/view';

type Panel = 'ending' | 'player';

export function RallyCorrections({
  row,
  names,
  onCorrect,
}: {
  row: SheetRow;
  names: SideNames;
  onCorrect: (row: SheetRow, field: CorrectableField, value: CorrectionValue) => void;
}) {
  const [open, setOpen] = useState<Panel | null>(null);
  const endingToggle = useRef<HTMLButtonElement>(null);
  const playerToggle = useRef<HTMLButtonElement>(null);
  const toggles = { ending: endingToggle, player: playerToggle };
  const winnerFix = switchWinner(row);
  const showPlayer = names.players.length > 0 && row.ending !== 'replay';
  const panelId = (p: Panel) => `rally-fix-${row.rally_id}-${p}`;

  function close(panel: Panel) {
    setOpen(null);
    toggles[panel].current?.focus();
  }

  function choose(panel: Panel, fix: Correction | null) {
    close(panel);
    if (fix) onCorrect(row, fix.field, fix.value);
  }

  function onPanelKey(panel: Panel) {
    return (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        close(panel);
      }
    };
  }

  function toggle(panel: Panel, label: string) {
    return (
      <button
        ref={toggles[panel]}
        type="button"
        className="button button--secondary rally-fix__button"
        aria-expanded={open === panel}
        aria-controls={open === panel ? panelId(panel) : undefined}
        aria-label={`${label}, rally ${row.number}`}
        onClick={() => setOpen(open === panel ? null : panel)}
        onKeyDown={open === panel ? onPanelKey(panel) : undefined}
      >
        {label}
      </button>
    );
  }

  return (
    <div className="rally-fix">
      {winnerFix && row.winning_side ? (
        <button
          type="button"
          className="button button--secondary rally-fix__button"
          // SC 2.5.3 Label in Name: the name starts with the visible words (flows-sprint-02 §5, PD-FL2-01).
          aria-label={`Switch winner, rally ${row.number}, to ${otherSide(row.winning_side) === names.mySide ? 'your side' : 'the other side'}`}
          onClick={() => onCorrect(row, winnerFix.field, winnerFix.value)}
        >
          Switch winner
        </button>
      ) : null}
      {toggle('ending', 'Change ending')}
      {open === 'ending' ? (
        <div id={panelId('ending')} role="group" aria-label={`Rally ${row.number} ending`} className="rally-fix__options" onKeyDown={onPanelKey('ending')}>
          {endingChoices(row, ENDINGS).map((ending) => (
            <button
              key={ending}
              type="button"
              className="button button--secondary rally-fix__button"
              aria-pressed={row.ending === ending}
              onClick={() => choose('ending', changeEnding(row, ending))}
            >
              {ENDING_LABELS[ending]}
            </button>
          ))}
        </div>
      ) : null}
      {showPlayer ? toggle('player', 'Change player') : null}
      {open === 'player' && showPlayer ? (
        <div id={panelId('player')} role="group" aria-label={`Rally ${row.number} player`} className="rally-fix__options" onKeyDown={onPanelKey('player')}>
          {playerChoices(row, names.players).map((p) => (
            <button
              key={p.slot}
              type="button"
              className="button button--secondary rally-fix__button"
              aria-pressed={row.responsible_player === p.slot}
              onClick={() => choose('player', changePlayer(row, p.slot))}
            >
              {p.nickname}
            </button>
          ))}
          <button
            type="button"
            className="button button--secondary rally-fix__button"
            aria-pressed={row.responsible_player === null}
            onClick={() => choose('player', changePlayer(row, null))}
          >
            Not tagged
          </button>
        </div>
      ) : null}
    </div>
  );
}
