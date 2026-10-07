// Full Tag shapes (ST-052; api-sprint-03 §5; docs/data/gold-label-schema.md §4, `full-tag-labels/v1`).
// Labels carry frames, slots and outcome values only, never nicknames or the consent reference.
import type { Ending, Side } from '@/lib/tagging/types';

export const FACET_KEYS = ['contact', 'trajectory', 'intent', 'technique'] as const;
export const FAULT_KINDS = ['serve', 'foot', 'two_bounce', 'nvz', 'other'] as const;
export type LabelFaultKind = (typeof FAULT_KINDS)[number];

export interface LabelOutcome {
  ending: Ending;
  winning_side: Side | null;
  responsible_player: string | null;
  fault_kind: LabelFaultKind | null;
}

export interface HitLabel {
  type: 'hit';
  frame: number;
  hitter: string;
  facets: Record<string, string>;
}

export interface BounceLabel {
  type: 'bounce';
  frame: number;
  visible: boolean;
  court_xy_m: [number, number] | null;
}

export type EventLabel = HitLabel | BounceLabel;

export interface RallyLabel {
  type: 'rally';
  start_frame: number;
  end_frame: number;
  outcome: LabelOutcome;
}

export interface SavedRally {
  id: string;
  start_frame: number;
  end_frame: number;
  outcome: LabelOutcome;
  events: EventLabel[];
}

export interface LabelDocument {
  schema: 'full-tag-labels/v1';
  clip: string;
  fps: number;
  frame_count: number;
  players: string[];
  rallies: SavedRally[];
}

export interface LabelSession {
  matchId: string;
  fps: number;
  frameCount: number;
  players: string[];
  version: number;
  document: LabelDocument;
}

export interface LabelSaved {
  version: number;
  rallies: number;
  events: number;
}
