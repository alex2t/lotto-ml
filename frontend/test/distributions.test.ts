import { beforeEach, describe, expect, it } from 'vitest';
import {
  freshnessPatterns,
  freshnessWeights,
  highNumbers,
  hmcCategoryDistribution,
  oddEvenPatterns,
  spreadDistribution,
  sumDistribution,
  sumDistributions,
  totalDraws,
} from '@/lib/data/distributions';
import { useFixtures } from './setup-fixtures';

describe('distributions', () => {
  beforeEach(() => useFixtures());

  it('odd/even patterns over the 6 main numbers cover every draw', () => {
    const buckets = Object.values(oddEvenPatterns('6_main'));
    const counted = buckets.reduce((sum, b) => sum + b.count, 0);
    expect(counted).toBe(totalDraws());
    expect(
      buckets.reduce((sum, b) => sum + b.percentage, 0),
    ).toBeCloseTo(100, 1);
  });

  it('odd/even over all 7 is a different distribution from the main 6', () => {
    expect(Object.keys(oddEvenPatterns('all_7'))).not.toEqual(
      Object.keys(oddEvenPatterns('6_main')),
    );
  });

  it('sum bands cover every draw', () => {
    const counted = Object.values(sumDistributions()).reduce(
      (sum, b) => sum + b.count,
      0,
    );
    expect(counted).toBe(totalDraws());
  });

  it('high numbers carry the threshold and a fair-draw share for each count (F-19)', () => {
    const { highFrom, byCount } = highNumbers();
    expect(highFrom).toBe(32);
    const counted = Object.values(byCount).reduce((sum, b) => sum + b.count, 0);
    expect(counted).toBe(totalDraws());
    for (const bucket of Object.values(byCount)) {
      expect(bucket.fair_percentage).toBeTypeOf('number');
    }
  });

  it('freshness patterns are over the 6 main numbers and sum to six balls', () => {
    for (const p of freshnessPatterns()) {
      expect(p.C0 + p.C1 + p.C_GE_2).toBe(6);
    }
    const weights = freshnessWeights();
    expect(Object.keys(weights).sort()).toEqual(['C0', 'C1', 'C_GE_2']);
  });

  it('the sum and spread statistics the anomaly checks use are present (F-29)', () => {
    expect(sumDistribution()).toHaveProperty('mean');
    expect(sumDistribution()).toHaveProperty('std');
    expect(spreadDistribution()).toHaveProperty('mean');
    expect(spreadDistribution()).toHaveProperty('std');
  });

  it('the HMC category counts cover the 47 numbers', () => {
    const counts = hmcCategoryDistribution().category_counts as Record<string, number>;
    expect(counts.hot + counts.medium + counts.cold).toBe(47);
  });
});
