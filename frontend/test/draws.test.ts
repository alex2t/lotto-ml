import { beforeEach, describe, expect, it } from 'vitest';
import { allDraws, byDate, byNumber, latest, page, sinceDate } from '@/lib/data/draws';
import { useFixtures } from './setup-fixtures';

describe('draws', () => {
  beforeEach(() => useFixtures());

  it('returns draws oldest first', () => {
    const dates = allDraws().map((d) => d.draw_date);
    expect([...dates].sort()).toEqual(dates);
  });

  it('latest() is the newest draw, not the first entry', () => {
    const dates = allDraws().map((d) => d.draw_date);
    expect(latest().draw_date).toBe(dates[dates.length - 1]);
  });

  it('every draw carries six main numbers and a bonus, all distinct and in 1-47', () => {
    for (const draw of allDraws()) {
      const balls = [...draw.main_numbers, draw.bonus_number];
      expect(draw.main_numbers).toHaveLength(6);
      expect(new Set(balls).size).toBe(7);
      expect(Math.min(...balls)).toBeGreaterThanOrEqual(1);
      expect(Math.max(...balls)).toBeLessThanOrEqual(47);
    }
  });

  it('pages newest first and reports the total', () => {
    const first = page(0, 5);
    expect(first.draws).toHaveLength(5);
    expect(first.total).toBe(allDraws().length);
    expect(first.draws[0].draw_date).toBe(latest().draw_date);

    const second = page(5, 5);
    expect(second.draws[0].draw_date < first.draws[4].draw_date).toBe(true);
  });

  it('byNumber returns only draws holding the number, with its pre-draw detail', () => {
    const n = latest().main_numbers[0];
    const appearances = byNumber(n);
    expect(appearances.length).toBeGreaterThan(0);
    for (const { draw, detail, asBonus } of appearances) {
      expect(draw.main_numbers.includes(n) || draw.bonus_number === n).toBe(true);
      expect(detail.number).toBe(n);
      expect(asBonus).toBe(draw.bonus_number === n);
    }
  });

  it('byDate throws for a date with no draw', () => {
    expect(() => byDate('1999-01-01')).toThrowError(/Missing key/);
  });

  it('sinceDate is inclusive of its boundary', () => {
    const boundary = latest().draw_date;
    expect(sinceDate(boundary).map((d) => d.draw_date)).toEqual([boundary]);
  });
});
