/**
 * The distributions a line is described against: odd/even, sums, spread, high numbers,
 * freshness bins and HMC patterns. All read from drawpick.py's artifacts.
 */
import { artifact, requireKey } from './artifacts';

export interface Bucket {
  count: number;
  percentage: number;
  odds: number;
  /** Present on high_number_distribution: the share a fair draw would give. */
  fair_percentage?: number;
}

type Stats = Record<string, unknown>;

function section(name: '6_main' | 'all_7'): Record<string, unknown> {
  const stats = artifact<Stats>('distributionStats');
  const key =
    name === '6_main' ? 'analysis_6_main_numbers' : 'analysis_all_7_numbers';
  return requireKey<Record<string, unknown>>(
    stats,
    key,
    'lotto_distribution_stats.json',
  );
}

export function totalDraws(): number {
  return requireKey<number>(
    artifact<Stats>('distributionStats'),
    'total_draws_analyzed',
    'lotto_distribution_stats.json',
  );
}

/** Odd/even patterns, e.g. "3_3", over the 6 main numbers or all 7. */
export function oddEvenPatterns(over: '6_main' | 'all_7' = '6_main'): Record<string, Bucket> {
  return requireKey<Record<string, Bucket>>(
    section(over),
    'odd_even_patterns',
    'lotto_distribution_stats.json',
  );
}

/** Sum bands, e.g. "S6_MID_LOW (125-139)". */
export function sumDistributions(over: '6_main' | 'all_7' = '6_main'): Record<string, Bucket> {
  return requireKey<Record<string, Bucket>>(
    section(over),
    'sum_distributions',
    'lotto_distribution_stats.json',
  );
}

export interface HighNumbers {
  /** The threshold a number counts as high from (32). */
  highFrom: number;
  /** Draws by how many main numbers were >= highFrom, with the fair-draw share (F-19). */
  byCount: Record<string, Bucket>;
}

export function highNumbers(): HighNumbers {
  const block = requireKey<Record<string, unknown>>(
    section('6_main'),
    'high_number_distribution',
    'lotto_distribution_stats.json',
  );
  return {
    highFrom: requireKey<number>(block, 'high_from', 'high_number_distribution'),
    byCount: requireKey<Record<string, Bucket>>(
      block,
      'by_count',
      'high_number_distribution',
    ),
  };
}

export interface FreshnessPattern {
  pattern: string;
  draws_matched: number;
  percentage: number;
  C0: number;
  C1: number;
  C_GE_2: number;
}

/** The freshness bin patterns past draws formed, over the 6 main numbers. */
export function freshnessPatterns(): FreshnessPattern[] {
  return requireKey<FreshnessPattern[]>(
    artifact<Stats>('freshness'),
    'distribution_analysis_6_main',
    'lotto_7_number_freshness_results.json',
  );
}

/** The C0/C1/C_GE_2 weights of a typical draw. */
export function freshnessWeights(): Record<string, Record<string, number>> {
  return requireKey<Record<string, Record<string, number>>>(
    artifact<Stats>('freshness'),
    'freshness_weight_calculation',
    'lotto_7_number_freshness_results.json',
  );
}

/** Range spread of past draws: mean, median, std, min, max. */
export function spreadDistribution(): Record<string, unknown> {
  return requireKey<Record<string, unknown>>(
    artifact<Stats>('rangeSpread'),
    'overall_distribution',
    'lotto_range_spread_validated.json',
  );
}

/** Sum of past draws: mean, median, std, min, max - what the anomaly checks use (F-29). */
export function sumDistribution(): Record<string, unknown> {
  return requireKey<Record<string, unknown>>(
    artifact<Stats>('sumContribution'),
    'overall_distribution',
    'lotto_sum_contribution_validated.json',
  );
}

/** How the 47 numbers currently split across hot/medium/cold. */
export function hmcCategoryDistribution(): Record<string, unknown> {
  return requireKey<Record<string, unknown>>(
    artifact<Stats>('hmcCategorization'),
    'category_distribution',
    'lotto_hmc_categorization_validated.json',
  );
}

/** Consecutive-pair frequencies in past draws. */
export function consecutivePairs(): Record<string, unknown> {
  return artifact<Record<string, unknown>>('consecutivePairs');
}

export interface BonusReturn {
  /** Share of bonus balls that came up as a main number within `window` draws. */
  rate: number;
  /** The same share in a fair draw. */
  fairRate: number;
  window: number;
}

/** How often a bonus ball came back as a main number, next to a fair draw (F-30). */
export function bonusReturn(): BonusReturn {
  const where = 'lotto_bonus_to_main_patterns.json';
  const patterns = artifact<Stats>('bonusToMain');
  const factors = requireKey<Stats>(patterns, 'transition_prediction_factors', where);
  const timing = requireKey<Stats>(patterns, 'timing_decay_weights', where);
  return {
    rate: requireKey<number>(factors, 'base_rate', 'transition_prediction_factors'),
    fairRate: requireKey<number>(factors, 'expected_random_rate', 'transition_prediction_factors'),
    // One weight per draw of the window the analyzer counted over.
    window: Object.keys(timing).length,
  };
}
