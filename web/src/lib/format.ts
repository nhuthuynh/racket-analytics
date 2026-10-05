// Display formatting for media facts and upload progress (ST-010).
// Pure functions: no React, no Next, no I/O (eslint enforces the import boundary).
// Units are SI (1 MB = 1,000,000 bytes), the convention phone file browsers show (judgment).

const UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const;
const STEP = 1000;

function requireNonNegative(value: number, name: string): void {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a finite number >= 0`);
  }
}

function requirePositive(value: number, name: string): void {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${name} must be a finite number > 0`);
  }
}

function unitIndexFor(bytes: number): number {
  let index = 0;
  let scaled = bytes;
  while (scaled >= STEP && index < UNITS.length - 1) {
    scaled /= STEP;
    index += 1;
  }
  return index;
}

function scaledIn(bytes: number, index: number): string {
  if (index === 0) return String(Math.round(bytes));
  return (bytes / STEP ** index).toFixed(1);
}

/** `1724207` → `"1.7 MB"`. */
export function formatBytes(bytes: number): string {
  requireNonNegative(bytes, 'bytes');
  const index = unitIndexFor(bytes);
  return `${scaledIn(bytes, index)} ${UNITS[index]}`;
}

/** `(1100000, 1724207)` → `"1.1 of 1.7 MB"`: both values in the unit of the total. */
export function formatProgressBytes(sent: number, total: number): string {
  requireNonNegative(sent, 'sent');
  requireNonNegative(total, 'total');
  const index = unitIndexFor(total);
  const shown = Math.min(sent, total);
  return `${scaledIn(shown, index)} of ${scaledIn(total, index)} ${UNITS[index]}`;
}

/** `(1900000000, 3000000000)` → `"1.9 GB of 3.0 GB"` (flows U-01 progress text). */
export function formatProgressAmount(sent: number, total: number): string {
  requireNonNegative(sent, 'sent');
  requireNonNegative(total, 'total');
  const index = unitIndexFor(total);
  const shown = Math.min(sent, total);
  return `${scaledIn(shown, index)} ${UNITS[index]} of ${scaledIn(total, index)} ${UNITS[index]}`;
}

/** `60000` → `"1:00"`; `3725000` → `"1:02:05"`. Rounds to the nearest second. */
export function formatDuration(ms: number): string {
  requireNonNegative(ms, 'duration');
  const totalSeconds = Math.round(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const ss = String(seconds).padStart(2, '0');
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${ss}`;
  return `${minutes}:${ss}`;
}

/** `60` → `"60 fps"`; `59.94` → `"59.94 fps"` (like Python's `{fps:g}`). */
export function formatFps(fps: number): string {
  requirePositive(fps, 'fps');
  return `${Number(fps.toFixed(3))} fps`;
}

/** `(1920, 1080)` → `"1920×1080"`. */
export function formatResolution(width: number, height: number): string {
  requirePositive(width, 'width');
  requirePositive(height, 'height');
  return `${width}×${height}`;
}

export interface MediaSummaryInput {
  duration_ms: number;
  fps: number;
  width: number;
  height: number;
}

/** The walking-skeleton line: `"Duration 1:00 · 60 fps · 1920×1080"`. */
export function formatMediaSummary(media: MediaSummaryInput): string {
  return [
    `Duration ${formatDuration(media.duration_ms)}`,
    formatFps(media.fps),
    formatResolution(media.width, media.height),
  ].join(' · ');
}

/** A size cap in words for copy: `10000000000` → `"10 GB"` (SI, like phone file browsers). */
export function formatSizeCap(bytes: number): string {
  requirePositive(bytes, 'bytes');
  const index = Math.max(unitIndexFor(bytes), 1);
  const value = Number((bytes / STEP ** index).toFixed(1));
  return `${value} ${UNITS[index]}`;
}

/** A duration cap in words: `9000000` → `"2 hours 30 minutes"`. Whole minutes. */
export function formatDurationCap(ms: number): string {
  requirePositive(ms, 'duration');
  const minutesTotal = Math.round(ms / 60_000);
  const hours = Math.floor(minutesTotal / 60);
  const minutes = minutesTotal % 60;
  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours} ${hours === 1 ? 'hour' : 'hours'}`);
  if (minutes > 0 || hours === 0) parts.push(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`);
  return parts.join(' ');
}
