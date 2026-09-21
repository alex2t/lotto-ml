/**
 * The hot/medium/cold pattern of the six main numbers.
 *
 * The distribution is read from `lotto_odds_results.json` `hmc_6`, written by drawpick.py
 * from each draw's PRE-draw categories (F-27). Its sibling `hmc` is over all seven balls -
 * every key in it sums to 7 - so a six-number line can only be compared with `hmc_6`, which
 * is what F-59 was about.
 */
import { artifact, requireKey } from './artifacts';
import type { Category, DrawEntry } from './types';

export interface HmcPattern {
  hot: number;
  medium: number;
  cold: number;
}

export function patternKey(p: HmcPattern): string {
  return `${p.hot}-${p.medium}-${p.cold}`;
}

/** A draw's pattern over its six main numbers, using the categories in force before it. */
export function drawPattern(draw: DrawEntry): HmcPattern {
  const counts: Record<Category, number> = { hot: 0, medium: 0, cold: 0 };
  for (const n of draw.main_numbers) {
    const detail = draw.winning_numbers_details.find((b) => b.number === n && !b.is_bonus);
    if (!detail) {
      throw new Error(`Draw ${draw.draw_date} has no pre-draw detail for main number ${n}`);
    }
    counts[detail.category] += 1;
  }
  return { hot: counts.hot, medium: counts.medium, cold: counts.cold };
}

export interface PatternShare {
  pattern: string;
  count: number;
  percentage: number;
}

/** Every six-ball pattern past draws have formed, most common first. */
export function sixBallPatterns(): PatternShare[] {
  const odds = artifact<Record<string, unknown>>('odds');
  const block = requireKey<Record<string, { count: number; percentage: number }>>(
    odds,
    'hmc_6',
    'lotto_odds_results.json',
  );
  return Object.entries(block)
    .map(([pattern, { count, percentage }]) => ({ pattern, count, percentage }))
    .sort((a, b) => b.count - a.count || a.pattern.localeCompare(b.pattern));
}

/** The share of past draws with this six-ball pattern; 0 if it has never happened. */
export function patternShare(pattern: string): number {
  return sixBallPatterns().find((p) => p.pattern === pattern)?.percentage ?? 0;
}
