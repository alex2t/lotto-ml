import { NextResponse } from 'next/server';
import { checkCredentials } from '@/lib/auth/credentials';
import { tooManyAttempts } from '@/lib/auth/rate-limit';
import { SESSION_COOKIE, cookieOptions, createSession } from '@/lib/auth/session';

export const runtime = 'nodejs';

export async function POST(request: Request) {
  const clientKey =
    request.headers.get('x-forwarded-for')?.split(',')[0].trim() ?? 'local';
  if (tooManyAttempts(clientKey)) {
    return NextResponse.json({ error: 'Too many attempts' }, { status: 429 });
  }

  const body = (await request.json()) as { username?: string; password?: string };
  if (!body.username || !body.password) {
    return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
  }

  if (!(await checkCredentials(body.username, body.password))) {
    return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, await createSession(), cookieOptions());
  return response;
}
