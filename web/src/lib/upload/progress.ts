// Upload progress state (ST-010; FR-022 core). A pure reducer: no React, no tus, no I/O.
// Invariants: the offset never goes backwards, and the percentage never exceeds 100.

export type UploadPhase = 'idle' | 'uploading' | 'complete' | 'failed';

export type UploadFailure = 'network' | 'conflict' | 'rejected' | 'unknown';

export interface UploadProgress {
  readonly phase: UploadPhase;
  readonly bytesSent: number;
  readonly bytesTotal: number;
  readonly failure: UploadFailure | null;
}

export type UploadProgressAction =
  | { type: 'started'; bytesTotal: number; bytesSent?: number }
  | { type: 'progressed'; bytesSent: number; bytesTotal: number }
  | { type: 'completed' }
  | { type: 'failed'; reason: UploadFailure }
  | { type: 'retried' };

export const initialUploadProgress: UploadProgress = Object.freeze({
  phase: 'idle',
  bytesSent: 0,
  bytesTotal: 0,
  failure: null,
});

function clamp(value: number, total: number): number {
  return Math.min(Math.max(value, 0), total);
}

export function uploadProgressReducer(
  state: UploadProgress,
  action: UploadProgressAction,
): UploadProgress {
  switch (action.type) {
    case 'started': {
      if (!Number.isFinite(action.bytesTotal) || action.bytesTotal <= 0) {
        throw new RangeError('bytesTotal must be > 0');
      }
      const resumedAt = Number.isFinite(action.bytesSent) ? (action.bytesSent ?? 0) : 0;
      return {
        phase: 'uploading',
        bytesTotal: action.bytesTotal,
        bytesSent: clamp(resumedAt, action.bytesTotal),
        failure: null,
      };
    }
    case 'progressed': {
      if (state.phase !== 'uploading') return state;
      if (!Number.isFinite(action.bytesSent) || action.bytesSent < 0) return state;
      const next = clamp(action.bytesSent, state.bytesTotal);
      if (next <= state.bytesSent) return state; // offset regression or no change
      return { ...state, bytesSent: next };
    }
    case 'completed':
      if (state.phase === 'idle') return state;
      return { ...state, phase: 'complete', bytesSent: state.bytesTotal, failure: null };
    case 'failed':
      if (state.phase === 'idle' || state.phase === 'complete') return state;
      return { ...state, phase: 'failed', failure: action.reason };
    case 'retried':
      if (state.phase !== 'failed') return state;
      return { ...state, phase: 'uploading', failure: null };
  }
}

/** Whole percent, floored, so 100 only when every byte is sent. */
export function percentOf(state: UploadProgress): number {
  if (state.bytesTotal <= 0) return 0;
  return Math.min(100, Math.floor((state.bytesSent / state.bytesTotal) * 100));
}
