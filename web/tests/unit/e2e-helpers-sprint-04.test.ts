// Unit tests for the Sprint 4 E2E helpers (ST-065): the "why" reader E2E-04-01 checks a drill's
// metric, value and n with, and the keyboard walk of E2E-04-05. Negative cases first.
import { describe, expect, it } from 'vitest';
import { parseWhy, tabUntil } from '../../e2e/helpers/sprint-04';

describe('parseWhy (a drill row\'s "Why:" text, FR-122)', () => {
  it('refuses a why without its n: the citation would not say how much data it rests on', () => {
    expect(parseWhy('Why: Serve faults: 29%')).toBeNull();
  });

  it('refuses a text that is not a why, or has no metric name', () => {
    expect(parseWhy('We could not show why this drill was chosen.')).toBeNull();
    expect(parseWhy('Why: 29% of 7 serves')).toBeNull();
    expect(parseWhy('')).toBeNull();
  });

  it('reads a proportion: metric name, value and n', () => {
    expect(parseWhy('Why: Rallies won when receiving: 33% of 6 serves received')).toEqual({
      metric: 'Rallies won when receiving',
      value: '33%',
      n: 6,
    });
  });

  it('reads a rate "over" games, and ignores the low-sample tag after it', () => {
    expect(parseWhy('Why: Unforced errors per game: 2.0 over 1 game low sample')).toEqual({
      metric: 'Unforced errors per game',
      value: '2.0',
      n: 1,
    });
  });
});

describe('tabUntil (keyboard-only walk, E2E-04-05)', () => {
  it('fails, naming the target and the presses, when Tab never reaches it', async () => {
    let presses = 0;
    await expect(
      tabUntil(async () => void presses++, async () => false, { max: 5, target: 'Mark done' }),
    ).rejects.toThrow('Tab did not reach Mark done in 5 presses');
    expect(presses).toBe(5);
  });

  it('presses nothing when the target already has focus', async () => {
    let presses = 0;
    await expect(tabUntil(async () => void presses++, async () => true, { target: 'x' })).resolves.toBe(0);
    expect(presses).toBe(0);
  });

  it('stops as soon as the target has focus and says how many presses it took', async () => {
    let presses = 0;
    const focused = async () => presses === 3;
    await expect(tabUntil(async () => void presses++, focused, { max: 10, target: 'Show me' })).resolves.toBe(3);
    expect(presses).toBe(3);
  });
});
