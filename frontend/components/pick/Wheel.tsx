'use client';

import { useState } from 'react';
import { Ball } from '@/components/ui/Ball';
import type { Category } from '@/lib/data/types';

/**
 * One wheel over one band. It spins for show; the number is chosen before the animation
 * starts and announced politely, so a screen reader and a reduced-motion viewer get the
 * result at the same moment everyone else does (web.md 5.2, 5.4).
 */
export function Wheel({
  band,
  numbers,
  onPick,
  disabled,
  instance = 0,
}: {
  band: Category;
  numbers: number[];
  onPick: (n: number) => void;
  disabled: boolean;
  /** Distinguishes several wheels on the same band, for the fallback's label. */
  instance?: number;
}) {
  const [spinning, setSpinning] = useState(false);
  const [landed, setLanded] = useState<number | null>(null);

  const empty = numbers.length === 0;
  const chooseId = `choose-${band}-${instance}`;

  function spin() {
    if (empty || disabled) return;
    const choice = numbers[Math.floor(Math.random() * numbers.length)];
    setLanded(choice);
    onPick(choice);
    setSpinning(true);
    window.setTimeout(() => setSpinning(false), 420);
  }

  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-surface p-4">
      <p className="text-xs uppercase tracking-widest text-muted">
        {band} ({numbers.length})
      </p>

      <div
        className={`flex h-20 w-20 items-center justify-center rounded-full border-2 border-border ${
          spinning ? 'ball-enter' : ''
        }`}
        aria-live="polite"
      >
        {empty ? (
          <span className="px-2 text-center text-xs text-muted">no numbers left</span>
        ) : landed === null ? (
          <span className="text-xs text-muted">ready</span>
        ) : (
          <Ball number={landed} category={band} size="md" />
        )}
      </div>

      <button
        type="button"
        onClick={spin}
        disabled={empty || disabled}
        className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-40"
      >
        {empty ? 'Empty' : 'Spin'}
      </button>

      {/*
        The plain way in (5.4). A wheel is a nice thing to press and a poor thing to depend
        on: this is the same pool, as a list, for anyone who would rather read it than spin
        it - which includes anyone using a screen reader or a keyboard.
      */}
      <label htmlFor={chooseId} className="sr-only">
        Choose a {band} number
      </label>
      <select
        id={chooseId}
        value=""
        disabled={empty || disabled}
        onChange={(event) => {
          const chosen = Number(event.target.value);
          if (chosen) {
            setLanded(chosen);
            onPick(chosen);
          }
        }}
        className="w-full rounded border border-border bg-background p-1 text-xs disabled:opacity-40"
      >
        <option value="">choose a number</option>
        {numbers.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </div>
  );
}
