import { beforeEach, describe, expect, it } from 'vitest';
import AdmZip from 'adm-zip';
import { NextRequest } from 'next/server';
import { GET as download } from '@/app/api/download/data/route';
import { GET as draws } from '@/app/api/draws/route';
import { GET as distributions } from '@/app/api/distributions/route';
import { GET as numbers } from '@/app/api/numbers/route';
import { GET as schedule } from '@/app/api/schedule/route';
import { POST as login } from '@/app/api/login/route';
import { proxy } from '@/proxy';
import { SESSION_COOKIE, createSession } from '@/lib/auth/session';
import { resetAttempts } from '@/lib/auth/rate-limit';
import { hashSync } from 'bcryptjs';
import { useFixtures } from './setup-fixtures';

const SECRET = 'a'.repeat(32);

function request(url: string): Request {
  return new Request(`http://localhost${url}`);
}

describe('public API routes', () => {
  beforeEach(() => useFixtures());

  it('/api/draws returns a page, not the whole history', async () => {
    const body = await (await draws(request('/api/draws?limit=3'))).json();
    expect(body.draws).toHaveLength(3);
    expect(body.total).toBeGreaterThan(3);
  });

  it('/api/draws?number= returns that number s appearances', async () => {
    const body = await (await draws(request('/api/draws?number=7'))).json();
    expect(body.number).toBe(7);
    for (const a of body.appearances) {
      expect(
        a.draw.main_numbers.includes(7) || a.draw.bonus_number === 7,
      ).toBe(true);
    }
  });

  it('/api/numbers returns 47 summaries, or one dossier', async () => {
    const all = await (await numbers(request('/api/numbers'))).json();
    expect(all.numbers).toHaveLength(47);
    const one = await (await numbers(request('/api/numbers?number=12'))).json();
    expect(one.number).toBe(12);
  });

  it('/api/distributions returns every distribution the picker compares against', async () => {
    const body = await (await distributions()).json();
    for (const key of [
      'oddEven',
      'sums',
      'spread',
      'highNumbers',
      'freshnessPatterns',
      'hmc',
    ]) {
      expect(body).toHaveProperty(key);
    }
  });

  it('/api/schedule reports the latest draw, the next one and the freshness', async () => {
    const body = await (await schedule()).json();
    expect(body.latestDraw.main_numbers).toHaveLength(6);
    expect(body.nextDrawDate > body.latestDrawDate).toBe(true);
    expect(['current', 'waiting', 'stale']).toContain(body.freshness);
  });
});

describe('admin', () => {
  beforeEach(() => {
    useFixtures();
    resetAttempts();
    process.env.SESSION_SECRET = SECRET;
    process.env.ADMIN_USERNAME = 'owner';
    process.env.ADMIN_PASSWORD_HASH = hashSync('correct horse', 4);
  });

  function loginRequest(body: unknown): Request {
    return new Request('http://localhost/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  it('the login route sets an httpOnly session cookie on success', async () => {
    const response = await login(
      loginRequest({ username: 'owner', password: 'correct horse' }),
    );
    expect(response.status).toBe(200);
    const cookie = response.cookies.get(SESSION_COOKIE);
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.value).toBeTruthy();
  });

  it('the login route rejects bad credentials with no cookie', async () => {
    const response = await login(loginRequest({ username: 'owner', password: 'no' }));
    expect(response.status).toBe(401);
    expect(response.cookies.get(SESSION_COOKIE)).toBeUndefined();
  });

  it('the proxy returns 401 to the download route when logged out', async () => {
    const response = await proxy(
      new NextRequest('http://localhost/api/download/data'),
    );
    expect(response.status).toBe(401);
  });

  it('the proxy lets a valid session through', async () => {
    const req = new NextRequest('http://localhost/api/download/data');
    req.cookies.set(SESSION_COOKIE, await createSession());
    const response = await proxy(req);
    expect(response.status).toBe(200);
  });

  it('the download streams a zip holding the artifacts and the CSV', async () => {
    const response = await download();
    expect(response.headers.get('Content-Type')).toBe('application/zip');
    expect(response.headers.get('Content-Disposition')).toMatch(
      /lotto-data-\d{4}-\d{2}-\d{2}\.zip/,
    );

    const zip = new AdmZip(Buffer.from(await response.arrayBuffer()));
    const names = zip.getEntries().map((e) => e.entryName);
    expect(names).toContain('irish500.csv');
    expect(names).toContain('lotto_draw_history.json');
    expect(names).toContain('lotto_trigger_periods.json');
  });
});
