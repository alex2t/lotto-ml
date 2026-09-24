/**
 * The 47 numbers as a table - what the Trigger Periods page was, once you take away the
 * page and keep what it actually did: a way of filtering and sorting the 47 numbers.
 *
 * Every column is read from an artifact. The filter rail below is the same set of filters
 * that page offered: category, freshness bin, volatility, trend, momentum and regime shift.
 */
import { artifact, requireKey } from './artifacts';
import { pool, type PoolNumber } from './pool';
import type { Category } from './types';

export interface NumberRow extends PoolNumber {
  volatility: number;
  trend: number;
  trendIsSignificant: boolean;
  /** recent_vs_baseline: how the recent window compares with the longer one. */
  momentum: number;
  inRegimeShift: boolean;
  averageGapDays: number;
  bonusAppearances: number;
}

export interface RailFilters {
  category?: Category;
  bin?: number;
  /** Only numbers whose trend the artifact marks significant. */
  trending?: boolean;
  /** Only numbers the artifact says are in a regime shift. */
  regimeShift?: boolean;
  /** Only numbers whose volatility is at or above this. */
  minVolatility?: number;
  /** Only numbers whose momentum is at or above this. */
  minMomentum?: number;
  /** Only numbers that were a bonus ball in the recent window. */
  recentBonus?: boolean;
}

export type SortKey =
  | 'number'
  | 'category'
  | 'totalCount'
  | 'volatility'
  | 'trend'
  | 'momentum'
  | 'recent10';

function features(n: number): Record<string, unknown> {
  const patterns = artifact<Record<string, unknown>>('advancedPatterns');
  const block = requireKey<Record<string, Record<string, unknown>>>(
    patterns,
    'per_number_features',
    'lotto_advanced_patterns.json',
  );
  return requireKey<Record<string, unknown>>(
    block,
    String(n),
    'lotto_advanced_patterns.json.per_number_features',
  );
}

function bonusProfile(n: number): Record<string, unknown> {
  const bonus = artifact<Record<string, unknown>>('bonusAnalysis');
  const block = requireKey<Record<string, Record<string, unknown>>>(
    bonus,
    'per_number_bonus_profile',
    'lotto_bonus_analysis.json',
  );
  return requireKey<Record<string, unknown>>(
    block,
    String(n),
    'lotto_bonus_analysis.json.per_number_bonus_profile',
  );
}

export function numberRows(): NumberRow[] {
  return pool().numbers.map((p) => {
    const f = features(p.number);
    const b = bonusProfile(p.number);
    return {
      ...p,
      volatility: f.appearance_volatility as number,
      trend: f.appearance_trend_raw as number,
      trendIsSignificant: f.trend_is_significant as boolean,
      momentum: f.recent_vs_baseline as number,
      inRegimeShift: f.in_regime_shift as boolean,
      averageGapDays: f.avg_gap_days as number,
      bonusAppearances: b.bonus_appearances as number,
    };
  });
}

/** The rail's filters from the /numbers query string, so the page and the chat panel agree. */
export function railFromParams(get: (key: string) => string | undefined): RailFilters {
  return {
    category: get('category') as Category | undefined,
    bin: get('bin') ? Number(get('bin')) : undefined,
    trending: get('trending') === '1',
    regimeShift: get('regime') === '1',
    minVolatility: get('volatility') ? Number(get('volatility')) : undefined,
    minMomentum: get('momentum') ? Number(get('momentum')) : undefined,
    recentBonus: get('bonus') === '1',
  };
}

export function applyRail(rows: NumberRow[], filters: RailFilters): NumberRow[] {
  return rows.filter((row) => {
    if (filters.category && row.category !== filters.category) return false;
    if (filters.bin !== undefined && row.freshnessBin !== filters.bin) return false;
    if (filters.trending && !row.trendIsSignificant) return false;
    if (filters.regimeShift && !row.inRegimeShift) return false;
    if (filters.minVolatility !== undefined && row.volatility < filters.minVolatility) {
      return false;
    }
    if (filters.minMomentum !== undefined && row.momentum < filters.minMomentum) return false;
    if (filters.recentBonus && !row.wasRecentBonus) return false;
    return true;
  });
}

const CATEGORY_ORDER: Record<Category, number> = { hot: 0, medium: 1, cold: 2 };

export function sortRows(rows: NumberRow[], key: SortKey, descending: boolean): NumberRow[] {
  const value = (row: NumberRow): number => {
    switch (key) {
      case 'category':
        return CATEGORY_ORDER[row.category];
      case 'totalCount':
        return row.totalCount;
      case 'volatility':
        return row.volatility;
      case 'trend':
        return row.trend;
      case 'momentum':
        return row.momentum;
      case 'recent10':
        return row.recent[10];
      default:
        return row.number;
    }
  };

  return [...rows].sort((a, b) =>
    descending ? value(b) - value(a) || a.number - b.number : value(a) - value(b) || a.number - b.number,
  );
}
