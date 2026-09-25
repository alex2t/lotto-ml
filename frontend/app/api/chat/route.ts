/**
 * The chat panel's endpoint (chat.md 7). Public, like everything a player does, so it is not
 * in proxy.ts's matcher; spending is held by the limits in lib/chat/budget.ts instead.
 *
 * POST { question, pathname, search?, line?, history? } -> { answer, source, cached }
 * GET  ?pathname=/pick&method=shake&line=complete       -> { suggestions }
 */
import { NextResponse } from 'next/server';
import { reply, type ChatInput } from '@/lib/chat/answer';
import { MAX_BODY_BYTES, MAX_QUESTION_CHARS } from '@/lib/chat/budget';
import { routeOf } from '@/lib/chat/match';
import { METHOD_SUGGESTED, suggestionsFor } from '@/lib/chat/prepared';
import type { PickMethod } from '@/lib/pick/current-line';
import { InvalidLine } from '@/lib/scoring/line';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/** The body as text, or null once it passes `max` bytes - the rest is never read. */
async function readCapped(request: Request, max: number): Promise<string | null> {
  if (Number(request.headers.get('content-length') ?? 0) > max) return null;
  const reader = request.body!.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > max) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  return Buffer.concat(chunks).toString('utf8');
}

export async function POST(request: Request) {
  const raw = await readCapped(request, MAX_BODY_BYTES);
  if (raw === null) return NextResponse.json({ error: 'Body too large' }, { status: 413 });

  const body = JSON.parse(raw) as Partial<ChatInput>;
  const question = typeof body.question === 'string' ? body.question.trim() : '';
  if (!question) return NextResponse.json({ error: 'No question' }, { status: 400 });
  if (question.length > MAX_QUESTION_CHARS) {
    return NextResponse.json(
      { error: `A question is at most ${MAX_QUESTION_CHARS} characters` },
      { status: 400 },
    );
  }

  const clientKey = request.headers.get('x-forwarded-for')?.split(',')[0].trim() ?? 'local';
  try {
    const answer = await reply(
      {
        question,
        pathname: typeof body.pathname === 'string' ? body.pathname : '/',
        search: typeof body.search === 'string' ? body.search : undefined,
        line: body.line,
        method: typeof body.method === 'string' ? body.method : undefined,
        history: Array.isArray(body.history) ? body.history : undefined,
      },
      { apiKey: process.env.OPENROUTER_API_KEY || undefined, clientKey },
    );
    return NextResponse.json(answer);
  } catch (error) {
    if (error instanceof InvalidLine) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    throw error;
  }
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const method = params.get('method');
  const known =
    method && Object.hasOwn(METHOD_SUGGESTED, method) ? (method as PickMethod) : undefined;
  return NextResponse.json({
    suggestions: suggestionsFor(
      routeOf(params.get('pathname') ?? '/'),
      known,
      params.get('line') === 'complete',
    ),
  });
}
