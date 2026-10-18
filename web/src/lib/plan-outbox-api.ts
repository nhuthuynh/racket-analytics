// Red stub (ST-063c): the follow-through client's port; the behaviour follows in the green commit.
import type { Session } from '@/lib/api/plan';
import type { DoneOp } from './plan-outbox';

type Failed = { kind: 'failed'; supportRef: string | null };
export type DoneResult =
  | { kind: 'done'; planVersion: number; replayed: boolean }
  | { kind: 'not_found' }
  | { kind: 'key_reused' }
  | { kind: 'plan_conflict' }
  | { kind: 'signed_out' }
  | Failed;
export type UndoResult =
  | { kind: 'undone'; planVersion: number }
  | { kind: 'not_found' }
  | { kind: 'plan_conflict' }
  | { kind: 'signed_out' }
  | Failed;
export type SwapResult =
  | { kind: 'swapped'; session: Session; planVersion: number }
  | { kind: 'no_alternative' }
  | { kind: 'session_done' }
  | { kind: 'plan_conflict' }
  | { kind: 'not_found' }
  | { kind: 'signed_out' }
  | Failed;

export interface FollowThroughApi {
  markDone(op: DoneOp): Promise<DoneResult>;
  undoDone(sessionId: string): Promise<UndoResult>;
  swap(assignmentId: string, reason: string): Promise<SwapResult>;
}

export function createFollowThroughApi(_opts: { baseUrl: string; fetch?: typeof fetch }): FollowThroughApi {
  return {
    markDone: async () => ({ kind: 'failed', supportRef: null }),
    undoDone: async () => ({ kind: 'failed', supportRef: null }),
    swap: async () => ({ kind: 'failed', supportRef: null }),
  };
}
