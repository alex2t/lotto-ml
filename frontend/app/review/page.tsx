import { cookies } from 'next/headers';
import Link from 'next/link';
import { Ball } from '@/components/ui/Ball';
import { Badge } from '@/components/ui/Badge';
import { ShapeCard } from '@/components/pick/ShapeCard';
import { latest } from '@/lib/data/draws';
import { toRow } from '@/lib/data/explore';
import { readPicks } from '@/lib/data/picks';
import { describeLine } from '@/lib/scoring/line';
import { SESSION_COOKIE, verifySession } from '@/lib/auth/session';
import { longDate } from '@/lib/format';
import type { Category } from '@/lib/data/types';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'The last draw - Irish Lotto',
  description: 'How the latest draw looked next to the draws before it.',
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
      <h2 className="text-sm uppercase tracking-widest text-muted">{title}</h2>
      {children}
    </section>
  );
}

async function isAdmin(): Promise<boolean> {
  const store = await cookies();
  return verifySession(store.get(SESSION_COOKIE)?.value);
}

/** The owner's half: how the generated lines did. Absent on the VPS, and says so. */
async function PicksReview({ drawn }: { drawn: number[] }) {
  if (!(await isAdmin())) return null;

  const picks = readPicks();
  if (!picks) {
    return (
      <Section title="Generated lines (admin)">
        <p className="text-sm text-muted">
          lottery_picks.txt is not on this machine. It is written by quickpick.py on the
          owner&apos;s PC, which is the only place models are trained.
        </p>
      </Section>
    );
  }

  const drawnSet = new Set(drawn);

  return (
    <Section title="Generated lines (admin)">
      <p className="text-sm text-muted">Generated {picks.generated ?? 'at an unknown time'}.</p>
      <ul className="flex flex-col gap-2">
        {picks.picks.map((pick) => {
          const hits = pick.main.filter((n) => drawnSet.has(n));
          return (
            <li key={pick.line} className="flex flex-wrap items-center gap-3 text-sm">
              <span className="w-56 truncate text-muted">{pick.model}</span>
              <span className="flex flex-wrap gap-1">
                {pick.main.map((n) => (
                  <Ball
                    key={n}
                    number={n}
                    size="sm"
                    className={drawnSet.has(n) ? 'ring-2 ring-accent' : 'opacity-60'}
                  />
                ))}
              </span>
              <Badge>{hits.length} matched</Badge>
            </li>
          );
        })}
      </ul>
      {picks.wheelLines.length > 0 && (
        <p className="text-sm text-muted">
          Plus {picks.wheelLines.length} wheel lines, which cover every 3-subset of the
          pool&apos;s top eight.
        </p>
      )}
    </Section>
  );
}

export default async function ReviewPage() {
  const draw = latest();
  const row = toRow(draw);
  const shape = describeLine(draw.main_numbers);

  const before = {
    hot: draw.categories_pre_draw.hot_numbers.length,
    medium: draw.categories_pre_draw.medium_numbers.length,
    cold: draw.categories_pre_draw.cold_numbers.length,
  };

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold">{longDate(draw.draw_date)}</h1>
        <div className="flex flex-wrap items-center gap-2">
          {row.main.map((n, i) => (
            <Ball key={n} number={n} category={row.categories[i] as Category} size="lg" showCategory />
          ))}
          <span className="px-1 text-muted" aria-hidden>
            +
          </span>
          <Ball number={row.bonus} isBonus size="lg" />
        </div>
        <p className="text-sm text-muted">
          Each ball carries the category it held before the draw, not today&apos;s.
        </p>
      </header>

      <ShapeCard shape={shape} />

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="What the board looked like beforehand">
          <dl className="flex flex-wrap gap-4 text-sm">
            <span>
              <dt className="text-xs text-muted">hot</dt>
              <dd>{before.hot} numbers</dd>
            </span>
            <span>
              <dt className="text-xs text-muted">medium</dt>
              <dd>{before.medium} numbers</dd>
            </span>
            <span>
              <dt className="text-xs text-muted">cold</dt>
              <dd>{before.cold} numbers</dd>
            </span>
          </dl>
          <p className="text-sm text-muted">
            The draw took {row.hmc.split('-')[0]} hot, {row.hmc.split('-')[1]} medium and{' '}
            {row.hmc.split('-')[2]} cold.
          </p>
        </Section>

        <Section title="The bonus window it faced">
          <p className="text-xs text-muted">
            The 10 bonus balls drawn before this one (F-33).
          </p>
          <div className="flex flex-wrap gap-1">
            {draw.recent_bonus_numbers.map((n, i) => (
              <Badge key={`${n}-${i}`} tone="bonus">
                {n}
              </Badge>
            ))}
          </div>
        </Section>
      </div>

      <PicksReview drawn={draw.main_numbers} />

      <p className="text-sm text-muted">
        Want to build your own line? <Link href="/pick" className="underline">Pick</Link>.
      </p>
    </main>
  );
}
