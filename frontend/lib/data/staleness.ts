/**
 * What the homepage says about how current the data is.
 *
 * Factual, never alarming: the data is late, nothing is broken (web.md 4.1).
 */
import { allDraws } from './draws';
import { DRAW_HOUR, freshness, irishInstant, nextDrawDate, scheduleWeekdays } from './schedule';

export interface Staleness {
  state: 'current' | 'waiting' | 'stale';
  /** How many expected draws have passed without appearing in the artifacts. */
  missing: number;
  /** The draw the site is showing instead. */
  showing: string;
  nextDraw: string;
}

const DAY_MS = 86_400_000;

function utcMidnight(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  return Date.UTC(y, m - 1, d);
}

/** Every scheduled draw date from the latest one up to `now`, excluding the latest. */
function expectedSince(latest: string, now: Date): string[] {
  const weekdays = new Set(scheduleWeekdays());
  const dates: string[] = [];
  let ms = utcMidnight(latest) + DAY_MS;
  // A draw is only "expected" once its own draw time has passed.
  while (dates.length < 60) {
    const iso = new Date(ms).toISOString().slice(0, 10);
    if (weekdays.has(new Date(ms).getUTCDay())) {
      if (irishInstant(iso, DRAW_HOUR) > now.getTime()) break;
      dates.push(iso);
    }
    ms += DAY_MS;
  }
  return dates;
}

export function staleness(now: Date = new Date()): Staleness {
  const draws = allDraws();
  const showing = draws[draws.length - 1].draw_date;
  return {
    state: freshness(now),
    missing: expectedSince(showing, now).length,
    showing,
    nextDraw: nextDrawDate(),
  };
}
