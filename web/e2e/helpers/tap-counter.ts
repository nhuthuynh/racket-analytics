// ST-080 tap/key counter (NFR-036.4; scorecard G05-05; docs/domain/fix-call-types.md). A fix
// is the taps and keys that act, from the control on the screen where the wrong value is seen to
// the corrected state. Moving focus (Tab, Shift+Tab, arrow keys) is not a fix and is recorded but
// not counted (E2E-02-05, TCR 2026-10-06); any other key passed as a move is refused, so a spec
// cannot hide an acting key. The count is annotated as a bare number under `taps`, which the
// G05-05 method reads with jq `tonumber`; a planted path uses its own type.
import type { Locator, Page, TestInfo } from '@playwright/test';

export const FIX_BUDGET = 2;
export type StepKind = 'tap' | 'key' | 'move';
export interface Step {
  kind: StepKind;
  what: string;
}

const MOVE_KEY = /^(Shift\+)?Tab$|^Arrow(Up|Down|Left|Right)$/;

/** Taps and keys that act; moves are free. */
export function countSteps(steps: readonly Step[]): number {
  return steps.filter((s) => s.kind !== 'move').length;
}

/** Null when `count` is within the budget; else why the fix is too slow. */
export function budgetProblem(count: number, budget = FIX_BUDGET): string | null {
  return count > budget ? `${count} taps or keys, over the budget of ${budget}` : null;
}

export class TapCounter {
  readonly steps: Step[] = [];

  constructor(private readonly page: Page) {}

  async tap(target: Locator, what: string): Promise<void> {
    await target.click();
    this.steps.push({ kind: 'tap', what });
  }

  async key(key: string, what = key): Promise<void> {
    await this.page.keyboard.press(key);
    this.steps.push({ kind: 'key', what });
  }

  async move(key: string): Promise<void> {
    if (!MOVE_KEY.test(key)) throw new Error(`"${key}" is not a move; record it with key()`);
    await this.page.keyboard.press(key);
    this.steps.push({ kind: 'move', what: key });
  }

  get count(): number {
    return countSteps(this.steps);
  }

  problem(): string | null {
    return budgetProblem(this.count);
  }

  expectWithinBudget(): void {
    const problem = this.problem();
    if (problem) throw new Error(`${problem}: ${this.path()}`);
  }

  /** Annotate the count (a bare number) and a readable line naming the fix and its steps. */
  report(info: TestInfo, label: string, type = 'taps'): void {
    info.annotations.push({ type, description: String(this.count) });
    info.annotations.push({ type: 'fix', description: `${label} (${this.count}: ${this.path()})` });
  }

  private path(): string {
    return this.steps.filter((s) => s.kind !== 'move').map((s) => `${s.kind} ${s.what}`).join(', ');
  }
}
