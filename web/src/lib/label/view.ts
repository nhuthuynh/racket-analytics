// Display helpers for L-01 Full Tag (ST-052; flows-sprint-03 §6). Pure.
import type { ApiFieldError } from '@/lib/api/types';
import type { EventLabel, LabelFaultKind, SavedRally } from './types';
import type { Ending } from '@/lib/tagging/types';

/** "0:25.33": minutes, seconds and hundredths of the frame's start (plain digits). */
export function frameTime(frame: number, fps: number): string {
  const hundredths = Math.floor((frame / fps) * 100 + 1e-6);
  const m = Math.floor(hundredths / 6000);
  const s = Math.floor((hundredths % 6000) / 100);
  const cs = hundredths % 100;
  return `${m}:${String(s).padStart(2, '0')}.${String(cs).padStart(2, '0')}`;
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

export const ENDING_WORDS: Readonly<Record<Ending, string>> = {
  winner: 'Winner',
  unforced_error: 'Unforced error',
  forced_error: 'Forced error',
  fault: 'Fault',
  replay: 'Replay',
};

export const FAULT_WORDS: Readonly<Record<LabelFaultKind, string>> = {
  serve: 'Serve',
  foot: 'Foot',
  two_bounce: 'Two bounce',
  nvz: 'Kitchen (non-volley zone)',
  other: 'Other',
};

/** "Hit by Carlos at frame 1530" / "Bounce in view at frame 1544 (3.1 m across, 12.4 m along)". */
export function markLine(mark: EventLabel, nickname: (slot: string) => string): string {
  if (mark.type === 'hit') return `Hit by ${nickname(mark.hitter)} at frame ${mark.frame}`;
  const where = mark.court_xy_m ? ` (${mark.court_xy_m[0]} m across, ${mark.court_xy_m[1]} m along)` : '';
  return `Bounce ${mark.visible ? 'in view' : 'not in view'} at frame ${mark.frame}${where}`;
}

/** "Rally 1: frames 6 to 70, unforced error by Sam, 3 events". */
export function savedLine(rally: SavedRally, number: number, nickname: (slot: string) => string): string {
  const who = rally.outcome.responsible_player ? ` by ${nickname(rally.outcome.responsible_player)}` : '';
  return `Rally ${number}: frames ${rally.start_frame} to ${rally.end_frame}, ${ENDING_WORDS[rally.outcome.ending].toLowerCase()}${who}, ${plural(rally.events.length, 'event', 'events')}`;
}

/** Saved rallies in frame order (the export numbers them the same way, r1, r2, …). */
export function inOrder(rallies: readonly SavedRally[]): SavedRally[] {
  return [...rallies].sort((a, b) => a.start_frame - b.start_frame);
}

/**
 * Why a label was refused, from the 422 field codes (api-sprint-03 §5.4; DR-03 R3-9 amendment 2:
 * the overlapped rally's number is computed here from the saved rallies, since the body has none).
 */
export function refusalReason(
  fields: readonly ApiFieldError[],
  saved: readonly SavedRally[],
  span: { start: number; end: number } | null,
): string {
  const reasons = fields.map((f) => {
    switch (f.code) {
      case 'outside_clip':
        return 'the frame is outside the video';
      case 'no_rally':
        return 'it is outside a rally';
      case 'overlaps_rally': {
        const i = span ? inOrder(saved).findIndex((r) => r.start_frame <= span.end && span.start <= r.end_frame) : -1;
        return i >= 0 ? `it overlaps rally ${i + 1}` : 'it overlaps a saved rally';
      }
      case 'out_of_order':
        return 'it is before the last event of this rally';
      case 'not_a_player':
        return 'choose a player of this match';
      default:
        return 'it is not valid';
    }
  });
  const unique = [...new Set(reasons.length ? reasons : ['it is not valid'])];
  return `This label was not saved: ${unique.join(', ')}.`;
}

export function exportLine(rallies: number, events: number, unsaved: number | null): string {
  const base = `Exported ${plural(rallies, 'rally', 'rallies')} with ${plural(events, 'event', 'events')}.`;
  return unsaved === null ? base : `${base} Rally ${unsaved} is not saved yet: choose how it ended to include it.`;
}
