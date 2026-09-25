import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import ADVICE from '@/lib/advice.json';
import {
  BUDGET_SPENT,
  MODEL_DOWN,
  NO_MODEL,
  RATE_LIMITED,
  reply,
  type ChatInput,
} from '@/lib/chat/answer';
import {
  DAILY_INPUT_TOKENS,
  DAILY_OUTPUT_TOKENS,
  MAX_BODY_BYTES,
  MAX_QUESTION_CHARS,
  PER_HOUR,
  PER_MINUTE,
  recordUsage,
  resetBudget,
} from '@/lib/chat/budget';
import { clearChatCache } from '@/lib/chat/cache';
import { pageContext } from '@/lib/chat/context';
import { MODEL, PROVIDER } from '@/lib/chat/openrouter';
import { LINE_QUESTION, METHOD_SUGGESTED, SUGGESTED } from '@/lib/chat/prepared';
import { SYSTEM_PROMPT } from '@/lib/chat/prompt';
import { GET, POST } from '@/app/api/chat/route';
import { dossier } from '@/lib/data/dossier';
import { describeLine } from '@/lib/scoring/line';
import { FIXTURE_DIR, useFixtures } from './setup-fixtures';

/** Layers 2 and 3, the four limits of chat.md 5 and the guard of chat.md 6. No network. */

/** A question none of the prepared or data answers takes. */
const OPEN = 'What stands out on this page?';
const KEY = 'test-key';
const NOON = Date.UTC(2026, 8, 24, 12);

type Body = Record<string, unknown>;

/** A stand-in for OpenRouter that records every request it receives. */
function fakeOpenRouter(content = 'Nothing on this page is out of the ordinary.', init: Partial<{
  status: number;
  provider: string;
  finish: string;
}> = {}) {
  const calls: Body[] = [];
  const fetchFn = vi.fn(async (_url: unknown, request?: RequestInit) => {
    calls.push(JSON.parse(request!.body as string));
    if (init.status) return new Response('upstream says no', { status: init.status });
    return Response.json({
      provider: init.provider ?? 'Cerebras',
      choices: [{ message: { content }, finish_reason: init.finish ?? 'stop' }],
      usage: { prompt_tokens: 1200, completion_tokens: 80 },
    });
  }) as unknown as typeof fetch;
  return { fetchFn, calls };
}

function ask(question: string, fetchFn: typeof fetch, extra: Partial<ChatInput> = {}, now = NOON) {
  return reply({ question, pathname: '/', ...extra }, { apiKey: KEY, fetchFn, clientKey: 'a', now });
}

beforeEach(() => {
  useFixtures();
  resetBudget();
  clearChatCache();
  delete process.env.OPENROUTER_API_KEY;
  vi.spyOn(console, 'info').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => vi.restoreAllMocks());

describe('layer 3 - the model', () => {
  it('answers what the other layers missed, with the pinned request of the cerebras skill', async () => {
    const { fetchFn, calls } = fakeOpenRouter();
    const answer = await ask(OPEN, fetchFn);
    expect(answer).toEqual({
      answer: 'Nothing on this page is out of the ordinary.',
      source: 'model',
      cached: false,
    });
    expect(calls).toHaveLength(1);
    const body = calls[0];
    expect(body.model).toBe(MODEL);
    expect(body.provider).toEqual({ order: ['cerebras'], allow_fallbacks: false, require_parameters: true });
    expect(body.provider).toEqual(PROVIDER);
    expect(body.max_tokens).toBe(300);
    expect(body.temperature).toBe(0.2);
    expect(body.reasoning).toEqual({ effort: 'low' });
    expect(body).not.toHaveProperty('stream');
  });

  it('sends the static system prompt first and the page facts with the question', async () => {
    const { fetchFn, calls } = fakeOpenRouter();
    await ask(OPEN, fetchFn, { pathname: '/numbers/12' });
    const sent = calls[0].messages as Array<{ role: string; content: string }>;
    expect(sent[0]).toEqual({ role: 'system', content: SYSTEM_PROMPT });
    const last = sent[sent.length - 1];
    expect(last.content).toContain(pageContext({ pathname: '/numbers/12' }).sheet);
    expect(last.content).toContain(`Question: ${OPEN}`);
  });

  it('tells the model every banned word, from the one list', () => {
    for (const phrase of ADVICE) expect(SYSTEM_PROMPT).toContain(phrase);
  });

  it('sends at most the previous two turns, not the transcript', async () => {
    const { fetchFn, calls } = fakeOpenRouter();
    const history = [1, 2, 3, 4].map((i) => ({ question: `q${i}`, answer: `a${i}` }));
    await ask(OPEN, fetchFn, { history });
    const sent = calls[0].messages as Array<{ content: string }>;
    expect(sent.map((m) => m.content).slice(1, -1)).toEqual(['q3', 'a3', 'q4', 'a4']);
  });

  it.each([429, 503])('a %s becomes a sentence after one call, never a retry', async (status) => {
    const { fetchFn } = fakeOpenRouter('', { status });
    expect(await ask(OPEN, fetchFn)).toEqual({ answer: MODEL_DOWN, source: 'unavailable', cached: false });
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it('refuses an answer served by any provider but Cerebras', async () => {
    const { fetchFn } = fakeOpenRouter('fine', { provider: 'DeepInfra' });
    expect((await ask(OPEN, fetchFn)).source).toBe('unavailable');
  });

  it('treats an answer eaten by reasoning as unavailable', async () => {
    const { fetchFn } = fakeOpenRouter('', { finish: 'length' });
    expect((await ask(OPEN, fetchFn)).answer).toBe(MODEL_DOWN);
  });

  it('turns a network failure into a sentence', async () => {
    const fetchFn = vi.fn(async () => {
      throw new TypeError('fetch failed');
    }) as unknown as typeof fetch;
    expect((await ask(OPEN, fetchFn)).answer).toBe(MODEL_DOWN);
  });
});

describe('the wording guard, at runtime', () => {
  it.each(ADVICE)('blocks a model answer containing "%s"', async (phrase) => {
    const { fetchFn } = fakeOpenRouter(`Well, that looks ${phrase} to me.`);
    const answer = await ask(OPEN, fetchFn, { pathname: '/numbers/12' });
    expect(answer.source).toBe('guarded');
    expect(answer.answer.toLowerCase()).not.toContain(phrase);
    expect(answer.answer).toContain(pageContext({ pathname: '/numbers/12' }).sheet);
  });

  it('never caches a blocked answer', async () => {
    const { fetchFn } = fakeOpenRouter('A strong pattern.');
    await ask(OPEN, fetchFn);
    await ask(OPEN, fetchFn);
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });
});

describe('layer 2 - the response cache', () => {
  it('answers the second asking without calling the model', async () => {
    const { fetchFn } = fakeOpenRouter();
    await ask(OPEN, fetchFn);
    const again = await ask('what stands out ON this page', fetchFn);
    expect(again).toMatchObject({ source: 'cache', cached: true });
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it('keeps answers for different pages apart', async () => {
    const { fetchFn } = fakeOpenRouter();
    await ask(OPEN, fetchFn, { pathname: '/numbers/12' });
    await ask(OPEN, fetchFn, { pathname: '/numbers/13' });
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it('drops an answer once drawpick.py rewrites an artifact', async () => {
    const copy = fs.mkdtempSync(path.join(os.tmpdir(), 'chat-cache-'));
    fs.cpSync(FIXTURE_DIR, copy, { recursive: true });
    useFixtures(copy);

    const { fetchFn } = fakeOpenRouter();
    await ask(OPEN, fetchFn);
    await ask(OPEN, fetchFn);
    expect(fetchFn).toHaveBeenCalledTimes(1);

    const later = new Date(Date.now() + 60_000);
    fs.utimesSync(path.join(copy, 'lotto_odds_results.json'), later, later);
    expect((await ask(OPEN, fetchFn)).source).toBe('model');
    expect(fetchFn).toHaveBeenCalledTimes(2);
    fs.rmSync(copy, { recursive: true });
  });
});

describe('the four limits of chat.md 5, each fired', () => {
  it('the daily input budget, once spent, stops the model call', async () => {
    const { fetchFn } = fakeOpenRouter();
    recordUsage({ prompt_tokens: DAILY_INPUT_TOKENS, completion_tokens: 0 }, NOON);
    expect(await ask(OPEN, fetchFn)).toMatchObject({ answer: BUDGET_SPENT, source: 'unavailable' });
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('the daily output budget does the same, and the next day starts afresh', async () => {
    const { fetchFn } = fakeOpenRouter();
    recordUsage({ prompt_tokens: 0, completion_tokens: DAILY_OUTPUT_TOKENS }, NOON);
    expect((await ask(OPEN, fetchFn)).answer).toBe(BUDGET_SPENT);
    expect((await ask(OPEN, fetchFn, {}, NOON + 24 * 3600_000)).source).toBe('model');
  });

  it('counts the usage OpenRouter reports against the budget', async () => {
    const { fetchFn } = fakeOpenRouter();
    recordUsage({ prompt_tokens: DAILY_INPUT_TOKENS - 1200, completion_tokens: 0 }, NOON);
    expect((await ask(OPEN, fetchFn)).source).toBe('model');
    expect((await ask('Anything else here?', fetchFn)).answer).toBe(BUDGET_SPENT);
  });

  it(`the rate limit refuses question ${PER_HOUR + 1} in an hour`, async () => {
    const { fetchFn } = fakeOpenRouter();
    const spacing = 2.5 * 60_000;
    for (let i = 0; i < PER_HOUR; i++) {
      const answer = await ask(`Open question ${'x'.repeat(i + 1)}`, fetchFn, {}, NOON + i * spacing);
      expect(answer.source).toBe('model');
    }
    const over = await ask('One question too many', fetchFn, {}, NOON + PER_HOUR * spacing);
    expect(over).toMatchObject({ answer: RATE_LIMITED, source: 'unavailable' });
    expect(fetchFn).toHaveBeenCalledTimes(PER_HOUR);
  });

  it(`the rate limit refuses question ${PER_MINUTE + 1} in a minute, but not the prepared answers`, async () => {
    const { fetchFn } = fakeOpenRouter();
    for (let i = 0; i < PER_MINUTE; i++) await ask(`Burst ${'y'.repeat(i + 1)}`, fetchFn, {}, NOON + i);
    expect((await ask('Burst over', fetchFn, {}, NOON + 10)).answer).toBe(RATE_LIMITED);
    expect((await ask('What is volatility?', fetchFn, {}, NOON + 11)).source).toBe('prepared');
  });

  function post(body: string, headers: Record<string, string> = {}) {
    return POST(
      new Request('http://localhost/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body,
      }),
    );
  }

  it(`a question over ${MAX_QUESTION_CHARS} characters is rejected`, async () => {
    const at = await post(JSON.stringify({ question: 'a'.repeat(MAX_QUESTION_CHARS), pathname: '/' }));
    expect(at.status).toBe(200);
    const over = await post(JSON.stringify({ question: 'a'.repeat(MAX_QUESTION_CHARS + 1), pathname: '/' }));
    expect(over.status).toBe(400);
  });

  it(`a body over ${MAX_BODY_BYTES} bytes is refused, declared or not`, async () => {
    const big = JSON.stringify({ question: 'hi', pathname: '/', pad: 'z'.repeat(MAX_BODY_BYTES) });
    expect((await post(big)).status).toBe(413);
    expect((await post('{}', { 'Content-Length': String(MAX_BODY_BYTES + 1) })).status).toBe(413);
  });
});

describe('without a key', () => {
  it('answers from the prepared and data layers, and says the rest is unavailable', async () => {
    const noKey = (question: string) =>
      reply({ question, pathname: '/' }, { clientKey: 'a', fetchFn: fakeOpenRouter().fetchFn });
    expect((await noKey('What is volatility?')).source).toBe('prepared');
    expect((await noKey('What is freshness?')).source).toBe('data');
    expect((await noKey('When is the next draw?')).source).toBe('data');
    expect(await noKey(OPEN)).toEqual({ answer: NO_MODEL, source: 'unavailable', cached: false });
  });

  it('the route works with no OPENROUTER_API_KEY set', async () => {
    const response = await POST(
      new Request('http://localhost/api/chat', {
        method: 'POST',
        body: JSON.stringify({ question: OPEN, pathname: '/explore', search: '?tab=statistics' }),
      }),
    );
    expect(await response.json()).toMatchObject({ source: 'unavailable', answer: NO_MODEL });
  });
});

describe('the route and the fact sheets', () => {
  it('GET returns the suggestions for the page', async () => {
    const response = await GET(new Request('http://localhost/api/chat?pathname=/numbers/7'));
    expect((await response.json()).suggestions).toEqual(SUGGESTED['/numbers']);
  });

  it('GET returns the picking method s questions on /pick, and ignores an unknown method', async () => {
    const get = async (query: string) =>
      (await (await GET(new Request(`http://localhost/api/chat?${query}`))).json()).suggestions;
    expect(await get('pathname=/pick&method=shake')).toEqual(METHOD_SUGGESTED.shake);
    expect((await get('pathname=/pick&method=shake&line=complete'))[0]).toBe(LINE_QUESTION);
    expect(await get('pathname=/pick&method=constructor')).toEqual(SUGGESTED['/pick']);
  });

  it('refuses a line that is not six numbers from 1 to 47', async () => {
    const response = await POST(
      new Request('http://localhost/api/chat', {
        method: 'POST',
        body: JSON.stringify({ question: 'Is my line typical?', pathname: '/pick', line: [1, 2, 99] }),
      }),
    );
    expect(response.status).toBe(400);
  });

  it('a number page s sheet holds the figures its dossier shows', () => {
    const d = dossier(12);
    const { sheet, focus } = pageContext({ pathname: '/numbers/12' });
    expect(focus.number).toBe(12);
    expect(sheet).toContain(`total appearances, bonus included: ${d.profile.totalCount}`);
    expect(sheet).toContain(`current gap: ${d.gaps.currentDraws} draws`);
  });

  it('the pick sheet holds the shape card s verdict and checks', () => {
    const line = [5, 12, 23, 31, 38, 44];
    const shape = describeLine(line);
    const { sheet } = pageContext({ pathname: '/pick', line });
    expect(sheet).toContain(`verdict: ${shape.verdict}`);
    for (const c of shape.checks) expect(sheet).toContain(c.comparison);
  });

  it('every destination builds a sheet', () => {
    for (const [pathname, search] of [
      ['/', ''],
      ['/pick', ''],
      ['/explore', '?tab=statistics'],
      ['/explore', '?tab=freshness'],
      ['/explore', '?tab=draws&contains=7'],
      ['/numbers', '?category=hot'],
      ['/review', ''],
    ]) {
      expect(pageContext({ pathname, search }).sheet, pathname + search).toMatch(/^- /);
    }
  });
});
