'use client';

import { ShoppingBag } from 'lucide-react';
import type { PoolNumber } from '@/lib/data/pool';

const TONE = {
  hot: 'bg-hot-soft text-hot border-hot',
  medium: 'bg-medium-soft text-medium border-medium',
  cold: 'bg-cold-soft text-cold border-cold',
} as const;

const STEPS = [
  ['Shape the bag', 'Take out any numbers you would rather not have - or skip this.'],
  ['Shake', 'Six roll out at random from what is left.'],
  ['Look', 'See how your line compares with past draws.'],
] as const;

/**
 * Shake the bag: what it does in three steps, and the bag itself - every number still in
 * it, the ones the filters took out, and the six that just rolled out.
 */
export function ShakeBag({
  numbers,
  inBag,
  line,
  shaking,
  onShake,
}: {
  numbers: PoolNumber[];
  inBag: Set<number>;
  line: number[];
  shaking: boolean;
  onShake: () => void;
}) {
  const kept = numbers.filter((n) => inBag.has(n.number));
  const out = numbers.filter((n) => !inBag.has(n.number));

  return (
    <section className="grid items-center gap-6 rounded-3xl border border-border bg-bonus-soft p-5 sm:p-8 md:grid-cols-2">
      <div className="flex flex-col gap-4">
        <h2 className="text-3xl font-bold tracking-tight">Six balls, one shake.</h2>
        <p className="text-muted">
          All 47 numbers start in the bag. Take out any you would rather not have, give it a
          shake, and six roll out at random - the same way the real draw works.
        </p>
        <ol className="flex flex-col gap-3">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="flex items-start gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground">
                {i + 1}
              </span>
              <span className="text-sm">
                <span className="font-semibold">{title}.</span>{' '}
                <span className="text-muted">{text}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="text-xs text-muted">
          Every line has the same 1 in 10,737,573 chance of the jackpot, however it was picked.
        </p>
      </div>

      <div
        className={`flex flex-col gap-4 rounded-[2rem] border border-border bg-surface-raised p-4 shadow-md sm:p-5 ${
          shaking ? 'bag-shaking' : ''
        }`}
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="flex items-center gap-2 font-semibold">
            <ShoppingBag className="h-5 w-5" aria-hidden />
            In the bag
          </span>
          <span className="text-sm text-muted">
            <span className="text-2xl font-bold text-foreground">{kept.length}</span> of 47
          </span>
        </div>

        <ul aria-label="Numbers in the bag" className="flex flex-wrap gap-1.5">
          {kept.map((n) => (
            <li
              key={n.number}
              aria-label={`${n.number}, ${n.category}${line.includes(n.number) ? ', in your line' : ''}`}
              className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold tabular-nums transition-transform ${
                TONE[n.category]
              } ${line.includes(n.number) ? 'scale-110 ring-2 ring-accent ring-offset-1' : ''}`}
            >
              <span aria-hidden>{String(n.number).padStart(2, '0')}</span>
            </li>
          ))}
        </ul>

        {out.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Taken out ({out.length})</span>
            <p className="text-xs leading-relaxed text-muted tabular-nums">
              {out.map((n) => n.number).join(' · ')}
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={onShake}
          disabled={shaking}
          className="flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-4 text-lg font-semibold text-accent-foreground transition-transform hover:scale-[1.02] active:scale-95 disabled:opacity-80"
        >
          <ShoppingBag className="h-5 w-5" aria-hidden />
          {shaking ? 'Shaking...' : line.length === 6 ? 'Shake again' : 'Shake'}
        </button>
      </div>
    </section>
  );
}
