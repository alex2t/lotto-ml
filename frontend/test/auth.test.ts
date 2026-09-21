import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { hashSync } from 'bcryptjs';
import { checkCredentials } from '@/lib/auth/credentials';
import { MAX_ATTEMPTS, WINDOW_MS, resetAttempts, tooManyAttempts } from '@/lib/auth/rate-limit';
import {
  SESSION_SECONDS,
  cookieOptions,
  createSession,
  verifySession,
} from '@/lib/auth/session';

const SECRET = 'a'.repeat(32);

describe('session', () => {
  beforeEach(() => {
    process.env.SESSION_SECRET = SECRET;
  });

  it('round-trips a session it signed', async () => {
    expect(await verifySession(await createSession())).toBe(true);
  });

  it('rejects a missing, malformed or foreign token', async () => {
    const token = await createSession();
    expect(await verifySession(undefined)).toBe(false);
    expect(await verifySession('not-a-token')).toBe(false);
    process.env.SESSION_SECRET = 'b'.repeat(32);
    expect(await verifySession(token)).toBe(false);
  });

  it('refuses to run without a long enough secret', async () => {
    process.env.SESSION_SECRET = 'short';
    await expect(createSession()).rejects.toThrowError(/SESSION_SECRET/);
  });

  it('sets an httpOnly, sameSite cookie that expires', () => {
    const options = cookieOptions();
    expect(options.httpOnly).toBe(true);
    expect(options.sameSite).toBe('lax');
    expect(options.maxAge).toBe(SESSION_SECONDS);
  });
});

describe('credentials', () => {
  beforeEach(() => {
    process.env.ADMIN_USERNAME = 'owner';
    process.env.ADMIN_PASSWORD_HASH = hashSync('correct horse', 4);
  });

  it('accepts the one account', async () => {
    expect(await checkCredentials('owner', 'correct horse')).toBe(true);
  });

  it('rejects a wrong password or a wrong username', async () => {
    expect(await checkCredentials('owner', 'wrong')).toBe(false);
    expect(await checkCredentials('someone', 'correct horse')).toBe(false);
  });

  it('throws when the account is not configured', async () => {
    delete process.env.ADMIN_PASSWORD_HASH;
    await expect(checkCredentials('owner', 'correct horse')).rejects.toThrowError(
      /ADMIN_PASSWORD_HASH/,
    );
  });
});

describe('rate limit', () => {
  afterEach(() => resetAttempts());

  it('allows MAX_ATTEMPTS then blocks', () => {
    for (let i = 0; i < MAX_ATTEMPTS; i += 1) {
      expect(tooManyAttempts('1.2.3.4')).toBe(false);
    }
    expect(tooManyAttempts('1.2.3.4')).toBe(true);
  });

  it('counts each caller separately', () => {
    for (let i = 0; i <= MAX_ATTEMPTS; i += 1) tooManyAttempts('1.2.3.4');
    expect(tooManyAttempts('5.6.7.8')).toBe(false);
  });

  it('forgets attempts older than the window', () => {
    const start = Date.now();
    for (let i = 0; i <= MAX_ATTEMPTS; i += 1) tooManyAttempts('1.2.3.4', start);
    expect(tooManyAttempts('1.2.3.4', start + WINDOW_MS + 1)).toBe(false);
  });
});
