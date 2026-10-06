'use client';

// The score sheet screen's client part (ST-030, ST-031). Holds the sheet and its version for
// If-Match; "Undo last change" (FR-052) replaces the sheet with the server's, reloads the
// correction history H-01 and says so in the polite status region. A stale version reloads the
// sheet and tells the player (IT-02-04).
import { useCallback, useEffect, useRef, useState } from 'react';
import { ScoreAnnouncer } from '@/components/tagging/ScoreAnnouncer';
import { ApiError, type ApiClient, type RallyDecision } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { commandProblem } from '@/lib/tagging/messages';
import type { Match } from '@/lib/api/types';
import type { CorrectableField, CorrectionValue, HistoryItem, RallyMedia, ScoreSheet, SheetRow, Versioned } from '@/lib/tagging/types';
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
  /** The "Watch rally n" button that opened V-01: focus goes back to it if the video fails (PD-S2R1-05). */
  const watchOpener = useRef<HTMLElement | null>(null);
  const [refocusWatch, setRefocusWatch] = useState(false);

  useEffect(() => {
    if (!refocusWatch || playing) return;
    setRefocusWatch(false);
    if (watchOpener.current?.isConnected) watchOpener.current.focus();
  }, [playing, refocusWatch]);

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

  function decide(row: SheetRow, decision: RallyDecision) {
    void run(
      'Decision',
      (v) => (api.resolveRally ?? browserApi.resolveRally)(match.id, v, row.rally_id, decision),
      () =>
        decision === 'withdraw'
          ? `Rally ${row.number} removed. It stays in the correction history.`
          : decision === 'move_to_previous_game'
            ? `Rally ${row.number} moved back to game ${row.game - 1}.`
            : `Rally ${row.number} moved to the next game.`,
    );
  }

  /**
   * Which move a "needs your decision" row can take (api-sprint-02 §3 Resolution), and, when none,
   * why (C3-03, Gherkin §7.7). C-03: while the game before the row's game is not over, the next
   * game is refused by the server, and only the earliest kept rally of the row's game may move
   * back. Otherwise the rally is past the end of its game and moves to the next one, but only the
   * latest kept rally of the game (by time on the video), so no rally of the game is left behind
   * it (PE-S2-R2-01; the server refuses others with decision/not_last_in_game, PE-S2-R3-01).
   */
  function moveFor(row: SheetRow): { decision: RallyDecision | null; why: string | null } {
    const sameGame = sheet.rows.filter((r) => r.game === row.game);
    const previous = sheet.games?.find((g) => g.number === row.game - 1);
    if (!previous || previous.winner !== null) {
      const last = sameGame.reduce<SheetRow | null>((a, r) => (a === null || r.start_ms > a.start_ms ? r : a), null);
      if (!last || last.rally_id === row.rally_id) return { decision: 'move_to_next_game', why: null };
      return {
        decision: null,
        why: `Only the last rally of game ${row.game} can move to the next game. Decide rally ${last.number} first.`,
      };
    }
    const first = sameGame.reduce<SheetRow | null>((a, r) => (a === null || r.start_ms < a.start_ms ? r : a), null);
    if (!first || first.rally_id === row.rally_id) return { decision: 'move_to_previous_game', why: null };
    return {
      decision: null,
      why: `Only the first rally of game ${row.game} can move back to game ${row.game - 1}. Decide rally ${first.number} first.`,
    };
  }

  async function watch(row: SheetRow, opener: HTMLElement) {
    watchOpener.current = opener;
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

  function correct(row: SheetRow, field: CorrectableField, value: CorrectionValue) {
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
            setRefocusWatch(true);
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
              <MoveOffer row={row} offer={moveFor(row)} onDecide={decide} />
            ) : null}
            <button type="button" className="button button--secondary rally-fix__button" onClick={(e) => void watch(row, e.currentTarget)}>
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

/** The decision buttons of a "needs your decision" row (ST-032, C-03, C3-03). */
function MoveOffer({
  row,
  offer,
  onDecide,
}: {
  row: SheetRow;
  offer: { decision: RallyDecision | null; why: string | null };
  onDecide: (row: SheetRow, decision: RallyDecision) => void;
}) {
  return (
    <span className="rally-fix">
      {offer.decision === 'move_to_next_game' ? (
        <button type="button" className="button rally-fix__button" onClick={() => onDecide(row, 'move_to_next_game')}>
          {`Move rally ${row.number} to the next game`}
        </button>
      ) : offer.decision === 'move_to_previous_game' ? (
        <button type="button" className="button rally-fix__button" onClick={() => onDecide(row, 'move_to_previous_game')}>
          {`Move rally ${row.number} back to game ${row.game - 1}`}
        </button>
      ) : null}
      <button type="button" className="button button--secondary rally-fix__button" onClick={() => onDecide(row, 'withdraw')}>
        {`Remove rally ${row.number}`}
      </button>
      {offer.why ? <span className="rally-fix__why">{offer.why}</span> : null}
    </span>
  );
}
