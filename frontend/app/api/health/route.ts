/**
 * Is the site up, and can it see the artifacts?
 *
 * Caddy polls this to decide whether to send traffic here. A process that is listening but
 * cannot read data/ - an unmounted volume, a permissions mistake on the VPS (F-45) - would
 * answer every page with an error, so the check reads the one artifact every page needs.
 */
import { NextResponse } from 'next/server';
import { latestDrawDate } from '@/lib/data/schedule';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    return NextResponse.json({ status: 'ok', latestDraw: latestDrawDate() });
  } catch (error) {
    return NextResponse.json(
      { status: 'no data', error: (error as Error).message },
      { status: 503 },
    );
  }
}
