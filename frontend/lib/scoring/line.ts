/**
 * What a line looks like next to past draws.
 *
 * This describes typicality, never a chance of winning: every line is equally likely, and
 * the verdict vocabulary is fixed to typical / uncommon / unusual so the wording is
 * testable in one place (web.md 4.2). Used by /pick and by /api/validate, so the page and
 * the API cannot disagree.
 */
import { artifact, requireKey } from '../data/artifacts';
import { latest } from '../data/draws';
import {
  highNumbers,
  oddEvenPatterns,
  spreadDistribution,
  sumDistribution,
  sumDistributions,
  totalDraws,
} from '../data/distributions';
import { patternKey, patternShare, sixBallPatterns } from '../data/hmc';
import { summary } from '../data/numbers';
import type { Category } from '../data/types';
import { SPREAD_BANDS, bandLabel, spreadBand, sumBand } from './bands';
import { notesFor, type Note } from './notes';

export const LINE_SIZE = 6;
export const MAX_NUMBER = 47;

export type Verdict = 'typical' | 'uncommon' | 'unusual';

/** Rendered with every verdict, always, by the same component. */
export const EQUAL_CHANCE =
  'That is not an advantage - every line is equally likely to win.';

export interface Bucket {
  key: string;
  label: string;
  percentage: number;
  /** True for the bucket the player's line falls in. */
  isLine: boolean;
}

export interface Check {
  id: string;
  title: string;
  /** What the line is, e.g. "2 odd, 4 even". */
  value: string;
  /** The share of past draws that look like this, or null when the check is not a share. */
  share: number | null;
  /** A factual comparison, never advice. */
  comparison: string;
  buckets: Bucket[];
  /** Information only, left out of the verdict (F-19). */
  informational?: boolean;
}

export interface LineShape {
  line: number[];
  drawsCompared: number;
  checks: Check[];
  /** What the Streamlit anomaly alerts became: facts about the line, never warnings. */
  notes: Note[];
  verdict: Verdict;
  equalChance: string;
}

export class InvalidLine extends Error {}

/** Exactly six distinct numbers in 1-47. Anything else is a caller error, not a 0 score. */
export function validateLine(numbers: unknown): number[] {
  if (!Array.isArray(numbers) || numbers.length !== LINE_SIZE) {
    throw new InvalidLine(`A line is exactly ${LINE_SIZE} numbers`);
  }
  const line = numbers.map((n) => {
    if (typeof n !== 'number' || !Number.isInteger(n) || n < 1 || n > MAX_NUMBER) {
      throw new InvalidLine(`${String(n)} is not a number between 1 and ${MAX_NUMBER}`);
    }
    return n;
  });
  if (new Set(line).size !== LINE_SIZE) {
    throw new InvalidLine('A line cannot repeat a number');
  }
  return [...line].sort((a, b) => a - b);
}

/** Draw-range shares from lotto_odds_results.json, in the band order the site shows. */
export function spreadBandShares(): Record<string, number> {
  const odds = artifact<Record<string, unknown>>('odds');
  const block = requireKey<Record<string, { percentage: number }>>(
    odds,
    'draw_range',
    'lotto_odds_results.json',
  );
  const ordered: Record<string, number> = {};
  for (const band of SPREAD_BANDS) {
    if (band.key in block) ordered[band.key] = block[band.key].percentage;
  }
  return ordered;
}

function toBuckets(
  entries: Array<[string, number]>,
  lineKey: string,
  label: (key: string) => string = (k) => k,
): Bucket[] {
  return entries.map(([key, percentage]) => ({
    key,
    label: label(key),
    percentage,
    isLine: key === lineKey,
  }));
}

function oddEvenCheck(line: number[]): Check {
  const odd = line.filter((n) => n % 2 === 1).length;
  const key = `${odd}_${LINE_SIZE - odd}`;
  const patterns = oddEvenPatterns('6_main');
  const share = patterns[key]?.percentage ?? 0;

  return {
    id: 'odd-even',
    title: 'Odd / even',
    value: `${odd} odd, ${LINE_SIZE - odd} even`,
    share,
    comparison: `${share.toFixed(1)}% of past draws had this split`,
    buckets: toBuckets(
      Object.entries(patterns).map(([k, v]) => [k, v.percentage]),
      key,
      (k) => k.replace('_', ' / '),
    ),
  };
}

function sumCheck(line: number[]): Check {
  const total = line.reduce((a, b) => a + b, 0);
  const band = sumBand(total);
  const bands = sumDistributions('6_main');
  const share = bands[band.key]?.percentage ?? 0;
  const stats = sumDistribution() as { mean: number };

  return {
    id: 'sum',
    title: 'Sum',
    value: String(total),
    share,
    comparison: `${bandLabel(band.key)} - ${share.toFixed(1)}% of past draws, which average ${stats.mean.toFixed(0)}`,
    buckets: toBuckets(
      Object.entries(bands).map(([k, v]) => [k, v.percentage]),
      band.key,
      bandLabel,
    ),
  };
}

function spreadCheck(line: number[]): Check {
  const spread = Math.max(...line) - Math.min(...line);
  const band = spreadBand(spread);
  const shares = spreadBandShares();
  const share = shares[band.key] ?? 0;
  const stats = spreadDistribution() as { mean: number };

  return {
    id: 'spread',
    title: 'Spread',
    value: String(spread),
    share,
    comparison: `${band.key} - ${share.toFixed(1)}% of past draws, which average ${stats.mean.toFixed(0)}`,
    buckets: toBuckets(Object.entries(shares), band.key),
  };
}

function hmcCheck(line: number[]): Check {
  const counts: Record<Category, number> = { hot: 0, medium: 0, cold: 0 };
  for (const n of line) counts[summary(n).category] += 1;
  const key = patternKey(counts);
  const share = patternShare(key);

  return {
    id: 'hmc',
    title: 'Hot / medium / cold',
    value: `${counts.hot} / ${counts.medium} / ${counts.cold}`,
    share,
    comparison:
      share > 0
        ? `${share.toFixed(1)}% of past draws had this shape`
        : 'no past draw has had this shape',
    buckets: toBuckets(
      sixBallPatterns()
        .slice(0, 10)
        .map((p) => [p.pattern, p.percentage] as [string, number]),
      key,
    ),
  };
}

function highNumbersCheck(line: number[]): Check {
  const { highFrom, byCount } = highNumbers();
  const count = line.filter((n) => n >= highFrom).length;
  const key = String(count);
  const bucket = byCount[key];
  const share = bucket?.percentage ?? 0;
  const fair = bucket?.fair_percentage;

  return {
    id: 'high-numbers',
    title: `${highFrom} and above`,
    value: String(count),
    share,
    comparison:
      fair === undefined
        ? `${share.toFixed(1)}% of past draws held ${count}`
        : `${share.toFixed(1)}% of past draws held ${count}; a fair draw gives ${fair.toFixed(1)}%`,
    buckets: toBuckets(
      Object.entries(byCount).map(([k, v]) => [k, v.percentage]),
      key,
    ),
    informational: true,
  };
}

function recentBonusCheck(line: number[]): Check {
  // The latest draw's list is the window for the NEXT draw - what a player's line faces (F-33).
  const window = latest().recent_bonus_numbers;
  const hits = line.filter((n) => window.includes(n));

  return {
    id: 'recent-bonus',
    title: 'Recent bonus',
    value: String(hits.length),
    share: null,
    comparison:
      hits.length === 0
        ? `none of your six was a bonus ball in the last ${window.length} draws`
        : `${hits.join(', ')} ${hits.length === 1 ? 'was a bonus ball' : 'were bonus balls'} in the last ${window.length} draws`,
    buckets: [],
    informational: true,
  };
}

/**
 * How much of a check's distribution is at most as common as the line's own outcome.
 *
 * Comparing a bucket's share with the largest share would not be comparable across checks,
 * because the checks have different numbers of buckets - an HMC pattern is one of about
 * twenty, an odd/even split one of seven, so the same ratio means different things. This
 * measure is a percentile and is comparable.
 */
function percentileOf(check: Check): number {
  if (check.share === null || check.buckets.length === 0) return 1;
  const atMostAsCommon = check.buckets.reduce(
    (sum, b) => (b.percentage <= (check.share as number) ? sum + b.percentage : sum),
    0,
  );
  return atMostAsCommon / 100;
}

/**
 * The thresholds are calibrated against the draws themselves, which are the definition of
 * typical: over the 499 draws on file the mean percentile has median 0.52, p25 0.40 and
 * p05 0.24, and 400 uniform random lines give the same median - the correct result for a
 * fair draw. So roughly two thirds of past draws read typical and the rarest twentieth
 * reads unusual. test/scoring.test.ts asserts that calibration still holds.
 *
 * Informational checks (high numbers, recent bonus) do not count (F-19).
 */
export const TYPICAL_FROM = 0.45;
export const UNCOMMON_FROM = 0.25;

function verdictFrom(checks: Check[]): Verdict {
  const scored = checks.filter((c) => !c.informational);
  const values = scored.map(percentileOf);
  const mean = values.reduce((a, b) => a + b, 0) / (values.length || 1);

  if (mean >= TYPICAL_FROM) return 'typical';
  if (mean >= UNCOMMON_FROM) return 'uncommon';
  return 'unusual';
}

export function describeLine(numbers: unknown): LineShape {
  const line = validateLine(numbers);
  const checks = [
    oddEvenCheck(line),
    sumCheck(line),
    spreadCheck(line),
    hmcCheck(line),
    highNumbersCheck(line),
    recentBonusCheck(line),
  ];

  return {
    line,
    drawsCompared: totalDraws(),
    checks,
    notes: notesFor(line),
    verdict: verdictFrom(checks),
    equalChance: EQUAL_CHANCE,
  };
}
