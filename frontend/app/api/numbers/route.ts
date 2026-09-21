/** The 47 per-number records: all summaries, or one number's full dossier. */
import { NextResponse } from 'next/server';
import { allSummaries, byCategory, record } from '@/lib/data/numbers';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const number = new URL(request.url).searchParams.get('number');
  if (number !== null) return NextResponse.json(record(Number(number)));
  return NextResponse.json({ numbers: allSummaries(), byCategory: byCategory() });
}
