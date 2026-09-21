/**
 * Notes on a line - what the Streamlit anomaly alerts became.
 *
 * Every note states a fact about past draws and stops there. The old alerts called lines
 * risky, advised diversification and quoted a frequency from memory that was four times
 * wrong (F-28), so each note here takes its figure from an artifact and describes rather
 * than warns.
 *
 * A check that cannot fire is not a safeguard (F-29): test/scoring.test.ts fires each one.
 */
import { spreadDistribution, sumDistribution } from '../data/distributions';
import { latest } from '../data/draws';
import { summary } from '../data/numbers';
import type { Category } from '../data/types';

export interface Note {
  id: string;
  text: string;
}

/** How many numbers apart from each other by one, as a run. */
function longestRun(line: number[]): number {
  const sorted = [...line].sort((a, b) => a - b);
  let best = 1;
  let run = 1;
  for (let i = 1; i < sorted.length; i += 1) {
    run = sorted[i] === sorted[i - 1] + 1 ? run + 1 : 1;
    best = Math.max(best, run);
  }
  return best;
}

export function notesFor(line: number[]): Note[] {
  const notes: Note[] = [];

  const sum = line.reduce((a, b) => a + b, 0);
  const sumStats = sumDistribution() as { mean: number; std: number; min: number; max: number };
  const away = Math.abs(sum - sumStats.mean) / sumStats.std;
  if (away >= 2) {
    notes.push({
      id: 'sum',
      text: `The sum ${sum} is ${away.toFixed(1)} standard deviations from the average past draw (${sumStats.mean.toFixed(0)}), which ranged from ${sumStats.min} to ${sumStats.max}.`,
    });
  }

  const spread = Math.max(...line) - Math.min(...line);
  const spreadStats = spreadDistribution() as { mean: number; std: number };
  if (Math.abs(spread - spreadStats.mean) / spreadStats.std >= 2) {
    notes.push({
      id: 'spread',
      text: `The spread ${spread} is unlike a typical draw, which spreads about ${spreadStats.mean.toFixed(0)}.`,
    });
  }

  const odd = line.filter((n) => n % 2 === 1).length;
  if (odd === 0 || odd === line.length) {
    notes.push({
      id: 'parity',
      text: `Every number is ${odd === 0 ? 'even' : 'odd'}. Past draws have done that, rarely.`,
    });
  }

  const run = longestRun(line);
  if (run >= 3) {
    notes.push({
      id: 'run',
      text: `${run} of the numbers run consecutively.`,
    });
  }

  const counts: Record<Category, number> = { hot: 0, medium: 0, cold: 0 };
  for (const n of line) counts[summary(n).category] += 1;
  for (const category of ['hot', 'medium', 'cold'] as Category[]) {
    if (counts[category] === line.length) {
      notes.push({
        id: `all-${category}`,
        text: `All six are ${category} right now.`,
      });
    }
  }

  const window = latest().recent_bonus_numbers;
  const fromWindow = line.filter((n) => window.includes(n));
  if (fromWindow.length >= 3) {
    notes.push({
      id: 'bonus-window',
      text: `${fromWindow.length} of the six were bonus balls in the last ${window.length} draws.`,
    });
  }

  const half = line.filter((n) => n >= 24).length;
  if (half === 0 || half === line.length) {
    notes.push({
      id: 'halves',
      text: `Every number is in the ${half === 0 ? 'lower' : 'upper'} half of 1-47.`,
    });
  }

  return notes;
}
