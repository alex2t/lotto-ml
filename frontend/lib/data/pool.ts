/**
 * The 47 numbers with everything the picker filters on.
 *
 * Each field is read from an artifact, including the freshness bin: the rule is the
 * artifact's own (its `recent_count_key` counted over its `c_max_threshold`), exactly as
 * ml_lotto/features/freshness.py applies it, so the bins here are the bins the rest of the
 * system uses.
 */
import { artifact, requireKey } from './artifacts';
import { latest } from './draws';
import { ALL_NUMBERS, summary } from './numbers';
import type { Category } from './types';

/** The windows the artifacts count, and the honest name for each (web.md 4.2). */
export const RECENT_WINDOWS = [
  { key: 'last_4', draws: 5 },
  { key: 'last_5', draws: 6 },
  { key: 'last_9', draws: 10 },
  { key: 'last_24', draws: 25 },
] as const;

export type RecentWindowKey = (typeof RECENT_WINDOWS)[number]['key'];

export interface PoolNumber {
  number: number;
  category: Category;
  /** Keyed by the honest window size, e.g. recent[10] is the last 10 draws. */
  recent: Record<number, number>;
  freshnessBin: number;
  wasRecentBonus: boolean;
  lastSeen: string;
  totalCount: number;
}

export interface Pool {
  numbers: PoolNumber[];
  /** How many draws the bonus window covers. */
  bonusWindow: number;
  /** The bin a number lands in when it is at or above the threshold. */
  maxBin: number;
  highFrom: number;
}

function freshnessMeta(): { recentKey: string; maxBin: number } {
  const fresh = artifact<Record<string, unknown>>('freshness');
  return {
    recentKey: requireKey<string>(
      fresh,
      'recent_count_key',
      'lotto_7_number_freshness_results.json',
    ),
    maxBin: requireKey<number>(
      fresh,
      'c_max_threshold',
      'lotto_7_number_freshness_results.json',
    ),
  };
}

export function pool(): Pool {
  const { recentKey, maxBin } = freshnessMeta();
  // The latest draw's list is the window facing the NEXT draw (F-33).
  const bonusWindow = latest().recent_bonus_numbers;
  const highFrom = requireKey<number>(
    requireKey<Record<string, unknown>>(
      requireKey<Record<string, unknown>>(
        artifact<Record<string, unknown>>('distributionStats'),
        'analysis_6_main_numbers',
        'lotto_distribution_stats.json',
      ),
      'high_number_distribution',
      'analysis_6_main_numbers',
    ),
    'high_from',
    'high_number_distribution',
  );

  const numbers = ALL_NUMBERS.map((n) => {
    const record = summary(n);
    const recent: Record<number, number> = {};
    for (const window of RECENT_WINDOWS) {
      recent[window.draws] = record.recent[window.key];
    }
    const count = record.recent[recentKey as RecentWindowKey];

    return {
      number: n,
      category: record.category,
      recent,
      freshnessBin: Math.min(count, maxBin),
      wasRecentBonus: bonusWindow.includes(n),
      lastSeen: record.lastSeen,
      totalCount: record.totalCount,
    };
  });

  return { numbers, bonusWindow: bonusWindow.length, maxBin, highFrom };
}
