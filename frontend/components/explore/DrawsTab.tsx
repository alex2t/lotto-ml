import Link from 'next/link';
import { Ball } from '@/components/ui/Ball';
import { Badge } from '@/components/ui/Badge';
import { byDate } from '@/lib/data/draws';
import { queryDraws, toRow, type DrawFilters } from '@/lib/data/explore';
import { oddEvenPatterns, sumDistributions } from '@/lib/data/distributions';
import { bandLabel } from '@/lib/scoring/bands';
import { longDate, shortDate } from '@/lib/format';
import type { Category } from '@/lib/data/types';

function DrawCard({ date }: { date: string }) {
  const draw = byDate(date);
  const row = toRow(draw);

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface-raised p-4">
      <h3 className="text-sm uppercase tracking-widest text-muted">{longDate(date)}</h3>
      <div className="flex flex-wrap items-center gap-2">
        {row.main.map((n, i) => (
          <Ball key={n} number={n} category={row.categories[i] as Category} showCategory />
        ))}
        <span className="px-1 text-muted" aria-hidden>
          +
        </span>
        <Ball number={row.bonus} isBonus />
      </div>
      <dl className="flex flex-wrap gap-3 text-sm text-muted">
        <span>{row.odd} odd / {6 - row.odd} even</span>
        <span>sum {row.sum}</span>
        <span>spread {row.spread}</span>
        <span>{row.high} at 32 or above</span>
        <span>hot/med/cold {row.hmc}</span>
      </dl>
      <div>
        <p className="text-xs text-muted">
          The 10 bonus balls before this draw - the window it faced (F-33):
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          {draw.recent_bonus_numbers
            .filter((n) => n !== draw.bonus_number || true)
            .map((n, i) => (
              <Badge key={`${n}-${i}`} tone="bonus">
                {n}
              </Badge>
            ))}
        </div>
      </div>
      <p className="text-xs text-muted">
        Each ball is tinted by the category it held before this draw, not today.
      </p>
    </section>
  );
}

export function DrawsTab({
  filters,
  page,
  openDraw,
  query,
}: {
  filters: DrawFilters;
  page: number;
  openDraw?: string;
  query: URLSearchParams;
}) {
  const result = queryDraws(filters, page);
  const linkTo = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(query);
    for (const [k, v] of Object.entries(changes)) {
      if (v === undefined || v === '') next.delete(k);
      else next.set(k, v);
    }
    return `/explore?${next.toString()}`;
  };

  return (
    <div className="flex flex-col gap-4">
      {openDraw && <DrawCard date={openDraw} />}

      <form className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4 text-sm">
        <input type="hidden" name="tab" value="draws" />
        <label className="flex flex-col gap-1">
          From
          <input
            type="date"
            name="from"
            defaultValue={filters.from ?? ''}
            className="rounded border border-border bg-background p-1"
          />
        </label>
        <label className="flex flex-col gap-1">
          To
          <input
            type="date"
            name="to"
            defaultValue={filters.to ?? ''}
            className="rounded border border-border bg-background p-1"
          />
        </label>
        <label className="flex flex-col gap-1">
          Contains numbers
          <input
            type="text"
            name="contains"
            placeholder="7, 23"
            defaultValue={filters.contains?.join(', ') ?? ''}
            className="w-28 rounded border border-border bg-background p-1"
          />
        </label>
        <label className="flex flex-col gap-1">
          Odd / even
          <select
            name="oddEven"
            defaultValue={filters.oddEven ?? ''}
            className="rounded border border-border bg-background p-1"
          >
            <option value="">any</option>
            {Object.keys(oddEvenPatterns('6_main')).map((k) => (
              <option key={k} value={k}>
                {k.replace('_', ' odd / ')} even
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Sum band
          <select
            name="sumBand"
            defaultValue={filters.sumBand ?? ''}
            className="rounded border border-border bg-background p-1"
          >
            <option value="">any</option>
            {Object.keys(sumDistributions('6_main')).map((k) => (
              <option key={k} value={k}>
                {bandLabel(k)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          32 and above
          <select
            name="highCount"
            defaultValue={filters.highCount?.toString() ?? ''}
            className="rounded border border-border bg-background p-1"
          >
            <option value="">any</option>
            {[0, 1, 2, 3, 4, 5, 6].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="rounded-full bg-accent px-4 py-2 text-accent-foreground">
          Filter
        </button>
        <Link href="/explore?tab=draws" className="underline">
          Reset
        </Link>
      </form>

      <p className="text-sm text-muted" aria-live="polite">
        {result.total} draws match. Page {result.page} of {result.pages}.
      </p>

      <ul className="flex flex-col gap-2">
        {result.rows.map((row) => (
          <li
            key={row.date}
            className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2"
          >
            <Link href={linkTo({ draw: row.date })} className="w-28 text-sm underline">
              {shortDate(row.date)}
            </Link>
            <span className="flex flex-wrap items-center gap-1">
              {row.main.map((n, i) => (
                <Ball key={n} number={n} category={row.categories[i] as Category} size="sm" />
              ))}
              <span className="px-1 text-muted" aria-hidden>
                +
              </span>
              <Ball number={row.bonus} isBonus size="sm" />
            </span>
            <span className="ml-auto flex flex-wrap gap-2 text-xs text-muted">
              <Badge>{row.odd} odd</Badge>
              <Badge>sum {row.sum}</Badge>
              <Badge>spread {row.spread}</Badge>
              <Badge>{row.high} high</Badge>
            </span>
          </li>
        ))}
      </ul>

      <nav className="flex items-center gap-3 text-sm">
        {result.page > 1 && (
          <Link href={linkTo({ page: String(result.page - 1) })} className="underline">
            Newer
          </Link>
        )}
        {result.page < result.pages && (
          <Link href={linkTo({ page: String(result.page + 1) })} className="underline">
            Older
          </Link>
        )}
      </nav>
    </div>
  );
}
