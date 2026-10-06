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
import type { CorrectableField, HistoryItem, RallyMedia, ScoreSheet, SheetRow, Versioned } from '@/lib/tagging/types';
import { sideNames } from '@/lib/tagging/view';
import { CorrectionHistory } from './CorrectionHistory';
import { RallyCorrections } from './RallyCorrections';
import { RallyVideo } from './RallyVideo';
import { ScoreSheetTable } from './ScoreSheetTable';

export type SheetApi = Pick<ApiClient, 'undo' | 'corrections' | 'correctRally' | 'getScoreSheet' | 'rallyMedia'> &
  Partial<Pick<ApiClient, 'resolveRally'>>;

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
  const [playing, setPlaying] = useState<{ number: number; media: RallyMedia } | null>(null);

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

  function decide(row: SheetRow, decision: 'withdraw' | 'move_to_next_game') {
    void run(
      'Decision',
      (v) => (api.resolveRally ?? browserApi.resolveRally)(match.id, v, row.rally_id, decision),
      () =>
        decision === 'withdraw'
          ? `Rally ${row.number} removed. It stays in the correction history.`
          : `Rally ${row.number} moved to the next game.`,
    );
  }

  async function watch(row: SheetRow) {
    setProblem(null);
    try {
      // A fresh short-lived link every time (NFR-055): an old one may have expired.
      const media = await api.rallyMedia(match.id, row.rally_id);
      setPlaying({ number: row.number, media });
    } catch (e) {
      const ref = e instanceof ApiError && e.supportRef ? ` Reference: ${e.supportRef}` : '';
      setPlaying(null);
      setProblem(`The video for rally ${row.number} could not be opened. Try again.${ref}`);
    }
  }

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
      {playing ? (
        <RallyVideo
          number={playing.number}
          media={playing.media}
          codec={match.media?.video_codec}
          onBroken={(why) => {
            const n = playing.number;
            setPlaying(null);
            setProblem(
              why === 'unplayable'
                ? 'This browser cannot play this video. Try another browser, such as Safari or Chrome. The score sheet still works here.'
                : `This video link no longer works. Choose 'Watch rally ${n}' again.`,
            );
          }}
        />
      ) : null}
      <ScoreSheetTable
        match={match}
        sheet={sheet}
        rowActions={(row) => (
          <>
            {row.marker === 'needs_decision' ? (
              <span className="rally-fix">
                <button type="button" className="button rally-fix__button" onClick={() => decide(row, 'move_to_next_game')}>
                  {`Move rally ${row.number} to the next game`}
                </button>
                <button type="button" className="button button--secondary rally-fix__button" onClick={() => decide(row, 'withdraw')}>
                  {`Remove rally ${row.number}`}
                </button>
              </span>
            ) : null}
            <button type="button" className="button button--secondary rally-fix__button" onClick={() => void watch(row)}>
              {`Watch rally ${row.number}`}
            </button>
            <RallyCorrections row={row} names={names} onCorrect={correct} />
          </>
        )}
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
