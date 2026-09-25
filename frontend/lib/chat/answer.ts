/**
 * One question through the four layers of chat.md 3, in order: prepared, data, cache, model.
 *
 * Most questions never reach the model. When one does it passes the limits of chat.md 5 and
 * the wording guard of chat.md 6 first. A missing key, a spent budget, a rate limit or a
 * failed call all answer with a sentence rather than throw - the chat panel must never be
 * able to take the site down.
 */
import { bannedIn, guardedReply } from './guard';
import { budgetLeft, modelRateLimited, recordUsage } from './budget';
import { cacheKey, cachedAnswer, remember } from './cache';
import { pageContext, type PageInput } from './context';
import { matchIntent } from './intents';
import { matchPrepared } from './match';
import { ModelUnavailable, complete } from './openrouter';
import { HISTORY_TURNS, messages, type Turn } from './prompt';

/** Where an answer came from. The panel shows it; the tests assert on it. */
export type Source = 'prepared' | 'data' | 'cache' | 'model' | 'guarded' | 'unavailable';

export interface ChatReply {
  answer: string;
  source: Source;
  cached: boolean;
}

export interface ChatInput extends PageInput {
  question: string;
  history?: Turn[];
}

export interface ChatDeps {
  apiKey?: string;
  fetchFn?: typeof fetch;
  /** Who is asking, for the rate limit. */
  clientKey: string;
  now?: number;
}

const TRY_SUGGESTED = 'The suggested questions, and questions about a number, still work.';

export const NO_MODEL = `That one is beyond the prepared answers, and free-form answers are not switched on here. ${TRY_SUGGESTED}`;
export const BUDGET_SPENT = `Free-form answers are used up for today. ${TRY_SUGGESTED}`;
export const RATE_LIMITED = `That is a lot of questions in a short time - free-form answers are paused for a while. ${TRY_SUGGESTED}`;
export const MODEL_DOWN = `The panel cannot answer that one right now. ${TRY_SUGGESTED}`;

function unavailable(answer: string): ChatReply {
  return { answer, source: 'unavailable', cached: false };
}

export async function reply(input: ChatInput, deps: ChatDeps): Promise<ChatReply> {
  const page = pageContext(input);

  const prepared = matchPrepared(input.question, page.route);
  if (prepared?.figures) {
    return { answer: `${prepared.answer} ${prepared.figures()}`, source: 'data', cached: false };
  }
  if (prepared) return { answer: prepared.answer, source: 'prepared', cached: false };

  const data = matchIntent(input.question, page.focus);
  if (data) return { answer: data.answer, source: 'data', cached: false };

  const history = (input.history ?? []).slice(-HISTORY_TURNS);
  const key = cacheKey(page.route, input.question, page.sheet, history);
  const hit = cachedAnswer(key);
  if (hit) return { answer: hit, source: 'cache', cached: true };

  const now = deps.now ?? Date.now();
  if (!deps.apiKey) return unavailable(NO_MODEL);
  if (!budgetLeft(now)) return unavailable(BUDGET_SPENT);
  if (modelRateLimited(deps.clientKey, now)) return unavailable(RATE_LIMITED);

  // The log chat.md 10 step 5 reads: every question the model answers twice belongs in layer 0.
  console.info(`[chat] model question on ${page.route}: ${input.question}`);
  try {
    const { text, usage } = await complete(
      messages(input.question, page.sheet, history),
      deps.apiKey,
      deps.fetchFn,
    );
    recordUsage(usage, now);
    const banned = bannedIn(text);
    if (banned.length) {
      console.warn(`[chat] answer blocked for ${banned.join(', ')}: ${text}`);
      return { answer: guardedReply(page.sheet), source: 'guarded', cached: false };
    }
    remember(key, text);
    return { answer: text, source: 'model', cached: false };
  } catch (error) {
    if (!(error instanceof ModelUnavailable)) throw error;
    console.warn(`[chat] model unavailable: ${error.message}`);
    return unavailable(MODEL_DOWN);
  }
}
