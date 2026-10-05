// ST-028a key map (FR-051; DES FR-UX-61; sprint-02 §5 key-map store). Negative cases first:
// turning single-key shortcuts off disables single character keys only; typing in a field and
// modifier chords never trigger a shortcut.
import { describe, expect, it } from 'vitest';
import { actionForKey, DEFAULT_KEYMAP, keyMapRows, loadSingleKeys, saveSingleKeys, type KeyEventLike } from '@/lib/tagging/keymap';

const ev = (key: string, over: Partial<KeyEventLike> = {}): KeyEventLike => ({
  key, ctrlKey: false, metaKey: false, altKey: false, targetTag: 'BODY', targetEditable: false, ...over,
});

describe('actionForKey', () => {
  it('turning single-key shortcuts off disables every character key', () => {
    for (const key of ['s', 'e', '1', '2', 'w', 'u', 'o', 'f', 'r', 'z', '?', 'j', 'l', ',', '.', '3']) {
      expect(actionForKey(ev(key), { singleKeys: false })).toBeNull();
    }
  });
  it('...but not the non-character keys (Space, Escape)', () => {
    expect(actionForKey(ev(' '), { singleKeys: false })).toBe('play_pause');
    expect(actionForKey(ev('Escape'), { singleKeys: false })).toBe('clear');
  });
  it('never fires while typing in a field, or with Ctrl, Meta or Alt', () => {
    expect(actionForKey(ev('s', { targetTag: 'INPUT' }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev('s', { targetTag: 'TEXTAREA' }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev('s', { targetEditable: true }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev('s', { ctrlKey: true }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev('z', { metaKey: true }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev('1', { altKey: true }), { singleKeys: true })).toBeNull();
  });
  it('Space on a button or link is the control own activation, not play/pause', () => {
    expect(actionForKey(ev(' ', { targetTag: 'BUTTON' }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev(' ', { targetTag: 'A' }), { singleKeys: true })).toBeNull();
    expect(actionForKey(ev(' ', { targetTag: 'VIDEO' }), { singleKeys: true })).toBeNull();
  });
  it('maps the FR-UX-61 keys, case-insensitive', () => {
    const on = { singleKeys: true };
    expect(actionForKey(ev('S'), on)).toBe('mark_start');
    expect(actionForKey(ev('e'), on)).toBe('mark_end');
    expect(actionForKey(ev('1'), on)).toBe('winner_mine');
    expect(actionForKey(ev('2'), on)).toBe('winner_other');
    expect(actionForKey(ev('w'), on)).toBe('ending_winner');
    expect(actionForKey(ev('u'), on)).toBe('ending_unforced_error');
    expect(actionForKey(ev('o'), on)).toBe('ending_forced_error');
    expect(actionForKey(ev('f'), on)).toBe('ending_fault');
    expect(actionForKey(ev('r'), on)).toBe('ending_replay');
    expect(actionForKey(ev('z'), on)).toBe('undo');
    expect(actionForKey(ev('?'), on)).toBe('show_keys');
    expect(actionForKey(ev('j'), on)).toBe('back_5s');
    expect(actionForKey(ev('l'), on)).toBe('forward_5s');
    expect(actionForKey(ev(','), on)).toBe('frame_back');
    expect(actionForKey(ev('.'), on)).toBe('frame_forward');
    expect(actionForKey(ev('3'), on)).toBe('player_1');
    expect(actionForKey(ev('6'), on)).toBe('player_4');
    expect(actionForKey(ev('x'), on)).toBeNull();
  });
  it('a ? typed on a button still opens the key map (it is not a button key)', () => {
    expect(actionForKey(ev('?', { targetTag: 'BUTTON' }), { singleKeys: true })).toBe('show_keys');
  });
});

describe('key map rows and the stored preference', () => {
  it('lists every shortcut with its key and what it does', () => {
    const rows = keyMapRows(['Ivy', 'Dana', 'Carlos', 'Bo']);
    expect(rows).toContainEqual({ key: 'S', does: 'Rally start' });
    expect(rows).toContainEqual({ key: '1', does: 'Won by your side' });
    expect(rows).toContainEqual({ key: '3', does: 'Player: Ivy' });
    expect(rows).toContainEqual({ key: 'Space', does: 'Play or pause the video' });
    expect(rows).toHaveLength(Object.keys(DEFAULT_KEYMAP).length + 2);
  });
  it('reads "on" when nothing is stored or storage is blocked, and remembers "off"', () => {
    const store = new Map<string, string>();
    const s = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
    expect(loadSingleKeys(s)).toBe(true);
    saveSingleKeys(s, false);
    expect(loadSingleKeys(s)).toBe(false);
    const blocked = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
    expect(loadSingleKeys(blocked)).toBe(true);
    expect(() => saveSingleKeys(blocked, false)).not.toThrow();
    expect(loadSingleKeys(null)).toBe(true);
  });
});
