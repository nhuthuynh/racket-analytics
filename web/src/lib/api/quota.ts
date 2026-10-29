// Q-10 over-limit words (ST-072b; FR-160; flows-sprint-04 §7; api-sprint-04 §7). Interim texts
// W-Q01/W-Q02 of interim-wording-sprint-04 §5, pending legal review (NFR-070, P16). Numbers come
// from the API only (PM-4 rule 2): the 429 `rate_limited` body carries no limit, so the count of
// matches is not named (decision ST-072b). The storage message is ST-072b-part2.

const KEPT = 'Your answers are kept.';
const MANY = 'You have started a lot of matches in the last hour.';

function localDay(at: Date, timeZone?: string): string {
  return new Intl.DateTimeFormat('en-CA', { dateStyle: 'short', ...(timeZone ? { timeZone } : {}) }).format(at);
}

/** 429 `rate_limited` at "Create match and upload" (W-Q01; W-Q02 without a readable `retry_at`). */
export function matchLimitMessage(retryAt: string | null, opts: { timeZone?: string; now?: Date } = {}): string {
  const at = retryAt ? new Date(retryAt) : null;
  if (!at || Number.isNaN(at.getTime())) return `${MANY} You can start a new match within the hour. ${KEPT}`;
  const { timeZone, now = new Date() } = opts;
  const time = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...(timeZone ? { timeZone } : {}),
  }).format(at);
  const when = localDay(at, timeZone) === localDay(now, timeZone) ? `at ${time}` : `tomorrow at ${time}`;
  return `${MANY} You can start a new match ${when}. ${KEPT}`;
}
