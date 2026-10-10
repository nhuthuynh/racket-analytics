// What the server already holds of the rally being saved (ST-052; api-sprint-03 §5.2). The label
// POSTs cannot be safely repeated (no idempotency key, no expected version, no edit or delete in
// Sprint 3), so after a failed or unanswered POST the client reads the session and sends only what
// is missing (PE-ST052-R1-04). Pure.
import type { EventLabel, LabelOutcome, LabelSession, SavedRally } from './types';

export function sameOutcome(a: LabelOutcome, b: LabelOutcome): boolean {
  return (
    a.ending === b.ending &&
    a.winning_side === b.winning_side &&
    a.responsible_player === b.responsible_player &&
    a.fault_kind === b.fault_kind
  );
}

export function sameEvent(a: EventLabel, b: EventLabel): boolean {
  if (a.type !== b.type || a.frame !== b.frame) return false;
  if (a.type === 'hit' && b.type === 'hit') return a.hitter === b.hitter;
  if (a.type === 'bounce' && b.type === 'bounce') {
    return a.visible === b.visible && (a.court_xy_m?.join() ?? null) === (b.court_xy_m?.join() ?? null);
  }
  return false;
}

export interface Reconciled {
  version: number;
  /** The saved rallies other than the one being saved, in frame order. */
  others: SavedRally[];
  /** The server's copy of the rally being saved, or null when it is not stored. */
  held: SavedRally | null;
  /** The marks still to send, in frame order. */
  rest: EventLabel[];
}

export function reconcile(
  session: LabelSession,
  span: { start: number; end: number },
  marks: readonly EventLabel[],
): Reconciled {
  const rallies = session.document.rallies;
  const held = rallies.find((r) => r.start_frame === span.start && r.end_frame === span.end) ?? null;
  const others = rallies.filter((r) => r !== held).sort((a, b) => a.start_frame - b.start_frame);
  const rest = held ? marks.filter((m) => !held.events.some((e) => sameEvent(e, m))) : [...marks];
  return { version: session.version, others, held, rest };
}
