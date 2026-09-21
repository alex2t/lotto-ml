/**
 * The server-side queries behind Explore.
 *
 * The draw history is 4.4 MB: it is filtered and paged here and only the page a view needs
 * crosses to the browser.
 */
import { allDraws } from './draws';
import { drawPattern, patternKey } from './hmc';
import { sumBand, spreadBand } from '../scoring/bands';
import type { DrawEntry } from './types';

export interface DrawFilters {
  from?: string;
  to?: string;
  /** Draws containing every one of these numbers. */
  contains?: number[];
  /** "3_3" etc. */
  oddEven?: string;
  sumBand?: string;
  highCount?: number;
}

export interface DrawRow {
  date: string;
  main: number[];
  categories: string[];
  bonus: number;
  odd: number;
  sum: number;
  spread: number;
  high: number;
  hmc: string;
}

export const HIGH_FROM = 32;

export function toRow(draw: DrawEntry): DrawRow {
  const main = draw.main_numbers;
  const categories = main.map((n) => {
    const detail = draw.winning_numbers_details.find((b) => b.number === n && !b.is_bonus);
    if (!detail) throw new Error(`Draw ${draw.draw_date} has no detail for ${n}`);
    return detail.category;
  });

  return {
    date: draw.draw_date,
    main,
    categories,
    bonus: draw.bonus_number,
    odd: main.filter((n) => n % 2 === 1).length,
    sum: main.reduce((a, b) => a + b, 0),
    spread: Math.max(...main) - Math.min(...main),
    high: main.filter((n) => n >= HIGH_FROM).length,
    hmc: patternKey(drawPattern(draw)),
  };
}

function matches(row: DrawRow, filters: DrawFilters): boolean {
  if (filters.from && row.date < filters.from) return false;
  if (filters.to && row.date > filters.to) return false;
  if (filters.contains?.length) {
    const all = [...row.main, row.bonus];
    if (!filters.contains.every((n) => all.includes(n))) return false;
  }
  if (filters.oddEven && `${row.odd}_${6 - row.odd}` !== filters.oddEven) return false;
  if (filters.sumBand && sumBand(row.sum).key !== filters.sumBand) return false;
  if (filters.highCount !== undefined && row.high !== filters.highCount) return false;
  return true;
}

export interface DrawQuery {
  rows: DrawRow[];
  total: number;
  page: number;
  pages: number;
}

export const PAGE_SIZE = 50;

/** Filtered draws, newest first, one page at a time. */
export function queryDraws(filters: DrawFilters, page = 1): DrawQuery {
  const all = allDraws().map(toRow).reverse().filter((row) => matches(row, filters));
  const pages = Math.max(1, Math.ceil(all.length / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), pages);

  return {
    rows: all.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE),
    total: all.length,
    page: current,
    pages,
  };
}

export interface SimilarDraw {
  row: DrawRow;
  /** How many of the player's six the draw held. */
  shared: number;
  sharedNumbers: number[];
}

/**
 * The past draws most like a line, exact matches included.
 *
 * Read with data['main_numbers'], which is what F-25 was about: an empty default made this
 * answer "no similar draws" for ten months.
 */
export function similarDraws(line: number[], limit = 10): SimilarDraw[] {
  const set = new Set(line);
  return allDraws()
    .map(toRow)
    .map((row) => {
      const sharedNumbers = row.main.filter((n) => set.has(n));
      return { row, shared: sharedNumbers.length, sharedNumbers };
    })
    .filter((d) => d.shared > 0)
    .sort((a, b) => b.shared - a.shared || b.row.date.localeCompare(a.row.date))
    .slice(0, limit);
}

/** How many past draws shared each possible count of numbers with the line. */
export function overlapHistogram(line: number[]): Record<number, number> {
  const set = new Set(line);
  const counts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
  for (const draw of allDraws()) {
    counts[draw.main_numbers.filter((n) => set.has(n)).length] += 1;
  }
  return counts;
}

/** The spread of a draw, for the Statistics tab, using the shared band rule. */
export function spreadKeyOf(spread: number): string {
  return spreadBand(spread).key;
}
