'use client';

// "Who serves first in game n?" (ST-027; FR-045, ST-021 explicit first server). One question
// with radio buttons and one button; the choice is required (flows §0 one question per page).
import { useState } from 'react';
import { otherSide, type Side } from '@/lib/tagging/types';

export function GameStartForm({
  game,
  mySide,
  label,
  intro,
  onStart,
}: {
  game: number;
  mySide: Side;
  label: (side: Side) => string;
  /** e.g. "Game 1 won by your side." */
  intro?: string | null;
  /** Starts the game; resolves to an error message, or null when it started. */
  onStart: (firstServingSide: Side) => Promise<string | null>;
}) {
  const [choice, setChoice] = useState<Side | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!choice) {
      setProblem(`Choose who serves first in game ${game}.`);
      return;
    }
    setBusy(true);
    setProblem(await onStart(choice));
    setBusy(false);
  }

  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        if (!busy) void submit();
      }}
    >
      {intro ? <p>{intro}</p> : null}
      {problem ? (
        <p role="alert" className="notice notice--error">
          {problem}
        </p>
      ) : null}
      <fieldset className="field">
        <legend className="field__label">{`Who serves first in game ${game}?`}</legend>
        {[mySide, otherSide(mySide)].map((side) => (
          <label key={side} className="choice">
            <input type="radio" name="first-server" value={side} checked={choice === side} onChange={() => setChoice(side)} />
            {label(side)}
          </label>
        ))}
      </fieldset>
      <p>
        <button type="submit" className="button" aria-busy={busy}>{`Start game ${game}`}</button>
      </p>
    </form>
  );
}
