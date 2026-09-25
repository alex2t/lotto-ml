import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

/**
 * Contrast, measured rather than assumed.
 *
 * web.md 5.4 asks for contrast checked in both themes. Choosing colours that look legible
 * is not that check - this one computes the WCAG 2.1 ratio for every pair the site actually
 * paints, in light and in dark, and fails if one falls short.
 *
 * The thresholds are WCAG AA: 4.5:1 for body text, 3:1 for large text and for the boundary
 * of a user interface component. A ball is a 36-80px circle with a number in it, so its
 * digits are large text; its border is a component boundary.
 */
const CSS = fs.readFileSync(
  path.join(import.meta.dirname, '..', 'app', 'globals.css'),
  'utf8',
);

const BODY_TEXT = 4.5;
const LARGE_TEXT = 3;

/** The custom properties declared in one `:root` block. */
function tokens(selector: string): Record<string, string> {
  const start = CSS.indexOf(selector);
  if (start === -1) throw new Error(`No ${selector} block in globals.css`);
  const block = CSS.slice(start, CSS.indexOf('}', start));
  const found: Record<string, string> = {};
  for (const [, name, value] of block.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{3,8});/g)) {
    found[name] = value;
  }
  return found;
}

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const full =
    hex.length === 4
      ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
      : hex;
  const r = parseInt(full.slice(1, 3), 16);
  const g = parseInt(full.slice(3, 5), 16);
  const b = parseInt(full.slice(5, 7), 16);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function ratio(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

/** Every foreground/background pair the site paints, and what it is used for. */
const PAIRS: Array<{ fg: string; bg: string; least: number; what: string }> = [
  { fg: 'foreground', bg: 'background', least: BODY_TEXT, what: 'body text' },
  { fg: 'foreground', bg: 'surface', least: BODY_TEXT, what: 'text on a panel' },
  { fg: 'foreground', bg: 'surface-raised', least: BODY_TEXT, what: 'text on a raised panel' },
  { fg: 'muted', bg: 'background', least: BODY_TEXT, what: 'secondary text' },
  { fg: 'muted', bg: 'surface', least: BODY_TEXT, what: 'secondary text on a panel' },
  { fg: 'accent-foreground', bg: 'accent', least: BODY_TEXT, what: 'a primary button' },
  // The Shake the bag panel is tinted with the bonus soft colour.
  { fg: 'foreground', bg: 'bonus-soft', least: BODY_TEXT, what: 'text on the bag panel' },
  { fg: 'muted', bg: 'bonus-soft', least: BODY_TEXT, what: 'secondary text on the bag panel' },
  // A ball: large digits on its own tint, and its border against the page.
  { fg: 'hot', bg: 'hot-soft', least: LARGE_TEXT, what: 'a hot ball' },
  { fg: 'medium', bg: 'medium-soft', least: LARGE_TEXT, what: 'a medium ball' },
  { fg: 'cold', bg: 'cold-soft', least: LARGE_TEXT, what: 'a cold ball' },
  { fg: 'bonus', bg: 'bonus-soft', least: LARGE_TEXT, what: 'a bonus ball' },
  { fg: 'hot', bg: 'background', least: LARGE_TEXT, what: 'a hot ball border' },
  { fg: 'medium', bg: 'background', least: LARGE_TEXT, what: 'a medium ball border' },
  { fg: 'cold', bg: 'background', least: LARGE_TEXT, what: 'a cold ball border' },
  { fg: 'bonus', bg: 'background', least: LARGE_TEXT, what: 'a bonus ball border' },
  // The bars a distribution is drawn with, against the panel they sit on.
  { fg: 'cold', bg: 'surface', least: LARGE_TEXT, what: 'a chart bar' },
  { fg: 'accent', bg: 'surface', least: LARGE_TEXT, what: 'the highlighted bar' },
];

describe.each([
  ['light', ':root {'],
  ['dark', ":root[data-theme='dark']"],
])('%s theme', (_theme, selector) => {
  const palette = tokens(selector);

  it('declares every colour the pairs need', () => {
    for (const { fg, bg } of PAIRS) {
      expect(palette[fg], fg).toBeDefined();
      expect(palette[bg], bg).toBeDefined();
    }
  });

  it.each(PAIRS)('$what has enough contrast', ({ fg, bg, least }) => {
    const measured = ratio(palette[fg], palette[bg]);
    expect(
      measured,
      `${fg} on ${bg} is ${measured.toFixed(2)}:1, needs ${least}:1`,
    ).toBeGreaterThanOrEqual(least);
  });
});

describe('the measure itself', () => {
  it('agrees with the known extremes', () => {
    expect(ratio('#000000', '#ffffff')).toBeCloseTo(21, 1);
    expect(ratio('#ffffff', '#ffffff')).toBeCloseTo(1, 5);
  });
});
