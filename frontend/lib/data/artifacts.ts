/**
 * Reads the JSON artifacts written by drawpick.py.
 *
 * Every read is cached per file mtime, so a rebuild on the mounted volume is picked up
 * without restarting the container. Fields are read with requireKey(), never a default:
 * a missing key is a bug and must throw (F-25).
 */
import fs from 'node:fs';
import path from 'node:path';

/** Where drawpick.py's artifacts live. Read lazily so a test can repoint it. */
export function dataDir(): string {
  return process.env.DATA_DIR ?? path.join(process.cwd(), '..', 'data');
}

type Entry = { mtimeMs: number; value: unknown };

const cache = new Map<string, Entry>();

/** Read an artifact, re-reading only when the file on disk has changed. */
export function readArtifact<T>(fileName: string): T {
  // The artifacts are a runtime mount, so these paths are dynamic on purpose and must not
  // pull the project into Turbopack's output trace.
  const filePath = path.join(/*turbopackIgnore: true*/ dataDir(), fileName);
  const { mtimeMs } = fs.statSync(/*turbopackIgnore: true*/ filePath);
  const cached = cache.get(filePath);
  if (cached && cached.mtimeMs === mtimeMs) return cached.value as T;

  const value = JSON.parse(fs.readFileSync(/*turbopackIgnore: true*/ filePath, 'utf8')) as T;
  cache.set(filePath, { mtimeMs, value });
  return value;
}

/** Read a key that must exist. Returns the value; throws naming the key if it is absent. */
export function requireKey<T>(
  source: Record<string, unknown>,
  key: string,
  where: string,
): T {
  if (!(key in source)) {
    throw new Error(`Missing key '${key}' in ${where}`);
  }
  return source[key] as T;
}

export const ARTIFACTS = {
  drawHistory: 'lotto_draw_history.json',
  triggerPeriods: 'lotto_trigger_periods.json',
  distributionStats: 'lotto_distribution_stats.json',
  freshness: 'lotto_7_number_freshness_results.json',
  bonusAnalysis: 'lotto_bonus_analysis.json',
  bonusToMain: 'lotto_bonus_to_main_patterns.json',
  oddEven: 'lotto_odd_even_validated.json',
  sumContribution: 'lotto_sum_contribution_validated.json',
  rangeSpread: 'lotto_range_spread_validated.json',
  consecutivePairs: 'lotto_consecutive_pairs_validated.json',
  hmcCategorization: 'lotto_hmc_categorization_validated.json',
  freshnessPatterns: 'lotto_freshness_patterns_validated.json',
  advancedPatterns: 'lotto_advanced_patterns.json',
  longTermPatterns: 'lotto_long_term_patterns.json',
  statisticsAnalysis: 'lotto_statistics_analysis.json',
  recencyZones: 'lotto_recency_zones_calculated.json',
  windowSaturation: 'lotto_window_saturation_calculated.json',
  odds: 'lotto_odds_results.json',
} as const;

export type ArtifactName = keyof typeof ARTIFACTS;

export function artifact<T>(name: ArtifactName): T {
  return readArtifact<T>(ARTIFACTS[name]);
}

/** Clears the mtime cache. Tests use it when swapping the fixture directory. */
export function clearArtifactCache(): void {
  cache.clear();
}
