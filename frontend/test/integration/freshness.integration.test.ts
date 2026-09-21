/**
 * The test the whole ingestion chain hangs on (nextStep/web.md 7.2, test 3).
 *
 * Appends a synthetic draw to a COPY of data/irish500.csv, runs drawpick.py against that
 * copy, points a running server's mount at it and asserts the HOMEPAGE shows the new draw
 * with no restart - which is what the mtime cache in artifacts.ts exists for. The real
 * data/ directory is never written to.
 *
 * It serves the page rather than reading the data layer, because 7.2 is about what someone
 * would see. The server is the standalone build, the same one the container runs.
 *
 * Slow (drawpick.py takes about a minute) and needs Python, so it is not in the default run:
 *   npm run test:integration
 */
import { afterAll, describe, expect, it } from 'vitest';
import { execFileSync, spawn, type ChildProcess } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { clearArtifactCache } from '@/lib/data/artifacts';
import { latestDrawDate, nextDrawDate } from '@/lib/data/schedule';
import { useFixtures } from '../setup-fixtures';

const PORT = Number(process.env.INTEGRATION_PORT ?? 3212);
let server: ChildProcess | null = null;
let serverLog: string[] = [];

afterAll(() => server?.kill());

/**
 * A request that survives a stale pooled socket.
 *
 * drawpick.py runs for about a minute between two requests to the same server, which is
 * long enough for the keep-alive connection Node pooled on the first one to be closed at
 * the other end. The retry is for that, not for a flaky server.
 */
async function get(url: string): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await fetch(url, { headers: { connection: 'close' } });
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(
    `${String(lastError)}
server said:
${serverLog.join('')}`,
  );
}

/** The standalone build, serving whatever is at `dataDir`. */
async function serve(dataDir: string): Promise<string> {
  const frontend = path.resolve(import.meta.dirname, '..', '..');
  if (!fs.existsSync(path.join(frontend, '.next', 'standalone'))) {
    throw new Error('No standalone build - run `npm run build` before this test');
  }

  server = spawn(
    process.execPath,
    [path.join(frontend, 'scripts', 'e2e-server.mjs')],
    {
      cwd: frontend,
      env: { ...process.env, DATA_DIR: dataDir, PORT: String(PORT), HOSTNAME: '127.0.0.1' },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  const log: string[] = [];
  server.stdout?.on('data', (d) => log.push(String(d)));
  server.stderr?.on('data', (d) => log.push(String(d)));
  server.on('exit', (code) => log.push(`server exited with ${code}`));
  serverLog = log;

  const base = `http://127.0.0.1:${PORT}`;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await get(`${base}/api/health`);
      if (response.ok) return base;
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error('the server never became healthy');
}

const REPO = path.resolve(import.meta.dirname, '..', '..', '..');
/** The repo's venv if there is one, else whatever `python` resolves to. */
function pythonExecutable(): string {
  if (process.env.PYTHON) return process.env.PYTHON;
  const candidates = [
    path.join(REPO, 'venv', 'Scripts', 'python.exe'),
    path.join(REPO, 'venv', 'bin', 'python'),
  ];
  return candidates.find((c) => fs.existsSync(c)) ?? 'python';
}

/** The draw after the newest one in the real CSV, as scrape_lotto.py would write it. */
function syntheticRow(nextDate: string): string {
  const [y, m, d] = nextDate.split('-').map(Number);
  const month = new Date(Date.UTC(y, m - 1, d)).toLocaleString('en-GB', {
    month: 'short',
    timeZone: 'UTC',
  });
  const numbers = [3, 11, 19, 27, 33, 41].map((n) => String(n).padStart(2, '0'));
  return `${String(d).padStart(2, '0')} ${month} ${y},${numbers.join(',')},07`;
}

describe('the site shows a newly ingested draw', () => {
  it('rebuilds from an appended CSV row and serves it without a restart', async () => {
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'lotto-ingest-'));
    const workData = path.join(work, 'data');
    fs.cpSync(path.join(REPO, 'data'), workData, { recursive: true });

    // Read the schedule from the copy before the rebuild.
    useFixtures(workData);
    const before = latestDrawDate();
    const expected = nextDrawDate();

    // Serving the OLD artifacts first, so the assertion afterwards is about a change.
    const base = await serve(workData);
    const firstHealth = await get(`${base}/api/health`).then((r) => r.json());
    expect(firstHealth.latestDraw).toBe(before);

    const csvPath = path.join(workData, 'irish500.csv');
    const lines = fs.readFileSync(csvPath, 'utf8').split('\n');
    // The CSV is newest-first, so a new draw goes immediately after the header.
    lines.splice(1, 0, syntheticRow(expected));
    fs.writeFileSync(csvPath, lines.join('\n'));

    execFileSync(pythonExecutable(), [path.join(REPO, 'drawpick.py')], {
      cwd: work,
      env: { ...process.env, PYTHONPATH: REPO, PYTHONIOENCODING: 'utf-8' },
      stdio: 'pipe',
    });

    // No restart and no cache clear: the mtime check must pick the rebuild up on its own.
    // Health first: it reads the same artifacts, so if it is fine the data is fine.
    const healthAfter = await get(`${base}/api/health`).then((r) => r.json());
    expect(healthAfter.latestDraw).toBe(expected);

    const response = await get(`${base}/`);
    expect(response.status, serverLog.join('')).toBe(200);
    const page = await response.text();
    const text = page.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

    expect(text).toContain(expected.slice(0, 4)); // the year of the new draw
    for (const n of [3, 11, 19, 27, 33, 41]) {
      expect(text).toMatch(new RegExp(`\\b0?${n}\\b`));
    }
    // And the page must no longer be showing the draw it had before.
    expect(before).not.toBe(expected);

    server?.kill();
    server = null;
    clearArtifactCache();
    fs.rmSync(work, { recursive: true, force: true });
  }, 600_000);
});
