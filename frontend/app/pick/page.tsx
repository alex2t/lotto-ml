import { pool } from '@/lib/data/pool';
import { latestDrawDate } from '@/lib/data/schedule';
import { highNumbers, oddEvenPatterns, sumDistributions } from '@/lib/data/distributions';
import { spreadBandShares } from '@/lib/scoring/line';
import { bandLabel } from '@/lib/scoring/bands';
import { Picker, type ShapeOptions } from '@/components/pick/Picker';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Pick a line - Irish Lotto',
  description:
    'Choose six numbers by wheel, by hand, by shape or at random, and see how the line compares with past draws.',
};

function shapeOptions(): ShapeOptions {
  return {
    oddEven: Object.entries(oddEvenPatterns('6_main')).map(([key, bucket]) => ({
      key,
      label: `${key.split('_')[0]} odd / ${key.split('_')[1]} even`,
      percentage: bucket.percentage,
    })),
    sums: Object.entries(sumDistributions('6_main')).map(([key, bucket]) => ({
      key,
      label: bandLabel(key),
      percentage: bucket.percentage,
    })),
    spreads: Object.entries(spreadBandShares()).map(([key, percentage]) => ({
      key,
      label: key,
      percentage,
    })),
    highCounts: Object.entries(highNumbers().byCount).map(([key, bucket]) => ({
      key,
      label: `${key} of six`,
      percentage: bucket.percentage,
    })),
  };
}

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/** Numbers handed to the picker by another page: distinct, in range, at most a line. */
function requestedLine(raw: string | undefined): number[] {
  if (!raw) return [];
  const numbers = raw
    .split(/[\s,]+/)
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 47);
  return [...new Set(numbers)].slice(0, 6);
}

export default async function PickPage({ searchParams }: PageProps<'/pick'>) {
  const params = await searchParams;
  const data = pool();
  const bin = one(params.bin) === undefined ? undefined : Number(one(params.bin));

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Build a line</h1>
        <p className="text-sm text-muted">
          Pick six numbers however you like. Everything here describes what past draws
          looked like - every line is equally likely to win.
        </p>
      </header>

      <Picker
        pool={data}
        shapeOptions={shapeOptions()}
        latestDraw={latestDrawDate()}
        initialLine={requestedLine(one(params.numbers))}
        initialBin={Number.isInteger(bin) && bin! >= 0 && bin! <= data.maxBin ? bin : undefined}
      />
    </main>
  );
}
