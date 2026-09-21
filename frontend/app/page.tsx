import Link from 'next/link';
import { allDraws, latest } from '@/lib/data/draws';
import { staleness } from '@/lib/data/staleness';
import { DRAW_HOUR } from '@/lib/data/schedule';
import { longDate } from '@/lib/format';
import { DrawBalls } from '@/components/ui/DrawBalls';
import { StalenessBanner } from '@/components/layout/StalenessBanner';

export const dynamic = 'force-dynamic';

export default function Home() {
  const draws = allDraws();
  const draw = latest();
  const state = staleness();

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-10">
      <StalenessBanner staleness={state} />

      <section className="flex flex-col items-center gap-6 text-center">
        <h1 className="text-sm uppercase tracking-widest text-muted">
          Latest draw - {longDate(draw.draw_date)}
        </h1>
        <DrawBalls draw={draw} size="lg" stagger />
        <p className="text-sm text-muted">
          Next draw: {longDate(state.nextDraw)}, {DRAW_HOUR}:00
        </p>
      </section>

      <p className="text-center text-sm text-muted">
        {draws.length} draws on file, back to {longDate(draws[0].draw_date)}.
      </p>

      <section className="flex flex-wrap justify-center gap-3">
        <Link
          href="/pick"
          className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-accent-foreground"
        >
          Build my line
        </Link>
        <Link
          href="/explore"
          className="rounded-full border border-border px-6 py-3 text-sm font-medium"
        >
          Explore the draws
        </Link>
      </section>
    </main>
  );
}
