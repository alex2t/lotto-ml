/**
 * The one place the site calls out to a model: openai/gpt-oss-120b through OpenRouter,
 * pinned to Cerebras (chat.md 4, the /cerebras skill).
 *
 * Server-side only - the key never reaches the browser. The panel does not stream, so the
 * whole answer can be scanned before any of it is shown. Any failure - a 429 or 5xx, a
 * timeout, another provider - becomes ModelUnavailable and is answered, never retried: a
 * retry loop on a public endpoint is how one bad minute becomes a bill.
 */
import type { Usage } from './budget';
import type { Message } from './prompt';

const URL = 'https://openrouter.ai/api/v1/chat/completions';
export const MODEL = 'openai/gpt-oss-120b';
export const PROVIDER = { order: ['cerebras'], allow_fallbacks: false, require_parameters: true };
const TIMEOUT_MS = 15_000;

export class ModelUnavailable extends Error {}

export interface Completion {
  text: string;
  usage: Usage;
}

export async function complete(
  messages: Message[],
  apiKey: string,
  fetchFn: typeof fetch = fetch,
): Promise<Completion> {
  let res: Response;
  try {
    res = await fetchFn(URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: MODEL,
        messages,
        provider: PROVIDER,
        reasoning: { effort: 'low' },
        max_tokens: 300,
        temperature: 0.2,
        seed: 7,
      }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (error) {
    throw new ModelUnavailable(`request failed: ${(error as Error).message}`);
  }
  if (!res.ok) throw new ModelUnavailable(`status ${res.status}: ${await res.text()}`);

  const body = await res.json();
  // The proof the pin held. If this fires the routing is wrong - fix the request.
  if (body.provider !== 'Cerebras') throw new ModelUnavailable(`served by ${body.provider}, not Cerebras`);

  const choice = body.choices[0];
  const text = (choice.message.content ?? '').trim();
  // Reasoning used the whole max_tokens: treat as unavailable rather than raise the cap.
  if (!text) throw new ModelUnavailable(`empty answer, finish_reason ${choice.finish_reason}`);
  return { text, usage: body.usage };
}
