import Link from 'next/link';
import { latest } from '@/lib/data/draws';
import { freshness, nextDrawDate } from '@/lib/data/schedule';

export const dynamic = 'force-dynamic';

/**
 * A holding page for Phase 3: it proves the data layer reads the mounted artifacts.
 * The real home page is built in Phase 4 (nextStep/web.md section 4.1).
 */
export default function Home() {
  const draw = latest();
  const state = freshness();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 p-6">
      <h1 className="text-3xl font-semibold">Irish Lotto</h1>
      <section className="flex flex-col gap-2">
        <h2 className="text-sm uppercase tracking-wide text-neutral-500">
          Latest draw
        </h2>
        <p className="text-lg">
          {draw.draw_date}: {draw.main_numbers.join(' ')} (bonus {draw.bonus_number})
        </p>
        <p className="text-sm text-neutral-500">
          Next draw {nextDrawDate()} - data {state}
        </p>
      </section>
      <p className="text-sm text-neutral-500">
        Every line is equally likely to win.
      </p>
      <Link className="text-sm underline text-neutral-500" href="/login">
        Admin
      </Link>
    </main>
  );
}
