'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Dices,
  Download,
  Grid3x3,
  Hand,
  Minus,
  Plus,
  Shapes,
  Sparkles,
  X,
} from 'lucide-react';
import { Ball } from '@/components/ui/Ball';
import { ShapeCard } from './ShapeCard';
import { Wheel } from './Wheel';
import { NumberGrid, NumberPeek } from './NumberGrid';
import type { Pool, PoolNumber } from '@/lib/data/pool';
import type { Category } from '@/lib/data/types';
import type { LineShape } from '@/lib/scoring/line';
import { spreadBand, sumBand } from '@/lib/scoring/bands';
import { drawLineImage, saveImage } from '@/lib/pick/line-image';
import { setCurrentLine } from '@/lib/pick/current-line';
import {
  NO_FILTERS,
  applyFilters,
  chips,
  clearFilter,
  sample,
  type Filters,
} from '@/lib/pick/filters';

const LINE_SIZE = 6;

/** The same fixed vocabulary the shape card uses. */
const VERDICT_SENTENCE = {
  typical: 'This line looks typical of past draws',
  uncommon: 'This line looks uncommon next to past draws',
  unusual: 'This line looks unusual next to past draws',
} as const;
const BANDS: Category[] = ['hot', 'medium', 'cold'];

type Method = 'wheels' | 'hand' | 'shake' | 'shape' | 'surprise';

const METHODS: Array<{ id: Method; label: string; icon: typeof Dices }> = [
  { id: 'wheels', label: 'Spin the wheels', icon: Dices },
  { id: 'hand', label: 'Pick by hand', icon: Hand },
  { id: 'shake', label: 'Shake the bag', icon: Grid3x3 },
  { id: 'shape', label: 'Follow a shape', icon: Shapes },
  { id: 'surprise', label: 'Surprise me', icon: Sparkles },
];

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

interface PickerProps {
  pool: Pool;
  shapeOptions: ShapeOptions;
  /** The newest draw on file, so a saved image says what it was drawn against. */
  latestDraw: string;
  /** Numbers to start the tray with, from /pick?numbers= - a dossier sends one this way. */
  initialLine?: number[];
  /** A freshness bin to start filtered to, from /pick?bin= - Explore sends one this way. */
  initialBin?: number;
}

export function Picker({
  pool,
  shapeOptions,
  latestDraw,
  initialLine,
  initialBin,
}: PickerProps) {
  const [method, setMethod] = useState<Method>(
    initialLine?.length ? 'hand' : 'wheels',
  );
  const [filters, setFilters] = useState<Filters>(
    initialBin === undefined ? NO_FILTERS : { ...NO_FILTERS, bins: [initialBin] },
  );
  const [line, setLine] = useState<number[]>(initialLine ?? []);
  // The chat panel sends the tray's line with a question asked on this page.
  useEffect(() => {
    setCurrentLine(line);
    return () => setCurrentLine([]);
  }, [line]);
  const [scored, setScored] = useState<{ key: string; shape: LineShape } | null>(null);
  const [peek, setPeek] = useState<PoolNumber | null>(null);
  // One wheel per band by default; a band can be given more, or taken down to none, which
  // is how a player builds a 4 hot / 1 medium / 1 cold line rather than being handed one.
  const [wheels, setWheels] = useState<Record<Category, number>>({
    hot: 1,
    medium: 1,
    cold: 1,
  });
  const [note, setNote] = useState<string | null>(null);
  const [shaking, setShaking] = useState(false);

  const available = useMemo(
    () => applyFilters(pool.numbers, filters, pool.highFrom),
    [pool, filters],
  );
  const availableSet = useMemo(
    () => new Set(available.map((n) => n.number)),
    [available],
  );
  const pickable = useMemo(
    () => available.filter((n) => !line.includes(n.number)).map((n) => n.number),
    [available, line],
  );

  // The shape card is scored server-side, so the page and /api/validate cannot disagree.
  const lineKey = line.join(',');
  useEffect(() => {
    if (line.length !== LINE_SIZE) return;
    let live = true;
    fetch('/api/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: LineShape | null) => {
        if (live && data) setScored({ key: lineKey, shape: data });
      });
    return () => {
      live = false;
    };
  }, [line, lineKey]);

  // Only ever show a card that belongs to the line on screen.
  const shape = scored?.key === lineKey ? scored.shape : null;

  function add(n: number) {
    setNote(null);
    setLine((current) => {
      if (current.includes(n)) return current;
      if (current.length >= LINE_SIZE) return current;
      return [...current, n];
    });
  }

  function toggle(n: number) {
    setPeek(pool.numbers.find((p) => p.number === n) ?? null);
    setLine((current) =>
      current.includes(n)
        ? current.filter((x) => x !== n)
        : current.length >= LINE_SIZE
          ? current
          : [...current, n],
    );
  }

  function fillRest(from: number[] = pickable) {
    const needed = LINE_SIZE - line.length;
    if (from.length < needed) {
      setNote(`Only ${from.length} numbers are left in the filters - ${needed} are needed.`);
      return;
    }
    setNote(null);
    setLine((current) => [...current, ...sample(from, needed)]);
  }

  function shakeTheBag() {
    if (available.length < LINE_SIZE) {
      setNote(`Only ${available.length} numbers are left in the filters - six are needed.`);
      return;
    }
    setNote(null);
    const picked = sample(available.map((n) => n.number), LINE_SIZE);

    // Animation may never delay information (5.2): with reduced motion, or no window to
    // schedule on, the whole line is in the DOM immediately.
    const reduced =
      typeof window === 'undefined' ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      setLine(picked);
      return;
    }

    setShaking(true);
    setLine([]);
    picked.forEach((n, i) => {
      window.setTimeout(() => {
        setLine((current) => [...current, n]);
        if (i === picked.length - 1) setShaking(false);
      }, 90 * (i + 1));
    });
  }

  function surprise() {
    setNote(null);
    setLine(sample(pool.numbers.map((n) => n.number), LINE_SIZE));
  }

  const bandNumbers = (band: Category) =>
    available.filter((n) => n.category === band && !line.includes(n.number)).map((n) => n.number);

  return (
    <div className="flex flex-col gap-6 pb-40">
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">How do you want to pick?</h2>
        <div className="flex flex-wrap gap-2">
          {METHODS.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setMethod(m.id)}
                aria-pressed={method === m.id}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm ${
                  method === m.id
                    ? 'border-accent bg-accent text-accent-foreground'
                    : 'border-border text-muted'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden />
                {m.label}
              </button>
            );
          })}
        </div>
      </section>

      {method !== 'surprise' && (
        <FilterPanel
          pool={pool}
          filters={filters}
          setFilters={setFilters}
          remaining={available.length}
        />
      )}

      {note && (
        <p role="status" className="text-sm text-muted">
          {note}
        </p>
      )}

      {method === 'wheels' && (
        <section className="grid gap-3 sm:grid-cols-3">
          {BANDS.map((band) => (
            <div key={band} className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="capitalize text-muted">{band}</span>
                <span className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() =>
                      setWheels((w) => ({ ...w, [band]: Math.max(0, w[band] - 1) }))
                    }
                    disabled={wheels[band] === 0}
                    aria-label={`One fewer ${band} wheel`}
                    className="rounded-full border border-border p-1 disabled:opacity-40"
                  >
                    <Minus className="h-3.5 w-3.5" aria-hidden />
                  </button>
                  <span className="w-12 text-center text-xs text-muted" aria-live="polite">
                    {wheels[band]} {wheels[band] === 1 ? 'wheel' : 'wheels'}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setWheels((w) => ({ ...w, [band]: Math.min(LINE_SIZE, w[band] + 1) }))
                    }
                    disabled={wheels[band] >= LINE_SIZE}
                    aria-label={`One more ${band} wheel`}
                    className="rounded-full border border-border p-1 disabled:opacity-40"
                  >
                    <Plus className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </span>
              </div>

              {wheels[band] === 0 ? (
                <p className="rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted">
                  No {band} wheel - this band contributes nothing.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {Array.from({ length: wheels[band] }, (_, i) => (
                    <Wheel
                      key={`${band}-${i}`}
                      band={band}
                      instance={i}
                      numbers={bandNumbers(band)}
                      onPick={add}
                      disabled={line.length >= LINE_SIZE}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {method === 'hand' && (
        <section className="flex flex-col gap-3">
          <NumberGrid
            numbers={pool.numbers}
            selected={line}
            available={availableSet}
            onToggle={toggle}
          />
          {peek && <NumberPeek item={peek} />}
        </section>
      )}

      {method === 'shake' && (
        <section className="flex flex-col items-start gap-3">
          <p className="text-sm text-muted">
            Six numbers at once, from the {available.length} your filters leave in.
          </p>
          <button
            type="button"
            onClick={shakeTheBag}
            className={`rounded-full bg-accent px-5 py-3 text-sm font-medium text-accent-foreground ${
              shaking ? 'bag-shaking' : ''
            }`}
          >
            {shaking ? 'Shaking' : 'Shake'}
          </button>
        </section>
      )}

      {method === 'shape' && (
        <ShapeBuilder
          options={shapeOptions}
          pool={pool}
          available={available}
          onLine={(picked, message) => {
            setLine(picked);
            setNote(message ?? null);
          }}
        />
      )}

      {method === 'surprise' && (
        <section className="flex flex-col items-start gap-3">
          <p className="text-sm text-muted">
            Six numbers from all 47, chosen at random. It is as good as any other method on
            this page.
          </p>
          <button
            type="button"
            onClick={surprise}
            className="rounded-full bg-accent px-5 py-3 text-sm font-medium text-accent-foreground"
          >
            Surprise me
          </button>
        </section>
      )}

      <Tray
        line={line}
        pool={pool}
        shape={shape}
        latestDraw={latestDraw}
        onClear={() => {
          setLine([]);
          setNote(null);
        }}
        onRemove={(n) => setLine((c) => c.filter((x) => x !== n))}
        onFill={() => fillRest()}
      />
    </div>
  );
}

function FilterPanel({
  pool,
  filters,
  setFilters,
  remaining,
}: {
  pool: Pool;
  filters: Filters;
  setFilters: (f: Filters) => void;
  remaining: number;
}) {
  const windows = [5, 6, 10, 25];
  const active = chips(filters, pool.highFrom);

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">Filters on what the wheels contain</h2>
        <p className="text-sm text-muted" aria-live="polite">
          {remaining} numbers left in the wheels
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          Drop numbers drawn more than
          <span className="flex items-center gap-2">
            <input
              type="number"
              min={0}
              max={6}
              value={filters.drawnMoreThan?.times ?? ''}
              placeholder="-"
              onChange={(e) =>
                setFilters({
                  ...filters,
                  drawnMoreThan: e.target.value
                    ? {
                        times: Number(e.target.value),
                        draws: filters.drawnMoreThan?.draws ?? 10,
                      }
                    : null,
                })
              }
              className="w-16 rounded border border-border bg-background p-1"
            />
            times in the last
            <select
              aria-label="window for the drawn-more-than filter"
              value={filters.drawnMoreThan?.draws ?? 10}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  drawnMoreThan: {
                    times: filters.drawnMoreThan?.times ?? 2,
                    draws: Number(e.target.value),
                  },
                })
              }
              className="rounded border border-border bg-background p-1"
            >
              {windows.map((w) => (
                <option key={w} value={w}>
                  {w} draws
                </option>
              ))}
            </select>
          </span>
        </label>

        {/* A label that wraps a select takes the option text into its accessible name, so
            the control sits beside its label rather than inside it. */}
        <div className="flex flex-col gap-1 text-sm">
          <label htmlFor="filter-not-drawn">Drop numbers not drawn at all in the last</label>
          <select
            id="filter-not-drawn"
            value={filters.notDrawnIn ?? ''}
            onChange={(e) =>
              setFilters({
                ...filters,
                notDrawnIn: e.target.value ? Number(e.target.value) : null,
              })
            }
            className="w-40 rounded border border-border bg-background p-1"
          >
            <option value="">no limit</option>
            {[5, 10, 25].map((w) => (
              <option key={w} value={w}>
                {w} draws
              </option>
            ))}
          </select>
        </div>

        <fieldset className="flex flex-col gap-1 text-sm">
          <legend>Keep freshness bins</legend>
          <span className="flex flex-wrap gap-2">
            {Array.from({ length: pool.maxBin + 1 }, (_, bin) => (
              <label key={bin} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={filters.bins.includes(bin)}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      bins: e.target.checked
                        ? [...filters.bins, bin].sort()
                        : filters.bins.filter((b) => b !== bin),
                    })
                  }
                />
                {bin === pool.maxBin ? `C${bin}+` : `C${bin}`}
              </label>
            ))}
          </span>
        </fieldset>

        <div className="flex flex-col gap-2 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={filters.dropRecentBonus}
              onChange={(e) =>
                setFilters({ ...filters, dropRecentBonus: e.target.checked })
              }
            />
            Drop numbers that were a bonus ball in the last {pool.bonusWindow} draws
          </label>
          <div className="flex items-center gap-2">
            <label htmlFor="filter-half">Half</label>
            <select
              id="filter-half"
              value={filters.half ?? ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  half: (e.target.value || null) as Filters['half'],
                })
              }
              className="rounded border border-border bg-background p-1"
            >
              <option value="">all numbers</option>
              <option value="high">{pool.highFrom} and above</option>
              <option value="low">below {pool.highFrom}</option>
            </select>
          </div>
        </div>
      </div>

      {active.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {active.map((chip) => (
            <button
              key={chip.id}
              type="button"
              onClick={() => setFilters(clearFilter(filters, chip.id))}
              className="flex items-center gap-1 rounded-full border border-border px-3 py-1 text-xs"
            >
              {chip.label}
              <X className="h-3 w-3" aria-hidden />
              <span className="sr-only">Remove filter</span>
            </button>
          ))}
          <button
            type="button"
            onClick={() => setFilters(NO_FILTERS)}
            className="text-xs underline"
          >
            Reset filters
          </button>
        </div>
      )}
    </section>
  );
}

function ShapeBuilder({
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
  const [odd, setOdd] = useState<number | null>(null);
  const [high, setHigh] = useState<number | null>(null);
  const [sum, setSum] = useState<string | null>(null);
  const [spread, setSpread] = useState<string | null>(null);

  function build() {
    const numbers = available.map((n) => n.number);
    for (let attempt = 0; attempt < 20000; attempt += 1) {
      const candidate = sample(numbers, LINE_SIZE);
      if (candidate.length < LINE_SIZE) break;
      const odds = candidate.filter((n) => n % 2 === 1).length;
      const highs = candidate.filter((n) => n >= pool.highFrom).length;
      if (odd !== null && odds !== odd) continue;
      if (high !== null && highs !== high) continue;
      if (sum !== null) {
        const total = candidate.reduce((a, b) => a + b, 0);
        if (sumBand(total).key !== sum) continue;
      }
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
    <section className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-4">
      <p className="text-sm text-muted">
        Start from what past draws have looked like. Each option shows the share of draws
        with that shape.
      </p>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Odd / even split</legend>
        <div className="flex flex-wrap gap-2">
          {options.oddEven.map((option) => {
            const value = Number(option.key.split('_')[0]);
            return (
              <button
                key={option.key}
                type="button"
                aria-pressed={odd === value}
                onClick={() => setOdd(odd === value ? null : value)}
                className={`rounded-full border px-3 py-1.5 text-sm ${
                  odd === value ? 'border-accent bg-accent text-accent-foreground' : 'border-border'
                }`}
              >
                {option.label} - {option.percentage.toFixed(1)}%
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">How many {pool.highFrom} and above</legend>
        <div className="flex flex-wrap gap-2">
          {options.highCounts.map((option) => {
            const value = Number(option.key);
            return (
              <button
                key={option.key}
                type="button"
                aria-pressed={high === value}
                onClick={() => setHigh(high === value ? null : value)}
                className={`rounded-full border px-3 py-1.5 text-sm ${
                  high === value ? 'border-accent bg-accent text-accent-foreground' : 'border-border'
                }`}
              >
                {option.label} - {option.percentage.toFixed(1)}%
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Sum</legend>
        <div className="flex flex-wrap gap-2">
          {options.sums.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={sum === option.key}
              onClick={() => setSum(sum === option.key ? null : option.key)}
              className={`rounded-full border px-3 py-1.5 text-sm ${
                sum === option.key
                  ? 'border-accent bg-accent text-accent-foreground'
                  : 'border-border'
              }`}
            >
              {option.label} - {option.percentage.toFixed(1)}%
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Spread, highest minus lowest</legend>
        <div className="flex flex-wrap gap-2">
          {options.spreads.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={spread === option.key}
              onClick={() => setSpread(spread === option.key ? null : option.key)}
              className={`rounded-full border px-3 py-1.5 text-sm ${
                spread === option.key
                  ? 'border-accent bg-accent text-accent-foreground'
                  : 'border-border'
              }`}
            >
              {option.label} - {option.percentage.toFixed(1)}%
            </button>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-wrap gap-3">
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
    </section>
  );
}

function Tray({
  line,
  pool,
  shape,
  latestDraw,
  onClear,
  onRemove,
  onFill,
}: {
  line: number[];
  pool: Pool;
  shape: LineShape | null;
  latestDraw: string;
  onClear: () => void;
  onRemove: (n: number) => void;
  onFill: () => void;
}) {
  const slots = Array.from({ length: LINE_SIZE }, (_, i) => line[i]);
  const categoryOf = (n: number) =>
    pool.numbers.find((p) => p.number === n)?.category;

  // A sheet, with two positions rather than free dragging: on a phone the shape card is
  // most of a screen, so it stays closed until there is something to show and can be put
  // away again. The handle is a button, so it works by keyboard and is announced.
  const [open, setOpen] = useState(false);
  const complete = line.length === LINE_SIZE;

  // Opening itself the moment the line is complete is the point of the sheet: the card is
  // what someone came for. Closing it again is theirs to decide.
  const [lastComplete, setLastComplete] = useState(false);
  if (complete !== lastComplete) {
    setLastComplete(complete);
    if (complete) setOpen(true);
  }

  async function savePng() {
    if (!shape) return;
    const blob = await drawLineImage({
      numbers: shape.line,
      categoryOf,
      verdict: VERDICT_SENTENCE[shape.verdict],
      drawDate: latestDraw,
    });
    if (blob) saveImage(blob, shape.line);
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-20 rounded-t-2xl border-t border-border bg-background/95 shadow-[0_-8px_24px_rgba(0,0,0,0.08)] backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 pb-3 pt-1">
        {/* The grab handle. It is a button because it does something. */}
        <button
          type="button"
          onClick={() => setOpen((current) => !current)}
          aria-expanded={open}
          aria-controls="line-sheet"
          disabled={!shape}
          className="mx-auto flex w-full max-w-24 flex-col items-center gap-1 py-1 disabled:opacity-40"
        >
          <span className="h-1 w-10 rounded-full bg-border" aria-hidden />
          <span className="sr-only">
            {open ? 'Collapse the line details' : 'Expand the line details'}
          </span>
          {shape &&
            (open ? (
              <ChevronDown className="h-3 w-3 text-muted" aria-hidden />
            ) : (
              <ChevronUp className="h-3 w-3 text-muted" aria-hidden />
            ))}
        </button>

        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs uppercase tracking-widest text-muted">Your line</span>
          <div className="flex flex-wrap items-center gap-2">
            {slots.map((n, i) =>
              n === undefined ? (
                <span
                  key={`slot-${i}`}
                  className="h-9 w-9 rounded-full border-2 border-dashed border-border"
                  aria-hidden
                />
              ) : (
                <button key={n} type="button" onClick={() => onRemove(n)} title={`Remove ${n}`}>
                  <Ball number={n} category={categoryOf(n)} size="sm" className="ball-enter" />
                </button>
              ),
            )}
          </div>
          <span className="text-sm text-muted">
            {line.length} of {LINE_SIZE} chosen
          </span>
          <span className="ml-auto flex gap-2">
            <button type="button" onClick={onClear} className="rounded-full border border-border px-3 py-1.5 text-sm">
              Clear
            </button>
            {line.length < LINE_SIZE && (
              <button
                type="button"
                onClick={onFill}
                className="rounded-full border border-border px-3 py-1.5 text-sm"
              >
                Fill the rest
              </button>
            )}
            {shape && (
              <button
                type="button"
                onClick={savePng}
                className="flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm"
              >
                <Download className="h-3.5 w-3.5" aria-hidden />
                Save PNG
              </button>
            )}
          </span>
        </div>

        {shape && (
          <div
            id="line-sheet"
            hidden={!open}
            className="max-h-[60vh] overflow-y-auto sm:max-h-[50vh]"
          >
            <ShapeCard shape={shape} />
          </div>
        )}
      </div>
    </div>
  );
}
