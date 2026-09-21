/**
 * A page of draws, newest first. The draw history artifact is 4.4 MB and is never sent whole.
 */
import { NextResponse } from 'next/server';
import { byNumber, page } from '@/lib/data/draws';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MAX_LIMIT = 100;

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;

  const number = params.get('number');
  if (number !== null) {
    const n = Number(number);
    return NextResponse.json({ number: n, appearances: byNumber(n) });
  }

  const offset = Math.max(0, Number(params.get('offset') ?? 0));
  const limit = Math.min(MAX_LIMIT, Math.max(1, Number(params.get('limit') ?? 25)));
  return NextResponse.json(page(offset, limit));
}
