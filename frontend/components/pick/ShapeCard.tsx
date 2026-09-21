import type { Check, LineShape } from '@/lib/scoring/line';

/**
 * The six checks as comparisons, not a score.
 *
 * The verdict word comes from the fixed vocabulary and the equal-chance sentence is
 * rendered with it, always, here - which is what makes the wording testable in one place.
 */
const VERDICT_TEXT = {
  typical: 'This line looks TYPICAL of past draws.',
  uncommon: 'This line looks UNCOMMON next to past draws.',
  unusual: 'This line looks UNUSUAL next to past draws.',
} as const;

function Distribution({ check }: { check: Check }) {
  const max = Math.max(...check.buckets.map((b) => b.percentage), 1);

  return (
    <div className="flex flex-wrap items-end gap-0.5" aria-hidden>
      {check.buckets.map((bucket) => (
        <span
          key={bucket.key}
          title={`${bucket.label}: ${bucket.percentage.toFixed(1)}%`}
          className={`w-2 rounded-sm ${bucket.isLine ? 'bg-accent' : 'bg-border'}`}
          style={{ height: `${Math.max(3, (bucket.percentage / max) * 28)}px` }}
        />
      ))}
    </div>
  );
}

export function ShapeCard({ shape }: { shape: LineShape }) {
  return (
    <section className="flex flex-col gap-4 rounded-xl border border-border bg-surface-raised p-4">
      <h2 className="text-sm uppercase tracking-widest text-muted">
        Your line next to {shape.drawsCompared} past draws
      </h2>

      <dl className="flex flex-col gap-3">
        {shape.checks.map((check) => (
          <div
            key={check.id}
            className="grid grid-cols-1 gap-1 border-b border-border pb-3 last:border-0 sm:grid-cols-[10rem_5rem_1fr] sm:items-center sm:gap-3"
          >
            <dt className="text-sm font-medium">{check.title}</dt>
            <dd className="text-sm tabular-nums">{check.value}</dd>
            <dd className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
              {check.buckets.length > 0 && <Distribution check={check} />}
              <span className="text-sm text-muted">{check.comparison}</span>
            </dd>
          </div>
        ))}
      </dl>

      {shape.notes.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm text-muted">
          {shape.notes.map((note) => (
            <li key={note.id}>{note.text}</li>
          ))}
        </ul>
      )}

      <p className="text-sm">
        <strong>{VERDICT_TEXT[shape.verdict]}</strong> {shape.equalChance}
      </p>
    </section>
  );
}
