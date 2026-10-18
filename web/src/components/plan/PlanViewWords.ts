// P-01 words (flows-sprint-04 §2, §8 copy register). Numbers in text with their n; at most one
// decimal (flows-sprint-03 §0). Weakness names and the "why" texts come from the API (COACH-4,
// metric dictionary); the unit and equipment words are the page's.
import type { Citation, DrillAssignment, TrainingPlan } from '@/lib/api/plan';
import { formatLocalDate } from '@/components/LocalDate';

const NUMBER = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });

export function count(n: number, one: string, many: string): string {
  return `${NUMBER.format(n)} ${n === 1 ? one : many}`;
}

const UNIT_WORDS: Readonly<Record<string, readonly [string, string]>> = {
  rallies_lost_per_game: ['rally lost per game', 'rallies lost per game'],
};

/** "2 rallies lost per game" (ADR 0003 unit, from the API's `ranking.unit`). */
export function perGame(value: number, unit: string): string {
  const [one, many] = UNIT_WORDS[unit] ?? [unit.replaceAll('_', ' '), unit.replaceAll('_', ' ')];
  return count(value, one, many);
}

/** ": 2 rallies lost per game, from 1 game" (after the weakness name). */
export function weaknessRate(value: number, unit: string, games: number): string {
  return `: ${perGame(value, unit)}, from ${count(games, 'game', 'games')}`;
}

export function splitLine(w: { onServePerGame: number; onReceivePerGame: number; concededPerGame: number }): string {
  const f = NUMBER.format;
  return `On serve: ${f(w.onServePerGame)} · On receive: ${f(w.onReceivePerGame)} · Points given away: ${f(w.concededPerGame)} per game`;
}

const NEED_WORDS: Readonly<Record<string, string>> = {
  wall: 'a wall',
  half_court: 'half a court',
  full_court: 'a full court',
  ball_machine: 'a ball machine',
  partner_feeder: 'a partner to feed',
};

/** "12 minutes · 1 player · Needs: a wall" (FR-UX-81). */
export function factsLine(a: DrillAssignment): string {
  const needs = a.drill.needs.map((n) => NEED_WORDS[n] ?? n.replaceAll('_', ' ')).join(', ');
  return `${count(a.minutes, 'minute', 'minutes')} · ${count(a.drill.players, 'player', 'players')} · Needs: ${needs || 'nothing extra'}`;
}

/** The metric name and value of a "why" text: "Serve faults: 29% of 7 serves" → both parts. */
export function whyParts(why: string): { metric: string; value: string } {
  const colon = why.indexOf(': ');
  if (colon < 0) return { metric: why, value: '' };
  return { metric: why.slice(0, colon), value: why.slice(colon + 2).split(/ (?:of|over) /)[0] ?? '' };
}

/** "Show me the rallies behind Serve faults, 29%" (label in name, SC 2.5.3). */
export function showMeName(c: Citation): string {
  const { metric, value } = whyParts(c.why);
  return `Show me the rallies behind ${value ? `${metric}, ${value}` : metric}`;
}

/** "Made on 17 Oct 2026 from 1 tagged match." The matches are those the citations draw on. */
export function madeOn(plan: TrainingPlan, timeZone?: string): string {
  const matches = new Set(
    plan.sessions.flatMap((s) => s.assignments.flatMap((a) => a.citation?.evidence.map((e) => e.matchId) ?? [])),
  );
  const from = matches.size > 0 ? ` from ${count(matches.size, 'tagged match', 'tagged matches')}` : '';
  return `Made on ${formatLocalDate(plan.createdAt, timeZone)}${from}.`;
}

/** "18 Oct 2026, 10:30": when the service worker kept the plan shown offline (P-01 Offline). */
export function offlineAsOf(iso: string, timeZone?: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone }).format(d);
}

/**
 * P-03 "Not for me" over the swap limit (429 `rate_limited`, `plan:swap` 120 per hour, ST-062-part2).
 * Local 24-hour time like `uploadRateLimitMessage`; interim copy (judgment) until PD-4 names the state.
 */
export function swapRateLimitMessage(retryAt: string | null, timeZone?: string): string {
  const lead = 'You have swapped many drills in a short time.';
  const at = retryAt ? new Date(retryAt) : null;
  if (!at || Number.isNaN(at.getTime())) return `${lead} Try again in an hour. Your reason is kept.`;
  const time = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...(timeZone ? { timeZone } : {}),
  }).format(at);
  return `${lead} You can swap again at ${time}. Your reason is kept.`;
}
