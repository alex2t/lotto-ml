/**
 * The draw schedule, derived from the data.
 *
 * The next draw is the first day after the latest draw falling on a weekday used by the
 * latest SCHEDULE_DRAWS draws, exactly as ml_lotto/features/walk_forward.py:next_draw_date
 * does it. Deriving it rather than hard-coding Mon/Wed/Sat means a schedule change is picked
 * up from the history.
 */
import { allDraws } from './draws';

/** How many recent draws define the current schedule (walk_forward.py:SCHEDULE_DRAWS). */
export const SCHEDULE_DRAWS = 6;

/** Draws take place about 20:00 Irish time. */
export const DRAW_HOUR = 20;

/** How long after a draw the artifacts may reasonably lag before the site calls them stale. */
export const GRACE_HOURS = 3;

const TIME_ZONE = 'Europe/Dublin';
const DAY_MS = 86_400_000;

function utcMidnight(date: string): number {
  const [y, m, d] = date.split('-').map(Number);
  return Date.UTC(y, m - 1, d);
}

function isoDate(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/** The UTC instant at which the Irish local clock reads `date` at `hour`. */
export function irishInstant(date: string, hour: number): number {
  const guess = utcMidnight(date) + hour * 3_600_000;
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: TIME_ZONE,
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(new Date(guess));
  const get = (type: string) => Number(parts.find((p) => p.type === type)!.value);
  const asShown = Date.UTC(
    get('year'),
    get('month') - 1,
    get('day'),
    get('hour') % 24,
    get('minute'),
  );
  return guess - (asShown - guess);
}

export function latestDrawDate(): string {
  const draws = allDraws();
  return draws[draws.length - 1].draw_date;
}

/** The weekdays (0 = Sunday) the schedule currently uses. */
export function scheduleWeekdays(): number[] {
  const dates = allDraws()
    .slice(-SCHEDULE_DRAWS)
    .map((d) => new Date(utcMidnight(d.draw_date)).getUTCDay());
  return [...new Set(dates)].sort((a, b) => a - b);
}

export function nextDrawDate(): string {
  const weekdays = new Set(scheduleWeekdays());
  let ms = utcMidnight(latestDrawDate()) + DAY_MS;
  while (!weekdays.has(new Date(ms).getUTCDay())) ms += DAY_MS;
  return isoDate(ms);
}

export type Freshness = 'current' | 'waiting' | 'stale';

/**
 * current - the next draw has not happened yet.
 * waiting - it has, and the artifacts have not caught up, within the grace period.
 * stale    - it has, and they still have not.
 */
export function freshness(now: Date = new Date()): Freshness {
  const expected = irishInstant(nextDrawDate(), DRAW_HOUR);
  if (now.getTime() < expected) return 'current';
  if (now.getTime() < expected + GRACE_HOURS * 3_600_000) return 'waiting';
  return 'stale';
}

export function isStale(now: Date = new Date()): boolean {
  return freshness(now) === 'stale';
}
