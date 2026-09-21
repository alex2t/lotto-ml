import { beforeEach, describe, expect, it } from 'vitest';
import { ALL_NUMBERS, allSummaries, byCategory, record, summary } from '@/lib/data/numbers';
import { useFixtures } from './setup-fixtures';

describe('numbers', () => {
  beforeEach(() => useFixtures());

  it('has a summary for all 47 numbers', () => {
    const summaries = allSummaries();
    expect(summaries).toHaveLength(47);
    expect(summaries.map((s) => s.number)).toEqual(ALL_NUMBERS);
    for (const s of summaries) {
      expect(['hot', 'medium', 'cold']).toContain(s.category);
      expect(s.totalCount).toBeGreaterThan(0);
    }
  });

  it('joins every per-number artifact into one dossier', () => {
    const r = record(7);
    expect(r.number).toBe(7);
    expect(r.patterns).toHaveProperty('appearance_volatility');
    // F-38: the affinity is only meaningful next to the fair-draw chance.
    expect(r.oddEven).toHaveProperty('affinity_score');
    expect(r.oddEven).toHaveProperty('chance_affinity_score');
    expect(r.sumContribution).toHaveProperty('contribution_score');
    expect(r.rangeSpread).toHaveProperty('contribution_score');
    expect(r.bonus).toHaveProperty('bonus_rate');
  });

  it('rejects a number outside 1-47', () => {
    expect(() => summary(0)).toThrowError(/outside 1-47/);
    expect(() => summary(48)).toThrowError(/outside 1-47/);
    expect(() => record(1.5)).toThrowError(/outside 1-47/);
  });

  it('byCategory partitions the 47 numbers', () => {
    const grouped = byCategory();
    const all = [...grouped.hot, ...grouped.medium, ...grouped.cold].sort(
      (a, b) => a - b,
    );
    expect(all).toEqual(ALL_NUMBERS);
  });
});
