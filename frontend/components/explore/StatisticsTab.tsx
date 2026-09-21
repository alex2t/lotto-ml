import Link from 'next/link';
import { BarChart, type Bar } from '@/components/charts/BarChart';
import { numberRows } from '@/lib/data/table';
import { distributionsBetween } from '@/lib/data/ranged';
import { allDraws } from '@/lib/data/draws';
import {
  consecutivePairs,
  highNumbers,
  hmcCategoryDistribution,
  oddEvenPatterns,
  spreadDistribution,
  sumDistribution,
  sumDistributions,
  totalDraws,
} from '@/lib/data/distributions';
import { artifact, requireKey } from '@/lib/data/artifacts';
import { record } from '@/lib/data/numbers';
import { ALL_NUMBERS } from '@/lib/data/numbers';
import { bandLabel } from '@/lib/scoring/bands';
import { spreadBandShares } from '@/lib/scoring/line';

function Panel({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      {note && <p className="text-xs text-muted">{note}</p>}
      {children}
    </section>
  );
}

interface Scenario {
  window_size: number;
  results: Record<string, { hit_count: number; total_windows: number; odds: number }>;
}

/** The historical scenario table the Trigger Periods page showed. */
function scenarios(): Scenario[] {
  const odds = artifact<Record<string, unknown>>('odds');
  return requireKey<Scenario[]>(odds, 'scenarios', 'lotto_odds_results.json');
}

function sevenBallPatterns(): Array<[string, number]> {
  const odds = artifact<Record<string, unknown>>('odds');
  const hmc = requireKey<Record<string, { percentage: number }>>(
    odds,
    'hmc',
    'lotto_odds_results.json',
  );
  return Object.entries(hmc)
    .map(([k, v]) => [k, v.percentage] as [string, number])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);
}

export function StatisticsTab({ from, to }: { from?: string; to?: string }) {
  const draws = totalDraws();
  // A range is counted from the draw history; with no range these are the artifacts' own
  // figures, and test/ranged.test.ts asserts the two agree over the whole history.
  const ranged = distributionsBetween(from, to);
  const filtered = Boolean(from || to);
  const over = filtered
    ? `${ranged.draws} draws, ${ranged.from} to ${ranged.to}`
    : `all ${draws} draws`;
  const share = (group: { key: string; percentage: number }[], key: string) =>
    group.find((g) => g.key === key)?.percentage ?? 0;
  const history = allDraws();
  const firstDate = history[0].draw_date;
  const lastDate = history[history.length - 1].draw_date;
  const rows = numberRows();
  const mostVolatile = [...rows].sort((a, b) => b.volatility - a.volatility).slice(0, 8);
  const biggestChange = [...rows]
    .sort((a, b) => Math.abs(b.trend) - Math.abs(a.trend))
    .slice(0, 8);
  const categories = hmcCategoryDistribution().category_counts as Record<string, number>;
  const sums = sumDistribution() as { mean: number; median: number; std: number };
  const spreads = spreadDistribution() as { mean: number; median: number; std: number };
  const high = highNumbers();
  const pairs = requireKey<Record<string, number>>(
    consecutivePairs() as Record<string, unknown>,
    'pair_counts',
    'lotto_consecutive_pairs_validated.json',
  );

  const oddEvenBars: Bar[] = Object.keys(oddEvenPatterns('6_main')).map((k) => ({
    key: k,
    label: `${k.split('_')[0]} odd / ${k.split('_')[1]} even`,
    value: share(ranged.oddEven, k),
  }));

  const affinityBars: Bar[] = ALL_NUMBERS.map((n) => {
    const oddEven = record(n).oddEven as Record<string, number>;
    return {
      key: String(n),
      label: String(n),
      value: (oddEven.affinity_score ?? 0) * 100,
      reference: (oddEven.chance_affinity_score ?? 0) * 100,
    };
  });

  const topPairs = Object.entries(pairs)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);

  return (
    <div className="flex flex-col gap-4">
      <form className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4 text-sm">
        <input type="hidden" name="tab" value="statistics" />
        <div className="flex flex-col gap-1">
          <label htmlFor="stats-from">From</label>
          <input
            id="stats-from"
            type="date"
            name="from"
            min={firstDate}
            max={lastDate}
            defaultValue={from ?? ''}
            className="rounded border border-border bg-background p-1"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="stats-to">To</label>
          <input
            id="stats-to"
            type="date"
            name="to"
            min={firstDate}
            max={lastDate}
            defaultValue={to ?? ''}
            className="rounded border border-border bg-background p-1"
          />
        </div>
        <button type="submit" className="rounded-full bg-accent px-4 py-2 text-accent-foreground">
          Apply to the counted charts
        </button>
        {filtered && (
          <Link href="/explore?tab=statistics" className="underline">
            All draws
          </Link>
        )}
        <p className="w-full text-xs text-muted">
          The range applies to the five charts counted straight from the draws: odd and
          even, sums, spread, the high-number breakdown and the six-ball patterns. The rest
          are figures the engine wrote over the whole history, and say so.
        </p>
      </form>

      <div className="grid gap-4 md:grid-cols-2">
      <Panel
        title="Hot, medium and cold right now"
        note={`How the 47 numbers split today. Recency-based: hot means drawn in the last 13 days, medium 14 to 26, cold 27 or more.`}
      >
        <BarChart
          caption={`The 47 numbers, categorised at the latest draw.`}
          unit=""
          bars={Object.entries(categories).map(([k, v]) => ({
            key: k,
            label: k,
            value: v,
          }))}
        />
      </Panel>

      <Panel title="Six-ball hot/medium/cold patterns" note={`Over ${over}.`}>
        <BarChart
          caption="Each draw's six main numbers, by the categories they held before it."
          bars={ranged.hmc
            .slice(0, 12)
            .map((p) => ({ key: p.key, label: p.key, value: p.percentage }))}
        />
      </Panel>

      <Panel
        title="Seven-ball patterns"
        note={`The same, counting the bonus ball. Written by the engine over all ${draws} draws, so a date range does not apply.`}
      >
        <BarChart
          caption="From lotto_odds_results.json."
          bars={sevenBallPatterns().map(([k, v]) => ({ key: k, label: k, value: v }))}
        />
      </Panel>

      <Panel title="Odd and even" note={`Over ${over}.`}>
        <BarChart caption="The split of the six main numbers." bars={oddEvenBars} />
      </Panel>

      <Panel
        title="Each number's odd-draw share"
        note={`Shown against what a fair draw gives, because the two only mean something together (F-38). Written by the engine over all ${draws} draws, so a date range does not apply.`}
      >
        <BarChart
          caption="A number's share of odd-heavy draws."
          bars={affinityBars}
          referenceLabel="a fair draw"
        />
      </Panel>

      <Panel
        title="Sums"
        note={`Over ${over}. Across the whole history the mean is ${sums.mean.toFixed(1)}, the median ${sums.median} and the standard deviation ${sums.std.toFixed(1)}.`}
      >
        <BarChart
          caption="The sum of the six main numbers."
          bars={Object.keys(sumDistributions('6_main')).map((k) => ({
            key: k,
            label: bandLabel(k),
            value: share(ranged.sums, k),
          }))}
        />
      </Panel>

      <Panel
        title="Spread"
        note={`Highest minus lowest, over ${over}. Across the whole history the mean is ${spreads.mean.toFixed(1)} and the median ${spreads.median}.`}
      >
        <BarChart
          caption="The spread of the six main numbers."
          bars={Object.keys(spreadBandShares()).map((k) => ({
            key: k,
            label: k,
            value: share(ranged.spreads, k),
          }))}
        />
      </Panel>

      <Panel
        title={`How many numbers at ${high.highFrom} or above`}
        note="Next to what a fair draw would give. Most people pick birthday numbers, so a high line shares a prize less often - it does not win more often (F-19)."
      >
        <BarChart
          caption={`Draws by their count of main numbers at ${high.highFrom} or above, over ${over}.`}
          bars={Object.entries(high.byCount).map(([k, v]) => ({
            key: k,
            label: `${k} of six`,
            value: share(ranged.highNumbers, k),
            reference: v.fair_percentage,
          }))}
          referenceLabel="a fair draw"
        />
      </Panel>

      <Panel
        title="The most volatile, and the biggest changes"
        note="Volatility is how uneven a number's gaps are; the trend compares its recent window with the older one. Both are read from lotto_advanced_patterns.json."
      >
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Most volatile</h4>
            <ul className="mt-2 flex flex-col gap-1">
              {mostVolatile.map((row) => (
                <li key={row.number} className="flex items-center gap-2">
                  <Link href={`/numbers/${row.number}`} className="underline tabular-nums">
                    {row.number}
                  </Link>
                  <span className="text-muted tabular-nums">{row.volatility.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs uppercase tracking-widest text-muted">Biggest change</h4>
            <ul className="mt-2 flex flex-col gap-1">
              {biggestChange.map((row) => (
                <li key={row.number} className="flex items-center gap-2">
                  <Link href={`/numbers/${row.number}`} className="underline tabular-nums">
                    {row.number}
                  </Link>
                  <span className="text-muted tabular-nums">{row.trend.toFixed(2)}</span>
                  {row.trendIsSignificant && (
                    <span className="text-xs text-muted">significant</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="text-xs text-muted">
          A trend is marked significant by Fisher&apos;s exact test on the raw counts of the
          two windows, which flags about 5% of numbers on fair draws (F-31).
        </p>
      </Panel>

      <Panel
        title="Historical scenarios"
        note="How often a number that came up N times in a window came up again in the next draw."
      >
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-muted">
              <th className="py-1 font-medium">Window</th>
              <th className="py-1 font-medium">Came up</th>
              <th className="py-1 font-medium">Hits</th>
              <th className="py-1 font-medium">Windows</th>
              <th className="py-1 font-medium">Share</th>
            </tr>
          </thead>
          <tbody>
            {scenarios().flatMap((scenario) =>
              Object.entries(scenario.results).map(([times, result]) => (
                <tr key={`${scenario.window_size}-${times}`} className="border-t border-border">
                  <td className="py-1 tabular-nums">{scenario.window_size} draws</td>
                  <td className="py-1">{times.replace('_', ' ')}</td>
                  <td className="py-1 tabular-nums">{result.hit_count}</td>
                  <td className="py-1 tabular-nums">{result.total_windows}</td>
                  <td className="py-1 tabular-nums">{(result.odds * 100).toFixed(1)}%</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </Panel>

      <Panel title="Consecutive pairs" note="How often two neighbours came up together.">
        <BarChart
          caption="Pair counts over the history."
          unit=""
          bars={topPairs.map(([k, v]) => ({ key: k, label: k, value: v }))}
        />
      </Panel>
      </div>
    </div>
  );
}
