// The upload running in this tab, if any (ST-014: "Your upload will stop" before sign-out).
// A tiny external store for useSyncExternalStore; no React import, no persistence.

export interface ActiveUpload {
  /** The match name shown in the sign-out question. */
  title: string;
  percent: number;
  /** Stops the transfer (sign out anyway). */
  stop: () => void;
}

let current: ActiveUpload | null = null;
const listeners = new Set<() => void>();

export function setActiveUpload(upload: ActiveUpload | null): void {
  current = upload;
  for (const listener of listeners) listener();
}

export function getActiveUpload(): ActiveUpload | null {
  return current;
}

export function subscribeActiveUpload(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
