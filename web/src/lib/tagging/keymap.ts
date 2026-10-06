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

export type CharAction = Exclude<KeyAction, 'play_pause' | 'clear'>;
export type KeyMap = Readonly<Record<CharAction, string>>;

/** Character key per action (lower case). FR-UX-61 plus O, R and 3-6 (judgment, logged). */
export const DEFAULT_KEYMAP: KeyMap = {
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

export function actionForKey(e: KeyEventLike, prefs: { singleKeys: boolean; map?: KeyMap }): KeyAction | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  if (TYPING.has(e.targetTag) || e.targetEditable) return null;
  if (e.key === 'Escape') return 'clear';
  if (e.key === ' ') return OWNS_SPACE.has(e.targetTag) ? null : 'play_pause';
  if (!prefs.singleKeys || e.key.length !== 1) return null;
  const key = e.key.toLowerCase();
  const map = prefs.map ?? DEFAULT_KEYMAP;
  return (Object.keys(map) as CharAction[]).find((action) => map[action] === key) ?? null;
}

export const DOES: Readonly<Record<CharAction, string>> = {
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
export function keyMapRows(playerNames: readonly string[], map: KeyMap = DEFAULT_KEYMAP): { key: string; does: string }[] {
  const rows: { key: string; does: string }[] = [{ key: 'Space', does: 'Play or pause the video' }];
  for (const [action, key] of Object.entries(map) as [CharAction, string][]) {
    const player = /^player_(\d)$/.exec(action);
    if (player) {
      const name = playerNames[Number(player[1]) - 1];
      if (name) rows.push({ key: key.toUpperCase(), does: `Player: ${name}` });
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

// ST-028b: remapping (SC 2.1.4 "remap"). One printable character per action, no two actions on
// one key; Space, Esc, Enter and Tab stay with the browser and the dialog.
const PRINTABLE = /^[^\s]$/u;

export function remapKey(map: KeyMap, action: CharAction, key: string): KeyMap | { error: string } {
  if (!PRINTABLE.test(key)) return { error: 'Choose a letter, number or symbol key.' };
  const k = key.toLowerCase();
  const other = (Object.keys(map) as CharAction[]).find((a) => a !== action && map[a] === k);
  if (other) return { error: `${k.toUpperCase()} is already used for ${DOES[other].replace(/ \(saves the rally\)$/, '')}.` };
  return map[action] === k ? map : { ...map, [action]: k };
}

const MAP_KEY = 'racket.tagging.keymap';

/** The stored remap, or the defaults when nothing valid is stored (blocked, broken, duplicated). */
export function loadKeyMap(store: PrefStore | null | undefined): KeyMap {
  try {
    const raw = store?.getItem(MAP_KEY);
    if (!raw) return DEFAULT_KEYMAP;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const map = { ...DEFAULT_KEYMAP } as Record<CharAction, string>;
    for (const action of Object.keys(DEFAULT_KEYMAP) as CharAction[]) {
      const v = parsed[action];
      if (v === undefined) continue;
      if (typeof v !== 'string' || !PRINTABLE.test(v)) return DEFAULT_KEYMAP;
      map[action] = v.toLowerCase();
    }
    const keys = Object.values(map);
    return new Set(keys).size === keys.length ? map : DEFAULT_KEYMAP;
  } catch {
    return DEFAULT_KEYMAP;
  }
}

export function saveKeyMap(store: PrefStore | null | undefined, map: KeyMap): void {
  try {
    store?.setItem(MAP_KEY, JSON.stringify(map));
  } catch {
    // Blocked storage: the map lasts for this page only.
  }
}
