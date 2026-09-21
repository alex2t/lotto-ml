/**
 * The countable distributions, over a date range.
 *
 * Rule 5 says the site computes nothing: a figure it shows is read from an artifact. A date
 * range cannot be precomputed for every possible pair of dates, so the choice is either to
 * drop the feature or to count. What is counted here is only ever **counting draws** - the
 * same operation drawpick.py performs, over the same pre-draw categories the draw history
 * already stores - and never a statistic with a test or a correction in it. The per-number
 * odd/even affinity, the trend flags, the scenario table and the validated distributions
 * stay exactly as the artifacts wrote them, over the whole history.
 *
 * What keeps this honest is `test/ranged.test.ts`: counted over the full history, every
 * figure here must equal the artifact's own to within its rounding. If the analyzer ever
 * changes how it counts, that test fails rather than the two drifting quietly apart.
 */
import { allDraws } from './draws';
import { drawPattern, patternKey } from './hmc';
import { spreadBand, sumBand } from '../scoring/bands';
import type { DrawEntry } from './types';

export interface Counted {
  key: string;
  count: number;
  percentage: number;
}

export interface RangedDistributions {
  draws: number;
  from: string;
  to: string;
  oddEven: Counted[];
  sums: Counted[];
  spreads: Counted[];
  highNumbers: Counted[];
  hmc: Counted[];
}

export const HIGH_FROM = 32;

function tally(
  draws: DrawEntry[],
  keyOf: (draw: DrawEntry) => string,
): Counted[] {
  const counts = new Map<string, number>();
  for (const draw of draws) {
    const key = keyOf(draw);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([key, count]) => ({
      key,
      count,
      percentage: draws.length ? (count / draws.length) * 100 : 0,
    }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

/** Every draw between two dates, inclusive. Either bound may be left out. */
export function drawsBetween(from?: string, to?: string): DrawEntry[] {
  return allDraws().filter(
    (d) => (!from || d.draw_date >= from) && (!to || d.draw_date <= to),
  );
}

export function distributionsBetween(from?: string, to?: string): RangedDistributions {
  const draws = drawsBetween(from, to);

  return {
    draws: draws.length,
    from: draws.length ? draws[0].draw_date : (from ?? ''),
    to: draws.length ? draws[draws.length - 1].draw_date : (to ?? ''),
    oddEven: tally(draws, (d) => {
      const odd = d.main_numbers.filter((n) => n % 2 === 1).length;
      return `${odd}_${6 - odd}`;
    }),
    sums: tally(draws, (d) => sumBand(d.main_numbers.reduce((a, b) => a + b, 0)).key),
    spreads: tally(
      draws,
      (d) => spreadBand(Math.max(...d.main_numbers) - Math.min(...d.main_numbers)).key,
    ),
    highNumbers: tally(draws, (d) =>
      String(d.main_numbers.filter((n) => n >= HIGH_FROM).length),
    ),
    hmc: tally(draws, (d) => patternKey(drawPattern(d))),
  };
}
