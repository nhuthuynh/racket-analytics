'use client';

// "Who serves first in game n?" (ST-027; FR-045, ST-021 explicit first server). One question
// with radio buttons and one button; the choice is required (flows §0 one question per page).
// Errors use the shared error summary [DPA/DESIGN-13] with the message inline too (PD-R3S2-01).
import { useState } from 'react';
import { ErrorSummary } from '@/components/ErrorSummary';
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
  /** A missing choice (a field error) or the server's reason (general). */
  const [problem, setProblem] = useState<{ message: string; field: boolean } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const firstId = `first-server-${mySide}`;
  const errorId = 'first-server-error';

  async function submit() {
    setAttempt((n) => n + 1);
    if (!choice) {
      setProblem({ message: `Choose who serves first in game ${game}.`, field: true });
      return;
    }
    setBusy(true);
    const failed = await onStart(choice);
    setProblem(failed ? { message: failed, field: false } : null);
    setBusy(false);
  }
  const fieldError = problem?.field ? problem.message : null;

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
        <ErrorSummary
          errors={problem.field ? [{ field: firstId, message: problem.message }] : []}
          general={problem.field ? undefined : problem.message}
          attempt={attempt}
        />
      ) : null}
      <fieldset className={`field${fieldError ? ' field--error' : ''}`} aria-describedby={fieldError ? errorId : undefined}>
        <legend className="field__label">{`Who serves first in game ${game}?`}</legend>
        {fieldError ? (
          <p id={errorId} className="field__error">
            <span className="visually-hidden">Error: </span>
            {fieldError}
          </p>
        ) : null}
        {[mySide, otherSide(mySide)].map((side) => (
          <label key={side} className="choice">
            <input
              id={side === mySide ? firstId : undefined}
              type="radio"
              name="first-server"
              value={side}
              checked={choice === side}
              onChange={() => setChoice(side)}
            />
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
