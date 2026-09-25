import { ChevronDown } from 'lucide-react';
import type { StatGuide } from '@/lib/guide/statistics';

/**
 * One statistic, collapsed to a single row until someone asks for the detail.
 *
 * A native `<details>`: it opens without client JavaScript, the keyboard and screen readers
 * already know it, and several can be open at once to compare. The height animation is CSS
 * (`.stat-card` in globals.css) where the browser supports it; elsewhere it opens at once.
 */
export function StatCard({
  entry,
  headline,
  scopeText,
  children,
}: {
  entry: StatGuide;
  headline: string;
  scopeText: string;
  children: React.ReactNode;
}) {
  return (
    <details
      id={entry.id}
      className="stat-card group scroll-mt-4 rounded-xl border border-border bg-surface transition-colors hover:border-muted open:border-foreground open:bg-surface-raised open:shadow-sm"
    >
      <summary className="flex cursor-pointer list-none flex-col gap-3 rounded-xl p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground sm:flex-row sm:items-center [&::-webkit-details-marker]:hidden">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h3 className="text-base font-semibold">{entry.title}</h3>
          <p className="text-sm text-muted">{entry.summary}</p>
          <p className="text-xs text-muted">{scopeText}</p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 sm:flex-col sm:items-end">
          <span className="rounded-full border border-border bg-background px-3 py-1 text-xs font-medium tabular-nums">
            {headline}
          </span>
          <span className="flex items-center gap-1 text-xs font-medium">
            <span className="group-open:hidden">View full breakdown</span>
            <span className="hidden group-open:inline">Hide breakdown</span>
            <ChevronDown
              aria-hidden
              className="size-4 transition-transform duration-200 group-open:rotate-180"
            />
          </span>
        </div>
      </summary>

      <div className="grid gap-6 border-t border-border p-4 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="flex min-w-0 flex-col gap-3">{children}</div>
        <aside className="flex flex-col gap-4 text-sm">
          <div className="flex flex-col gap-1">
            <h4 className="text-xs font-semibold uppercase tracking-widest text-muted">
              How to read it
            </h4>
            <p>{entry.howToRead}</p>
          </div>
          <div className="flex flex-col gap-1">
            <h4 className="text-xs font-semibold uppercase tracking-widest text-muted">
              What it shows
            </h4>
            <p>{entry.whatItMeans}</p>
          </div>
        </aside>
      </div>
    </details>
  );
}
