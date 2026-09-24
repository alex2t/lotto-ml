/**
 * Matching a question against the prepared answers (chat.md 3, layer 0).
 *
 * Deterministic and local: lower-case, strip punctuation, and look for an entry whose
 * pattern words all appear in the question. The longest matching pattern wins, and an entry
 * belonging to the current destination wins a tie - so "what does this table show?" gets
 * the draws table on /explore and the 47-number table on /numbers.
 */
import ADVICE from '@/lib/advice.json';
import { PREPARED, RATING_ID, type ChatRoute, type Prepared } from './prepared';

const ROUTES: ChatRoute[] = ['/pick', '/explore', '/numbers', '/review'];

/** The destination a pathname belongs to: /numbers/12 is /numbers. */
export function routeOf(pathname: string): ChatRoute {
  return ROUTES.find((r) => pathname === r || pathname.startsWith(`${r}/`)) ?? '/';
}

/** Lower-case, punctuation to spaces, whitespace collapsed. */
export function normalise(question: string): string {
  return question
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

/** A crude plural fold, applied to question and pattern alike: "draws" is "draw". */
function stem(word: string): string {
  return word.length > 3 && word.endsWith('s') ? word.slice(0, -1) : word;
}

function words(text: string): string[] {
  return normalise(text).split(' ').filter(Boolean).map(stem);
}

const ROUTE_WEIGHT = 0.5;

/** How well an entry matches, or 0 when none of its patterns is wholly in the question. */
function score(entry: Prepared, asked: Set<string>, route: ChatRoute): number {
  const best = Math.max(
    0,
    ...entry.patterns.map((p) => {
      const need = words(p);
      return need.every((w) => asked.has(w)) ? need.length : 0;
    }),
  );
  if (best === 0) return 0;
  return best + (entry.routes.includes(route) ? ROUTE_WEIGHT : 0);
}

/** The prepared entry that answers a question, or null when none does. */
export function matchPrepared(question: string, route: ChatRoute): Prepared | null {
  const text = normalise(question);
  // A question in the site's banned vocabulary is asking for a rating, whatever else it says.
  if (ADVICE.some((phrase) => text.includes(phrase))) {
    return PREPARED.find((e) => e.id === RATING_ID)!;
  }

  const asked = new Set(words(text));
  let winner: Prepared | null = null;
  let top = 0;
  for (const entry of PREPARED) {
    const s = score(entry, asked, route);
    if (s > top) {
      top = s;
      winner = entry;
    }
  }
  return winner;
}
