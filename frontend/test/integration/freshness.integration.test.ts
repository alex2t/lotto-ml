/**
 * The test the whole ingestion chain hangs on (nextStep/web.md 7.2, test 3).
 *
 * Appends a synthetic draw to a COPY of data/irish500.csv, runs drawpick.py against that
 * copy, points the data layer at the rebuilt artifacts and asserts the site shows the new
 * draw with no restart - which is what the mtime cache in artifacts.ts exists for. The real
 * data/ directory is never written to.
 *
 * Slow (drawpick.py takes about a minute) and needs Python, so it is not in the default run:
 *   npm run test:integration
 */
import { describe, expect, it } from 'vitest';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { clearArtifactCache } from '@/lib/data/artifacts';
import { latest } from '@/lib/data/draws';
import { latestDrawDate, nextDrawDate } from '@/lib/data/schedule';
import { useFixtures } from '../setup-fixtures';

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
  it('rebuilds from an appended CSV row and serves it without a restart', () => {
    const work = fs.mkdtempSync(path.join(os.tmpdir(), 'lotto-ingest-'));
    const workData = path.join(work, 'data');
    fs.cpSync(path.join(REPO, 'data'), workData, { recursive: true });

    // Read the schedule from the copy before the rebuild.
    useFixtures(workData);
    const before = latestDrawDate();
    const expected = nextDrawDate();

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
    const draw = latest();
    expect(draw.draw_date).toBe(expected);
    expect(draw.draw_date > before).toBe(true);
    expect(draw.main_numbers).toEqual([3, 11, 19, 27, 33, 41]);
    expect(draw.bonus_number).toBe(7);

    clearArtifactCache();
    fs.rmSync(work, { recursive: true, force: true });
  }, 600_000);
});
