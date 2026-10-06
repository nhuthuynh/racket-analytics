'use client';

// Quick Tag T-01 (ST-027; FR-050; DES FR-UX-60). The video is on top; below it the rally control
// bar: Rally start, Rally end, winner side, an optional responsible player and the ending.
// Choosing the ending saves the rally. Every control is a button of at least 48 px (NFR-028) and
// nothing needs dragging (NFR-030). The score shown at once is provisional (NFR-012a); the
// server's sheet replaces it (FR-049). After a tag the video keeps playing from the end of the
// rally, ready to mark the next start (FR-050 R1 behaviour).
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { Match, ParticipantSlot } from '@/lib/api/types';
import { initialTagging, taggingReducer, type Pending } from '@/lib/tagging/reducer';
import { currentCall } from '@/lib/tagging/score';
import { gameStatus, sideNames, tagLine, winnerWord } from '@/lib/tagging/view';
import { ENDING_LABELS, ENDINGS, otherSide, type Ending, type ScoreSheet, type Side } from '@/lib/tagging/types';
import { commandProblem, tagFailureMessage as failureMessage } from '@/lib/tagging/messages';
import {
  actionForKey,
  DEFAULT_KEYMAP,
  loadKeyMap,
  loadSingleKeys,
  remapKey,
  saveKeyMap,
  saveSingleKeys,
  type KeyAction,
  type KeyMap,
} from '@/lib/tagging/keymap';
import { GameStartForm } from './GameStartForm';
import { KeyMapDialog } from './KeyMapDialog';
import { ScoreAnnouncer } from './ScoreAnnouncer';

export type QuickTagApi = Pick<ApiClient, 'tagRally' | 'startGame' | 'getScoreSheet' | 'undo'>;

export function QuickTag({
  match,
  initialSheet,
  initialVersion,
  api = browserApi,
  videoSrc,
  clock,
}: {
  match: Match;
  initialSheet: ScoreSheet;
  initialVersion: number;
  api?: QuickTagApi;
  /** A playable URL for the match video, or null when none can be had. */
  videoSrc: string | null;
  /** Test seam: the current time in ms. Default: the video's time, else this page's clock. */
  clock?: () => number;
}) {
  const names = useMemo(() => sideNames(match), [match]);
  const status0 = gameStatus(initialSheet);
  const [state, dispatch] = useReducer(
    taggingReducer,
    initialTagging({
      sheet: initialSheet,
      version: initialVersion,
      firstServingSide: status0.firstServingSide ?? 'A',
      game: Math.max(1, status0.current),
    }),
  );
  const status = gameStatus(state.sheet);
  const [gameOverSeen, setGameOverSeen] = useState(false);
  const [singleKeys, setSingleKeys] = useState(true);
  const [keysOpen, setKeysOpen] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const opener = useRef<HTMLElement | null>(null);
  const keysButton = useRef<HTMLButtonElement>(null);
  const [refocusKeys, setRefocusKeys] = useState(false);
  useEffect(() => {
    if (keysOpen || !refocusKeys) return;
    setRefocusKeys(false);
    const back = opener.current;
    // "?" pressed with nothing focused: the opener was the page body, so go to the button
    // that opens the same dialog.
    if (back && back.isConnected && back !== document.body) back.focus();
    else keysButton.current?.focus();
  }, [keysOpen, refocusKeys]);
  const video = useRef<HTMLVideoElement>(null);
  const [keyMap, setKeyMap] = useState<KeyMap>(DEFAULT_KEYMAP);
  useEffect(() => {
    setSingleKeys(loadSingleKeys(typeof window === 'undefined' ? null : window.localStorage));
    setKeyMap(loadKeyMap(typeof window === 'undefined' ? null : window.localStorage));
  }, []);
  const opened = useRef(0);
  useEffect(() => {
    opened.current = performance.now();
  }, []);

  const now = useCallback((): number => {
    if (clock) return clock();
    const v = video.current;
    if (v && v.readyState > 0) return Math.floor(v.currentTime * 1000);
    return Math.floor(performance.now() - opened.current);
  }, [clock]);

  const refresh = useCallback(() => api.getScoreSheet(match.id), [api, match.id]);

  // One request per pending tag; a re-render never sends it twice.
  const sent = useRef<Pending | null>(null);
  useEffect(() => {
    const pending = state.pending;
    if (!pending || sent.current === pending) return;
    sent.current = pending;
    void (async () => {
      try {
        const r = await api.tagRally(match.id, pending.baseVersion, pending.tag);
        dispatch({ type: 'confirmed', sheet: r.sheet, version: r.version });
        const saved = r.sheet.rows[r.sheet.rows.length - 1];
        if (saved) setAnnouncement(tagLine(saved, names.mySide));
      } catch (e) {
        if (e instanceof ApiError && (e.code === 'stale_match' || e.code === 'game_over')) {
          try {
            const latest = await refresh();
            if (e.code === 'game_over') {
              setGameOverSeen(true);
              dispatch({ type: 'failed', message: 'This game is over. Start the next game to go on tagging.' });
              dispatch({ type: 'confirmed', sheet: latest.sheet, version: latest.version ?? pending.baseVersion });
              return;
            }
            dispatch({ type: 'stale', sheet: latest.sheet, version: latest.version ?? pending.baseVersion });
            return;
          } catch {
            dispatch({ type: 'failed', message: 'This match was changed on another device. Reload the page to see the latest score.' });
            return;
          }
        }
        dispatch({ type: 'failed', message: failureMessage(e) });
      }
    })();
  }, [api, match.id, names.mySide, refresh, state.pending]);

  const tagging = !status.matchOver;
  const undoing = useRef(false);
  const undo = useCallback(async () => {
    if (undoing.current || state.pending) return;
    undoing.current = true;
    try {
      const r = await api.undo(match.id, state.version);
      dispatch({ type: 'confirmed', sheet: r.sheet, version: r.version });
      setAnnouncement('Last change undone.');
    } catch (e) {
      dispatch({ type: 'failed', message: commandProblem(e, 'Undo') });
    } finally {
      undoing.current = false;
    }
  }, [api, match.id, state.pending, state.version]);
  // Keyboard tagging (ST-028a): document-level, so focus can stay on any control (E2E-02-03).
  const onKey = useRef<(action: KeyAction) => void>(() => {});
  onKey.current = (action: KeyAction) => {
    const v = video.current;
    const fps = match.media?.fps && match.media.fps > 0 ? match.media.fps : 30;
    const players = names.players;
    switch (action) {
      case 'show_keys':
        opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        setKeysOpen(true);
        return;
      case 'play_pause':
        if (v) void (v.paused ? v.play().catch(() => {}) : v.pause());
        return;
      case 'back_5s':
      case 'forward_5s':
      case 'frame_back':
      case 'frame_forward': {
        if (!v) return;
        const step = action.startsWith('frame') ? 1 / fps : 5;
        v.currentTime = Math.max(0, v.currentTime + (action.endsWith('back') || action === 'back_5s' ? -step : step));
        return;
      }
      case 'undo':
        void undo();
        return;
      default:
    }
    if (!tagging) return;
    if (action === 'mark_start') dispatch({ type: 'mark_start', ms: now() });
    else if (action === 'mark_end') dispatch({ type: 'mark_end', ms: now() });
    else if (action === 'clear') dispatch({ type: 'clear' });
    else if (action === 'winner_mine') dispatch({ type: 'choose_winner', side: names.mySide });
    else if (action === 'winner_other') dispatch({ type: 'choose_winner', side: otherSide(names.mySide) });
    else if (action.startsWith('player_')) {
      const p = players[Number(action.slice(7)) - 1];
      if (p) dispatch({ type: 'choose_player', slot: p.slot });
    } else if (action.startsWith('ending_')) dispatch({ type: 'choose_ending', ending: action.slice(7) as Ending });
  };
  useEffect(() => {
    if (keysOpen) return;
    const listener = (e: KeyboardEvent) => {
      const target = e.target instanceof HTMLElement ? e.target : null;
      const action = actionForKey(
        {
          key: e.key,
          ctrlKey: e.ctrlKey,
          metaKey: e.metaKey,
          altKey: e.altKey,
          targetTag: target?.tagName ?? 'BODY',
          targetEditable: target?.isContentEditable ?? false,
        },
        { singleKeys, map: keyMap },
      );
      if (!action) return;
      e.preventDefault();
      onKey.current(action);
    };
    document.addEventListener('keydown', listener);
    return () => document.removeEventListener('keydown', listener);
  }, [keyMap, keysOpen, singleKeys]);

  const needsGame = status.current === 0 || (status.over && !status.matchOver) || (gameOverSeen && status.over);
  const nextGame = status.current === 0 ? 1 : status.current + 1;

  async function startGame(firstServingSide: Side): Promise<string | null> {
    try {
      const r = await api.startGame(match.id, state.version, { first_serving_side: firstServingSide, ends_switched: false });
      setGameOverSeen(false);
      dispatch({ type: 'game_started', sheet: r.sheet, version: r.version, game: nextGame, firstServingSide });
      return null;
    } catch (e) {
      const ref = e instanceof ApiError && e.supportRef ? ` Reference: ${e.supportRef}` : '';
      return `Game ${nextGame} could not be started. Try again.${ref}`;
    }
  }

  const call = state.pending
    ? state.pending.optimisticCall
    : currentCall(state.sheet.rows, state.game, state.firstServingSide)?.call ?? null;
  const serving = currentCall(state.sheet.rows, state.game, state.firstServingSide)?.servingSide ?? null;
  const last = state.sheet.rows[state.sheet.rows.length - 1];
  const lastLine = last && !state.pending ? tagLine(last, names.mySide) : null;
  const d = state.draft;
  const busy = state.pending !== null;

  function choosePlayer(slot: ParticipantSlot) {
    dispatch({ type: 'choose_player', slot: d.responsible_player === slot ? null : slot });
  }

  return (
    <div className="stack quick-tag">
      <div className="quick-tag__video">
        {videoSrc ? (
          // The match video is the player's own recording; tagging needs the picture only.
          <video ref={video} src={videoSrc} controls playsInline preload="auto" className="quick-tag__player" />
        ) : (
          <p className="notice notice--info">
            The video cannot be played here right now. Rally times come from this page&apos;s clock.
          </p>
        )}
      </div>

      <div role="group" aria-label="Score" className="quick-tag__score">
        <p className="quick-tag__game">{status.matchOver ? 'Match over' : `Game ${state.game}`}</p>
        {/* Before a game is started the first server is the question being asked, so neither
            the call nor the server is shown as fact (PD-S2R1-06, HAX G1/G2). */}
        {call && !needsGame ? <p className="quick-tag__call">{call}</p> : null}
        {serving && !status.matchOver && !needsGame ? (
          <p className="quick-tag__serving">{serving === names.mySide ? 'Your side serves' : 'Other side serves'}</p>
        ) : null}
        {busy ? <p className="quick-tag__saving">Saving…</p> : null}
        <p className="quick-tag__label">{state.sheet.label}</p>
      </div>
      <ScoreAnnouncer message={announcement || lastLine || ''} />

      {state.notice ? (
        <p role="alert" className="notice notice--error">
          {state.notice}
        </p>
      ) : null}

      {status.matchOver ? (
        <div className="stack">
          <p>{`Match won by ${winnerWord(status.matchWinner, names.mySide)}.`}</p>
          <p>
            <Link href={`/matches/${match.id}/sheet`} className="button">
              Open the score sheet
            </Link>
          </p>
        </div>
      ) : needsGame ? (
        <GameStartForm
          key={nextGame}
          game={nextGame}
          mySide={names.mySide}
          label={names.label}
          intro={status.over && status.lastWinner ? `Game ${status.current} won by ${winnerWord(status.lastWinner, names.mySide)}.` : null}
          onStart={startGame}
        />
      ) : (
        <div className="quick-tag__bar" role="group" aria-label="Tag the rally">
          <div className="quick-tag__row">
            <button type="button" className="button button--secondary tag-button" aria-pressed={d.start_ms !== undefined} onClick={() => dispatch({ type: 'mark_start', ms: now() })}>
              Rally start
            </button>
            <button type="button" className="button button--secondary tag-button" aria-pressed={d.end_ms !== undefined} onClick={() => dispatch({ type: 'mark_end', ms: now() })}>
              Rally end
            </button>
          </div>
          <div className="quick-tag__row" role="group" aria-label="Won by">
            {([names.mySide, otherSide(names.mySide)] as const).map((side) => (
              <button key={side} type="button" className="button button--secondary tag-button" aria-pressed={d.winning_side === side} onClick={() => dispatch({ type: 'choose_winner', side })}>
                {names.label(side)}
              </button>
            ))}
          </div>
          {names.players.length > 0 ? (
            <div className="quick-tag__row" role="group" aria-label="Who hit it (optional)">
              {names.players.map((p) => (
                <button key={p.slot} type="button" className="button button--secondary tag-button" aria-pressed={d.responsible_player === p.slot} onClick={() => choosePlayer(p.slot)}>
                  {p.nickname}
                </button>
              ))}
            </div>
          ) : null}
          <div className="quick-tag__row" role="group" aria-label="Ending (saves the rally)">
            {ENDINGS.map((ending: Ending) => (
              <button key={ending} type="button" className="button tag-button" onClick={() => dispatch({ type: 'choose_ending', ending })}>
                {ENDING_LABELS[ending]}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="quick-tag__row">
        <button type="button" className="button button--secondary" onClick={() => void undo()}>
          Undo
        </button>
        <button
          ref={keysButton}
          type="button"
          className="button button--secondary"
          onClick={(e) => {
            opener.current = e.currentTarget;
            setKeysOpen(true);
          }}
        >
          Keyboard shortcuts
        </button>
        <Link href={`/matches/${match.id}/sheet`} className="button button--secondary">
          Score sheet
        </Link>
      </div>
      {keysOpen ? (
        <KeyMapDialog
          playerNames={names.players.map((p) => p.nickname)}
          singleKeys={singleKeys}
          onSingleKeys={(on) => {
            setSingleKeys(on);
            saveSingleKeys(window.localStorage, on);
          }}
          map={keyMap}
          onRemap={(action, key) => {
            const next = remapKey(keyMap, action, key);
            if ('error' in next) return next.error;
            setKeyMap(next);
            saveKeyMap(window.localStorage, next);
            return null;
          }}
          onReset={() => {
            setKeyMap(DEFAULT_KEYMAP);
            saveKeyMap(window.localStorage, DEFAULT_KEYMAP);
          }}
          onClose={() => {
            // Focus moves in an effect once the dialog is gone: while the modal is still open
            // the opener is inert and focus() does nothing (PD-S2R1-04, SC 2.4.3).
            setKeysOpen(false);
            setRefocusKeys(true);
          }}
        />
      ) : null}
    </div>
  );
}
