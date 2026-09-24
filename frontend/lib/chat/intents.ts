/**
 * Layer 1 of the chat panel: questions with a figure for an answer (chat.md 3).
 *
 * The intent is recognised by pattern, the number is pulled out of the question, a
 * lib/data/ reader supplies the figure, and a fixed sentence states it. No model, no
 * rounding drift, no invented number - and the figure is the one the page shows, because it
 * comes from the same reader.
 */
import { allDraws, latest } from '@/lib/data/draws';
import { dossier } from '@/lib/data/dossier';
import { highNumbers, oddEvenPatterns, sumDistributions, totalDraws } from '@/lib/data/distributions';
import { byCategory, summary } from '@/lib/data/numbers';
import { RECENT_WINDOWS } from '@/lib/data/pool';
import { nextDrawDate } from '@/lib/data/schedule';
import type { Category, DrawEntry } from '@/lib/data/types';
import { describeLine } from '@/lib/scoring/line';
import { sumBand } from '@/lib/scoring/bands';
import { longDate, percent, plural } from '@/lib/format';
import { normalise } from './match';

/** What the page the question was asked on is showing. Built by context.ts. */
export interface PageFocus {
  /** The number whose fact sheet is open, if any. */
  number?: number;
  /** The line in the picker's tray, when it is complete. */
  line?: number[];
}

export interface DataAnswer {
  intent: string;
  answer: string;
}

const MONTHS = [
  'january', 'february', 'march', 'april', 'may', 'june',
  'july', 'august', 'september', 'october', 'november', 'december',
];

/** A date in the question, as ISO: 2026-09-19, or 19 September 2026 / 19 sep 2026. */
function dateIn(text: string): string | undefined {
  const iso = text.match(/\b(\d{4}) (\d{1,2}) (\d{1,2})\b/);
  if (iso) return `${iso[1]}-${iso[2].padStart(2, '0')}-${iso[3].padStart(2, '0')}`;
  const words = text.match(/\b(\d{1,2}) ([a-z]{3,9}) (\d{4})\b/);
  if (!words) return undefined;
  const month = MONTHS.findIndex((m) => m.startsWith(words[2]) && words[2].length >= 3);
  if (month < 0) return undefined;
  return `${words[3]}-${String(month + 1).padStart(2, '0')}-${words[1].padStart(2, '0')}`;
}

/** "the last 10 draws" -> 10. */
function windowIn(text: string): number | undefined {
  const m = text.match(/\blast (\d{1,3}) draw/);
  return m ? Number(m[1]) : undefined;
}

/** The first ball number (1-47) in the question, ignoring a window size and a date. */
function ballIn(text: string): number | undefined {
  const stripped = text
    .replace(/\blast \d{1,3} draws?\b/, ' ')
    .replace(/\b\d{4} \d{1,2} \d{1,2}\b/, ' ')
    .replace(/\b\d{1,2} [a-z]{3,9} \d{4}\b/, ' ');
  for (const m of stripped.matchAll(/\b(\d{1,2})\b/g)) {
    const n = Number(m[1]);
    if (n >= 1 && n <= 47) return n;
  }
  return undefined;
}

/** The ball the question is about: one it names, or the one whose page it was asked on. */
function subject(text: string, focus: PageFocus): number | undefined {
  return ballIn(text) ?? focus.number;
}

function drawSentence(draw: DrawEntry): string {
  return `${longDate(draw.draw_date)}: ${draw.main_numbers.join(', ')}, with ${draw.bonus_number} as the bonus.`;
}

function listCategory(category: Category, numbers: number[]): string {
  return numbers.length
    ? `${plural(numbers.length, `${category} number`)} right now: ${numbers.join(', ')}.`
    : `No number is ${category} right now.`;
}

type Intent = {
  id: string;
  /** Returns the answer, or undefined when the question is not this intent. */
  answer: (text: string, focus: PageFocus) => string | undefined;
};

const INTENTS: Intent[] = [
  {
    id: 'line-shape',
    answer(text, focus) {
      if (!focus.line || !/\b(my|this) line\b/.test(text)) return undefined;
      const shape = describeLine(focus.line);
      const checks = shape.checks
        .filter((c) => !c.informational)
        .map((c) => `${c.title.toLowerCase()} ${c.value} (${c.comparison})`)
        .join('; ');
      return `Next to ${shape.drawsCompared} past draws, ${shape.line.join(', ')} reads ${shape.verdict}: ${checks}. ${shape.equalChance}`;
    },
  },
  {
    id: 'draw-on-date',
    answer(text) {
      const date = dateIn(text);
      if (!date) return undefined;
      const draw = allDraws().find((d) => d.draw_date === date);
      return draw
        ? `The draw on ${drawSentence(draw)}`
        : `There is no draw on file for ${longDate(date)}.`;
    },
  },
  {
    id: 'high-share',
    answer(text) {
      const m = text.match(/\b(\d) (?:of (?:the )?)?(?:main )?numbers? (?:at |of )?(?:32|thirty two)\b|\b(\d) high numbers?\b/);
      if (!m) return undefined;
      const count = m[1] ?? m[2];
      const high = highNumbers();
      const bucket = high.byCount[count];
      if (!bucket) return `A line has six main numbers, so it can hold 0 to 6 at ${high.highFrom} or above.`;
      return `${percent(bucket.percentage)} of past draws (${bucket.count}) had ${count} main numbers at ${high.highFrom} or above; a fair draw gives ${percent(bucket.fair_percentage as number)}.`;
    },
  },
  {
    id: 'odd-even-share',
    answer(text) {
      const odd = text.match(/\b(\d) odd\b/)?.[1];
      const even = text.match(/\b(\d) even\b/)?.[1];
      if (odd === undefined || even === undefined) return undefined;
      const bucket = oddEvenPatterns()[`${odd}_${even}`];
      if (!bucket) return 'A line has six main numbers, so its odd and even counts add up to 6.';
      return `${percent(bucket.percentage)} of past draws (${bucket.count}) had ${odd} odd and ${even} even main numbers.`;
    },
  },
  {
    id: 'sum-share',
    answer(text) {
      const m = text.match(/\bsum (?:of |is |was )?(\d{2,3})\b/);
      if (!m) return undefined;
      const total = Number(m[1]);
      const band = sumBand(total);
      const bucket = sumDistributions()[band.key];
      return `A sum of ${total} falls in the band ${band.key}, which held ${percent(bucket.percentage)} of past draws (${bucket.count}).`;
    },
  },
  {
    id: 'partners',
    answer(text, focus) {
      if (!/\b(drawn with|partners?|pairs? with|comes? up with|come up together)\b/.test(text)) {
        return undefined;
      }
      const n = subject(text, focus);
      if (n === undefined) return undefined;
      const { top, expected } = dossier(n).partners;
      const listed = top
        .slice(0, 3)
        .map((p) => `${p.number} (${plural(p.count, 'time')})`)
        .join(', ');
      return `${n} has most often been drawn with ${listed}. A fair draw would put any given pair together about ${expected.toFixed(1)} times over these draws, so counts like these are within what chance produces.`;
    },
  },
  {
    id: 'number-count',
    answer(text, focus) {
      if (!/\b(how (many times|often)|times has|count for)\b/.test(text)) return undefined;
      const n = subject(text, focus);
      if (n === undefined) return undefined;
      const s = summary(n);
      const draws = windowIn(text);
      const window = RECENT_WINDOWS.find((w) => w.draws === draws);
      if (window) {
        return `${n} came up ${plural(s.recent[window.key], 'time')} as a main number in the last ${window.draws} draws.`;
      }
      const recent = RECENT_WINDOWS.map((w) => `${s.recent[w.key]} in the last ${w.draws}`).join(', ');
      const lead = draws ? `The site keeps counts for the last 5, 6, 10 and 25 draws. ` : '';
      return `${lead}${n} has been drawn ${plural(s.totalCount, 'time')} in the ${totalDraws()} draws on file, bonus ball included. As a main number it came up ${recent}.`;
    },
  },
  {
    id: 'number-last',
    answer(text, focus) {
      if (!/\b(last (drawn|seen|came up|come up|appeared)|when did|category|is \d{1,2} (hot|medium|cold))\b/.test(text)) {
        return undefined;
      }
      const n = subject(text, focus);
      if (n === undefined) return undefined;
      const s = summary(n);
      return `${n} was last drawn on ${longDate(s.lastSeen.replaceAll('/', '-'))}, which makes it ${s.category} at the latest draw.`;
    },
  },
  {
    id: 'categories-now',
    answer(text) {
      const named = (['hot', 'medium', 'cold'] as Category[]).filter((c) =>
        new RegExp(`\\b${c}\\b`).test(text),
      );
      if (!named.length || !/\b(which|what|list|show)\b/.test(text) || !/\bnumbers?\b/.test(text)) {
        return undefined;
      }
      const groups = byCategory();
      return named.map((c) => listCategory(c, groups[c])).join(' ');
    },
  },
  {
    id: 'next-draw',
    answer(text) {
      if (!/\b(next draw|when is the draw|next lotto|draw next)\b/.test(text)) return undefined;
      return `The next draw is on ${longDate(nextDrawDate())}, at about 8pm.`;
    },
  },
  {
    id: 'latest-draw',
    answer(text) {
      if (!/\b(last|latest|most recent|previous) (draw|result)s?\b/.test(text)) return undefined;
      return `The latest draw on file is ${drawSentence(latest())}`;
    },
  },
  {
    id: 'draw-count',
    answer(text) {
      if (!/\b(how many draws|how far back|first draw|since when)\b/.test(text)) return undefined;
      const first = allDraws()[0].draw_date;
      return `There are ${totalDraws()} draws on file, from ${longDate(first)} to ${longDate(latest().draw_date)}.`;
    },
  },
];

/** The data answer to a question, or null when it is not one of these intents. */
export function matchIntent(question: string, focus: PageFocus = {}): DataAnswer | null {
  const text = normalise(question);
  for (const intent of INTENTS) {
    const answer = intent.answer(text, focus);
    if (answer !== undefined) return { intent: intent.id, answer };
  }
  return null;
}
