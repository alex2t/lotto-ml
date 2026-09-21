import Link from 'next/link';
import { Ball } from '@/components/ui/Ball';
import { Badge } from '@/components/ui/Badge';
import {
  applyRail,
  numberRows,
  sortRows,
  type RailFilters,
  type SortKey,
} from '@/lib/data/table';
import type { Category } from '@/lib/data/types';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'The 47 numbers - Irish Lotto',
  description:
    'Every number with its category, recent counts, volatility, trend and momentum, sortable and filterable.',
};

const COLUMNS: Array<{ key: SortKey; label: string; hint: string }> = [
  { key: 'number', label: 'Number', hint: '' },
  { key: 'category', label: 'Category', hint: 'hot, medium or cold at the latest draw' },
  { key: 'recent10', label: 'Last 10', hint: 'times drawn in the last 10 draws' },
  { key: 'totalCount', label: 'Total', hint: 'times drawn in the whole history' },
  { key: 'volatility', label: 'Volatility', hint: 'how uneven its gaps are' },
  { key: 'trend', label: 'Trend', hint: 'recent window against the older one' },
  { key: 'momentum', label: 'Momentum', hint: 'recent count against its baseline' },
];

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function NumbersPage({ searchParams }: PageProps<'/numbers'>) {
  const params = await searchParams;

  const filters: RailFilters = {
    category: one(params.category) as Category | undefined,
    bin: one(params.bin) ? Number(one(params.bin)) : undefined,
    trending: one(params.trending) === '1',
    regimeShift: one(params.regime) === '1',
    minVolatility: one(params.volatility) ? Number(one(params.volatility)) : undefined,
    minMomentum: one(params.momentum) ? Number(one(params.momentum)) : undefined,
    recentBonus: one(params.bonus) === '1',
  };

  const sort = (one(params.sort) ?? 'number') as SortKey;
  const descending = one(params.dir) !== 'asc';
  const rows = sortRows(applyRail(numberRows(), filters), sort, descending);

  const sortLink = (key: SortKey) => {
    const next = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      const single = one(v);
      if (single) next.set(k, single);
    }
    next.set('sort', key);
    next.set('dir', sort === key && descending ? 'asc' : 'desc');
    return `/numbers?${next.toString()}`;
  };

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">The 47 numbers</h1>
        <p className="text-sm text-muted">
          Every number with what the artifacts record about it. Sort by any column, narrow
          with the filters, and open one for its full fact sheet.
        </p>
      </header>

      <form className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4 text-sm">
        <div className="flex flex-col gap-1">
          <label htmlFor="rail-category">Category</label>
          <select
            id="rail-category"
            name="category"
            defaultValue={filters.category ?? ''}
            className="rounded border border-border bg-background p-1"
          >
            <option value="">any</option>
            <option value="hot">hot</option>
            <option value="medium">medium</option>
            <option value="cold">cold</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="rail-bin">Freshness bin</label>
          <select
            id="rail-bin"
            name="bin"
            defaultValue={filters.bin?.toString() ?? ''}
            className="rounded border border-border bg-background p-1"
          >
            <option value="">any</option>
            <option value="0">C0</option>
            <option value="1">C1</option>
            <option value="2">C2+</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="rail-volatility">Volatility at least</label>
          <input
            id="rail-volatility"
            name="volatility"
            type="number"
            step="0.05"
            defaultValue={filters.minVolatility ?? ''}
            className="w-24 rounded border border-border bg-background p-1"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="rail-momentum">Momentum at least</label>
          <input
            id="rail-momentum"
            name="momentum"
            type="number"
            step="0.1"
            defaultValue={filters.minMomentum ?? ''}
            className="w-24 rounded border border-border bg-background p-1"
          />
        </div>

        <label className="flex items-center gap-2">
          <input type="checkbox" name="trending" value="1" defaultChecked={filters.trending} />
          A significant trend only
        </label>

        <label className="flex items-center gap-2">
          <input type="checkbox" name="regime" value="1" defaultChecked={filters.regimeShift} />
          In a regime shift
        </label>

        <label className="flex items-center gap-2">
          <input type="checkbox" name="bonus" value="1" defaultChecked={filters.recentBonus} />
          A recent bonus ball
        </label>

        <button type="submit" className="rounded-full bg-accent px-4 py-2 text-accent-foreground">
          Filter
        </button>
        <Link href="/numbers" className="underline">
          Reset
        </Link>
      </form>

      <p className="text-sm text-muted" aria-live="polite">
        {rows.length} of 47 numbers.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[42rem] text-left text-sm">
          <thead>
            <tr className="text-muted">
              {COLUMNS.map((column) => (
                <th key={column.key} scope="col" className="py-2 font-medium" title={column.hint}>
                  <Link href={sortLink(column.key)} className="underline">
                    {column.label}
                    {sort === column.key ? (descending ? ' v' : ' ^') : ''}
                  </Link>
                </th>
              ))}
              <th scope="col" className="py-2 font-medium">
                Notes
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.number} className="border-t border-border">
                <td className="py-2">
                  <Link href={`/numbers/${row.number}`} className="flex items-center gap-2">
                    <Ball number={row.number} category={row.category} size="sm" />
                  </Link>
                </td>
                <td className="py-2 capitalize">{row.category}</td>
                <td className="py-2 tabular-nums">{row.recent[10]}</td>
                <td className="py-2 tabular-nums">{row.totalCount}</td>
                <td className="py-2 tabular-nums">{row.volatility.toFixed(2)}</td>
                <td className="py-2 tabular-nums">{row.trend.toFixed(2)}</td>
                <td className="py-2 tabular-nums">{row.momentum.toFixed(2)}</td>
                <td className="flex flex-wrap gap-1 py-2">
                  <Badge>C{row.freshnessBin}</Badge>
                  {row.trendIsSignificant && <Badge>significant trend</Badge>}
                  {row.inRegimeShift && <Badge>regime shift</Badge>}
                  {row.wasRecentBonus && <Badge tone="bonus">recent bonus</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && (
        <p className="text-sm text-muted">
          No number matches those filters. <Link href="/numbers" className="underline">Reset</Link>.
        </p>
      )}
    </main>
  );
}
