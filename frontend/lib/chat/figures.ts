/**
 * The figures a prepared answer quotes (chat.md 3, layer 0 with data).
 *
 * The explanation of a picker filter is hand-written in prepared.ts; the numbers that make
 * it concrete - how many numbers sit in each freshness bin today, how often a bonus ball
 * came back - are read here from the same lib/data/ readers the picker uses, so they move
 * with every rebuild and never drift from the page.
 */
import { bonusReturn, freshnessPatterns, totalDraws } from '@/lib/data/distributions';
import { pool, type Pool } from '@/lib/data/pool';
import { plural } from '@/lib/format';

function binLabel(p: Pool, bin: number): string {
  return bin === p.maxBin ? `C${bin}+` : `C${bin}`;
}

function listed(numbers: number[]): string {
  return numbers.length ? `: ${numbers.join(', ')}` : '';
}

/** The share of past draws, over the main six, matching `keep`, counted from the patterns. */
function drawShare(keep: (p: { C0: number; C1: number; C_GE_2: number }) => boolean): string {
  const matched = freshnessPatterns()
    .filter(keep)
    .reduce((sum, p) => sum + p.draws_matched, 0);
  return `${Math.round((100 * matched) / totalDraws())}%`;
}

function mostCommonMix(p: Pool): string {
  const top = freshnessPatterns().reduce((a, b) => (b.draws_matched > a.draws_matched ? b : a));
  return `${top.C0} ${binLabel(p, 0)}, ${top.C1} ${binLabel(p, 1)} and ${top.C_GE_2} ${binLabel(p, p.maxBin)}, in ${top.percentage}% of draws`;
}

export function freshnessFigures(): string {
  const p = pool();
  const bins = Array.from({ length: p.maxBin + 1 }, (_, bin) =>
    p.numbers.filter((n) => n.freshnessBin === bin).map((n) => n.number),
  );
  const counts = bins.map((ns, bin) => `${ns.length} are ${binLabel(p, bin)}`);
  const top = bins[p.maxBin];
  return (
    `The count is over the last ${p.freshnessDraws} draws. Right now ` +
    `${counts.slice(0, -1).join(', ')} and ${counts.at(-1)}` +
    `${top.length ? ` (${top.join(', ')})` : ''}. ` +
    `The mix past draws held most often was ${mostCommonMix(p)}.`
  );
}

export function busyFigures(): string {
  const p = pool();
  const busy = p.numbers.filter((n) => n.freshnessBin === p.maxBin).map((n) => n.number);
  return (
    `Right now ${plural(busy.length, 'number')} came up ${p.maxBin === 2 ? 'twice' : `${p.maxBin} times`} or more in the last ` +
    `${p.freshnessDraws} draws${listed(busy)}. ${drawShare((m) => m.C_GE_2 > 0)} of past draws ` +
    `held at least one number like that.`
  );
}

export function quietFigures(): string {
  const p = pool();
  const quiet = p.numbers.filter((n) => n.freshnessBin === 0).map((n) => n.number);
  return (
    `Right now ${plural(quiet.length, 'number')} did not come up in the last ${p.freshnessDraws} ` +
    `draws, so they are ${binLabel(p, 0)}. ${drawShare((m) => m.C0 >= 3)} of past draws held ` +
    `three or more numbers like that.`
  );
}

export function bonusFigures(): string {
  const p = pool();
  const b = bonusReturn();
  return (
    `Over the draws on file, ${(100 * b.rate).toFixed(1)}% of bonus balls came up as a main ` +
    `number within the next ${b.window} draws; a fair draw gives ${(100 * b.fairRate).toFixed(1)}%. ` +
    `The bonus balls of the last ${p.bonusWindow} draws were ${p.recentBonus.join(', ')}.`
  );
}
