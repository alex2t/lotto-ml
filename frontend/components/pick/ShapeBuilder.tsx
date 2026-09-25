'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ArrowUpDown, Divide, MoveHorizontal, Scale, Shapes } from 'lucide-react';
import type { Pool, PoolNumber } from '@/lib/data/pool';
import { spreadBand, sumBand } from '@/lib/scoring/bands';
import { sample } from '@/lib/pick/filters';

const LINE_SIZE = 6;

export interface ShapeOption {
  key: string;
  label: string;
  percentage: number;
}

export interface ShapeOptions {
  oddEven: ShapeOption[];
  sums: ShapeOption[];
  spreads: ShapeOption[];
  highCounts: ShapeOption[];
}

/** One trait of a line, as a card: what it means in plain words, then its options. */
function Trait({
  step,
  icon: Icon,
  title,
  what,
  example,
  options,
  chosen,
  onChoose,
}: {
  step: number;
  icon: typeof Shapes;
  title: string;
  what: string;
  example: string;
  options: ShapeOption[];
  chosen: string | null;
  onChoose: (key: string | null) => void;
}) {
  const widest = Math.max(...options.map((o) => o.percentage));
  return (
    <fieldset className="flex flex-col gap-3 rounded-2xl border border-border bg-surface-raised p-4 shadow-sm">
      <legend className="sr-only">{title}</legend>
      <header className="flex items-start gap-3">
        <span className="rounded-full border border-border bg-surface p-2" aria-hidden>
          <Icon className="h-4 w-4" />
        </span>
        <div className="mr-auto">
          <p className="text-xs uppercase tracking-widest text-muted">Part {step}</p>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-sm text-muted">{what}</p>
          <p className="mt-1 text-xs text-muted">{example}</p>
        </div>
        {chosen !== null && (
          <button type="button" onClick={() => onChoose(null)} className="shrink-0 text-xs underline">
            Any
          </button>
        )}
      </header>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {options.map((option) => {
          const on = chosen === option.key;
          return (
            <button
              key={option.key}
              type="button"
              aria-pressed={on}
              onClick={() => onChoose(on ? null : option.key)}
              className={`flex flex-col gap-1.5 rounded-xl border p-2.5 text-left transition-colors ${
                on
                  ? 'border-accent bg-accent text-accent-foreground'
                  : 'border-border bg-background hover:border-foreground'
              }`}
            >
              <span className="text-sm font-semibold">{option.label}</span>
              <span className="h-1.5 w-full overflow-hidden rounded-full bg-surface" aria-hidden>
                <span
                  className={`block h-full rounded-full ${on ? 'bg-accent-foreground' : 'bg-cold'}`}
                  style={{ width: `${(100 * option.percentage) / widest}%` }}
                />
              </span>
              <span className="text-xs">in {option.percentage.toFixed(1)}% of past draws</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function ShapeBuilder({
  options,
  pool,
  available,
  onLine,
}: {
  options: ShapeOptions;
  pool: Pool;
  available: PoolNumber[];
  onLine: (line: number[], message?: string) => void;
}) {
  const [odd, setOdd] = useState<string | null>(null);
  const [high, setHigh] = useState<string | null>(null);
  const [sum, setSum] = useState<string | null>(null);
  const [spread, setSpread] = useState<string | null>(null);

  const labelOf = (list: ShapeOption[], key: string | null) =>
    list.find((o) => o.key === key)?.label;
  const summary = [
    odd && labelOf(options.oddEven, odd),
    high && `${labelOf(options.highCounts, high)} at ${pool.highFrom}+`,
    sum && `sum ${labelOf(options.sums, sum)}`,
    spread && `spread ${labelOf(options.spreads, spread)}`,
  ].filter(Boolean);

  function build() {
    const numbers = available.map((n) => n.number);
    const odds = odd === null ? null : Number(odd.split('_')[0]);
    const highs = high === null ? null : Number(high);
    for (let attempt = 0; attempt < 20000; attempt += 1) {
      const candidate = sample(numbers, LINE_SIZE);
      if (candidate.length < LINE_SIZE) break;
      if (odds !== null && candidate.filter((n) => n % 2 === 1).length !== odds) continue;
      if (highs !== null && candidate.filter((n) => n >= pool.highFrom).length !== highs) continue;
      if (sum !== null && sumBand(candidate.reduce((a, b) => a + b, 0)).key !== sum) continue;
      if (spread !== null) {
        const range = Math.max(...candidate) - Math.min(...candidate);
        if (spreadBand(range).key !== spread) continue;
      }
      onLine(candidate.sort((a, b) => a - b));
      return;
    }
    onLine(
      [],
      'No line in the remaining pool has that shape - try dropping one of the choices or a filter.',
    );
  }

  function reset() {
    setOdd(null);
    setHigh(null);
    setSum(null);
    setSpread(null);
    onLine([]);
  }

  return (
    <section className="flex flex-col gap-4" aria-labelledby="shape-title">
      <div className="flex flex-col gap-4 rounded-2xl border border-border bg-linear-to-br from-cold-soft to-surface-raised p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span className="rounded-full border border-cold bg-surface-raised p-2 text-cold" aria-hidden>
            <Shapes className="h-5 w-5" />
          </span>
          <div>
            <h2 id="shape-title" className="text-xl font-bold tracking-tight">
              Follow a shape
            </h2>
            <p className="text-sm">
              A shape is what six numbers look like together - how many are odd, how many
              are high, what they add up to and how far apart they sit. Choose the parts you
              care about and the picker fills a line that has them.
            </p>
          </div>
        </div>

        <ol className="grid gap-2 sm:grid-cols-3">
          {[
            'Tap an option in any of the four parts below. One is enough; leave the rest on Any.',
            'Press "Fill a line with this shape". Press it again for another line with the same shape.',
            'Your line lands in the tray at the bottom, described next to past draws.',
          ].map((text, i) => (
            <li key={text} className="flex gap-2 rounded-xl bg-surface-raised p-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                {i + 1}
              </span>
              {text}
            </li>
          ))}
        </ol>

        <p className="text-sm">
          Each option says how often past draws had it. A common shape is not a likelier one -
          every line of six has the same chance. To see the full charts behind these figures,
          have a look at the Explore section.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/explore?tab=statistics"
            className="flex items-center gap-1.5 rounded-full border border-border bg-surface-raised px-4 py-2 text-sm font-medium hover:border-foreground"
          >
            Odd/even, sums and spreads on Explore
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            href="/explore?tab=patterns"
            className="flex items-center gap-1.5 rounded-full border border-border bg-surface-raised px-4 py-2 text-sm font-medium hover:border-foreground"
          >
            The draws most like a line
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Trait
          step={1}
          icon={Divide}
          title="Odd and even"
          what="How many of your six are odd numbers."
          example="3, 8, 15, 22, 31, 40 is 3 odd / 3 even."
          options={options.oddEven}
          chosen={odd}
          onChoose={setOdd}
        />
        <Trait
          step={2}
          icon={ArrowUpDown}
          title={`How many ${pool.highFrom} and above`}
          what={`How many of your six are ${pool.highFrom} or higher - numbers no birthday can be.`}
          example={`5, 12, 19, 33, 40, 44 has 3 of six at ${pool.highFrom} or above.`}
          options={options.highCounts}
          chosen={high}
          onChoose={setHigh}
        />
        <Trait
          step={3}
          icon={Scale}
          title="Sum"
          what="Add your six numbers together."
          example="3 + 8 + 15 + 22 + 31 + 40 = 119."
          options={options.sums}
          chosen={sum}
          onChoose={setSum}
        />
        <Trait
          step={4}
          icon={MoveHorizontal}
          title="Spread"
          what="Your highest number minus your lowest - how wide the line reaches."
          example="3 to 40 is a spread of 37."
          options={options.spreads}
          chosen={spread}
          onChoose={setSpread}
        />
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-4 sm:flex-row sm:items-center">
        <p className="mr-auto text-sm" aria-live="polite">
          <span className="font-semibold">Your shape: </span>
          {summary.length ? summary.join(' - ') : 'nothing chosen yet, so any six will do.'}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={build}
            className="w-fit rounded-full bg-accent px-5 py-3 text-sm font-medium text-accent-foreground"
          >
            Fill a line with this shape
          </button>
          <button type="button" onClick={reset} className="text-sm underline">
            Clear the shape
          </button>
        </div>
      </div>
    </section>
  );
}
