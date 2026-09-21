/**
 * The admin session: one account, a signed httpOnly cookie, nothing else.
 *
 * NextAuth is machinery for a problem this does not have. The public site never checks for
 * a session, so a failure here can never take the site down.
 */
import { SignJWT, jwtVerify } from 'jose';

export const SESSION_COOKIE = 'lotto_admin';

/** Short-lived on purpose: the session exists to download a zip. */
export const SESSION_SECONDS = 2 * 60 * 60;

const SUBJECT = 'admin';

function secret(): Uint8Array {
  const value = process.env.SESSION_SECRET;
  if (!value || value.length < 32) {
    throw new Error('SESSION_SECRET must be set to at least 32 characters');
  }
  return new TextEncoder().encode(value);
}

export async function createSession(): Promise<string> {
  return new SignJWT({})
    .setProtectedHeader({ alg: 'HS256' })
    .setSubject(SUBJECT)
    .setIssuedAt()
    .setExpirationTime(`${SESSION_SECONDS}s`)
    .sign(secret());
}

/** True when the token is a valid, unexpired admin session. */
export async function verifySession(token: string | undefined): Promise<boolean> {
  if (!token) return false;
  try {
    const { payload } = await jwtVerify(token, secret());
    return payload.sub === SUBJECT;
  } catch {
    return false;
  }
}

export function cookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge: SESSION_SECONDS,
  };
}
