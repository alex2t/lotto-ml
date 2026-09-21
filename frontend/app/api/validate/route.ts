/** Scores a line against the artifacts. The picker calls this, so page and API agree. */
import { NextResponse } from 'next/server';
import { InvalidLine, describeLine } from '@/lib/scoring/line';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const body = (await request.json()) as { line?: unknown };
  try {
    return NextResponse.json(describeLine(body.line));
  } catch (error) {
    if (error instanceof InvalidLine) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    throw error;
  }
}
