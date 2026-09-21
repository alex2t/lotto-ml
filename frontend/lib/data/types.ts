/** The shapes of the artifacts the site reads. Mirrors what drawpick.py writes. */

export type Category = 'hot' | 'medium' | 'cold';

export interface RecentCounts {
  last_4: number;
  last_5: number;
  last_9: number;
  last_24: number;
}

export interface BallDetail {
  number: number;
  is_bonus: boolean;
  /** The category in force BEFORE this draw (F-27). */
  category: Category;
  days_since_last_hit: number;
  recent_counts: RecentCounts;
  win_bias_ratio: number;
  freshness_weights: Record<string, number>;
  current_freshness_bin: number;
  is_recent_bonus_hit: boolean;
  bonus_hit_contribution: number;
}

export interface DrawEntry {
  draw_index: number;
  draw_date: string;
  main_numbers: number[];
  bonus_number: number;
  hmc_summary: {
    hot_count: number;
    medium_count: number;
    cold_count: number;
    hmc_distribution: string;
    draw_range: number;
  };
  categories_pre_draw: {
    hot_numbers: number[];
    medium_numbers: number[];
    cold_numbers: number[];
  };
  winning_numbers_details: BallDetail[];
  all_numbers_bias_ratios: Record<string, number>;
  freshness_pattern_weights: Record<string, number>;
  /** The 10 bonus balls up to and including this draw - the window for the NEXT draw (F-33). */
  recent_bonus_numbers: number[];
  distribution_features: Record<string, string | number>;
  bonus_hit_analysis: Record<string, string | number | boolean>;
}

export type DrawHistory = Record<string, DrawEntry>;

export interface TriggerPeriodRecord {
  total_count: number;
  /** yyyy/mm/dd, as the analyzer writes it. */
  last_seen: string;
  category: Category;
  recent: RecentCounts;
  series: Record<string, unknown>;
}

export type TriggerPeriods = Record<string, TriggerPeriodRecord>;
