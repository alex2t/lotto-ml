import { notFound } from 'next/navigation';
import Link from 'next/link';
import { dossier } from '@/lib/data/dossier';
import { NUMBER_COUNT } from '@/lib/data/numbers';
import { Ball } from '@/components/ui/Ball';
import { Badge } from '@/components/ui/Badge';
import { shortDate } from '@/lib/format';

export const dynamic = 'force-dynamic';

function num(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}

function str(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

/** Plain words for a scored field, with the figure beside them - never a verdict. */
function bandWord(value: number | null, low: number, high: number): string {
  if (value === null) return 'not recorded';
  if (value <= low) return 'low';
  if (value >= high) return 'high';
  return 'moderate';
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
      <h2 className="text-sm uppercase tracking-widest text-muted">{title}</h2>
      {children}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-sm tabular-nums">{value}</dd>
    </div>
  );
}

export default async function NumberPage({ params }: PageProps<'/numbers/[n]'>) {
  const { n } = await params;
  const value = Number(n);
  if (!Number.isInteger(value) || value < 1 || value > NUMBER_COUNT) notFound();

  const d = dossier(value);
  const p = d.record.patterns;
  const bonus = d.record.bonus;
  const oddEven = d.record.oddEven;

  const trend = num(p.appearance_trend_raw);
  const volatility = num(p.appearance_volatility);
  const recentBonus = d.profile.wasRecentBonus;

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-wrap items-center gap-4">
        <Ball number={d.number} category={d.profile.category} size="lg" showCategory />
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold capitalize">
            {d.profile.category}
          </h1>
          <p className="text-sm text-muted">
            Last drawn {d.profile.lastSeen.replaceAll('/', '-')} - {d.gaps.currentDraws} draws
            ago. {d.profile.totalCount} appearances in the history.
          </p>
        </div>
        <Link href="/pick" className="ml-auto rounded-full bg-accent px-4 py-2 text-sm text-accent-foreground">
          Add {d.number} to a line
        </Link>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Recent activity">
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[5, 6, 10, 25].map((w) => (
              <Fact key={w} label={`last ${w} draws`} value={d.profile.recent[w]} />
            ))}
          </dl>
          <p className="text-sm text-muted">
            Freshness bin C{d.profile.freshnessBin}
            {d.profile.freshnessBin === 2 ? '+' : ''}, from its count over the last 5 draws.
          </p>
        </Section>

        <Section title="Gaps">
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Fact
              label="average"
              value={d.gaps.averageDraws === null ? '-' : `${d.gaps.averageDraws.toFixed(1)} draws`}
            />
            <Fact label="longest" value={d.gaps.longestDraws === null ? '-' : `${d.gaps.longestDraws} draws`} />
            <Fact label="current" value={`${d.gaps.currentDraws} draws`} />
            <Fact
              label="average days"
              value={num(p.avg_gap_days) === null ? '-' : `${num(p.avg_gap_days)!.toFixed(1)}`}
            />
          </dl>
        </Section>

        <Section title="Trend and volatility">
          <dl className="grid grid-cols-2 gap-3">
            <Fact
              label="trend"
              value={`${trend === null ? '-' : trend.toFixed(2)} (${
                p.trend_is_significant ? 'a significant change' : 'no significant change'
              })`}
            />
            <Fact
              label="volatility"
              value={`${volatility === null ? '-' : volatility.toFixed(2)} - ${bandWord(volatility, 0.8, 1.0)}`}
            />
            <Fact label="recent vs baseline" value={num(p.recent_vs_baseline)?.toFixed(2) ?? '-'} />
            <Fact
              label="regime shift"
              value={p.in_regime_shift ? 'in one now' : `${num(p.regime_shifts_detected) ?? 0} recorded`}
            />
          </dl>
        </Section>

        <Section title="As a bonus ball">
          <dl className="grid grid-cols-2 gap-3">
            <Fact label="times" value={num(bonus.bonus_appearances) ?? 0} />
            <Fact
              label="last"
              value={str(bonus.last_bonus_date) ? shortDate(str(bonus.last_bonus_date)!) : 'never'}
            />
            <Fact
              label="share of its appearances"
              value={`${((num(bonus.bonus_rate) ?? 0) * 100).toFixed(0)}%`}
            />
            <Fact
              label="in the recent window"
              value={recentBonus ? 'yes' : 'no'}
            />
          </dl>
        </Section>

        <Section title="Odd or even">
          <p className="text-sm">
            {d.number % 2 === 1 ? 'An odd number.' : 'An even number.'} It appears in{' '}
            {((num(oddEven.affinity_score) ?? 0) * 100).toFixed(0)}% of the draws it is in
            that are odd-heavy, against{' '}
            {((num(oddEven.chance_affinity_score) ?? 0) * 100).toFixed(0)}% expected in a
            fair draw.
          </p>
          <p className="text-sm text-muted">
            {oddEven.statistically_validated
              ? 'The difference survives a fair-draw test.'
              : 'The difference does not survive a fair-draw test (F-38).'}
          </p>
        </Section>

        <Section title="Trigger series">
          {Object.keys(d.series).length === 0 ? (
            <p className="text-sm text-muted">No series recorded.</p>
          ) : (
            <pre className="overflow-x-auto text-xs text-muted">
              {JSON.stringify(d.series, null, 2).slice(0, 1200)}
            </pre>
          )}
        </Section>
      </div>

      <Section title={`Appearance history (${d.appearances.length})`}>
        <ul className="flex flex-wrap gap-2">
          {d.appearances.slice(0, 60).map((a) => (
            <li key={`${a.date}-${a.asBonus}`}>
              <Link href={`/explore?draw=${a.date}`}>
                <Badge tone={a.asBonus ? 'bonus' : (a.category as 'hot' | 'medium' | 'cold')}>
                  {shortDate(a.date)}
                  {a.asBonus ? ' (bonus)' : ''}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
        {d.appearances.length > 60 && (
          <p className="text-sm text-muted">Showing the 60 most recent.</p>
        )}
      </Section>
    </main>
  );
}
