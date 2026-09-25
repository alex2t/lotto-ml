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
    <main className="home-hero">
      <div className="mx-auto flex min-h-[calc(100svh-8rem)] max-w-5xl flex-col justify-center gap-8 px-4 py-12 sm:gap-10 sm:px-6 sm:py-16 lg:py-24">
        <StalenessBanner staleness={state} />

        <p className="text-center text-sm font-light tracking-wide text-muted sm:text-base">
          The lottery is random. Looking for logic is human.
        </p>

        <section className="flex flex-col items-center gap-6 text-center">
          <h1 className="text-sm uppercase tracking-widest text-gold">
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

        <section className="flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
          <Link
            href="/pick"
            className="rounded-full bg-gold px-8 py-3 text-center text-sm font-semibold text-gold-foreground shadow-[0_0_0_1px_rgb(255_236_190/0.55),0_0_28px_rgb(233_196_106/0.45)] transition hover:bg-gold-bright hover:shadow-[0_0_0_1px_rgb(255_236_190/0.8),0_0_36px_rgb(233_196_106/0.6)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold"
          >
            Build my line
          </Link>
          <Link
            href="/explore"
            className="rounded-full border border-foreground/60 bg-navy/40 px-8 py-3 text-center text-sm font-medium backdrop-blur-sm transition hover:border-gold hover:text-gold focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gold"
          >
            Explore the draws
          </Link>
        </section>
      </div>
    </main>
  );
}
