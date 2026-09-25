/**
 * The Statistics tab's figures: each chart's bars and the one-line headline its card shows
 * while collapsed.
 *
 * Everything is read from the artifacts, or counted from the draw history by `ranged.ts`;
 * picking the largest bar for a headline is the only step taken here. The chat panel's
 * `/explore` fact sheet (nextStep/chat.md section 4) is meant to read the same headlines, so
 * the panel and the page cannot disagree.
 */
import type { Bar } from '@/components/charts/BarChart';
import { artifact, requireKey } from './artifacts';
import { distributionsBetween, type Counted } from './ranged';
import {
  highNumbers,
  hmcCategoryDistribution,
  oddEvenPatterns,
  spreadDistribution,
  sumDistribution,
  sumDistributions,
  totalDraws,
} from './distributions';
import { ALL_NUMBERS, record } from './numbers';
import { numberRows, type NumberRow } from './table';
import { bandLabel } from '../scoring/bands';
import { spreadBandShares } from '../scoring/line';
import type { StatId } from '../guide/statistics';

export interface ScenarioRow {
  key: string;
  label: string;
  hits: number;
  windows: number;
  percentage: number;
}

export interface StatisticsView {
  totalDraws: number;
  filtered: boolean;
  /** "all 499 draws", or "120 draws, 2026-01-01 to 2026-09-23". */
  over: string;
  rangedDraws: number;
  headlines: Record<StatId, string>;
  bars: {
    hmcNow: Bar[];
    hmcSix: Bar[];
    hmcSeven: Bar[];
    oddEven: Bar[];
    sums: Bar[];
    spread: Bar[];
    highNumbers: Bar[];
    oddShare: Bar[];
    consecutivePairs: Bar[];
  };
  highFrom: number;
  sumStats: { mean: number; median: number; std: number };
  spreadStats: { mean: number; median: number };
  mostVolatile: NumberRow[];
  biggestChange: NumberRow[];
  scenarios: ScenarioRow[];
  /** The engine's chi-square p-value across all 46 consecutive pairs. */
  pairsPValue: number;
}

const pct = (value: number) => `${value.toFixed(1)}%`;

function top(bars: Bar[]): Bar | undefined {
  return bars.reduce<Bar | undefined>((best, b) => (!best || b.value > best.value ? b : best), undefined);
}

function mostCommon(bars: Bar[], draws: number): string {
  const best = top(bars);
  return draws && best ? `Most common: ${best.label}, ${pct(best.value)}` : 'No draws in this range';
}

function shareOf(group: Counted[], key: string): number {
  return group.find((g) => g.key === key)?.percentage ?? 0;
}

function sevenBallBars(): Bar[] {
  const odds = artifact<Record<string, unknown>>('odds');
  const hmc = requireKey<Record<string, { percentage: number }>>(odds, 'hmc', 'lotto_odds_results.json');
  return Object.entries(hmc)
    .map(([k, v]) => ({ key: k, label: k, value: v.percentage }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 12);
}

function scenarioRows(): ScenarioRow[] {
  const odds = artifact<Record<string, unknown>>('odds');
  const scenarios = requireKey<
    Array<{
      window_size: number;
      results: Record<string, { hit_count: number; total_windows: number; odds: number }>;
    }>
  >(odds, 'scenarios', 'lotto_odds_results.json');
  return scenarios.flatMap((s) =>
    Object.entries(s.results).map(([times, r]) => ({
      key: `${s.window_size}-${times}`,
      label: `${times.split('_')[0]} times in ${s.window_size} draws`,
      hits: r.hit_count,
      windows: r.total_windows,
      percentage: r.odds * 100,
    })),
  );
}

function oddShareBars(): Bar[] {
  return ALL_NUMBERS.map((n) => {
    const oddEven = record(n).oddEven;
    return {
      key: String(n),
      label: String(n),
      value: requireKey<number>(oddEven, 'affinity_score', 'lotto_odd_even_validated.json') * 100,
      reference:
        requireKey<number>(oddEven, 'chance_affinity_score', 'lotto_odd_even_validated.json') *
        100,
    };
  });
}

function consecutivePairBars(): { bars: Bar[]; pValue: number } {
  const artifactData = artifact<Record<string, unknown>>('consecutivePairs');
  const file = 'lotto_consecutive_pairs_validated.json';
  const counts = requireKey<Record<string, number>>(artifactData, 'pair_counts', file);
  const test = requireKey<Record<string, unknown>>(artifactData, 'overall_chi_square_test', file);
  const details = requireKey<Record<string, { expected: number }>>(test, 'pair_details', file);
  const bars = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12)
    .map(([k, v]) => ({
      key: k,
      label: k,
      value: v,
      reference: requireKey<{ expected: number }>(details, k, file).expected,
    }));
  return { bars, pValue: requireKey<number>(test, 'p_value', file) };
}

export function statisticsView(from?: string, to?: string): StatisticsView {
  const draws = totalDraws();
  const ranged = distributionsBetween(from, to);
  const filtered = Boolean(from || to);
  const over = filtered
    ? `${ranged.draws} draws, ${ranged.from} to ${ranged.to}`
    : `all ${draws} draws`;

  const categories = requireKey<Record<string, number>>(
    hmcCategoryDistribution(),
    'category_counts',
    'lotto_hmc_categorization_validated.json',
  );
  const high = highNumbers();
  const rows = numberRows();
  const pairs = consecutivePairBars();
  const scenarios = scenarioRows();
  const oddEvenFile = artifact<Record<string, unknown>>('oddEven');
  const oddDeviations = requireKey<number>(
    oddEvenFile,
    'num_significant_deviations',
    'lotto_odd_even_validated.json',
  );

  const bars = {
    hmcNow: Object.entries(categories).map(([k, v]) => ({ key: k, label: k, value: v })),
    hmcSix: ranged.hmc.slice(0, 12).map((p) => ({ key: p.key, label: p.key, value: p.percentage })),
    hmcSeven: sevenBallBars(),
    oddEven: Object.keys(oddEvenPatterns('6_main')).map((k) => ({
      key: k,
      label: `${k.split('_')[0]} odd / ${k.split('_')[1]} even`,
      value: shareOf(ranged.oddEven, k),
    })),
    sums: Object.keys(sumDistributions('6_main')).map((k) => ({
      key: k,
      label: bandLabel(k),
      value: shareOf(ranged.sums, k),
    })),
    spread: Object.keys(spreadBandShares()).map((k) => ({
      key: k,
      label: k,
      value: shareOf(ranged.spreads, k),
    })),
    highNumbers: Object.entries(high.byCount).map(([k, v]) => ({
      key: k,
      label: `${k} of six`,
      value: shareOf(ranged.highNumbers, k),
      reference: v.fair_percentage,
    })),
    oddShare: oddShareBars(),
    consecutivePairs: pairs.bars,
  };

  const busiest = pairs.bars[0];
  const flagged = rows.filter((r) => r.trendIsSignificant).length;
  const firstScenario = scenarios[0];

  const headlines: Record<StatId, string> = {
    'hmc-now': Object.entries(categories)
      .map(([k, v]) => `${v} ${k}`)
      .join(', '),
    'hmc-six': mostCommon(bars.hmcSix, ranged.draws),
    'hmc-seven': mostCommon(bars.hmcSeven, draws),
    'odd-even': mostCommon(bars.oddEven, ranged.draws),
    sums: mostCommon(bars.sums, ranged.draws),
    spread: mostCommon(bars.spread, ranged.draws),
    'high-numbers': mostCommon(bars.highNumbers, ranged.draws),
    'odd-share': `${oddDeviations} of 47 stand out from a fair draw`,
    'volatility-trend': `${flagged} of 47 with a significant change`,
    'consecutive-pairs': `Busiest: ${busiest.label}, ${busiest.value} draws (fair: ${busiest.reference?.toFixed(1)})`,
    'repeat-windows': `${firstScenario.label}: ${pct(firstScenario.percentage)} of windows`,
  };

  const sums = sumDistribution() as { mean: number; median: number; std: number };
  const spreads = spreadDistribution() as { mean: number; median: number };

  return {
    totalDraws: draws,
    filtered,
    over,
    rangedDraws: ranged.draws,
    headlines,
    bars,
    highFrom: high.highFrom,
    sumStats: sums,
    spreadStats: spreads,
    mostVolatile: [...rows].sort((a, b) => b.volatility - a.volatility).slice(0, 8),
    biggestChange: [...rows].sort((a, b) => Math.abs(b.trend) - Math.abs(a.trend)).slice(0, 8),
    scenarios,
    pairsPValue: pairs.pValue,
  };
}

