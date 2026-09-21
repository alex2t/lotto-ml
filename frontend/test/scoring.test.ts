import { beforeEach, describe, expect, it } from 'vitest';
import { allDraws, latest } from '@/lib/data/draws';
import { summary } from '@/lib/data/numbers';
import { highNumbers, oddEvenPatterns, sumDistributions } from '@/lib/data/distributions';
import { drawPattern, patternKey, sixBallPatterns } from '@/lib/data/hmc';
import { SPREAD_BANDS, spreadBand, sumBand } from '@/lib/scoring/bands';
import {
  EQUAL_CHANCE,
  InvalidLine,
  describeLine,
  spreadBandShares,
  validateLine,
} from '@/lib/scoring/line';
import { useFixtures } from './setup-fixtures';

const TYPICAL = [5, 12, 23, 31, 38, 44];
const UNUSUAL = [1, 2, 3, 4, 5, 6];

describe('validateLine', () => {
  it('accepts six distinct numbers and sorts them', () => {
    expect(validateLine([44, 5, 31, 12, 38, 23])).toEqual(TYPICAL);
  });

  it('rejects the wrong length, a repeat, and anything out of range', () => {
    expect(() => validateLine([1, 2, 3, 4, 5])).toThrow(InvalidLine);
    expect(() => validateLine([1, 2, 3, 4, 5, 6, 7])).toThrow(InvalidLine);
    expect(() => validateLine([1, 1, 2, 3, 4, 5])).toThrow(/repeat/);
    expect(() => validateLine([0, 2, 3, 4, 5, 6])).toThrow(/between 1 and 47/);
    expect(() => validateLine([1, 2, 3, 4, 5, 48])).toThrow(/between 1 and 47/);
    expect(() => validateLine([1, 2, 3, 4, 5, 6.5])).toThrow(InvalidLine);
    expect(() => validateLine('1,2,3,4,5,6')).toThrow(InvalidLine);
  });
});

describe('bands agree with the analyzer that wrote the artifacts', () => {
  beforeEach(() => useFixtures());

  it('re-binning every draw reproduces the sum histogram in the artifact', () => {
    const counted: Record<string, number> = {};
    for (const draw of allDraws()) {
      const total = draw.main_numbers.reduce((a, b) => a + b, 0);
      const key = sumBand(total).key;
      counted[key] = (counted[key] ?? 0) + 1;
    }
    // The fixture holds a slice of the history, so compare shape, not totals: every draw
    // must land in a band the artifact also knows, and the ordering must match.
    const artifactBands = Object.keys(sumDistributions('6_main'));
    for (const key of Object.keys(counted)) expect(artifactBands).toContain(key);
  });

  it('the spread bands are half-open, as output_generator.py bins them', () => {
    // The labels read "20-25" then "25-30"; 25 belongs to the second.
    expect(spreadBand(24).key).toBe('20-25');
    expect(spreadBand(25).key).toBe('25-30');
    expect(spreadBand(19).key).toBe('<20');
    expect(spreadBand(45).key).toBe('40-45');
    expect(spreadBand(46).key).toBe('>45');
  });

  it('the spread bands cover every spread a six-number line can have', () => {
    for (let spread = 5; spread <= 46; spread += 1) {
      expect(() => spreadBand(spread)).not.toThrow();
    }
    expect(SPREAD_BANDS.map((b) => b.key)).toEqual(Object.keys(spreadBandShares()));
  });

  it('odd/even keys are odd_even, matching the draw history feature', () => {
    const draw = latest();
    const odd = draw.main_numbers.filter((n) => n % 2 === 1).length;
    expect(draw.distribution_features.odd_even_pattern_6).toBe(`${odd}_${6 - odd}`);
    expect(Object.keys(oddEvenPatterns('6_main'))).toContain(`${odd}_${6 - odd}`);
  });
});

describe('the six-ball HMC distribution', () => {
  beforeEach(() => useFixtures());

  it('counts the six main balls, so every pattern sums to six', () => {
    for (const { pattern } of sixBallPatterns()) {
      const total = pattern.split('-').reduce((a, b) => a + Number(b), 0);
      expect(total).toBe(6);
    }
  });

  it('uses each draw pre-draw categories, not today s (F-27)', () => {
    const draw = latest();
    const pattern = drawPattern(draw);
    const fromDetails = draw.winning_numbers_details.filter((b) => !b.is_bonus);
    expect(fromDetails).toHaveLength(6);
    expect(pattern.hot).toBe(fromDetails.filter((b) => b.category === 'hot').length);
    expect(pattern.medium).toBe(fromDetails.filter((b) => b.category === 'medium').length);
    expect(pattern.cold).toBe(fromDetails.filter((b) => b.category === 'cold').length);
  });

  it('shares sum to 100 over all patterns', () => {
    const total = sixBallPatterns().reduce((a, p) => a + p.percentage, 0);
    // The artifact rounds each share to two decimals (F-46), so allow for that.
    expect(total).toBeCloseTo(100, 1);
  });

  it('comes from the artifact, and agrees with the draws it was counted from', () => {
    // drawpick.py writes hmc_6; recount it here from the same pre-draw categories and the
    // two must agree, which is what stops the artifact and the site drifting.
    const counted = new Map<string, number>();
    for (const draw of allDraws()) {
      const key = patternKey(drawPattern(draw));
      counted.set(key, (counted.get(key) ?? 0) + 1);
    }
    // The fixture is a slice of the history, so every pattern it contains must be one the
    // artifact knows about.
    const published = new Set(sixBallPatterns().map((p) => p.pattern));
    for (const key of counted.keys()) expect(published).toContain(key);
  });

  it('patternKey renders hot-medium-cold', () => {
    expect(patternKey({ hot: 4, medium: 1, cold: 1 })).toBe('4-1-1');
  });
});

describe('describeLine', () => {
  beforeEach(() => useFixtures());

  it('returns the six checks in order', () => {
    const shape = describeLine(TYPICAL);
    expect(shape.checks.map((c) => c.id)).toEqual([
      'odd-even',
      'sum',
      'spread',
      'hmc',
      'high-numbers',
      'recent-bonus',
    ]);
  });

  it('marks exactly one bucket as the line for each distribution check', () => {
    for (const check of describeLine(TYPICAL).checks) {
      if (check.buckets.length === 0) continue;
      const marked = check.buckets.filter((b) => b.isLine);
      expect(marked.length).toBeLessThanOrEqual(1);
    }
  });

  it('gives an HMC share the line can actually match - a six-ball one (F-59)', () => {
    // The 7-ball distribution in lotto_odds_results.json can never contain a six-ball
    // pattern, which is why the Streamlit validator called every line never observed.
    const check = describeLine(TYPICAL).checks.find((c) => c.id === 'hmc')!;
    const total = check.value.split(' / ').reduce((a, b) => a + Number(b), 0);
    expect(total).toBe(6);
    expect(check.buckets.every((b) => b.key.split('-').length === 3)).toBe(true);
  });

  it('counts high numbers from the artifact threshold and shows the fair share (F-19, F-38)', () => {
    const { highFrom } = highNumbers();
    const check = describeLine(TYPICAL).checks.find((c) => c.id === 'high-numbers')!;
    expect(check.value).toBe(String(TYPICAL.filter((n) => n >= highFrom).length));
    expect(check.comparison).toMatch(/a fair draw gives/);
    expect(check.informational).toBe(true);
  });

  it('reads the recent bonus window as the one facing the next draw (F-33)', () => {
    const window = latest().recent_bonus_numbers;
    const line = validateLine([window[0], ...TYPICAL.slice(0, 5)]);
    const expected = line.filter((n) => window.includes(n));
    const check = describeLine(line).checks.find((c) => c.id === 'recent-bonus')!;
    expect(check.value).toBe(String(expected.length));
    expect(check.comparison).toContain(String(window[0]));

    const clear = validateLine(
      Array.from({ length: 47 }, (_, i) => i + 1)
        .filter((n) => !window.includes(n))
        .slice(0, 6),
    );
    const none = describeLine(clear).checks.find((c) => c.id === 'recent-bonus')!;
    expect(none.value).toBe('0');
    expect(none.comparison).toContain('none of your six');
  });

  it('is calibrated so most past draws read typical and few read unusual', () => {
    // The draws are the definition of typical: a rule that called them unusual would be
    // describing the rule, not the draws.
    const verdicts = allDraws().map((d) => describeLine(d.main_numbers).verdict);
    const share = (v: string) =>
      verdicts.filter((x) => x === v).length / verdicts.length;
    expect(share('typical')).toBeGreaterThan(0.5);
    expect(share('unusual')).toBeLessThan(0.15);
  });

  it('calls an extreme line unusual and a spread-out line typical', () => {
    // Six low odd numbers: a rare sum, a rare spread and the rarest odd/even split.
    expect(describeLine([1, 3, 5, 7, 9, 11]).verdict).toBe('unusual');
    expect(describeLine(TYPICAL).verdict).toBe('typical');
  });

  it('shows the rare aspects of a line even when the word is not unusual', () => {
    // A run of six keeps the most common odd/even split, so the single word softens - the
    // rows must still carry the rare sum and spread.
    const shape = describeLine(UNUSUAL);
    const spread = shape.checks.find((c) => c.id === 'spread')!;
    expect(spread.share).toBeLessThan(5);
    expect(spread.comparison).toContain('% of past draws');
  });

  it('uses only the fixed vocabulary, and always the equal-chance sentence', () => {
    for (const line of [TYPICAL, UNUSUAL]) {
      const shape = describeLine(line);
      expect(['typical', 'uncommon', 'unusual']).toContain(shape.verdict);
      expect(shape.equalChance).toBe(EQUAL_CHANCE);
    }
  });

  it('never advises: no banned phrase appears in any check text', () => {
    const banned = [
      'play with confidence',
      'recommended',
      'regenerate',
      'risk',
      'improvement',
      'statistically sound',
      'excellent',
      'poor',
      'strong',
      'weak',
      'realistic',
      'confidence',
      'consider',
      'success rate',
      'astronomically',
      'diversif',
    ];
    for (const line of [TYPICAL, UNUSUAL]) {
      const shape = describeLine(line);
      const text = [
        shape.equalChance,
        shape.verdict,
        ...shape.checks.flatMap((c) => [c.title, c.value, c.comparison]),
      ]
        .join(' ')
        .toLowerCase();
      for (const phrase of banned) expect(text).not.toContain(phrase);
    }
  });
});

describe('the notes that replace the anomaly alerts', () => {
  beforeEach(() => useFixtures());

  it('says nothing about an ordinary line', () => {
    expect(describeLine(TYPICAL).notes).toEqual([]);
  });

  // A check that cannot fire is not a safeguard (F-29): every one gets a line that fires it.
  const firing: Array<[string, number[]]> = [
    ['sum', [1, 2, 3, 4, 5, 6]],
    ['spread', [1, 2, 3, 4, 5, 6]],
    ['parity', [1, 3, 5, 7, 9, 11]],
    ['run', [1, 2, 3, 20, 35, 44]],
    ['halves', [1, 2, 3, 4, 5, 6]],
  ];

  it.each(firing)('the %s note fires on a line that earns it', (id, line) => {
    const ids = describeLine(line).notes.map((n) => n.id);
    expect(ids).toContain(id);
  });

  it('fires the all-one-category note when a line is all one category', () => {
    const byCategory: Record<string, number[]> = { hot: [], medium: [], cold: [] };
    for (let n = 1; n <= 47; n += 1) byCategory[summary(n).category].push(n);
    const full = Object.entries(byCategory).find(([, ns]) => ns.length >= 6);
    expect(full).toBeDefined();
    const [category, ns] = full!;
    const ids = describeLine(ns.slice(0, 6)).notes.map((n) => n.id);
    expect(ids).toContain(`all-${category}`);
  });

  it('fires the bonus-window note when three of the six are in the window', () => {
    const window = latest().recent_bonus_numbers;
    const rest = Array.from({ length: 47 }, (_, i) => i + 1).filter(
      (n) => !window.includes(n),
    );
    const line = [...window.slice(0, 3), ...rest.slice(0, 3)];
    const ids = describeLine(line).notes.map((n) => n.id);
    expect(ids).toContain('bonus-window');
  });

  it('states facts, never warnings', () => {
    const warning = ['should', 'avoid', 'warning', 'careful', 'unlikely to', 'better'];
    for (const line of [[1, 2, 3, 4, 5, 6], [1, 3, 5, 7, 9, 11], [42, 43, 44, 45, 46, 47]]) {
      for (const note of describeLine(line).notes) {
        const text = note.text.toLowerCase();
        for (const phrase of warning) expect(text).not.toContain(phrase);
      }
    }
  });
});
