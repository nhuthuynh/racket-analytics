// ST-028b remap tagging keys (FR-051; WCAG SC 2.1.4 "remap" option; sprint-02 §5 key-map store
// test 1). Negative cases first: a key already used is refused, as is a key that is not one
// printable character; a stored map that is broken falls back to the defaults.
import { describe, expect, it } from 'vitest';
import { actionForKey, DEFAULT_KEYMAP, keyMapRows, loadKeyMap, remapKey, saveKeyMap } from '@/lib/tagging/keymap';

const ev = (key: string) => ({ key, ctrlKey: false, metaKey: false, altKey: false, targetTag: 'BODY', targetEditable: false });

describe('remapKey', () => {
  it('refuses a key that another action uses, and says which', () => {
    expect(remapKey(DEFAULT_KEYMAP, 'mark_start', 'E')).toEqual({ error: 'E is already used for Rally end.' });
  });
  it('refuses Space, Esc, Enter, Tab and anything longer than one character', () => {
    for (const key of [' ', 'Escape', 'Enter', 'Tab', 'ArrowLeft', '']) {
      expect(remapKey(DEFAULT_KEYMAP, 'mark_start', key)).toEqual({ error: 'Choose a letter, number or symbol key.' });
    }
  });
  it('remaps an action, lower-cased; the old key stops working and the new one works', () => {
    const r = remapKey(DEFAULT_KEYMAP, 'mark_start', 'A');
    if ('error' in r) throw new Error(r.error);
    expect(r.mark_start).toBe('a');
    expect(actionForKey(ev('a'), { singleKeys: true, map: r })).toBe('mark_start');
    expect(actionForKey(ev('s'), { singleKeys: true, map: r })).toBeNull();
    expect(keyMapRows([], r)).toContainEqual({ key: 'A', does: 'Rally start' });
  });
  it('choosing the same key again is allowed (no change)', () => {
    expect(remapKey(DEFAULT_KEYMAP, 'mark_start', 's')).toEqual(DEFAULT_KEYMAP);
  });
});

describe('stored key map', () => {
  const store = () => {
    const m = new Map<string, string>();
    return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
  };
  it('a broken or duplicated stored map gives the defaults', () => {
    const s = store();
    s.setItem('racket.tagging.keymap', '{"mark_start":"e"}');
    expect(loadKeyMap(s)).toEqual(DEFAULT_KEYMAP);
    s.setItem('racket.tagging.keymap', 'not json');
    expect(loadKeyMap(s)).toEqual(DEFAULT_KEYMAP);
    s.setItem('racket.tagging.keymap', '{"mark_start":"ab"}');
    expect(loadKeyMap(s)).toEqual(DEFAULT_KEYMAP);
  });
  it('keeps a valid remap', () => {
    const s = store();
    const r = remapKey(DEFAULT_KEYMAP, 'undo', 'x');
    if ('error' in r) throw new Error(r.error);
    saveKeyMap(s, r);
    expect(loadKeyMap(s).undo).toBe('x');
  });
});

describe('stored key map, swaps', () => {
  it('a stored swap of two keys is kept', () => {
    const m = new Map<string, string>([['racket.tagging.keymap', JSON.stringify({ ...DEFAULT_KEYMAP, mark_start: 'e', mark_end: 's' })]]);
    const map = loadKeyMap({ getItem: (k) => m.get(k) ?? null, setItem: () => {} });
    expect([map.mark_start, map.mark_end]).toEqual(['e', 's']);
  });
});
