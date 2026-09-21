/**
 * What the wheels contain.
 *
 * Every filter removes numbers from the pool, and the picker shows the cost of each one
 * immediately - a filter whose effect is invisible is just a switch.
 */
import type { PoolNumber } from '../data/pool';

export interface Filters {
  /** Remove numbers drawn more than `times` in the last `draws` draws. */
  drawnMoreThan: { draws: number; times: number } | null;
  /** Remove numbers not drawn at all in the last `draws` draws. */
  notDrawnIn: number | null;
  /** Freshness bins to keep. Empty means all of them. */
  bins: number[];
  /** Remove numbers that were a bonus ball in the recent window. */
  dropRecentBonus: boolean;
  /** 'high' keeps numbers >= highFrom, 'low' keeps the rest. */
  half: 'high' | 'low' | null;
}

export const NO_FILTERS: Filters = {
  drawnMoreThan: null,
  notDrawnIn: null,
  bins: [],
  dropRecentBonus: false,
  half: null,
};

export interface Chip {
  id: keyof Filters;
  label: string;
}

/** What the player has narrowed to, as removable chips. */
export function chips(filters: Filters, highFrom: number): Chip[] {
  const out: Chip[] = [];
  if (filters.drawnMoreThan) {
    const { draws, times } = filters.drawnMoreThan;
    out.push({
      id: 'drawnMoreThan',
      label: `drawn more than ${times} time${times === 1 ? '' : 's'} in the last ${draws} draws`,
    });
  }
  if (filters.notDrawnIn) {
    out.push({
      id: 'notDrawnIn',
      label: `not drawn in the last ${filters.notDrawnIn} draws`,
    });
  }
  if (filters.bins.length > 0) {
    out.push({ id: 'bins', label: `freshness ${filters.bins.map((b) => `C${b}`).join(', ')}` });
  }
  if (filters.dropRecentBonus) {
    out.push({ id: 'dropRecentBonus', label: 'was a recent bonus ball' });
  }
  if (filters.half) {
    out.push({
      id: 'half',
      label: filters.half === 'high' ? `${highFrom} and above` : `below ${highFrom}`,
    });
  }
  return out;
}

export function applyFilters(
  numbers: PoolNumber[],
  filters: Filters,
  highFrom: number,
): PoolNumber[] {
  return numbers.filter((n) => {
    if (filters.drawnMoreThan) {
      const { draws, times } = filters.drawnMoreThan;
      if (n.recent[draws] > times) return false;
    }
    if (filters.notDrawnIn && n.recent[filters.notDrawnIn] === 0) return false;
    if (filters.bins.length > 0 && !filters.bins.includes(n.freshnessBin)) return false;
    if (filters.dropRecentBonus && n.wasRecentBonus) return false;
    if (filters.half === 'high' && n.number < highFrom) return false;
    if (filters.half === 'low' && n.number >= highFrom) return false;
    return true;
  });
}

/** Removes one chip's filter. */
export function clearFilter(filters: Filters, id: keyof Filters): Filters {
  return { ...filters, [id]: NO_FILTERS[id] };
}

/** A uniform pick of `count` distinct numbers from `from`. */
export function sample(from: number[], count: number): number[] {
  const pool = [...from];
  const picked: number[] = [];
  while (picked.length < count && pool.length > 0) {
    const index = Math.floor(Math.random() * pool.length);
    picked.push(pool.splice(index, 1)[0]);
  }
  return picked;
}
