/**
 * One number's fact sheet - every section Number Insights showed, read from the artifacts.
 *
 * A fact sheet, never a rating: nothing here scores a number or calls it due (F-30).
 */
import { artifact, requireKey } from './artifacts';
import { allDraws, byNumber } from './draws';
import { record, series, summary, type NumberRecord } from './numbers';
import { pool, type PoolNumber } from './pool';

export interface Appearance {
  date: string;
  asBonus: boolean;
  /** The category in force before that draw (F-27). */
  category: string;
  daysSinceLastHit: number;
}

export interface GapStats {
  appearances: number;
  averageDraws: number | null;
  longestDraws: number | null;
  /** How many draws since it last appeared. */
  currentDraws: number;
}

export interface Partner {
  number: number;
  count: number;
}

export interface Partners {
  /** The numbers most often drawn with this one. */
  top: Partner[];
  /** How often any pair comes up in a fair draw over the same history. */
  expected: number;
}

export interface Dossier {
  number: number;
  profile: PoolNumber;
  record: NumberRecord;
  appearances: Appearance[];
  gaps: GapStats;
  /** The trigger series the artifact records for this number. */
  series: Record<string, unknown>;
  /** The numbers it has come up with most often, and what chance alone gives (F-38's rule). */
  partners: Partners;
}

/** Gaps measured in draws between appearances. */
function gapStats(dates: string[], allDates: string[]): GapStats {
  const indexOf = new Map(allDates.map((d, i) => [d, i]));
  const positions = dates
    .map((d) => indexOf.get(d))
    .filter((i): i is number => i !== undefined)
    .sort((a, b) => a - b);

  if (positions.length === 0) {
    return {
      appearances: 0,
      averageDraws: null,
      longestDraws: null,
      currentDraws: allDates.length,
    };
  }

  const gaps: number[] = [];
  for (let i = 1; i < positions.length; i += 1) gaps.push(positions[i] - positions[i - 1]);

  return {
    appearances: positions.length,
    averageDraws: gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : null,
    longestDraws: gaps.length ? Math.max(...gaps) : null,
    currentDraws: allDates.length - 1 - positions[positions.length - 1],
  };
}

export function dossier(n: number): Dossier {
  summary(n); // Validates the number before anything heavier runs.

  const appearances: Appearance[] = byNumber(n).map((a) => ({
    date: a.draw.draw_date,
    asBonus: a.asBonus,
    category: a.detail.category,
    daysSinceLastHit: a.detail.days_since_last_hit,
  }));

  const profile = pool().numbers.find((p) => p.number === n);
  if (!profile) throw new Error(`No pool entry for ${n}`);

  return {
    number: n,
    profile,
    record: record(n),
    appearances,
    gaps: gapStats(
      appearances.map((a) => a.date),
      allDraws().map((d) => d.draw_date),
    ),
    series: series(n),
    partners: partners(n),
  };
}

/** Co-occurrence counts, written by drawpick.py - the site does not count them itself. */
function partners(n: number): Partners {
  const pairs = artifact<Record<string, unknown>>('numberPairs');
  const perNumber = requireKey<Record<string, { top_partners: Partner[] }>>(
    pairs,
    'per_number',
    'lotto_number_pairs.json',
  );
  const record = requireKey<{ top_partners: Partner[] }>(
    perNumber,
    String(n),
    'lotto_number_pairs.json.per_number',
  );
  return {
    top: record.top_partners,
    expected: requireKey<number>(
      pairs,
      'expected_count_per_pair',
      'lotto_number_pairs.json',
    ),
  };
}
