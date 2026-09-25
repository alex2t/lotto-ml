/**
 * What each chart on the Statistics tab shows, in plain words.
 *
 * One entry per chart, written once and read twice: the tab renders it as the card's
 * summary and explanation, and the chat panel (nextStep/chat.md, layer 0) answers from it -
 * `patterns` are the phrases its prepared-answer matcher scores against, and
 * `chatAnswer()` is the reply, so an entry maps onto the panel's `Prepared` as
 * `{ id, patterns, answer: chatAnswer(entry), routes: ['/explore'] }`. Text only: every
 * figure comes from `lib/data/statistics.ts`, which reads the artifacts.
 */

export type StatId =
  | 'hmc-now'
  | 'hmc-six'
  | 'hmc-seven'
  | 'odd-even'
  | 'sums'
  | 'spread'
  | 'high-numbers'
  | 'odd-share'
  | 'volatility-trend'
  | 'consecutive-pairs'
  | 'repeat-windows';

/** Whether a date range changes the chart: counted from the draws, or written by the engine. */
export type Scope = 'today' | 'counted' | 'whole';

export interface StatGuide {
  id: StatId;
  title: string;
  /** One sentence: what the chart measures. Shown on the collapsed card. */
  summary: string;
  /** How to read the chart itself: what a bar, a key or a mark stands for. */
  howToRead: string;
  /** What the figures do and do not say about a draw. */
  whatItMeans: string;
  scope: Scope;
  /** Phrases a person might ask the chat with. */
  patterns: string[];
}

export interface StatGroup {
  title: string;
  blurb: string;
  ids: StatId[];
}

export const STAT_GROUPS: StatGroup[] = [
  {
    title: 'Right now',
    blurb: 'Where the 47 numbers stand at the latest draw.',
    ids: ['hmc-now'],
  },
  {
    title: 'The shape of a draw',
    blurb: 'What six drawn numbers usually look like together.',
    ids: ['odd-even', 'sums', 'spread', 'high-numbers', 'hmc-six', 'hmc-seven'],
  },
  {
    title: 'Number by number',
    blurb: 'Single numbers and pairs, over the whole history.',
    ids: ['odd-share', 'volatility-trend', 'consecutive-pairs', 'repeat-windows'],
  },
];

export const STATISTICS_GUIDE: StatGuide[] = [
  {
    id: 'hmc-now',
    title: 'Hot, medium and cold right now',
    summary: 'How the 47 numbers split today by how recently each one was drawn.',
    howToRead:
      'Hot means drawn in the last 13 days, medium 14 to 26 days ago, cold 27 days or more. Each bar is how many of the 47 numbers sit in that group at the latest draw.',
    whatItMeans:
      'It is a label for recency, nothing more. The draw has no memory: a cold number is exactly as likely to come up next as a hot one.',
    scope: 'today',
    patterns: [
      'what does hot mean',
      'what is hot medium cold',
      'what is a cold number',
      'how many numbers are hot',
      'hot medium cold right now',
    ],
  },
  {
    id: 'odd-even',
    title: 'Odd and even',
    summary: 'How many of the six main numbers were odd, and how many even.',
    howToRead:
      '"3 odd / 3 even" means three odd and three even main numbers. Each bar is the share of draws with that split. The bonus ball is not counted.',
    whatItMeans:
      'With 24 odd and 23 even numbers in the drum, 3/3, 4/2 and 2/4 splits are what chance produces most often. Six odd or six even is rare only because few combinations make it.',
    scope: 'counted',
    patterns: [
      'odd and even',
      'how many odd numbers',
      'odd even split',
      'most common odd even',
      'all odd numbers',
    ],
  },
  {
    id: 'sums',
    title: 'Sums',
    summary: 'The total of the six main numbers, grouped into bands.',
    howToRead:
      'Each bar is a band of totals and the share of draws whose six main numbers added up to a total inside it. The labels are inclusive: 140-154 holds 140 to 154.',
    whatItMeans:
      'Totals bunch in the middle because most combinations of six numbers land there. A line of 1 to 6 adds up to 21, and almost no other combination does.',
    scope: 'counted',
    patterns: [
      'what is the sum',
      'sum of the numbers',
      'average sum',
      'sum bands',
      'what total do draws have',
    ],
  },
  {
    id: 'spread',
    title: 'Spread',
    summary: 'The gap between the highest and the lowest main number.',
    howToRead:
      'Highest minus lowest of the six main numbers. The bands are half-open: 20-25 means 20 to 24, and 25 belongs to 25-30. The last band, 40-45, includes 45.',
    whatItMeans:
      'Wide spreads are the usual case, because six numbers taken at random from 47 nearly always reach across most of the range.',
    scope: 'counted',
    patterns: [
      'what is the spread',
      'what does 20-25 mean',
      'highest minus lowest',
      'range of the numbers',
      'spread bands',
    ],
  },
  {
    id: 'high-numbers',
    title: 'Numbers 32 and above',
    summary: 'How many of the six main numbers were 32 or higher.',
    howToRead:
      'The bars are past draws; the vertical mark on each is what a fair draw gives. The two track each other closely.',
    whatItMeans:
      'High numbers are not drawn more often. Many people play birthdays, 1 to 31, so a line with high numbers shares a prize less often when it wins - it does not win more often.',
    scope: 'counted',
    patterns: [
      'numbers above 32',
      'high numbers',
      'birthday numbers',
      'how many numbers 32 or above',
      'why 32',
    ],
  },
  {
    id: 'hmc-six',
    title: 'Hot/medium/cold patterns',
    summary: 'The mix of hot, medium and cold numbers past draws had.',
    howToRead:
      'A pattern such as 4-1-1 means 4 hot, 1 medium and 1 cold among the six main numbers, each judged by the group it was in just before that draw. The bars are the 12 most common patterns.',
    whatItMeans:
      'Hot-heavy patterns top the list because a large share of the 47 numbers is hot at any time. This is the distribution a line is compared with on the Pick page.',
    scope: 'counted',
    patterns: [
      'what does 4-1-1 mean',
      'hot medium cold pattern',
      'most common pattern',
      'six ball pattern',
      'pattern of a draw',
    ],
  },
  {
    id: 'hmc-seven',
    title: 'Patterns with the bonus ball',
    summary: 'The same hot/medium/cold mix, counted over all seven balls.',
    howToRead:
      'Each pattern here adds up to 7, because the bonus ball is included. The engine wrote it over the whole history.',
    whatItMeans:
      'Shown for completeness. A six-number line is always compared with the six-ball patterns above, never with these - the keys cannot match.',
    scope: 'whole',
    patterns: [
      'seven ball pattern',
      'pattern with the bonus',
      'why are there two pattern charts',
      'six ball or seven ball',
    ],
  },
  {
    id: 'odd-share',
    title: "Each number's odd-draw share",
    summary: 'For each number, how often the draws it came up in were mostly odd.',
    howToRead:
      'An odd draw here has at least as many odd main numbers as even. The bar is the share of a number\'s appearances that were in such a draw; the vertical mark is what a fair draw gives that number.',
    whatItMeans:
      'An odd number brings one odd ball with it, so its fair share sits near 83% and an even number\'s near 54%. Only the gap between bar and mark means anything; the badge counts the numbers whose gap still stands out after correcting for testing 47 numbers at once.',
    scope: 'whole',
    patterns: [
      'odd draw share',
      'odd affinity',
      'does a number prefer odd draws',
      'why is the odd share high',
    ],
  },
  {
    id: 'volatility-trend',
    title: 'Volatile numbers and biggest changes',
    summary: 'Which numbers came up most unevenly, and which changed pace the most.',
    howToRead:
      'Volatility is how uneven the gaps between a number\'s appearances are. The trend compares its recent window with the older one. "Significant" means Fisher\'s exact test on the two windows\' counts flagged it.',
    whatItMeans:
      'The test flags about 5% of numbers on fair draws, so two or three flags among 47 is what chance alone produces. A flag describes the past and does not carry forward.',
    scope: 'whole',
    patterns: [
      'what is volatility',
      'what is the trend',
      'what does significant mean',
      'biggest change',
      'most volatile number',
    ],
  },
  {
    id: 'consecutive-pairs',
    title: 'Consecutive pairs',
    summary: 'How often two neighbouring numbers, such as 12 and 13, came up in the same draw.',
    howToRead:
      'Each bar is how many draws held that pair, busiest first; the vertical mark is how many a fair draw gives over the same number of draws.',
    whatItMeans:
      'Some pair is always the busiest. The engine\'s chi-square test across all 46 pairs says whether the counts as a whole depart from chance.',
    scope: 'whole',
    patterns: [
      'consecutive numbers',
      'numbers next to each other',
      'consecutive pairs',
      'busiest pair',
    ],
  },
  {
    id: 'repeat-windows',
    title: 'Repeats inside a window',
    summary: 'How often some number came up several times in a short run of draws.',
    howToRead:
      'A window is a run of consecutive draws, all seven balls counted. "2 times in 5 draws" is the share of 5-draw windows in which at least one number came up exactly twice. A number\'s windows are not allowed to overlap, so one busy spell is counted once.',
    whatItMeans:
      'Five draws put 35 balls out of 47 on the table, so some number turning up twice is the ordinary case, not a streak. Eight times in 25 draws is rare, as chance would have it: a number averages under four.',
    scope: 'whole',
    patterns: [
      'historical scenarios',
      'repeats in a window',
      'what does 2 times in 5 draws mean',
      'how often does a number repeat',
    ],
  },
];

export function guide(id: StatId): StatGuide {
  const entry = STATISTICS_GUIDE.find((g) => g.id === id);
  if (!entry) throw new Error(`No statistics guide entry for ${id}`);
  return entry;
}

/** The chat panel's reply for a statistic: what it measures, how to read it, what it shows. */
export function chatAnswer(entry: StatGuide): string {
  return `${entry.summary} ${entry.howToRead} ${entry.whatItMeans}`;
}
