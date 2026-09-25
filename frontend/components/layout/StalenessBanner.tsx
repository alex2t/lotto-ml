import { AlertCircle } from 'lucide-react';
import type { Staleness } from '@/lib/data/staleness';
import { longDate } from '@/lib/format';

/**
 * Shown only when the artifacts have not caught up with a draw that has taken place.
 * Styled for the home page's navy and gold palette (`.home-hero`), where it is rendered.
 */
export function StalenessBanner({ staleness }: { staleness: Staleness }) {
  if (staleness.state === 'current') return null;

  const missing = staleness.missing;
  const lead =
    staleness.state === 'waiting'
      ? `${longDate(staleness.nextDraw)}'s draw is not in yet - the site is waiting for the latest result.`
      : `${missing === 1 ? 'One draw is' : `${missing} draws are`} not in yet - the site is waiting for the latest result.`;

  return (
    <div
      role="status"
      className="home-banner mx-auto flex w-full max-w-2xl items-start gap-3 rounded-xl border border-gold/35 px-4 py-3 text-sm text-foreground sm:px-5"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-gold" aria-hidden />
      <p>
        {lead} Showing {longDate(staleness.showing)}.
      </p>
    </div>
  );
}
