import { beforeEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  ARTIFACTS,
  artifact,
  clearArtifactCache,
  readArtifact,
  requireKey,
} from '@/lib/data/artifacts';
import { useFixtures } from './setup-fixtures';

describe('artifacts', () => {
  beforeEach(() => useFixtures());

  it('reads every artifact the site uses', () => {
    for (const name of Object.keys(ARTIFACTS) as Array<keyof typeof ARTIFACTS>) {
      expect(artifact<object>(name)).toBeTypeOf('object');
    }
  });

  it('throws on a missing key rather than defaulting', () => {
    expect(() => requireKey({ a: 1 }, 'b', 'somewhere')).toThrowError(/Missing key 'b'/);
  });

  it('returns a present key, including a falsy one', () => {
    expect(requireKey({ a: 0 }, 'a', 'somewhere')).toBe(0);
  });

  it('re-reads a file whose mtime changed, without a restart', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lotto-artifacts-'));
    const file = 'probe.json';
    fs.writeFileSync(path.join(dir, file), JSON.stringify({ v: 1 }));
    process.env.DATA_DIR = dir;
    clearArtifactCache();

    expect(readArtifact<{ v: number }>(file).v).toBe(1);

    const later = Date.now() + 2000;
    fs.writeFileSync(path.join(dir, file), JSON.stringify({ v: 2 }));
    fs.utimesSync(path.join(dir, file), later / 1000, later / 1000);

    expect(readArtifact<{ v: number }>(file).v).toBe(2);
  });
});
