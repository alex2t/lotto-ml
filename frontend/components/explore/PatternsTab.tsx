import Link from 'next/link';
import { Ball } from '@/components/ui/Ball';
import { Badge } from '@/components/ui/Badge';
import { BarChart } from '@/components/charts/BarChart';
import { ShapeCard } from '@/components/pick/ShapeCard';
import { overlapHistogram, similarDraws } from '@/lib/data/explore';
import { InvalidLine, describeLine } from '@/lib/scoring/line';
import { shortDate } from '@/lib/format';
import type { Category } from '@/lib/data/types';

/**
 * Pattern Comparison: the past draws most like a line.
 *
 * The exact-match case must work - reading main_numbers with an empty default is what made
 * the Streamlit page answer "no similar draws" for ten months (F-25).
 */
export function PatternsTab({ line }: { line?: string }) {
  const parsed = line
    ? line
        .split(/[\s,]+/)
        .filter(Boolean)
        .map(Number)
    : null;

  let shape = null;
  let error: string | null = null;
  if (parsed) {
    try {
      shape = describeLine(parsed);
    } catch (e) {
      error = e instanceof InvalidLine ? e.message : 'That line could not be read';
    }
  }

  const matches = shape ? similarDraws(shape.line) : [];
  const histogram = shape ? overlapHistogram(shape.line) : null;
  const total = histogram
    ? Object.values(histogram).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <div className="flex flex-col gap-4">
      <form className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4 text-sm">
        <input type="hidden" name="tab" value="patterns" />
        <label className="flex flex-col gap-1">
          Six numbers
          <input
            type="text"
            name="line"
            defaultValue={line ?? ''}
            placeholder="5, 12, 23, 31, 38, 44"
            className="w-64 rounded border border-border bg-background p-2"
          />
        </label>
        <button type="submit" className="rounded-full bg-accent px-4 py-2 text-accent-foreground">
          Find similar draws
        </button>
        <Link href="/pick" className="underline">
          Or build one on Pick
        </Link>
      </form>

      {error && (
        <p role="alert" className="text-sm text-muted">
          {error}
        </p>
      )}

      {shape && histogram && (
        <>
          <ShapeCard shape={shape} />

          <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
            <h3 className="text-sm font-semibold">
              How many of your six each past draw held
            </h3>
            <BarChart
              caption={`Over ${total} draws.`}
              unit=""
              bars={Object.entries(histogram).map(([k, v]) => ({
                key: k,
                label: `${k} shared`,
                value: v,
              }))}
            />
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold">The draws most like it</h3>
            {matches.length === 0 ? (
              <p className="text-sm text-muted">
                No past draw has held any of these six numbers.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {matches.map((match) => (
                  <li
                    key={match.row.date}
                    className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2"
                  >
                    <Link
                      href={`/explore?tab=draws&draw=${match.row.date}`}
                      className="w-28 text-sm underline"
                    >
                      {shortDate(match.row.date)}
                    </Link>
                    <span className="flex flex-wrap items-center gap-1">
                      {match.row.main.map((n, i) => (
                        <Ball
                          key={n}
                          number={n}
                          category={match.row.categories[i] as Category}
                          size="sm"
                          className={
                            match.sharedNumbers.includes(n) ? 'ring-2 ring-accent' : 'opacity-60'
                          }
                        />
                      ))}
                    </span>
                    <span className="ml-auto">
                      <Badge>
                        {match.shared} of your six
                        {match.shared === 6 ? ' - an exact match' : ''}
                      </Badge>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
