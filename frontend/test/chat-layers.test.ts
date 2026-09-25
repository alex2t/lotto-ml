import { beforeEach, describe, expect, it } from 'vitest';
import {
  LINE_QUESTION,
  METHOD_SUGGESTED,
  PREPARED,
  RATING_ID,
  SUGGESTED,
  suggestionsFor,
  type ChatRoute,
} from '@/lib/chat/prepared';
import { bonusFigures, busyFigures, freshnessFigures, quietFigures } from '@/lib/chat/figures';
import { matchPrepared, normalise, routeOf } from '@/lib/chat/match';
import { matchIntent } from '@/lib/chat/intents';
import { allDraws, latest } from '@/lib/data/draws';
import { dossier } from '@/lib/data/dossier';
import { pool } from '@/lib/data/pool';
import {
  bonusReturn,
  freshnessPatterns,
  highNumbers,
  oddEvenPatterns,
  sumDistributions,
  totalDraws,
} from '@/lib/data/distributions';
import { byCategory, summary } from '@/lib/data/numbers';
import { nextDrawDate } from '@/lib/data/schedule';
import { describeLine } from '@/lib/scoring/line';
import { longDate, percent } from '@/lib/format';
import { useFixtures } from './setup-fixtures';

/** Layers 0 and 1 of the chat panel (chat.md 3, 9). */

describe('layer 0 - the prepared answers', () => {
  it('holds the catalogue chat.md describes', () => {
    expect(PREPARED.length).toBeGreaterThanOrEqual(50);
    expect(new Set(PREPARED.map((e) => e.id)).size).toBe(PREPARED.length);
  });

  it.each(PREPARED.map((e) => [e.id, e] as const))(
    '%s answers its own question, on its own page',
    (_id, entry) => {
      const route: ChatRoute = entry.routes[0] ?? '/';
      expect(matchPrepared(entry.question, route)?.id).toBe(entry.id);
    },
  );

  it('weights the entry for the page it is asked on', () => {
    expect(matchPrepared('What does this table show?', '/explore')?.id).toBe('draws-table');
    expect(matchPrepared('What does this table show?', '/numbers')?.id).toBe('numbers-table');
  });

  it('matches regardless of case and punctuation', () => {
    expect(matchPrepared('WHAT do Hot, medium & cold MEAN??', '/')?.id).toBe('hmc-meaning');
    expect(normalise('Is 20-25 "half-open"?')).toBe('is 20 25 half open');
  });

  it('answers a question in the banned vocabulary with the fixed rating answer', () => {
    expect(matchPrepared('Is 7 a strong number?', '/')?.id).toBe(RATING_ID);
    expect(matchPrepared('Would you consider this line?', '/pick')?.id).toBe(RATING_ID);
  });

  it('answers what to play and what will win without a model', () => {
    expect(matchPrepared('What numbers should I play this Saturday?', '/')?.id).toBe(
      'out-of-scope-play',
    );
    expect(matchPrepared('Which numbers will win on Saturday?', '/')?.id).toBe(
      'out-of-scope-predict',
    );
    expect(matchPrepared('Is 12 overdue?', '/numbers')?.id).toBe('out-of-scope-memory');
  });

  it('leaves a question it has no answer for alone', () => {
    expect(matchPrepared('Why is the sky blue at dusk?', '/')).toBeNull();
  });

  it('maps a pathname to its destination', () => {
    expect(routeOf('/numbers/12')).toBe('/numbers');
    expect(routeOf('/explore')).toBe('/explore');
    expect(routeOf('/')).toBe('/');
    expect(routeOf('/login')).toBe('/');
  });
});

/** A question for each intent - none of them may be claimed by a prepared answer first. */
const INTENT_QUESTIONS: Array<[string, string]> = [
  ['number-count', 'How many times has 7 come up?'],
  ['number-count', 'How often has 20 come up in the last 25 draws?'],
  ['number-last', 'When was 13 last drawn?'],
  ['categories-now', 'Which numbers are hot right now?'],
  ['latest-draw', 'What was the last draw?'],
  ['next-draw', 'When is the next draw?'],
  ['high-share', 'How many draws had 3 numbers 32 or above?'],
  ['odd-even-share', 'How often were there 4 odd and 2 even?'],
  ['sum-share', 'How common is a sum of 140?'],
  ['partners', 'What is 7 most often drawn with?'],
  ['draw-count', 'How many draws are on file?'],
];

describe('layer 1 - the data answers', () => {
  beforeEach(() => useFixtures());

  it.each(INTENT_QUESTIONS)('%s: "%s" reaches its intent, not a prepared answer', (id, q) => {
    expect(matchPrepared(q, '/')).toBeNull();
    expect(matchIntent(q)?.intent).toBe(id);
  });

  it('states a number s counts as the readers hold them', () => {
    const s = summary(7);
    const total = matchIntent('How many times has 7 come up?')!.answer;
    expect(total).toContain(`drawn ${s.totalCount} times`);
    expect(total).toContain(`${s.recent.last_9} in the last 10`);

    const windowed = matchIntent('How often has 7 come up in the last 25 draws?')!.answer;
    expect(windowed).toContain(`${s.recent.last_24}`);
    expect(windowed).toContain('last 25 draws');
  });

  it('names the windows it has when asked for another one', () => {
    const answer = matchIntent('How many times has 7 come up in the last 12 draws?')!.answer;
    expect(answer).toContain('last 5, 6, 10 and 25 draws');
  });

  it('states when a number was last drawn and its category', () => {
    const s = summary(13);
    const answer = matchIntent('When was 13 last drawn?')!.answer;
    expect(answer).toContain(longDate(s.lastSeen.replaceAll('/', '-')));
    expect(answer).toContain(s.category);
  });

  it('lists exactly the numbers in a category', () => {
    const cold = byCategory().cold;
    const answer = matchIntent('Which numbers are cold right now?')!.answer;
    expect(answer).toContain(cold.join(', '));
    expect(answer).not.toContain('hot number');
  });

  it('states the latest draw, a draw by date, and a date with no draw', () => {
    const draw = latest();
    expect(matchIntent('What was the latest result?')!.answer).toContain(
      draw.main_numbers.join(', '),
    );
    const older = allDraws()[3];
    expect(matchIntent(`What came out on ${older.draw_date}?`)!.answer).toContain(
      older.main_numbers.join(', '),
    );
    expect(matchIntent('What was drawn on 1 January 1990?')!.answer).toContain(
      'no draw on file',
    );
  });

  it('states the next draw date', () => {
    expect(matchIntent('When is the next draw?')!.answer).toContain(longDate(nextDrawDate()));
  });

  it('states the high-number, odd/even and sum shares from the distributions', () => {
    const high = highNumbers().byCount['3'];
    expect(matchIntent('How many draws had 3 numbers 32 or above?')!.answer).toContain(
      percent(high.percentage),
    );
    const split = oddEvenPatterns()['4_2'];
    expect(matchIntent('How often were there 4 odd and 2 even?')!.answer).toContain(
      `${percent(split.percentage)} of past draws (${split.count})`,
    );
    const reversed = oddEvenPatterns()['2_4'];
    expect(matchIntent('How often were there 4 even and 2 odd?')!.answer).toContain(
      `(${reversed.count})`,
    );
    const band = sumDistributions()['S6_MID (140-154)'];
    expect(matchIntent('How common is a sum of 140?')!.answer).toContain(
      `${percent(band.percentage)} of past draws (${band.count})`,
    );
  });

  it('states a number s partners with the fair-draw expectation beside them', () => {
    const { top, expected } = dossier(7).partners;
    const answer = matchIntent('What is 7 most often drawn with?')!.answer;
    expect(answer).toContain(`${top[0].number} (${top[0].count} times)`);
    expect(answer).toContain(expected.toFixed(1));
  });

  it('states the draw count and the first date', () => {
    const answer = matchIntent('How many draws are on file?')!.answer;
    expect(answer).toContain(`${totalDraws()} draws`);
    expect(answer).toContain(longDate(allDraws()[0].draw_date));
  });

  it('uses the page s number when the question names none', () => {
    const answer = matchIntent('How many times has it come up?', { number: 12 })!.answer;
    expect(answer).toContain(`12 has been drawn ${summary(12).totalCount} times`);
    expect(matchIntent('How many times has it come up?')).toBeNull();
  });

  it('describes the tray s line with the shape card s verdict', () => {
    const line = [5, 12, 23, 31, 38, 44];
    const answer = matchIntent('Is my line typical?', { line })!.answer;
    expect(answer).toContain(`reads ${describeLine(line).verdict}`);
    expect(answer).toContain('equally likely to win');
    expect(matchIntent('Is my line typical?')).toBeNull();
  });

  it('never answers a suggested question with the model', () => {
    const line = [5, 12, 23, 31, 38, 44];
    const offered: Array<[ChatRoute, string]> = [
      ...Object.entries(SUGGESTED).flatMap(([route, qs]) =>
        qs.map((q): [ChatRoute, string] => [route as ChatRoute, q]),
      ),
      ...Object.values(METHOD_SUGGESTED).flatMap((qs) =>
        [LINE_QUESTION, ...qs].map((q): [ChatRoute, string] => ['/pick', q]),
      ),
    ];
    for (const [route, q] of offered) {
      const answered = matchPrepared(q, route) ?? matchIntent(q, { line });
      expect(answered, `${route}: ${q}`).not.toBeNull();
    }
  });
});

describe('the picker s questions follow the way of picking', () => {
  beforeEach(() => useFixtures());

  it('offers each method its own questions, and the line question once the line is complete', () => {
    expect(suggestionsFor('/pick', 'shake')).toEqual(METHOD_SUGGESTED.shake);
    expect(suggestionsFor('/pick', 'wheels')).not.toEqual(METHOD_SUGGESTED.shake);
    expect(suggestionsFor('/pick')).toEqual(SUGGESTED['/pick']);
    expect(suggestionsFor('/pick', 'shake', true)[0]).toBe(LINE_QUESTION);
    // Another page ignores a method it might be sent.
    expect(suggestionsFor('/numbers', 'shake', true)).toEqual(SUGGESTED['/numbers']);
  });

  it('no longer offers the verdict arithmetic as a question on /pick', () => {
    const all = [...SUGGESTED['/pick'], ...Object.values(METHOD_SUGGESTED).flat()];
    expect(all).not.toContain('How is the verdict worked out?');
  });

  // The owner's own wording of the questions a player on Shake the bag asks.
  it.each([
    ['what is freshness', 'freshness-bin'],
    ['What is freshness C0., C1, C2', 'freshness-bin'],
    ['why would I want to drop numbers drawn more than 2 times?', 'drop-busy'],
    ['Why take out numbers drawn a lot lately?', 'drop-busy'],
    ['Why drop numbers not drawn at all in the last 10 draws?', 'drop-quiet'],
    [
      'What is the function drop number that were a bonus ball why would I want to use?',
      'drop-bonus',
    ],
    ['How do the filters work?', 'bag-filters'],
  ])('on /pick "%s" reaches %s', (question, id) => {
    expect(matchPrepared(question, '/pick')?.id).toBe(id);
  });

  it('states the freshness bins as the pool holds them', () => {
    const p = pool();
    const text = freshnessFigures();
    const busy = p.numbers.filter((n) => n.freshnessBin === p.maxBin).map((n) => n.number);
    expect(text).toContain(`last ${p.freshnessDraws} draws`);
    expect(text).toContain(`${p.numbers.filter((n) => n.freshnessBin === 0).length} are C0`);
    expect(text).toContain(`${busy.length} are C${p.maxBin}+`);
    const top = [...freshnessPatterns()].sort((a, b) => b.draws_matched - a.draws_matched)[0];
    expect(text).toContain(`in ${top.percentage}% of draws`);
  });

  it('counts past draws by freshness over every draw on file', () => {
    // The shares busyFigures and quietFigures state are counted from these patterns, so
    // they must cover each draw exactly once.
    const covered = freshnessPatterns().reduce((sum, p) => sum + p.draws_matched, 0);
    expect(covered).toBe(totalDraws());
    for (const p of freshnessPatterns()) expect(p.C0 + p.C1 + p.C_GE_2).toBe(6);
  });

  it('names the busy numbers and the share of draws that held one', () => {
    const p = pool();
    const busy = p.numbers.filter((n) => n.freshnessBin === p.maxBin).map((n) => n.number);
    const withBusy = freshnessPatterns()
      .filter((m) => m.C_GE_2 > 0)
      .reduce((sum, m) => sum + m.draws_matched, 0);
    const text = busyFigures();
    if (busy.length) expect(text).toContain(busy.join(', '));
    expect(text).toContain(`${Math.round((100 * withBusy) / totalDraws())}% of past draws`);
  });

  it('states the bonus return rate next to a fair draw, and the recent bonus balls', () => {
    const b = bonusReturn();
    const text = bonusFigures();
    expect(b.window).toBe(10);
    expect(text).toContain(`${(100 * b.rate).toFixed(1)}%`);
    expect(text).toContain(`a fair draw gives ${(100 * b.fairRate).toFixed(1)}%`);
    expect(text).toContain(pool().recentBonus.join(', '));
  });

  it('says how many numbers are quiet', () => {
    const p = pool();
    const quiet = p.numbers.filter((n) => n.freshnessBin === 0).length;
    expect(quietFigures()).toContain(`Right now ${quiet} number`);
  });
});
