// Red stub (ST-063c): the outbox port and its types; the behaviour follows in the green commit.
import type { DoneResult } from './plan-outbox-api';

export interface DoneOp {
  op_id: string;
  session_id: string;
}
export interface OutboxStore {
  get(sessionId: string): Promise<DoneOp | undefined>;
  put(op: DoneOp): Promise<void>;
  delete(sessionId: string): Promise<void>;
  all(): Promise<DoneOp[]>;
}
export type SendDone = (op: DoneOp) => Promise<DoneResult>;
export interface SyncReport {
  synced: string[];
  dropped: string[];
  kept: string[];
  planChanged: boolean;
  signedOut: boolean;
}
export interface Outbox {
  queueDone(sessionId: string): Promise<DoneOp>;
  cancel(sessionId: string): Promise<void>;
  pending(): Promise<DoneOp[]>;
  sync(send: SendDone): Promise<SyncReport>;
}

export function createOutbox(_store: OutboxStore, _newOpId?: () => string): Outbox {
  throw new Error('not implemented');
}
