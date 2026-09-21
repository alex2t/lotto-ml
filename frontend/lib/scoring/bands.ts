/**
 * Which band a sum or a spread falls in.
 *
 * These mirror lotto_analysis/config/config.py and utils/output_generator.py exactly,
 * including the part the labels hide: the range bins are half-open, so "20-25" is 20 to 24
 * and 25 belongs to "25-30". The sum labels already print their inclusive maximum.
 *
 * test/scoring.test.ts re-bins every past draw and asserts the histogram equals the counts
 * in the artifacts, which is what stops this drifting from the analyzer.
 */

export interface Band {
  key: string;
  /** Lower bound, inclusive. */
  min: number;
  /** Upper bound, inclusive. */
  max: number;
}

/** SUM_BINS_6_NUMBERS - stored as [lower, upper), shown here as inclusive bounds. */
export const SUM_BANDS_6: Band[] = [
  { key: 'S6_VERY_LOW (<110)', min: 0, max: 109 },
  { key: 'S6_LOW (110-124)', min: 110, max: 124 },
  { key: 'S6_MID_LOW (125-139)', min: 125, max: 139 },
  { key: 'S6_MID (140-154)', min: 140, max: 154 },
  { key: 'S6_MID_HIGH (155-169)', min: 155, max: 169 },
  { key: 'S6_HIGH (170-184)', min: 170, max: 184 },
  { key: 'S6_VERY_HIGH (>=185)', min: 185, max: Infinity },
];

/** RANGE_BINS, plus the '<20' and '>45' tails output_generator.py adds. */
export const SPREAD_BANDS: Band[] = [
  { key: '<20', min: 0, max: 19 },
  { key: '20-25', min: 20, max: 24 },
  { key: '25-30', min: 25, max: 29 },
  { key: '30-35', min: 30, max: 34 },
  { key: '35-40', min: 35, max: 39 },
  { key: '40-45', min: 40, max: 45 },
  { key: '>45', min: 46, max: Infinity },
];

function find(bands: Band[], value: number, what: string): Band {
  const band = bands.find((b) => value >= b.min && value <= b.max);
  if (!band) throw new Error(`No ${what} band covers ${value}`);
  return band;
}

export function sumBand(total: number): Band {
  return find(SUM_BANDS_6, total, 'sum');
}

export function spreadBand(spread: number): Band {
  return find(SPREAD_BANDS, spread, 'spread');
}

/** The human range in a band key: "S6_LOW (110-124)" -> "110-124". */
export function bandLabel(key: string): string {
  const inBrackets = key.match(/\(([^)]+)\)/);
  return inBrackets ? inBrackets[1] : key;
}
