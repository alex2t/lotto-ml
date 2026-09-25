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
      className="stat-card group scroll-mt-4 rounded-xl border border-border bg-surface shadow-[0_8px_24px_rgb(0_0_0/0.18)] transition-colors hover:border-gold/60 open:border-gold/70 open:bg-surface-raised"
    >
      <summary className="flex cursor-pointer list-none flex-col gap-3 rounded-xl p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground sm:flex-row sm:items-center [&::-webkit-details-marker]:hidden">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h3 className="text-base font-semibold">{entry.title}</h3>
          <p className="text-sm text-muted">{entry.summary}</p>
          <p className="text-xs text-muted">{scopeText}</p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 sm:flex-col sm:items-end">
          <span className="rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-xs font-semibold tabular-nums text-gold">
            {headline}
          </span>
          <span className="flex items-center gap-2 text-xs font-medium text-muted group-hover:text-foreground">
            <span className="group-open:hidden">View full breakdown</span>
            <span className="hidden group-open:inline">Hide breakdown</span>
            <span className="grid size-7 place-items-center rounded-full bg-gold/15 text-gold" aria-hidden>
              <ChevronDown className="size-4 transition-transform duration-200 group-open:rotate-180" />
            </span>
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
