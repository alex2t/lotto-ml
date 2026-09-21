import { beforeEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { allDraws } from '@/lib/data/draws';
import {
  highNumbers,
  oddEvenPatterns,
  sumDistributions,
  totalDraws,
} from '@/lib/data/distributions';
import { sixBallPatterns } from '@/lib/data/hmc';
import { spreadBandShares } from '@/lib/scoring/line';
import { distributionsBetween, drawsBetween } from '@/lib/data/ranged';
import { useFixtures } from './setup-fixtures';

/**
 * The date-range charts count draws rather than reading a precomputed figure, because no
 * artifact can hold every possible range. This is what stops that counting drifting from
 * the analyzer: over the full history the two must agree.
 *
 * The fixture holds a slice of the history, so the artifact's own totals are over more
 * draws than the fixture contains. The agreement is therefore asserted against what the
 * artifact says for the draws that ARE in the fixture, by recounting them the same way.
 */
describe('counting a date range', () => {
  beforeEach(() => useFixtures());

  it('with no bounds, counts every draw on file', () => {
    expect(drawsBetween().length).toBe(allDraws().length);
    expect(distributionsBetween().draws).toBe(allDraws().length);
  });

  it('narrows to the range, inclusive at both ends', () => {
    const dates = allDraws().map((d) => d.draw_date);
    const from = dates[2];
    const to = dates[dates.length - 3];
    const within = drawsBetween(from, to);

    expect(within[0].draw_date).toBe(from);
    expect(within[within.length - 1].draw_date).toBe(to);
    expect(within.length).toBe(dates.length - 4);
  });

  it('an empty range says so rather than dividing by zero', () => {
    const none = distributionsBetween('1990-01-01', '1990-12-31');
    expect(none.draws).toBe(0);
    expect(none.oddEven).toEqual([]);
  });

  it('every share sums to 100 within a range', () => {
    const ranged = distributionsBetween();
    for (const group of [
      ranged.oddEven,
      ranged.sums,
      ranged.spreads,
      ranged.highNumbers,
      ranged.hmc,
    ]) {
      expect(group.reduce((a, b) => a + b.percentage, 0)).toBeCloseTo(100, 6);
    }
  });

  it('counts each draw exactly once in every distribution', () => {
    const ranged = distributionsBetween();
    for (const group of [
      ranged.oddEven,
      ranged.sums,
      ranged.spreads,
      ranged.highNumbers,
      ranged.hmc,
    ]) {
      expect(group.reduce((a, b) => a + b.count, 0)).toBe(ranged.draws);
    }
  });

  it('uses the same bands and keys the artifacts use', () => {
    const ranged = distributionsBetween();
    const known = (keys: string[], counted: { key: string }[]) => {
      for (const { key } of counted) expect(keys).toContain(key);
    };

    known(Object.keys(oddEvenPatterns('6_main')), ranged.oddEven);
    known(Object.keys(sumDistributions('6_main')), ranged.sums);
    known(Object.keys(spreadBandShares()), ranged.spreads);
    known(Object.keys(highNumbers().byCount), ranged.highNumbers);
    known(
      sixBallPatterns().map((p) => p.pattern),
      ranged.hmc,
    );
  });

});

/**
 * The agreement that matters is against the artifacts the site actually serves, so this
 * points at the real data directory rather than the fixture slice. It skips if there is no
 * data/ - a fresh checkout before drawpick.py has run.
 */
const REAL_DATA = path.join(import.meta.dirname, '..', '..', 'data');

describe.skipIf(!fs.existsSync(path.join(REAL_DATA, 'lotto_draw_history.json')))(
  'counted over the whole history, against the real artifacts',
  () => {
    beforeEach(() => useFixtures(REAL_DATA));

    it('counts every draw the artifact was written over', () => {
      expect(distributionsBetween().draws).toBe(totalDraws());
    });

    it('reproduces the odd/even shares', () => {
      const artifact = oddEvenPatterns('6_main');
      for (const counted of distributionsBetween().oddEven) {
        expect(counted.percentage).toBeCloseTo(artifact[counted.key].percentage, 1);
      }
    });

    it('reproduces the sum band shares', () => {
      const artifact = sumDistributions('6_main');
      for (const counted of distributionsBetween().sums) {
        expect(counted.percentage).toBeCloseTo(artifact[counted.key].percentage, 1);
      }
    });

    it('reproduces the spread shares', () => {
      const artifact = spreadBandShares();
      for (const counted of distributionsBetween().spreads) {
        expect(counted.percentage).toBeCloseTo(artifact[counted.key], 1);
      }
    });

    it('reproduces the high-number shares', () => {
      const artifact = highNumbers().byCount;
      for (const counted of distributionsBetween().highNumbers) {
        expect(counted.percentage).toBeCloseTo(artifact[counted.key].percentage, 1);
      }
    });

    it('reproduces the six-ball HMC shares written by drawpick.py', () => {
      const artifact = new Map(sixBallPatterns().map((p) => [p.pattern, p.percentage]));
      for (const counted of distributionsBetween().hmc) {
        expect(counted.percentage).toBeCloseTo(artifact.get(counted.key)!, 1);
      }
    });
  },
);
