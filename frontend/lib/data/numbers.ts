/**
 * The 47 per-number records, joined across the artifacts that hold one.
 *
 * Nothing here computes a statistic: every field is read from what drawpick.py wrote.
 */
import { artifact, requireKey } from './artifacts';
import type { Category, TriggerPeriodRecord, TriggerPeriods } from './types';

/** Irish Lotto is 6/47 plus a bonus. */
export const NUMBER_COUNT = 47;

export const ALL_NUMBERS: number[] = Array.from(
  { length: NUMBER_COUNT },
  (_, i) => i + 1,
);

type PerNumber = Record<string, Record<string, unknown>>;

function perNumber(
  file: Parameters<typeof artifact>[0],
  section: string,
  n: number,
  fileName: string,
): Record<string, unknown> {
  const root = artifact<Record<string, unknown>>(file);
  const block = requireKey<PerNumber>(root, section, fileName);
  return requireKey<Record<string, unknown>>(block, String(n), `${fileName}.${section}`);
}

export interface NumberSummary {
  number: number;
  category: Category;
  totalCount: number;
  lastSeen: string;
  recent: TriggerPeriodRecord['recent'];
}

export interface NumberRecord extends NumberSummary {
  /** lotto_advanced_patterns.json: volatility, gaps, trend, regime shifts. */
  patterns: Record<string, unknown>;
  /** lotto_odd_even_validated.json, including the fair-draw chance it must be shown against (F-38). */
  oddEven: Record<string, unknown>;
  /** lotto_sum_contribution_validated.json. */
  sumContribution: Record<string, unknown>;
  /** lotto_range_spread_validated.json. */
  rangeSpread: Record<string, unknown>;
  /** lotto_bonus_analysis.json per-number bonus profile. */
  bonus: Record<string, unknown>;
}

function assertNumber(n: number): void {
  if (!Number.isInteger(n) || n < 1 || n > NUMBER_COUNT) {
    throw new Error(`Number ${n} is outside 1-${NUMBER_COUNT}`);
  }
}

function trigger(n: number): TriggerPeriodRecord {
  const periods = artifact<TriggerPeriods>('triggerPeriods');
  return requireKey<TriggerPeriodRecord>(
    periods as unknown as Record<string, unknown>,
    String(n),
    'lotto_trigger_periods.json',
  );
}

export function summary(n: number): NumberSummary {
  assertNumber(n);
  const record = trigger(n);
  return {
    number: n,
    category: record.category,
    totalCount: record.total_count,
    lastSeen: record.last_seen,
    recent: record.recent,
  };
}

/** The trigger series the artifact records for a number. */
export function series(n: number): Record<string, unknown> {
  assertNumber(n);
  return trigger(n).series;
}

export function allSummaries(): NumberSummary[] {
  return ALL_NUMBERS.map(summary);
}

export function record(n: number): NumberRecord {
  assertNumber(n);
  return {
    ...summary(n),
    patterns: perNumber(
      'advancedPatterns',
      'per_number_features',
      n,
      'lotto_advanced_patterns.json',
    ),
    oddEven: perNumber(
      'oddEven',
      'per_number_affinity',
      n,
      'lotto_odd_even_validated.json',
    ),
    sumContribution: perNumber(
      'sumContribution',
      'per_number_contribution',
      n,
      'lotto_sum_contribution_validated.json',
    ),
    rangeSpread: perNumber(
      'rangeSpread',
      'per_number_contribution',
      n,
      'lotto_range_spread_validated.json',
    ),
    bonus: perNumber(
      'bonusAnalysis',
      'per_number_bonus_profile',
      n,
      'lotto_bonus_analysis.json',
    ),
  };
}

/** The numbers in each category, as the latest artifacts see them. */
export function byCategory(): Record<Category, number[]> {
  const grouped: Record<Category, number[]> = { hot: [], medium: [], cold: [] };
  for (const s of allSummaries()) grouped[s.category].push(s.number);
  return grouped;
}
