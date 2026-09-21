import Link from 'next/link';
import { DrawsTab } from '@/components/explore/DrawsTab';
import { StatisticsTab } from '@/components/explore/StatisticsTab';
import { FreshnessTab } from '@/components/explore/FreshnessTab';
import { PatternsTab } from '@/components/explore/PatternsTab';
import type { DrawFilters } from '@/lib/data/explore';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Explore the draws - Irish Lotto',
  description:
    'Every draw on file, the distributions behind them, the freshness bins and the draws most like a line.',
};

const TABS = [
  { id: 'draws', label: 'Draws' },
  { id: 'statistics', label: 'Statistics' },
  { id: 'freshness', label: 'Freshness' },
  { id: 'patterns', label: 'Patterns' },
] as const;

type Tab = (typeof TABS)[number]['id'];

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function ExplorePage({ searchParams }: PageProps<'/explore'>) {
  const params = await searchParams;
  const tab = (one(params.tab) ?? 'draws') as Tab;
  const active = TABS.some((t) => t.id === tab) ? tab : 'draws';

  const contains = one(params.contains)
    ?.split(/[\s,]+/)
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 47);

  const highCount = one(params.highCount);
  const filters: DrawFilters = {
    from: one(params.from),
    to: one(params.to),
    contains: contains?.length ? contains : undefined,
    oddEven: one(params.oddEven),
    sumBand: one(params.sumBand),
    highCount: highCount ? Number(highCount) : undefined,
  };

  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const single = one(value);
    if (single) query.set(key, single);
  }
  query.set('tab', active);

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Explore the draws</h1>
        <p className="text-sm text-muted">
          What the draws have looked like. Everything here is counted from past results.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <Link
            key={t.id}
            href={`/explore?tab=${t.id}`}
            aria-current={active === t.id ? 'page' : undefined}
            className={`rounded-full px-4 py-2 text-sm ${
              active === t.id
                ? 'bg-accent text-accent-foreground'
                : 'border border-border text-muted'
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>

      {active === 'draws' && (
        <DrawsTab
          filters={filters}
          page={Number(one(params.page) ?? 1)}
          openDraw={one(params.draw)}
          query={query}
        />
      )}
      {active === 'statistics' && <StatisticsTab />}
      {active === 'freshness' && (
        <FreshnessTab
          bin={one(params.bin) ? Number(one(params.bin)) : undefined}
          mode={one(params.mode) === '7' ? '7' : '6'}
        />
      )}
      {active === 'patterns' && <PatternsTab line={one(params.line)} />}
    </main>
  );
}
