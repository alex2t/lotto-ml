/**
 * What stops a public endpoint running up a bill (chat.md 5): a daily token budget counted
 * from the usage OpenRouter returns, and a per-client rate limit. Both apply to the model
 * layer only - a visitor over either still gets the prepared and data answers.
 *
 * The first limit, the credit cap on the OpenRouter key, lives at OpenRouter and is the only
 * one that holds if this code is wrong.
 */
import { limiter } from '@/lib/auth/rate-limit';

/**
 * Set low while the panel is new (chat.md 10, step 3): at the Cerebras endpoint's prices
 * this is about $0.25 a day, and far more than the site uses legitimately.
 */
export const DAILY_INPUT_TOKENS = 500_000;
export const DAILY_OUTPUT_TOKENS = 100_000;

/** A body over this is refused unread; a question over this is refused before any layer. */
export const MAX_BODY_BYTES = 8 * 1024;
export const MAX_QUESTION_CHARS = 500;

export const PER_MINUTE = 5;
export const PER_HOUR = 20;

export interface Usage {
  prompt_tokens: number;
  completion_tokens: number;
}

let day = '';
let spent = { input: 0, output: 0 };

function rollOver(now: number): void {
  const today = new Date(now).toISOString().slice(0, 10);
  if (today !== day) {
    day = today;
    spent = { input: 0, output: 0 };
  }
}

/** Whether today's budget still has room for a model call. */
export function budgetLeft(now = Date.now()): boolean {
  rollOver(now);
  return spent.input < DAILY_INPUT_TOKENS && spent.output < DAILY_OUTPUT_TOKENS;
}

export function recordUsage(usage: Usage, now = Date.now()): void {
  rollOver(now);
  spent.input += usage.prompt_tokens;
  spent.output += usage.completion_tokens;
}

const perMinute = limiter(60_000, PER_MINUTE);
const perHour = limiter(60 * 60_000, PER_HOUR);

/** Records a model question from a client and reports whether it is over either limit. */
export function modelRateLimited(clientKey: string, now = Date.now()): boolean {
  const minute = perMinute.hit(clientKey, now);
  const hour = perHour.hit(clientKey, now);
  return minute || hour;
}

/** Tests start each case with an untouched budget and no recorded questions. */
export function resetBudget(): void {
  day = '';
  spent = { input: 0, output: 0 };
  perMinute.reset();
  perHour.reset();
}
