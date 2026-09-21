import { afterEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import { staleness } from '@/lib/data/staleness';
import { DRAW_HOUR, irishInstant } from '@/lib/data/schedule';
import { StalenessBanner } from '@/components/layout/StalenessBanner';
import { useFixtures } from './setup-fixtures';

/**
 * What the homepage says about how current the data is (web.md 7.2, tests 1 and 2).
 *
 * The draw history is built here rather than committed, because both cases are defined
 * relative to today: "the newest draw is today" and "the newest draw is four days old with
 * an expected draw in between" are different dates every time they run.
 *
 * This asserts the two things the homepage is made of - the state `staleness()` returns,
 * and the words `StalenessBanner` renders for it. It does not drive a browser; that the
 * banner is placed on the page is covered by the Playwright pass.
 */
const DAY = 86_400_000;

function iso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/**
 * A draw history ending on `last`, one draw a week.
 *
 * Weekly on purpose: `nextDrawDate()` reads the schedule from the weekdays of the latest six
 * draws, so a cadence of every two days makes every weekday a draw day and the "next draw"
 * lands tomorrow whatever the last draw was. One weekday gives one predictable next date.
 */
function historyEnding(last: Date, everyDays = 7): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lotto-staleness-'));
  const history: Record<string, unknown> = {};

  for (let i = 7; i >= 0; i -= 1) {
    const date = iso(new Date(last.getTime() - i * everyDays * DAY));
    history[date] = {
      draw_index: 100 - i,
      draw_date: date,
      main_numbers: [1, 2, 3, 4, 5, 6],
      bonus_number: 7,
    };
  }

  fs.writeFileSync(
    path.join(dir, 'lotto_draw_history.json'),
    JSON.stringify(history),
  );
  return dir;
}

/** Midday UTC today, so neither end of the day lands in yesterday or tomorrow. */
function middayToday(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 12));
}

afterEach(() => useFixtures());

describe('the newest draw is today', () => {
  it('is current, and the homepage shows no banner', () => {
    const today = middayToday();
    useFixtures(historyEnding(today));

    // Weekly, so today is on the schedule and the next one is a week away.
    const state = staleness(new Date(today.getTime() + 3 * 3_600_000));

    expect(state.state).toBe('current');
    expect(state.showing).toBe(iso(today));
    expect(state.missing).toBe(0);

    // The homepage renders the banner only when it has something to say.
    expect(renderToStaticMarkup(StalenessBanner({ staleness: state }))).toBe('');
  });
});

describe('a draw has passed and is not in yet', () => {
  it('is waiting, and the banner names the draw being shown', () => {
    const today = middayToday();
    const aWeekAgo = new Date(today.getTime() - 7 * DAY);
    useFixtures(historyEnding(aWeekAgo));

    // Weekly, so one was due today at 20:00 Irish time. An hour after that it is waiting,
    // not stale - the grace period is three hours.
    const due = irishInstant(iso(today), DRAW_HOUR);
    const state = staleness(new Date(due + 3_600_000));

    expect(state.state).toBe('waiting');
    expect(state.showing).toBe(iso(aWeekAgo));
    expect(state.missing).toBe(1);

    const html = renderToStaticMarkup(StalenessBanner({ staleness: state }));
    expect(html).toContain('not in yet');
    expect(html).toContain('waiting for the latest result');
    // It must name the draw it IS showing, so nobody reads old numbers as new ones.
    expect(html).toMatch(/Showing/);
    expect(html).toContain(String(aWeekAgo.getUTCFullYear()));
  });

  it('turns stale once the grace period has passed', () => {
    const today = middayToday();
    const aWeekAgo = new Date(today.getTime() - 7 * DAY);
    useFixtures(historyEnding(aWeekAgo));

    const due = irishInstant(iso(today), DRAW_HOUR);
    expect(staleness(new Date(due + 4 * 3_600_000)).state).toBe('stale');
  });

  it('says how many are missing once more than one has passed', () => {
    const today = middayToday();
    const threeWeeksAgo = new Date(today.getTime() - 21 * DAY);
    useFixtures(historyEnding(threeWeeksAgo));

    const state = staleness(today);

    expect(state.state).toBe('stale');
    expect(state.missing).toBeGreaterThan(1);
    const html = renderToStaticMarkup(StalenessBanner({ staleness: state }));
    expect(html).toContain(`${state.missing} draws are`);
  });
});

describe('the banner itself', () => {
  it('is a status, so a screen reader is told without being interrupted', () => {
    const today = middayToday();
    useFixtures(historyEnding(new Date(today.getTime() - 21 * DAY)));
    const html = renderToStaticMarkup(
      StalenessBanner({ staleness: staleness(today) }),
    );
    expect(html).toContain('role="status"');
  });

  it('never suggests anything is broken', () => {
    // The data is late; nothing has failed. Alarming wording would be a lie about the site.
    const today = middayToday();
    useFixtures(historyEnding(new Date(today.getTime() - 21 * DAY)));
    const html = renderToStaticMarkup(
      StalenessBanner({ staleness: staleness(today) }),
    ).toLowerCase();

    for (const word of ['error', 'failed', 'broken', 'problem', 'unavailable']) {
      expect(html).not.toContain(word);
    }
  });
});
