import { describe, expect, it, beforeEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import ADVICE from '@/lib/advice.json';
import { EQUAL_CHANCE, describeLine } from '@/lib/scoring/line';
import { useFixtures } from './setup-fixtures';

/**
 * The site describes how typical a line looks, never how likely it is to win.
 *
 * This is the source half of the guard that replaces tests/test_site_wording.py (web.md
 * 7.4): the ADVICE list moves across verbatim and is checked against every source file, so
 * a banned word is caught before it can render. The rendered half is test/e2e/.
 *
 * The list is lib/advice.json, the one copy the chat panel's system prompt and its runtime
 * guard read too (chat.md 6). It is JSON so it is not itself a scanned source.
 */
const ROOT = path.resolve(import.meta.dirname, '..');
const SCANNED = ['app', 'components', 'lib'];

/**
 * What a source file could put in front of someone: comments stripped, because a comment is
 * not rendered, and JSX tag names stripped, because `<strong>` is markup rather than a word
 * the site says. Attribute values stay - a title or an aria-label is read by someone.
 */
function renderable(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/.*$/gm, '$1 ')
    .replace(/<\/?[A-Za-z][A-Za-z0-9.]*/g, ' ');
}

function sources(): string[] {
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (/\.(ts|tsx)$/.test(entry.name)) files.push(full);
    }
  };
  for (const dir of SCANNED) walk(path.join(ROOT, dir));
  return files;
}

describe('the site never advises', () => {
  it('has sources to scan', () => {
    expect(sources().length).toBeGreaterThan(15);
  });

  it('scans the chat panel s prepared answers and its system prompt', () => {
    const scanned = sources().map((f) => path.relative(ROOT, f).replaceAll('\\', '/'));
    expect(scanned).toContain('lib/chat/prepared.ts');
    expect(scanned).toContain('lib/chat/prompt.ts');
  });

  it.each(ADVICE)('no source says %s', (phrase) => {
    const offenders = sources().filter((file) =>
      renderable(fs.readFileSync(file, 'utf8')).toLowerCase().includes(phrase),
    );
    expect(offenders.map((f) => path.relative(ROOT, f))).toEqual([]);
  });
});

describe('the equal-chance sentence', () => {
  beforeEach(() => useFixtures());

  it('is the one from the Streamlit test, verbatim', () => {
    expect(EQUAL_CHANCE.toLowerCase()).toContain('equally likely to win');
  });

  it('comes back with every verdict, whatever the line', () => {
    for (const line of [
      [1, 2, 3, 4, 5, 6],
      [5, 12, 23, 31, 38, 44],
      [42, 43, 44, 45, 46, 47],
      [1, 3, 5, 7, 9, 11],
    ]) {
      expect(describeLine(line).equalChance).toBe(EQUAL_CHANCE);
    }
  });

  it('is in the footer of every page, so it cannot be missed', () => {
    const footer = fs.readFileSync(
      path.join(ROOT, 'components', 'layout', 'Footer.tsx'),
      'utf8',
    );
    expect(footer.toLowerCase()).toContain('equally likely to win');
  });
});
