import { beforeEach, describe, expect, it } from 'vitest';
import { dossier } from '@/lib/data/dossier';
import { artifact, requireKey } from '@/lib/data/artifacts';
import { useFixtures } from './setup-fixtures';

describe('the number dossier', () => {
  beforeEach(() => useFixtures());

  it('carries every section the fact sheet shows', () => {
    const d = dossier(23);
    expect(d.number).toBe(23);
    expect(d.profile.category).toBeDefined();
    expect(d.record.patterns).toHaveProperty('appearance_volatility');
    expect(d.record.bonus).toHaveProperty('bonus_rate');
    expect(d.gaps.appearances).toBeGreaterThanOrEqual(0);
    expect(Array.isArray(d.appearances)).toBe(true);
  });

  it('rejects a number outside 1-47 rather than inventing one', () => {
    expect(() => dossier(0)).toThrow();
    expect(() => dossier(48)).toThrow();
  });

  describe('often drawn with', () => {
    it('reads the counts from the artifact, never counting them itself', () => {
      // The site computes nothing: drawpick.py writes lotto_number_pairs.json.
      const pairs = artifact<Record<string, unknown>>('numberPairs');
      const perNumber = requireKey<Record<string, { top_partners: unknown[] }>>(
        pairs,
        'per_number',
        'lotto_number_pairs.json',
      );
      expect(dossier(23).partners.top).toEqual(perNumber['23'].top_partners);
    });

    it('never lists the number itself as its own partner', () => {
      for (const n of [1, 7, 23, 47]) {
        expect(dossier(n).partners.top.map((p) => p.number)).not.toContain(n);
      }
    });

    it('is ordered by count, most frequent first', () => {
      const counts = dossier(23).partners.top.map((p) => p.count);
      expect(counts).toEqual([...counts].sort((a, b) => b - a));
    });

    it('publishes the fair-draw expectation, so a count is never read alone (F-38)', () => {
      const { expected } = dossier(23).partners;
      expect(expected).toBeGreaterThan(0);
      // And the top count must be the same order of magnitude - it is sampling noise, not
      // a pairing, and the page says so next to it.
      const top = dossier(23).partners.top[0];
      if (top) expect(top.count).toBeLessThan(expected * 3);
    });
  });
});
