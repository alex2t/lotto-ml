import Link from 'next/link';
import { BarChart } from '@/components/charts/BarChart';
import { artifact, requireKey } from '@/lib/data/artifacts';
import { freshnessPatterns, freshnessWeights } from '@/lib/data/distributions';
import type { FreshnessPattern } from '@/lib/data/distributions';
import { pool } from '@/lib/data/pool';

const BIN_TONE = ['bg-cold-soft text-cold', 'bg-medium-soft text-medium', 'bg-hot-soft text-hot'];

/**
 * The C0-C3 matrix, with the bin definitions beside it rather than in a manual.
 */
/** The same patterns counted over all seven balls, which is the artifact's other mode. */
function sevenBallPatterns(): FreshnessPattern[] {
  return requireKey<FreshnessPattern[]>(
    artifact<Record<string, unknown>>('freshness'),
    'distribution_analysis_7_numbers',
    'lotto_7_number_freshness_results.json',
  );
}

export function FreshnessTab({ bin, mode = '6' }: { bin?: number; mode?: '6' | '7' }) {
  const data = pool();
  const weights = freshnessWeights();
  const patterns = mode === '7' ? sevenBallPatterns() : freshnessPatterns();

  const bins = Array.from({ length: data.maxBin + 1 }, (_, i) => i);
  const inBin = (b: number) => data.numbers.filter((n) => n.freshnessBin === b);

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4">
        <h3 className="text-sm font-semibold">What the bins mean</h3>
        <p className="text-sm text-muted">
          A number&apos;s bin is how many times it came up in the last 5 draws, capped at{' '}
          {data.maxBin}. C0 means it did not come up at all; C{data.maxBin}+ means{' '}
          {data.maxBin} or more. A typical draw holds{' '}
          {Object.entries(weights)
            .map(
              ([k, v]) =>
                `${(v.percentage as number).toFixed(0)}% ${k.replace(`C_GE_${data.maxBin}`, `C${data.maxBin}+`)}`,
            )
            .join(', ')}
          .
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        {bins.map((b) => {
          const members = inBin(b);
          const selected = bin === b;
          return (
            <div
              key={b}
              className={`flex flex-col gap-2 rounded-xl border p-4 ${
                selected ? 'border-accent' : 'border-border'
              } bg-surface`}
            >
              <div className="flex items-baseline justify-between">
                <h4 className="text-sm font-semibold">
                  C{b}
                  {b === data.maxBin ? '+' : ''}
                </h4>
                <span className="text-xs text-muted">{members.length} numbers</span>
              </div>
              <ul className="flex flex-wrap gap-1">
                {members.map((n) => (
                  <li key={n.number}>
                    <Link
                      href={`/numbers/${n.number}`}
                      className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold tabular-nums ${
                        BIN_TONE[Math.min(b, BIN_TONE.length - 1)]
                      }`}
                    >
                      {n.number}
                    </Link>
                  </li>
                ))}
              </ul>
              <Link
                href={selected ? '/explore?tab=freshness' : `/explore?tab=freshness&bin=${b}`}
                className="text-xs underline"
              >
                {selected ? 'Clear highlight' : 'Highlight this bin'}
              </Link>
            </div>
          );
        })}
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold">The patterns past draws formed</h3>
          <span className="flex gap-2 text-sm">
            {(['6', '7'] as const).map((option) => (
              <Link
                key={option}
                href={`/explore?tab=freshness${bin === undefined ? '' : `&bin=${bin}`}${
                  option === '6' ? '' : '&mode=7'
                }`}
                aria-current={mode === option ? 'true' : undefined}
                className={`rounded-full px-3 py-1 ${
                  mode === option ? 'bg-accent text-accent-foreground' : 'border border-border'
                }`}
              >
                {option === '6' ? 'main 6' : 'all 7'}
              </Link>
            ))}
          </span>
        </div>
        <BarChart
          caption={
            mode === '7'
              ? "Each draw's seven balls, by how many fell in each bin."
              : "Each draw's six main numbers, by how many fell in each bin."
          }
          bars={patterns.slice(0, 12).map((p) => ({
            key: p.pattern,
            label: p.pattern,
            value: p.percentage,
          }))}
        />
      </section>
    </div>
  );
}
