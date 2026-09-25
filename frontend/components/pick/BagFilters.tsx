'use client';

import { useId, useState } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  ArrowUpDown,
  Flame,
  Info,
  Leaf,
  Lightbulb,
  Snowflake,
  Star,
  X,
} from 'lucide-react';
import { Ball } from '@/components/ui/Ball';
import { Carousel, type CarouselSlide } from '@/components/ui/Carousel';
import type { Pool } from '@/lib/data/pool';
import type { BonusReturn } from '@/lib/data/distributions';
import { NO_FILTERS, applyFilters, chips, clearFilter, type Filters } from '@/lib/pick/filters';

/**
 * The filters as slides of a carousel: each says in a sentence what it does, how many
 * numbers it takes out right now, what to look for (More info), and where on Explore the
 * figures behind it are - a filter whose effect is invisible is just a switch.
 */

const WINDOWS = [5, 10, 25];
const TIMES = [1, 2, 3];

function timesLabel(times: number): string {
  return times === 1 ? 'once' : times === 2 ? 'twice' : `${times} times`;
}

interface Option<T> {
  value: T;
  label: string;
}

function Pills<T>({
  label,
  options,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-xs text-muted" aria-hidden>
        {label}
      </span>
      {options.map((o) => (
        <button
          key={o.label}
          type="button"
          disabled={disabled}
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-full border px-3 py-1.5 text-sm transition-colors disabled:opacity-40 ${
            value === o.value
              ? 'border-accent bg-accent text-accent-foreground'
              : 'border-border bg-background hover:border-foreground'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function FilterSlide({
  icon: Icon,
  tone,
  title,
  what,
  hint,
  explore,
  takesOut,
  children,
}: {
  icon: typeof Flame;
  tone: { backdrop: string; icon: string };
  title: string;
  what: string;
  hint: React.ReactNode;
  explore: { href: string; label: string };
  takesOut: number;
  children: React.ReactNode;
}) {
  const [info, setInfo] = useState(false);
  const hintId = useId();

  return (
    <article
      className={`relative flex h-full min-h-72 flex-col gap-4 overflow-hidden bg-linear-to-br to-surface-raised p-5 sm:px-10 sm:py-8 ${tone.backdrop}`}
    >
      {/* The backdrop: the card's icon, large and faint, where a trailer would play. */}
      <Icon
        className={`pointer-events-none absolute -right-6 -bottom-8 h-56 w-56 opacity-15 ${tone.icon}`}
        aria-hidden
      />
      <header className="relative flex flex-wrap items-center gap-3">
        <span
          className={`rounded-full border border-current bg-surface-raised p-2 ${tone.icon}`}
          aria-hidden
        >
          <Icon className="h-5 w-5" />
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
            takesOut ? 'bg-accent text-accent-foreground' : 'bg-surface text-muted'
          }`}
        >
          {takesOut ? `takes out ${takesOut}` : 'off'}
        </span>
      </header>
      <div className="relative flex max-w-xl flex-col gap-1">
        <h3 className="text-2xl font-bold tracking-tight">{title}</h3>
        <p className="text-sm">{what}</p>
      </div>
      <div className="relative flex flex-col gap-2">{children}</div>
      <div className="relative mt-auto flex flex-wrap items-center gap-2 pt-1">
        <button
          type="button"
          onClick={() => setInfo((v) => !v)}
          aria-expanded={info}
          aria-controls={hintId}
          className="flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-foreground"
        >
          <Info className="h-4 w-4" aria-hidden />
          More info
        </button>
        <Link
          href={explore.href}
          className="flex items-center gap-1.5 rounded-full border border-border bg-surface-raised px-4 py-2 text-sm font-medium hover:border-foreground"
        >
          {explore.label}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
      <p
        id={hintId}
        hidden={!info}
        className="relative max-w-xl gap-2 rounded-xl border border-border bg-surface-raised p-3 text-sm [&:not([hidden])]:flex"
      >
        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>{hint}</span>
      </p>
    </article>
  );
}

export function BagFilters({
  pool,
  filters,
  setFilters,
  remaining,
  heading,
  remainingLabel,
  bonus,
}: {
  pool: Pool;
  filters: Filters;
  setFilters: (f: Filters) => void;
  remaining: number;
  heading: string;
  remainingLabel: string;
  bonus: BonusReturn;
}) {
  const active = chips(filters, pool.highFrom);
  const takesOut = (key: keyof Filters) =>
    pool.numbers.length -
    applyFilters(pool.numbers, { ...NO_FILTERS, [key]: filters[key] }, pool.highFrom).length;
  const inBin = (bin: number) => pool.numbers.filter((n) => n.freshnessBin === bin).length;
  const busyWindow = filters.drawnMoreThan?.draws ?? 10;
  const binName = (bin: number) => (bin === pool.maxBin ? `C${bin}+` : `C${bin}`);
  const binMeaning = (bin: number) =>
    bin === 0 ? 'not drawn' : bin === pool.maxBin ? `${timesLabel(bin)} or more` : timesLabel(bin);
  const statistics = { href: '/explore?tab=statistics', label: 'See it on Explore' };

  const slides: CarouselSlide[] = [
    {
      id: 'busy',
      label: 'Busy lately',
      marked: takesOut('drawnMoreThan') > 0,
      content: (
        <FilterSlide
          icon={Flame}
          tone={{ backdrop: 'from-hot-soft', icon: 'text-hot' }}
          title="Busy lately"
          what="Take out the numbers that have been coming up a lot."
          hint="These numbers have been showing up. Keep them or leave them out - the next draw gives every ball the same chance."
          explore={statistics}
          takesOut={takesOut('drawnMoreThan')}
        >
          <Pills
            label="Drawn more than"
            options={[
              { value: null as number | null, label: 'Off' },
              ...TIMES.map((t) => ({ value: t as number | null, label: timesLabel(t) })),
            ]}
            value={filters.drawnMoreThan?.times ?? null}
            onChange={(times) =>
              setFilters({
                ...filters,
                drawnMoreThan: times === null ? null : { times, draws: busyWindow },
              })
            }
          />
          <Pills
            label="in the last"
            disabled={!filters.drawnMoreThan}
            options={WINDOWS.map((w) => ({ value: w, label: `${w} draws` }))}
            value={busyWindow}
            onChange={(draws) =>
              filters.drawnMoreThan &&
              setFilters({ ...filters, drawnMoreThan: { ...filters.drawnMoreThan, draws } })
            }
          />
        </FilterSlide>
      ),
    },
    {
      id: 'quiet',
      label: 'Quiet lately',
      marked: takesOut('notDrawnIn') > 0,
      content: (
        <FilterSlide
          icon={Snowflake}
          tone={{ backdrop: 'from-cold-soft', icon: 'text-cold' }}
          title="Quiet lately"
          what="Take out the numbers that have not come up at all for a while."
          hint="The other side of the same taste. A long gap does not make a number any more likely - the balls have no memory."
          explore={statistics}
          takesOut={takesOut('notDrawnIn')}
        >
          <Pills
            label="Not drawn in the last"
            options={[
              { value: null as number | null, label: 'Off' },
              ...WINDOWS.map((w) => ({ value: w as number | null, label: `${w} draws` })),
            ]}
            value={filters.notDrawnIn}
            onChange={(notDrawnIn) => setFilters({ ...filters, notDrawnIn })}
          />
        </FilterSlide>
      ),
    },
    {
      id: 'freshness',
      label: 'Freshness',
      marked: takesOut('bins') > 0,
      content: (
        <FilterSlide
          icon={Leaf}
          tone={{ backdrop: 'from-medium-soft', icon: 'text-medium' }}
          title="Freshness"
          what={`Keep only the groups you tap, by how often each number came up in the last ${pool.freshnessDraws} draws.`}
          hint="Nothing tapped keeps every group. The Freshness tab on Explore shows which mixes past draws had."
          explore={{ href: '/explore?tab=freshness', label: 'See it on Explore' }}
          takesOut={takesOut('bins')}
        >
          <div role="group" aria-label="Keep freshness groups" className="grid grid-cols-3 gap-2">
            {Array.from({ length: pool.maxBin + 1 }, (_, bin) => {
              const on = filters.bins.includes(bin);
              return (
                <button
                  key={bin}
                  type="button"
                  aria-pressed={on}
                  onClick={() =>
                    setFilters({
                      ...filters,
                      bins: on
                        ? filters.bins.filter((b) => b !== bin)
                        : [...filters.bins, bin].sort(),
                    })
                  }
                  className={`flex flex-col items-start rounded-xl border p-2.5 text-left transition-colors ${
                    on
                      ? 'border-accent bg-accent text-accent-foreground'
                      : 'border-border bg-background hover:border-foreground'
                  }`}
                >
                  <span className="text-base font-semibold">{binName(bin)}</span>
                  <span className="text-xs">{binMeaning(bin)}</span>
                  <span className="text-xs">{inBin(bin)} numbers</span>
                </button>
              );
            })}
          </div>
        </FilterSlide>
      ),
    },
    {
      id: 'bonus',
      label: 'Recent bonus balls',
      marked: takesOut('dropRecentBonus') > 0,
      content: (
        <FilterSlide
          icon={Star}
          tone={{ backdrop: 'from-bonus-soft', icon: 'text-bonus' }}
          title="Recent bonus balls"
          what={`Take out the bonus balls of the last ${pool.bonusWindow} draws.`}
          hint={`Some people think a bonus ball comes back soon. Over past draws, ${(100 * bonus.rate).toFixed(1)}% came back as a main number within ${bonus.window} draws - a fair draw gives ${(100 * bonus.fairRate).toFixed(1)}%.`}
          explore={{ href: '/explore?tab=draws', label: 'See the draws on Explore' }}
          takesOut={takesOut('dropRecentBonus')}
        >
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              role="switch"
              aria-checked={filters.dropRecentBonus}
              onClick={() => setFilters({ ...filters, dropRecentBonus: !filters.dropRecentBonus })}
              className="flex items-center gap-2 text-sm"
            >
              <span
                className={`relative h-6 w-11 rounded-full border transition-colors ${
                  filters.dropRecentBonus ? 'border-accent bg-accent' : 'border-border bg-surface'
                }`}
                aria-hidden
              >
                <span
                  className={`absolute top-0.5 h-4.5 w-4.5 rounded-full transition-all ${
                    filters.dropRecentBonus ? 'left-5.5 bg-accent-foreground' : 'left-0.5 bg-muted'
                  }`}
                />
              </span>
              Take them out
            </button>
            <span className="flex flex-wrap gap-1">
              {[...new Set(pool.recentBonus)].map((n) => (
                <Ball key={n} number={n} isBonus size="sm" className="h-7 w-7 text-xs" />
              ))}
            </span>
          </div>
        </FilterSlide>
      ),
    },
    {
      id: 'half',
      label: 'High or low',
      marked: takesOut('half') > 0,
      content: (
        <FilterSlide
          icon={ArrowUpDown}
          tone={{ backdrop: 'from-surface', icon: 'text-foreground' }}
          title="High or low"
          what={`Keep only the numbers below ${pool.highFrom}, or only ${pool.highFrom} and above.`}
          hint={`Numbers from ${pool.highFrom} up cannot be birthdays, so fewer people play them - a win is shared less often. The chance of winning is the same.`}
          explore={statistics}
          takesOut={takesOut('half')}
        >
          <Pills
            label="Keep"
            options={[
              { value: null as Filters['half'], label: 'All 47' },
              { value: 'low' as Filters['half'], label: `1 to ${pool.highFrom - 1}` },
              { value: 'high' as Filters['half'], label: `${pool.highFrom} to 47` },
            ]}
            value={filters.half}
            onChange={(half) => setFilters({ ...filters, half })}
          />
        </FilterSlide>
      ),
    },
  ];

  // Arriving with a filter already on (Explore sends /pick?bin=) opens on that card.
  const [start] = useState(() => Math.max(0, slides.findIndex((s) => s.marked)));

  return (
    <section className="flex flex-col gap-4" aria-labelledby="bag-filters-title">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="bag-filters-title" className="text-lg font-semibold">
            {heading}
          </h2>
          <p className="text-sm text-muted">
            Optional. Five cards, each taking some numbers out to suit your taste. Swipe,
            use the arrows or tap a bar to move between them.
          </p>
        </div>
        <p className="text-sm font-medium" aria-live="polite">
          {remaining} {remainingLabel}
        </p>
      </div>

      <Carousel label="Filters" slides={slides} start={start} />

      {active.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted">Taking out:</span>
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
          <button type="button" onClick={() => setFilters(NO_FILTERS)} className="text-xs underline">
            Reset filters
          </button>
        </div>
      )}
    </section>
  );
}
