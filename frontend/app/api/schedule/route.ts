/** The latest draw, the next one, and whether the artifacts have caught up. */
import { NextResponse } from 'next/server';
import { latest } from '@/lib/data/draws';
import { freshness, latestDrawDate, nextDrawDate } from '@/lib/data/schedule';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  const draw = latest();
  return NextResponse.json({
    latestDrawDate: latestDrawDate(),
    nextDrawDate: nextDrawDate(),
    freshness: freshness(),
    latestDraw: {
      draw_date: draw.draw_date,
      main_numbers: draw.main_numbers,
      bonus_number: draw.bonus_number,
    },
  });
}
