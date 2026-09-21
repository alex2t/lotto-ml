'use client';

import Link from 'next/link';
import { CATEGORY_INITIAL } from '@/components/ui/Ball';
import type { PoolNumber } from '@/lib/data/pool';

const TONE = {
  hot: 'bg-hot-soft text-hot border-hot',
  medium: 'bg-medium-soft text-medium border-medium',
  cold: 'bg-cold-soft text-cold border-cold',
} as const;

/**
 * The 1-47 grid: six columns on a phone, 44px targets. Each cell carries its category
 * initial as well as its tint, and its count in the last 10 draws.
 */
export function NumberGrid({
  numbers,
  selected,
  available,
  onToggle,
  window = 10,
}: {
  numbers: PoolNumber[];
  selected: number[];
  available: Set<number>;
  onToggle: (n: number) => void;
  window?: number;
}) {
  return (
    <ul className="grid grid-cols-6 gap-1.5 sm:grid-cols-8 md:grid-cols-12">
      {numbers.map((item) => {
        const isSelected = selected.includes(item.number);
        const isOut = !available.has(item.number) && !isSelected;
        return (
          <li key={item.number}>
            <button
              type="button"
              onClick={() => onToggle(item.number)}
              aria-pressed={isSelected}
              aria-label={`${item.number}, ${item.category}, drawn ${item.recent[window]} times in the last ${window} draws`}
              className={`flex h-11 w-full flex-col items-center justify-center rounded-lg border text-sm font-semibold tabular-nums ${
                TONE[item.category]
              } ${isSelected ? 'ring-2 ring-offset-1 ring-accent' : ''} ${
                isOut ? 'opacity-30' : ''
              }`}
            >
              <span aria-hidden>{String(item.number).padStart(2, '0')}</span>
              <span className="text-[0.6rem] font-normal leading-none opacity-80" aria-hidden>
                {CATEGORY_INITIAL[item.category]}
                {item.recent[window]}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** The peek card behind a number, shown beside the grid. */
export function NumberPeek({ item, window = 25 }: { item: PoolNumber; window?: number }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
      <span className="font-semibold">{item.number}</span>
      <span className="text-muted">{item.category}</span>
      <span className="text-muted">last seen {item.lastSeen.replaceAll('/', '-')}</span>
      <span className="text-muted">
        {item.recent[window]} in the last {window} draws
      </span>
      <Link href={`/numbers/${item.number}`} className="underline">
        Full dossier
      </Link>
    </div>
  );
}
