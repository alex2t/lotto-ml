/**
 * The runtime half of the wording guard (chat.md 6): every model answer is scanned against
 * the ADVICE list before any of it is shown, which is why the panel does not stream.
 *
 * The list is lib/advice.json, the same copy test/wording.test.ts scans the source with, so
 * the two cannot drift.
 */
import ADVICE from '@/lib/advice.json';

/** The banned phrases an answer contains; empty when it may be shown. */
export function bannedIn(answer: string): string[] {
  const text = answer.toLowerCase();
  return ADVICE.filter((phrase) => text.includes(phrase));
}

/** What the panel says instead of a blocked answer, followed by the page's own figures. */
export function guardedReply(sheet: string): string {
  return `I cannot phrase an answer to that one the way this site speaks. Here are the figures this page is showing:\n${sheet}`;
}
