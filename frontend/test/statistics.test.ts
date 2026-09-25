import { beforeEach, describe, expect, it } from 'vitest';
import { artifact, requireKey } from '@/lib/data/artifacts';
import { distributionsBetween } from '@/lib/data/ranged';
import { statisticsView } from '@/lib/data/statistics';
import { chatAnswer, STAT_GROUPS, STATISTICS_GUIDE } from '@/lib/guide/statistics';
import { useFixtures } from './setup-fixtures';

describe('the statistics guide', () => {
  it('puts every statistic in exactly one group', () => {
    const grouped = STAT_GROUPS.flatMap((g) => g.ids);
    expect([...grouped].sort()).toEqual(STATISTICS_GUIDE.map((g) => g.id).sort());
    expect(new Set(grouped).size).toBe(grouped.length);
  });

  it('explains every statistic and gives the chat questions to match', () => {
    for (const entry of STATISTICS_GUIDE) {
      expect(entry.summary.length, entry.id).toBeGreaterThan(20);
      expect(entry.howToRead.length, entry.id).toBeGreaterThan(40);
      expect(entry.whatItMeans.length, entry.id).toBeGreaterThan(40);
      expect(entry.patterns.length, entry.id).toBeGreaterThanOrEqual(3);
      expect(chatAnswer(entry), entry.id).toContain(entry.whatItMeans);
    }
  });
});

describe('the statistics headlines', () => {
  beforeEach(() => useFixtures());

  it('gives every statistic a headline', () => {
    const view = statisticsView();
    for (const entry of STATISTICS_GUIDE) {
      expect(view.headlines[entry.id], entry.id).toBeTruthy();
    }
  });

  it('names the most common six-ball pattern that the draws give', () => {
    const top = distributionsBetween().hmc[0];
    expect(statisticsView().headlines['hmc-six']).toBe(
      `Most common: ${top.key}, ${top.percentage.toFixed(1)}%`,
    );
  });

  it('counts all 47 numbers across hot, medium and cold', () => {
    const counts = statisticsView().headlines['hmc-now'].match(/\d+/g)!.map(Number);
    expect(counts.reduce((a, b) => a + b, 0)).toBe(47);
  });

  it('quotes the engine for the odd-share count and the busiest pair', () => {
    const view = statisticsView();
    const oddEven = artifact<Record<string, unknown>>('oddEven');
    const deviations = requireKey<number>(oddEven, 'num_significant_deviations', 'odd/even');
    expect(view.headlines['odd-share']).toMatch(new RegExp(`^${deviations} of 47`));

    const counts = requireKey<Record<string, number>>(
      artifact<Record<string, unknown>>('consecutivePairs'),
      'pair_counts',
      'pairs',
    );
    const busiest = Math.max(...Object.values(counts));
    expect(view.headlines['consecutive-pairs']).toContain(`, ${busiest} draws`);
  });

  it('says a range with no draws in it has none, rather than a zero share', () => {
    const view = statisticsView('2100-01-01', '2100-12-31');
    expect(view.rangedDraws).toBe(0);
    for (const id of ['odd-even', 'sums', 'spread', 'high-numbers', 'hmc-six'] as const) {
      expect(view.headlines[id], id).toBe('No draws in this range');
    }
  });

  it('describes a repeat scenario as windows, not as the next draw (F-70)', () => {
    const odds = artifact<Record<string, unknown>>('odds');
    const scenarios = requireKey<
      Array<{ window_size: number; results: Record<string, { hit_count: number; total_windows: number }> }>
    >(odds, 'scenarios', 'odds');
    const first = scenarios[0];
    const [times, result] = Object.entries(first.results)[0];
    const row = statisticsView().scenarios[0];

    expect(row.label).toBe(`${times.split('_')[0]} times in ${first.window_size} draws`);
    expect(row.percentage).toBeCloseTo((result.hit_count / result.total_windows) * 100, 1);
  });
});
