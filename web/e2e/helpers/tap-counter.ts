// ST-080 tap/key counter (NFR-036.4). Skeleton for the red step: the API only.
import type { Locator, Page, TestInfo } from '@playwright/test';

export const FIX_BUDGET = 2;
export type StepKind = 'tap' | 'key' | 'move';
export interface Step {
  kind: StepKind;
  what: string;
}

export function countSteps(_steps: readonly Step[]): number {
  return 0;
}

export function budgetProblem(_count: number, _budget = FIX_BUDGET): string | null {
  return null;
}

export class TapCounter {
  readonly steps: Step[] = [];
  constructor(private readonly page: Page) {}
  async tap(_target: Locator, _what: string): Promise<void> {}
  async key(_key: string, _what = _key): Promise<void> {}
  async move(_key: string): Promise<void> {}
  get count(): number {
    return 0;
  }
  problem(): string | null {
    return null;
  }
  expectWithinBudget(): void {}
  report(_info: TestInfo, _label: string, _type = 'taps'): void {}
}
