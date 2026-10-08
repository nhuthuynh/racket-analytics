// Route isolation check (CI-WEBKIT-PD-R3S2-02). Stub: implemented after the tests are seen failing.
export interface UnisolatedRoute {
  /** Spec path relative to the scanned directory, with "/" separators. */
  file: string;
  /** 1-based line of the route call. */
  line: number;
}

export function unisolatedRoutes(source: string): number[] {
  void source;
  return [];
}

export function checkSpecs(dir: string): UnisolatedRoute[] {
  void dir;
  return [];
}
