'use client';

// The score sheet screen's client part (ST-030, ST-031). Holds the sheet and its version for
// If-Match; "Undo last change" (FR-052) replaces the sheet with the server's, reloads the
// correction history H-01 and says so in the polite status region. A stale version reloads the
// sheet and tells the player (IT-02-04).
import { useCallback, useEffect, useState } from 'react';
import { ScoreAnnouncer } from '@/components/tagging/ScoreAnnouncer';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { commandProblem } from '@/lib/tagging/messages';
import type { Match } from '@/lib/api/types';
import type { CorrectableField, HistoryItem, ScoreSheet, SheetRow, Versioned } from '@/lib/tagging/types';
import { sideNames } from '@/lib/tagging/view';
import { CorrectionHistory } from './CorrectionHistory';
import { RallyCorrections } from './RallyCorrections';
import { ScoreSheetTable } from './ScoreSheetTable';

export type SheetApi = Pick<ApiClient, 'undo' | 'corrections' | 'correctRally' | 'getScoreSheet' | 'rallyMedia'>;

export function ScoreSheetView({
  match,
  initialSheet,
  initialVersion,
  api = browserApi,
}: {
  match: Match;
  initialSheet: ScoreSheet;
  initialVersion: number;
  api?: SheetApi;
}) {
  const [sheet, setSheet] = useState(initialSheet);
  const [version, setVersion] = useState(initialVersion);
  const [history, setHistory] = useState<HistoryItem[] | null>(null);
  const [historyFailed, setHistoryFailed] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [said, setSaid] = useState('');
  const [busy, setBusy] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await api.corrections(match.id));
      setHistoryFailed(false);
    } catch {
      setHistoryFailed(true);
    }
  }, [api, match.id]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  /** Runs one command with the current version; returns the new state or null on failure. */
  const run = useCallback(
    async (what: string, command: (v: number) => Promise<Versioned>, done: (r: Versioned) => string) => {
      if (busy) return;
      setBusy(true);
      setProblem(null);
      try {
        const r = await command(version);
        setSheet(r.sheet);
        setVersion(r.version);
        setSaid(done(r));
        await loadHistory();
      } catch (e) {
        if (e instanceof ApiError && e.code === 'stale_match') {
          try {
            const latest = await api.getScoreSheet(match.id);
            setSheet(latest.sheet);
            if (latest.version !== null) setVersion(latest.version);
            await loadHistory();
          } catch {
            // Keep what is shown; the message below asks for a reload.
          }
          setProblem('This match was changed on another device. The latest score sheet is shown; check it and try again.');
        } else {
          setProblem(commandProblem(e, what));
        }
      } finally {
        setBusy(false);
      }
    },
    [api, busy, loadHistory, match.id, version],
  );

  const names = sideNames(match);
  function correct(row: SheetRow, field: CorrectableField, value: string | null) {
    void run(
      'Correction',
      (v) => api.correctRally(match.id, v, row.rally_id, field, value),
      () => `Rally ${row.number} corrected. The score sheet is up to date.`,
    );
  }

  return (
    <div className="stack">
      {problem ? (
        <p role="alert" className="notice notice--error">
          {problem}
        </p>
      ) : null}
      <ScoreAnnouncer message={said} />
      <ScoreSheetTable
        match={match}
        sheet={sheet}
        rowActions={(row) => <RallyCorrections row={row} names={names} onCorrect={correct} />}
      />
      <p>
        <button
          type="button"
          className="button button--secondary"
          aria-busy={busy}
          onClick={() => void run('Undo', (v) => api.undo(match.id, v), () => 'Last change undone.')}
        >
          Undo last change
        </button>
      </p>
      <section aria-labelledby="history-title" className="stack">
        <h2 id="history-title">Correction history</h2>
        {historyFailed ? (
          <div className="stack">
            <p>The correction history could not be loaded.</p>
            <p>
              <button type="button" className="button button--secondary" onClick={() => void loadHistory()}>
                Reload the history
              </button>
            </p>
          </div>
        ) : history ? (
          <CorrectionHistory items={history} match={match} />
        ) : (
          <p>Loading the history…</p>
        )}
      </section>
    </div>
  );
}
