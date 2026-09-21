import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  DRAW_HOUR,
  GRACE_HOURS,
  freshness,
  irishInstant,
  latestDrawDate,
  nextDrawDate,
  scheduleWeekdays,
} from '@/lib/data/schedule';
import { useFixtures } from './setup-fixtures';

/** A draw history holding nothing but the dates - all schedule.ts reads. */
function historyOf(dates: string[]): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lotto-schedule-'));
  const history = Object.fromEntries(
    dates.map((date, i) => [
      date,
      {
        draw_index: i,
        draw_date: date,
        main_numbers: [1, 2, 3, 4, 5, 6],
        bonus_number: 7,
      },
    ]),
  );
  fs.writeFileSync(
    path.join(dir, 'lotto_draw_history.json'),
    JSON.stringify(history),
  );
  return dir;
}

describe('schedule', () => {
  afterEach(() => useFixtures());

  it('reads the latest draw date from the real artifacts', () => {
    useFixtures();
    expect(latestDrawDate()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('follows a Wednesday/Saturday schedule', () => {
    // Wednesdays and Saturdays through August 2025; the last is Saturday 2025-08-30.
    useFixtures(
      historyOf([
        '2025-08-13',
        '2025-08-16',
        '2025-08-20',
        '2025-08-23',
        '2025-08-27',
        '2025-08-30',
      ]),
    );
    expect(scheduleWeekdays()).toEqual([3, 6]);
    expect(nextDrawDate()).toBe('2025-09-03');
  });

  it('picks up a schedule change from the latest six draws', () => {
    // Monday is added partway through; the older Wed/Sat-only draws must not hide it.
    useFixtures(
      historyOf([
        '2025-08-16',
        '2025-08-20',
        '2025-08-23',
        '2025-08-25',
        '2025-08-27',
        '2025-08-30',
        '2025-09-01',
        '2025-09-03',
      ]),
    );
    expect(scheduleWeekdays()).toEqual([1, 3, 6]);
    // Saturday 2025-09-06 comes before the following Monday.
    expect(nextDrawDate()).toBe('2025-09-06');
  });

  it('never returns the latest draw date itself', () => {
    useFixtures(historyOf(['2025-09-01', '2025-09-03', '2025-09-06']));
    expect(nextDrawDate() > latestDrawDate()).toBe(true);
  });

  describe('freshness', () => {
    beforeEach(() => {
      useFixtures(historyOf(['2025-08-27', '2025-08-30']));
    });

    it('is current before the next draw', () => {
      const expected = irishInstant(nextDrawDate(), DRAW_HOUR);
      expect(freshness(new Date(expected - 60_000))).toBe('current');
    });

    it('is waiting from the draw until the grace period ends', () => {
      const expected = irishInstant(nextDrawDate(), DRAW_HOUR);
      expect(freshness(new Date(expected))).toBe('waiting');
      expect(
        freshness(new Date(expected + GRACE_HOURS * 3_600_000 - 60_000)),
      ).toBe('waiting');
    });

    it('is stale once the grace period has passed', () => {
      const expected = irishInstant(nextDrawDate(), DRAW_HOUR);
      expect(freshness(new Date(expected + GRACE_HOURS * 3_600_000))).toBe('stale');
    });
  });

  it('irishInstant accounts for Irish summer time', () => {
    // 2025-07-01 is IST (UTC+1); 2025-01-01 is GMT.
    expect(new Date(irishInstant('2025-07-01', 20)).toISOString()).toBe(
      '2025-07-01T19:00:00.000Z',
    );
    expect(new Date(irishInstant('2025-01-01', 20)).toISOString()).toBe(
      '2025-01-01T20:00:00.000Z',
    );
  });
});
