/**
 * The draw history, server side only.
 *
 * lotto_draw_history.json is 4.4 MB and must never be sent to the browser whole. Everything
 * here returns a page, one number's appearances, or a summary - never the parsed artifact.
 */
import { artifact, requireKey } from './artifacts';
import type { DrawEntry, DrawHistory } from './types';

/** Every draw, oldest first. */
export function allDraws(): DrawEntry[] {
  const history = artifact<DrawHistory>('drawHistory');
  return Object.keys(history)
    .sort()
    .map((date) => requireKey<DrawEntry>(history, date, 'lotto_draw_history.json'));
}

export function latest(): DrawEntry {
  const draws = allDraws();
  if (draws.length === 0) throw new Error('lotto_draw_history.json holds no draws');
  return draws[draws.length - 1];
}

export function byDate(date: string): DrawEntry {
  const history = artifact<DrawHistory>('drawHistory');
  return requireKey<DrawEntry>(history, date, 'lotto_draw_history.json');
}

export interface DrawPage {
  draws: DrawEntry[];
  total: number;
  offset: number;
  limit: number;
}

/** A page of draws, newest first. */
export function page(offset = 0, limit = 25): DrawPage {
  const draws = allDraws().reverse();
  return {
    draws: draws.slice(offset, offset + limit),
    total: draws.length,
    offset,
    limit,
  };
}

/** Every draw containing a number, newest first, with how it was drawn. */
export function byNumber(n: number): Array<{
  draw: DrawEntry;
  asBonus: boolean;
  detail: DrawEntry['winning_numbers_details'][number];
}> {
  return allDraws()
    .reverse()
    .filter((d) => d.main_numbers.includes(n) || d.bonus_number === n)
    .map((draw) => {
      const detail = draw.winning_numbers_details.find((b) => b.number === n);
      if (!detail) {
        throw new Error(
          `Draw ${draw.draw_date} lists ${n} but has no winning_numbers_details entry for it`,
        );
      }
      return { draw, asBonus: draw.bonus_number === n, detail };
    });
}

/** Every draw on or after a date, oldest first. */
export function sinceDate(date: string): DrawEntry[] {
  return allDraws().filter((d) => d.draw_date >= date);
}
