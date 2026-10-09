// Settled-read check (CI-E2E-MAIN-RED; tests/features/e2e_settled_read.feature).
// Red-first stub: the rule is not implemented yet.
export interface UnsettledRead {
  /** Spec path relative to the scanned directory, with "/" separators. */
  file: string;
  /** 1-based line of the text read. */
  line: number;
}

/** Lines where a spec reads page text after a navigation with no wait in between. */
export function unsettledReads(_source: string): number[] {
  return [];
}

/** Every unsettled read under `dir` (recursively, *.spec.ts only). */
export function checkSpecs(_dir: string): UnsettledRead[] {
  return [];
}
