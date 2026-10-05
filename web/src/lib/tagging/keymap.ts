// Keyboard tagging (ST-028a; FR-051; DES FR-UX-61). One key per action; single character keys
// can be turned off (WCAG SC 2.1.4 "turn off" option; remapping is ST-028b). Space and Escape
// are not character keys and stay on. A shortcut never fires while typing in a field or with
// Ctrl, Meta or Alt held, so browser and screen-reader commands keep working.

export type KeyAction =
  | 'mark_start'
  | 'mark_end'
  | 'winner_mine'
  | 'winner_other'
  | 'player_1'
  | 'player_2'
  | 'player_3'
  | 'player_4'
  | 'ending_winner'
  | 'ending_unforced_error'
  | 'ending_forced_error'
  | 'ending_fault'
  | 'ending_replay'
  | 'undo'
  | 'show_keys'
  | 'back_5s'
  | 'forward_5s'
  | 'frame_back'
  | 'frame_forward'
  | 'play_pause'
  | 'clear';

type CharAction = Exclude<KeyAction, 'play_pause' | 'clear'>;

/** Character key per action (lower case). FR-UX-61 plus O, R and 3-6 (judgment, logged). */
export const DEFAULT_KEYMAP: Readonly<Record<CharAction, string>> = {
  mark_start: 's',
  mark_end: 'e',
  winner_mine: '1',
  winner_other: '2',
  player_1: '3',
  player_2: '4',
  player_3: '5',
  player_4: '6',
  ending_winner: 'w',
  ending_unforced_error: 'u',
  ending_forced_error: 'o',
  ending_fault: 'f',
  ending_replay: 'r',
  undo: 'z',
  show_keys: '?',
  back_5s: 'j',
  forward_5s: 'l',
  frame_back: ',',
  frame_forward: '.',
};

const BY_KEY = new Map(Object.entries(DEFAULT_KEYMAP).map(([action, key]) => [key, action as CharAction]));

export interface KeyEventLike {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  /** Upper-case tag name of the event target. */
  targetTag: string;
  targetEditable: boolean;
}

const TYPING = new Set(['INPUT', 'TEXTAREA', 'SELECT']);
/** Space activates these itself (and the video's own controls handle Space when it has focus). */
const OWNS_SPACE = new Set(['BUTTON', 'A', 'SUMMARY', 'VIDEO', 'AUDIO']);

export function actionForKey(e: KeyEventLike, prefs: { singleKeys: boolean }): KeyAction | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  if (TYPING.has(e.targetTag) || e.targetEditable) return null;
  if (e.key === 'Escape') return 'clear';
  if (e.key === ' ') return OWNS_SPACE.has(e.targetTag) ? null : 'play_pause';
  if (!prefs.singleKeys || e.key.length !== 1) return null;
  return BY_KEY.get(e.key.toLowerCase()) ?? null;
}

const DOES: Readonly<Record<CharAction, string>> = {
  mark_start: 'Rally start',
  mark_end: 'Rally end',
  winner_mine: 'Won by your side',
  winner_other: 'Won by the other side',
  player_1: 'Player',
  player_2: 'Player',
  player_3: 'Player',
  player_4: 'Player',
  ending_winner: 'Ending: winner (saves the rally)',
  ending_unforced_error: 'Ending: unforced error (saves the rally)',
  ending_forced_error: 'Ending: forced error (saves the rally)',
  ending_fault: 'Ending: fault (saves the rally)',
  ending_replay: 'Ending: replay (saves the rally)',
  undo: 'Undo the last change',
  show_keys: 'Show these shortcuts',
  back_5s: 'Back 5 seconds',
  forward_5s: 'Forward 5 seconds',
  frame_back: 'Back one frame',
  frame_forward: 'Forward one frame',
};

/** Rows of the key map dialog (K-01), players named in slot order. */
export function keyMapRows(playerNames: readonly string[]): { key: string; does: string }[] {
  const rows: { key: string; does: string }[] = [{ key: 'Space', does: 'Play or pause the video' }];
  for (const [action, key] of Object.entries(DEFAULT_KEYMAP) as [CharAction, string][]) {
    const player = /^player_(\d)$/.exec(action);
    if (player) {
      const name = playerNames[Number(player[1]) - 1];
      if (name) rows.push({ key, does: `Player: ${name}` });
      continue;
    }
    rows.push({ key: key.toUpperCase(), does: DOES[action] });
  }
  rows.push({ key: 'Esc', does: 'Clear the marks of the rally being tagged' });
  return rows;
}

interface PrefStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const PREF_KEY = 'racket.tagging.single-keys';

/** The "use single-key shortcuts" preference; on unless the player turned it off. */
export function loadSingleKeys(store: PrefStore | null | undefined): boolean {
  try {
    return store?.getItem(PREF_KEY) !== 'off';
  } catch {
    return true;
  }
}

export function saveSingleKeys(store: PrefStore | null | undefined, on: boolean): void {
  try {
    store?.setItem(PREF_KEY, on ? 'on' : 'off');
  } catch {
    // Blocked storage: the choice lasts for this page only.
  }
}
