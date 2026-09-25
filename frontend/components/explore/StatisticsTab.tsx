import Link from 'next/link';
import { BarChart } from '@/components/charts/BarChart';
import { StatCard } from '@/components/explore/StatCard';
import { allDraws } from '@/lib/data/draws';
import { statisticsView, type StatisticsView } from '@/lib/data/statistics';
import type { NumberRow } from '@/lib/data/table';
import {
  guide,
  STAT_GROUPS,
  STATISTICS_GUIDE,
  type StatGuide,
  type StatId,
} from '@/lib/guide/statistics';

function scopeText(entry: StatGuide, view: StatisticsView): string {
  if (entry.scope === 'today') return 'At the latest draw';
  if (entry.scope === 'counted') return `Over ${view.over}`;
  return view.filtered
    ? `All ${view.totalDraws} draws - a date range does not apply`
    : `All ${view.totalDraws} draws`;
}

function NumberList({
  title,
  rows,
  value,
  showFlag = false,
}: {
  title: string;
  rows: NumberRow[];
  value: (row: NumberRow) => string;
  showFlag?: boolean;
}) {
  return (
    <div>
      <h4 className="text-xs uppercase tracking-widest text-muted">{title}</h4>
      <ul className="mt-2 flex flex-col gap-1">
        {rows.map((row) => (
          <li key={row.number} className="flex items-center gap-2">
            <Link href={`/numbers/${row.number}`} className="underline tabular-nums">
              {row.number}
            </Link>
            <span className="text-muted tabular-nums">{value(row)}</span>
            {showFlag && row.trendIsSignificant && (
              <span className="text-xs text-muted">significant</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function detail(id: StatId, view: StatisticsView): React.ReactNode {
  const { bars } = view;
  switch (id) {
    case 'hmc-now':
      return (
        <BarChart caption="The 47 numbers, grouped at the latest draw." unit="" bars={bars.hmcNow} />
      );
    case 'hmc-six':
      return (
        <BarChart
          caption="Each draw's six main numbers, by the group they held before it."
          bars={bars.hmcSix}
        />
      );
    case 'hmc-seven':
      return <BarChart caption="From lotto_odds_results.json." bars={bars.hmcSeven} />;
    case 'odd-even':
      return <BarChart caption="The split of the six main numbers." bars={bars.oddEven} />;
    case 'sums':
      return (
        <>
          <BarChart caption="The sum of the six main numbers." bars={bars.sums} />
          <p className="text-xs text-muted">
            Across the whole history the mean is {view.sumStats.mean.toFixed(1)}, the median{' '}
            {view.sumStats.median} and the standard deviation {view.sumStats.std.toFixed(1)}.
          </p>
        </>
      );
    case 'spread':
      return (
        <>
          <BarChart caption="The spread of the six main numbers." bars={bars.spread} />
          <p className="text-xs text-muted">
            Across the whole history the mean is {view.spreadStats.mean.toFixed(1)} and the
            median {view.spreadStats.median}.
          </p>
        </>
      );
    case 'high-numbers':
      return (
        <BarChart
          caption={`Draws by their count of main numbers at ${view.highFrom} or above.`}
          bars={bars.highNumbers}
          referenceLabel="a fair draw"
        />
      );
    case 'odd-share':
      return (
        <BarChart
          caption="A number's share of odd draws."
          bars={bars.oddShare}
          referenceLabel="a fair draw"
        />
      );
    case 'volatility-trend':
      return (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <NumberList
            title="Most volatile"
            rows={view.mostVolatile}
            value={(r) => r.volatility.toFixed(2)}
          />
          <NumberList
            title="Biggest change"
            rows={view.biggestChange}
            value={(r) => r.trend.toFixed(2)}
            showFlag
          />
        </div>
      );
    case 'consecutive-pairs':
      return (
        <>
          <BarChart
            caption="The 12 busiest pairs, by the number of draws that held both."
            unit=""
            bars={bars.consecutivePairs}
            referenceLabel="a fair draw"
          />
          <p className="text-xs text-muted">
            Chi-square across all 46 pairs: p = {view.pairsPValue.toFixed(2)}.{' '}
            {view.pairsPValue < 0.05
              ? 'The counts as a whole depart from a fair draw.'
              : 'The counts as a whole are in line with a fair draw.'}
          </p>
        </>
      );
    case 'repeat-windows':
      return (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-muted">
              <th className="py-1 font-medium">Scenario</th>
              <th className="py-1 font-medium">Windows with it</th>
              <th className="py-1 font-medium">Windows</th>
              <th className="py-1 font-medium">Share</th>
            </tr>
          </thead>
          <tbody>
            {view.scenarios.map((row) => (
              <tr key={row.key} className="border-t border-border">
                <td className="py-1">{row.label}</td>
                <td className="py-1 tabular-nums">{row.hits}</td>
                <td className="py-1 tabular-nums">{row.windows}</td>
                <td className="py-1 tabular-nums">{row.percentage.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
  }
}

export function StatisticsTab({ from, to }: { from?: string; to?: string }) {
  const view = statisticsView(from, to);
  const history = allDraws();
  const firstDate = history[0].draw_date;
  const lastDate = history[history.length - 1].draw_date;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold">
            {STATISTICS_GUIDE.length} statistics about past draws
          </h2>
          <p className="text-sm text-muted">
            Each row gives the headline figure. Open one to see its chart, how to read it and
            what it shows; open several to compare. These describe past draws - every line is
            equally likely to win the next one.
          </p>
        </div>

        <form className="flex flex-wrap items-end gap-3 border-t border-border pt-4 text-sm">
          <input type="hidden" name="tab" value="statistics" />
          <div className="flex flex-col gap-1">
            <label htmlFor="stats-from" className="text-xs text-muted">
              From
            </label>
            <input
              id="stats-from"
              type="date"
              name="from"
              min={firstDate}
              max={lastDate}
              defaultValue={from ?? ''}
              className="rounded-lg border border-border bg-background px-2 py-1.5"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="stats-to" className="text-xs text-muted">
              To
            </label>
            <input
              id="stats-to"
              type="date"
              name="to"
              min={firstDate}
              max={lastDate}
              defaultValue={to ?? ''}
              className="rounded-lg border border-border bg-background px-2 py-1.5"
            />
          </div>
          <button
            type="submit"
            className="rounded-full bg-accent px-4 py-2 text-accent-foreground"
          >
            Apply date range
          </button>
          {view.filtered && (
            <Link href="/explore?tab=statistics" className="py-2 underline">
              All draws
            </Link>
          )}
          <p className="w-full text-xs text-muted">
            A range changes the rows that say &quot;Over ...&quot; - they are counted straight
            from the draws. The others were written by the engine over the whole history.
          </p>
        </form>
      </div>

      {STAT_GROUPS.map((group) => (
        <section key={group.title} className="flex flex-col gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">
              {group.title}
            </h2>
            <p className="text-sm text-muted">{group.blurb}</p>
          </div>
          <div className="flex flex-col gap-2">
            {group.ids.map((id) => {
              const entry = guide(id);
              return (
                <StatCard
                  key={id}
                  entry={entry}
                  headline={view.headlines[id]}
                  scopeText={scopeText(entry, view)}
                >
                  {detail(id, view)}
                </StatCard>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
