/**
 * Layer 0 of the chat panel: questions answered by hand, with no model (chat.md 3).
 *
 * A hand-written answer about the site's own vocabulary is both free and better than a
 * generated one - it can say "20-25 means 20 to 24" and be right. Every answer here is
 * source, so test/wording.test.ts scans it like any page. A pattern is a set of words that
 * must all appear in the question; see match.ts.
 *
 * An entry about a picker filter also carries `figures`, which reads today's numbers from
 * lib/data/ (figures.ts) and is appended to the hand-written explanation - the words are
 * checked here, the figures come from the artifacts.
 */
import type { PickMethod } from '@/lib/pick/current-line';
import { bonusFigures, busyFigures, freshnessFigures, quietFigures } from './figures';

/** The five destinations, as the panel groups them. */
export type ChatRoute = '/' | '/pick' | '/explore' | '/numbers' | '/review';

export interface Prepared {
  id: string;
  /** The question as a person would ask it; shown when the entry is suggested. */
  question: string;
  patterns: string[];
  answer: string;
  /** Today's figures, read from the artifacts and appended to the answer. */
  figures?: () => string;
  /** The destinations this entry belongs to. Empty means it belongs everywhere. */
  routes: ChatRoute[];
}

/** The id of the entry that answers any question using a word from lib/advice.json. */
export const RATING_ID = 'out-of-scope-rating';

export const PREPARED: Prepared[] = [
  // The vocabulary
  {
    id: 'hmc-meaning',
    question: 'What do hot, medium and cold mean?',
    patterns: ['hot mean', 'cold mean', 'medium mean', 'hot defined', 'hmc mean', 'hmc'],
    answer:
      'Hot, medium and cold describe how recently a number was drawn, nothing more. Hot means it came up within the last 13 days, medium 14 to 26 days ago, and cold 27 days or more. A hot number is no likelier to come up next than a cold one.',
    routes: [],
  },
  {
    id: 'hmc-thresholds',
    question: 'Why 13 and 27 days?',
    patterns: ['13 day', '27 day', 'why 13', 'why 27', 'category threshold'],
    answer:
      'The 13 and 27 day cut-offs are set in the analysis engine, and every page uses the same two. They sort the numbers by how recently each came up; they do not change anyone\'s chances.',
    routes: [],
  },
  {
    id: 'category-change',
    question: 'Why did a number change category?',
    patterns: ['category change', 'category changed', 'change category', 'changed category'],
    answer:
      'Categories are worked out again after every draw from how many days ago each number last came up. A number turns hot the draw it comes up, then drifts to medium and cold as the days pass without it.',
    routes: [],
  },
  {
    id: 'freshness-bin',
    question: 'What is freshness?',
    patterns: ['freshness', 'what freshness', 'freshness bin', 'freshness mean', 'bin mean', 'c0', 'c1', 'c2'],
    answer:
      'Freshness sorts the numbers by how often each came up lately. C0 means not at all, C1 once, and C2+ twice or more. It describes the recent past; it does not change any number\'s chance in the next draw.',
    figures: freshnessFigures,
    routes: [],
  },
  {
    id: 'freshness-tab',
    question: 'What does the Freshness tab show?',
    patterns: ['freshness tab', 'freshness pattern', 'freshness chart'],
    answer:
      'The Freshness tab shows how many of each past draw\'s numbers sat in each bin just before it was drawn, and how often each mix has come up. Select a bin to see its numbers, or send it to the picker as a filter.',
    routes: ['/explore'],
  },
  {
    id: 'pre-draw-category',
    question: 'What does the category on a past draw mean?',
    patterns: ['pre draw', 'predraw', 'category before', 'category past draw', 'board looked'],
    answer:
      'On a past draw each ball shows the category it held just before that draw, not today\'s. Using today\'s categories on old draws would make the recent ones look all hot.',
    routes: ['/explore', '/review'],
  },
  {
    id: 'bonus-ball',
    question: 'What is the bonus ball?',
    patterns: ['bonus ball mean', 'what bonus ball', 'bonus mean', 'what bonus'],
    answer:
      'The bonus is a seventh ball, drawn after the six main numbers from the 41 left. A line you pick here is six numbers, so it is compared with the six main numbers of past draws.',
    routes: [],
  },
  {
    id: 'pick-bonus',
    question: 'Do I pick the bonus ball?',
    patterns: ['pick bonus', 'choose bonus', 'select bonus'],
    answer:
      'No - you choose six numbers and the bonus is drawn by the lottery. It only matters for some of the lower prize tiers, where five, four or three matches plus the bonus pays more.',
    routes: [],
  },
  {
    id: 'recent-bonus',
    question: 'What does recent bonus mean?',
    patterns: ['recent bonus mean', 'recent bonus', 'recently bonus', 'bonus window'],
    answer:
      'A number is marked as a recent bonus when it was the bonus ball in one of the last 10 draws. The shape card shows it for information only; it does not count towards the verdict.',
    routes: [],
  },
  {
    id: 'high-numbers',
    question: 'Why does the site count numbers 32 and above?',
    patterns: ['why 32', 'high number mean', 'birthday', 'high numbers mean'],
    answer:
      'Numbers from 32 up cannot be a day of the month, so lines built from birthdays leave them out. A line with more of them is no likelier to win, but if it wins it is less likely to share the prize. The site shows the count for information only.',
    routes: [],
  },
  {
    id: 'odd-even',
    question: 'What does the odd and even check mean?',
    patterns: ['odd even mean', 'odd even check', 'why odd even'],
    answer:
      'It counts how many of the six numbers are odd and how many even. Splits near the middle, such as 3 odd and 3 even, come up most often simply because there are more ways to make them.',
    routes: [],
  },
  {
    id: 'sum',
    question: 'How are the sum bands cut?',
    patterns: ['sum mean', 'sum band mean', 'sum bands cut', 'sum band cut', 'how sum band', 'what sum band'],
    answer:
      'The sum is the six main numbers added together. Past sums are grouped into seven bands: under 110, 110-124, 125-139, 140-154, 155-169, 170-184, and 185 or more. Sums near the middle are common because most combinations of six numbers land there.',
    routes: [],
  },
  {
    id: 'spread',
    question: 'Why does the spread band 20-25 stop at 24?',
    patterns: ['spread mean', 'what spread', '20 25 mean', 'spread band', 'half open', 'stop 24', 'why 25'],
    answer:
      'The spread is the highest number minus the lowest. The bands are half-open: "20-25" means 20 to 24, and a spread of 25 falls in "25-30". The labels are the analysis engine\'s own, kept as written so the site matches it.',
    routes: [],
  },
  {
    id: 'six-seven-ball',
    question: 'What are the six-ball and seven-ball figures?',
    patterns: ['six ball', 'seven ball', '6 ball', '7 ball'],
    answer:
      'Some figures count the six main numbers and some count all seven balls, bonus included. A line is six numbers, so it is always compared with the six-ball figures. A seventh ball can only widen a draw\'s spread, so the seven-ball figures would make a line look lower than it is.',
    routes: [],
  },
  {
    id: 'hmc-pattern',
    question: 'What is a hot/medium/cold pattern?',
    patterns: ['hmc pattern', 'hot medium cold pattern', 'pattern hot medium cold'],
    answer:
      'A line\'s pattern counts how many of its six numbers are hot, medium and cold right now - for example 2 hot, 2 medium, 2 cold. The site compares it with the pattern each past draw had just before it was drawn.',
    routes: [],
  },
  {
    id: 'pattern-rare',
    question: 'Why has my pattern rarely been seen?',
    patterns: ['never observed', 'never seen', 'rarely seen', 'pattern rare'],
    answer:
      'A rare pattern means few past draws had that mix of hot, medium and cold numbers. It describes those draws; it makes no difference to the line\'s chances.',
    routes: ['/pick'],
  },
  {
    id: 'consecutive',
    question: 'What are consecutive pairs?',
    patterns: ['consecutive', 'neighbour', 'back to back'],
    answer:
      'Consecutive numbers are neighbours such as 14 and 15. The Statistics tab counts how often past draws held a pair of them.',
    routes: [],
  },
  {
    id: 'scenarios',
    question: 'What are historical scenarios?',
    patterns: ['historical scenario', 'scenario'],
    answer:
      'They show how often a number that came up a given number of times in a recent window came up again in the next draw. They describe the past; they make no number likelier next time.',
    routes: ['/explore'],
  },

  // The tables
  {
    id: 'numbers-table',
    question: 'What does this table show?',
    patterns: ['this table', 'table show', 'table mean', 'column mean', 'columns'],
    answer:
      'All 47 numbers with what the analysis records about each: its category at the latest draw, times drawn in the last 10 draws and in the whole history, volatility, trend and momentum. Sort by any column, narrow it with the filters, or open a number for its fact sheet.',
    routes: ['/numbers'],
  },
  {
    id: 'draws-table',
    question: 'What does this table show?',
    patterns: ['this table', 'table show', 'table mean', 'column mean', 'columns'],
    answer:
      'The Draws tab lists every draw on file, newest first, with its six numbers and bonus. Filter by date, by a number it held, by odd/even split, sum band or count of high numbers, and open a draw to see its pre-draw categories and bonus window.',
    routes: ['/explore'],
  },
  {
    id: 'recent-windows',
    question: 'What do the recent counts count?',
    patterns: ['recent count', 'last 10 mean', 'window mean', 'why 5 6 10 25'],
    answer:
      'The recent counts are over the last 5, 6, 10 and 25 draws, and count the six main numbers only - a number that came up as the bonus is not counted there.',
    routes: [],
  },
  {
    id: 'total-count',
    question: 'What does Total mean?',
    patterns: ['total mean', 'total column', 'whole history'],
    answer:
      'Total is how many times a number has been drawn across every draw on file, bonus ball included.',
    routes: ['/numbers'],
  },
  {
    id: 'volatility',
    question: 'What is volatility?',
    patterns: ['volatility', 'volatile'],
    answer:
      'Volatility is how uneven a number\'s gaps between appearances are. A high value means it came in bursts and droughts, a low one that its gaps were more regular. It says nothing about when it comes up next.',
    routes: ['/numbers', '/explore'],
  },
  {
    id: 'trend',
    question: 'What does trend mean?',
    patterns: ['trend', 'trending'],
    answer:
      'Trend compares how often a number came up in its recent window with the older one. A trend is marked significant only by Fisher\'s exact test on the raw counts, which flags about 5 in 100 numbers even on perfectly fair draws.',
    routes: ['/numbers', '/explore'],
  },
  {
    id: 'momentum',
    question: 'What is momentum?',
    patterns: ['momentum'],
    answer:
      'Momentum is a number\'s recent rate set against its long-run rate. Above 1 means it has come up more often lately than usual, below 1 less often. On fair draws it swings either way by chance.',
    routes: ['/numbers'],
  },
  {
    id: 'regime-shift',
    question: 'What is a regime shift?',
    patterns: ['regime shift', 'regime'],
    answer:
      'A regime shift marks a number whose smoothed rate of appearing reached a peak or a low point within the most recent draws. It describes a turn in the past, and fair draws produce such turns all the time.',
    routes: ['/numbers'],
  },
  {
    id: 'filters',
    question: 'How do the filters work?',
    patterns: ['filter', 'filters'],
    answer:
      'The filters narrow the 47 numbers by category, freshness bin, volatility, momentum, a significant trend, a recent regime shift or a recent bonus. They only change what the table shows; every number stays equally likely to be drawn.',
    routes: ['/numbers'],
  },
  {
    id: 'gaps',
    question: 'What is a gap?',
    patterns: ['gap', 'gaps'],
    answer:
      'A gap is the number of draws between two appearances of a number. The fact sheet shows its average gap, its longest, and how many draws since it last came up. A long current gap does not make it any more likely to come up.',
    routes: ['/numbers'],
  },
  {
    id: 'drawn-with',
    question: 'What does often drawn with mean?',
    patterns: ['drawn with mean', 'partners mean', 'pair mean', 'pairs mean'],
    answer:
      'It counts the past draws in which two numbers were both among the six main numbers. The fair-draw expectation is shown beside it, because over this many draws the busiest pairs sit a few appearances above it by chance alone - a high count is not a pairing.',
    routes: ['/numbers'],
  },
  {
    id: 'dossier',
    question: 'What is on a number\'s fact sheet?',
    patterns: ['fact sheet', 'dossier', 'number page'],
    answer:
      'Everything the analysis records about one number: its category, recent and total counts, its gaps, the numbers it has most often been drawn with, and every draw it appeared in. It is a record, never a rating.',
    routes: ['/numbers'],
  },
  {
    id: 'statistics-tab',
    question: 'What do these charts show?',
    patterns: ['statistics tab', 'these charts', 'this chart', 'date range'],
    answer:
      'How past draws were spread: odd and even, sums, spread, high numbers and hot/medium/cold patterns. Five charts are counted straight from the draws and follow the date range; the rest were written by the engine over the whole history and say so.',
    routes: ['/explore'],
  },
  {
    id: 'patterns-tab',
    question: 'What does the Patterns tab do?',
    patterns: ['patterns tab', 'similar draws', 'exact match', 'closest draw'],
    answer:
      'It takes six numbers and finds the past draws that shared the most of them. An exact match means that line was once drawn; it is no likelier to be drawn again.',
    routes: ['/explore'],
  },
  {
    id: 'significant',
    question: 'What does significant mean?',
    patterns: ['significant mean', 'p value', 'statistically significant', 'significant'],
    answer:
      'It means a statistical test found a difference bigger than chance usually produces. On fair draws about 5 in 100 numbers get flagged anyway, so a flag is a curiosity, not a signal.',
    routes: [],
  },
  {
    id: 'fair-draw',
    question: 'What is a fair draw?',
    patterns: ['fair draw', 'chance alone'],
    answer:
      'One where every ball has the same chance every time. The site often shows what a fair draw would give beside a real count, because a count only means something next to what chance alone produces.',
    routes: [],
  },
  {
    id: 'share',
    question: 'What does a percentage on a chart mean?',
    patterns: ['percentage mean', 'percent mean', 'share mean', 'what percentage'],
    answer:
      'A share such as 32% means that proportion of past draws on file looked like this. It describes draws that happened; it is not a chance of winning.',
    routes: [],
  },

  // The verdict
  {
    id: 'verdict',
    question: 'What do typical, uncommon and unusual mean?',
    patterns: ['typical mean', 'uncommon mean', 'unusual mean', 'verdict mean', 'verdict'],
    answer:
      'They say how much a line looks like past draws on odd and even, sum, spread and hot/medium/cold pattern. About two thirds of past draws read typical and the rarest twentieth read unusual. Every line is equally likely to win, whichever word it gets.',
    routes: [],
  },
  {
    id: 'verdict-how',
    question: 'How is the verdict worked out?',
    patterns: ['how verdict', 'verdict worked', 'verdict calculated', 'how typical worked', 'how score'],
    answer:
      'Your line is set beside past draws four ways: odd and even, the sum, the spread, and the hot/medium/cold mix. If it looks like most past draws on those four, it reads typical; if it looks like only a few of them, uncommon or unusual. The count of numbers 32 and above and the recent bonus balls are shown for interest only. None of it changes the chance of winning, which is the same for every line.',
    routes: ['/pick'],
  },
  {
    id: 'shape-card',
    question: 'What are the checks on the shape card?',
    patterns: ['shape card', 'what checks', 'these checks'],
    answer:
      'Six checks: odd and even, sum, spread, hot/medium/cold pattern, how many numbers are 32 or above, and recent bonus balls. Each shows your line next to the share of past draws that looked the same; the last two are information only.',
    routes: ['/pick'],
  },
  {
    id: 'good-line',
    question: 'Why won\'t the site say a line is good?',
    patterns: ['good line', 'best line', 'better line', 'good number', 'best number', 'lucky', 'say good'],
    answer:
      'Because no line is better than another: every combination of six numbers has the same chance in a fair draw, 1 in 10,737,573 for the jackpot. The site describes how a line looks next to past draws and leaves the choosing to you.',
    routes: [],
  },
  {
    id: 'odds',
    question: 'What are the odds of winning?',
    patterns: ['equally likely', 'same chance', 'odds winning', 'chance winning', 'odds jackpot', 'what odds', 'chance jackpot'],
    answer:
      'Every line of six numbers has the same chance: 1 in 10,737,573 of matching all six for the jackpot. Hot, cold, typical or unusual, none of it changes that.',
    routes: [],
  },

  // The picker
  {
    id: 'picker',
    question: 'How do I build a line?',
    patterns: ['build line', 'how pick', 'wheel', 'wheels', 'shake', 'surprise me', 'use picker'],
    answer:
      'Five ways: spin the wheels, which add one number per band; pick by hand on the 1-47 grid; shake the bag for six at once; build from a shape such as a sum band; or let surprise me choose. Whatever you pick, the shape card describes it against past draws.',
    routes: ['/pick'],
  },
  {
    id: 'wheels',
    question: 'How do the wheels work?',
    patterns: ['how wheel', 'wheel work', 'more wheel', 'add wheel', 'fewer wheel', 'spin wheel'],
    answer:
      'There is a wheel for each group: hot, medium and cold. Spin one and it stops on a number from its group, which goes into your line. Use + and - to give a group more wheels or none - four hot wheels with one medium and one cold builds a line of 4 hot, 1 medium and 1 cold.',
    routes: ['/pick'],
  },
  {
    id: 'grid-colours',
    question: 'What do the colours on the grid mean?',
    patterns: ['colour', 'color', 'colours mean', 'grid mean', 'small number', 'faded'],
    answer:
      'Each number is tinted by its group and carries its initial: H for hot, M for medium, C for cold. The small figure beside the initial is how many times it came up in the last 10 draws. A faded number is one your filters have taken out; you can still tap it.',
    routes: ['/pick'],
  },
  {
    id: 'shake',
    question: 'What does shaking the bag do?',
    patterns: ['shake bag', 'shaking bag', 'what shake', 'what shaking'],
    answer:
      'It draws six numbers at random from whatever is left in the bag, just as the real draw does from 47. Shake the full bag, or take some numbers out first with the filters to suit your taste. Your line then shows how it compares with past draws.',
    routes: ['/pick'],
  },
  {
    id: 'bag-filters',
    question: 'What do the filters on the bag do?',
    patterns: ['filter', 'drop', 'why drop', 'drop number', 'take out', 'filter bag', 'bag filter'],
    answer:
      'Each filter takes some numbers out of the bag before you shake it, and the bag shows how many are left. They are there to shape the bag to your taste: numbers that came up a lot lately, numbers that have been quiet, freshness, recent bonus balls, or only high or only low numbers. Whatever is left, every line has the same chance.',
    routes: ['/pick'],
  },
  {
    id: 'drop-busy',
    question: 'Why take out numbers drawn a lot lately?',
    patterns: ['drawn lot', 'take out drawn lot', 'drop drawn', 'drawn more than', 'drop busy', 'busy number'],
    answer:
      'Some people like to leave out the numbers that have been coming up a lot, and others like to keep them in - it is a matter of taste. A number that came up often lately is exactly as likely in the next draw as any other.',
    figures: busyFigures,
    routes: ['/pick'],
  },
  {
    id: 'drop-quiet',
    question: 'Why take out numbers not drawn lately?',
    patterns: ['not drawn', 'drop not drawn', 'not drawn lately', 'quiet number', 'not drawn at all'],
    answer:
      'It is the same taste the other way round: some people like a line of numbers that have been showing up. A number that has not come up for a while is exactly as likely as any other - the balls have no memory.',
    figures: quietFigures,
    routes: ['/pick'],
  },
  {
    id: 'drop-bonus',
    question: 'Why take out numbers that were a bonus ball?',
    patterns: ['drop bonus', 'take out bonus', 'drop bonus ball', 'drop number bonus ball', 'were bonus', 'was bonus'],
    answer:
      'Some people believe a bonus ball comes back as a main number soon, so they keep recent ones in or take them out on purpose. It is a matter of taste - every line is equally likely to win.',
    figures: bonusFigures,
    routes: ['/pick'],
  },
  {
    id: 'shape-method',
    question: 'What does follow a shape do?',
    patterns: ['follow shape', 'shape do', 'what shape', 'build shape'],
    answer:
      'You choose what the line should look like - how many odd numbers, how many 32 and above, the sum, the spread - and the picker finds six numbers that fit. Each option shows the share of past draws that had that shape, so you can see which shapes are common.',
    routes: ['/pick'],
  },
  {
    id: 'surprise',
    question: 'What does surprise me do?',
    patterns: ['what surprise me', 'surprise me do', 'random line', 'at random'],
    answer:
      'It picks six numbers from all 47 at random, ignoring every filter. A random line has exactly the same chance as one chosen with care: 1 in 10,737,573 for the jackpot.',
    routes: ['/pick'],
  },
  {
    id: 'save-line',
    question: 'Can I save my line?',
    patterns: ['save line', 'save my line', 'png', 'download line'],
    answer: 'Yes - once a line is complete it can be saved as a PNG image from the line sheet.',
    routes: ['/pick'],
  },

  // The data
  {
    id: 'data-source',
    question: 'Where do the numbers come from?',
    patterns: ['data come from', 'numbers come from', 'where data', 'data source', 'source data'],
    answer:
      'From the published Irish Lotto results. Each draw is added to the history, the analysis engine rebuilds every figure on the site from it, and the pages only display what it wrote.',
    routes: [],
  },
  {
    id: 'updates',
    question: 'How often is the site updated?',
    patterns: ['how often update', 'how often updated', 'when update', 'when updated', 'site updated'],
    answer:
      'After every draw, once the result has been added and the figures rebuilt. The homepage says so when it is still waiting for the latest result.',
    routes: [],
  },
  {
    id: 'staleness',
    question: 'What does the waiting banner mean?',
    patterns: ['not in yet', 'waiting latest', 'banner', 'stale', 'out of date'],
    answer:
      'That a draw has taken place and its result is not on the site yet. The figures are complete up to the date the banner names; nothing is broken, the data is just behind.',
    routes: ['/'],
  },
  {
    id: 'about-site',
    question: 'What is this site for?',
    patterns: ['site for', 'this site', 'about site'],
    answer:
      'Picking an Irish Lotto line for fun, with a few facts about past draws beside it - hot and cold numbers, odd and even, sums, spread and the rest. It describes and never tells you what to play, because every line is equally likely to win.',
    routes: ['/'],
  },
  {
    id: 'rules',
    question: 'How does Irish Lotto work?',
    patterns: ['lotto work', 'how lotto', '6 47', 'how many ball', 'rules'],
    answer:
      'Six main numbers are drawn from 1 to 47, then a bonus ball from the 41 left. The jackpot needs all six main numbers.',
    routes: [],
  },
  {
    id: 'review-page',
    question: 'What does the review page show?',
    patterns: ['review page', 'review'],
    answer:
      'The latest draw, described the way the shape card describes a line, with the category each ball held just before the draw and the bonus window it faced.',
    routes: ['/review'],
  },
  {
    id: 'models',
    question: 'What are the generated lines?',
    patterns: ['generated line', 'model', 'models', 'machine learning'],
    answer:
      'The owner\'s own learning project: models trained on past draws, compared on the review page\'s admin half. They sit at chance, which is the correct result for a fair draw, so they are an engineering exercise and not a tip.',
    routes: [],
  },
  {
    id: 'help',
    question: 'What can I ask?',
    patterns: ['what can ask', 'what can you', 'who are you', 'help'],
    answer:
      'Anything about what this site shows: its tables, its words and its figures. Ask about a number - how often 23 has come up, when it was last drawn, what it is most often drawn with - or about the next draw.',
    routes: [],
  },

  // Out of scope
  {
    id: 'out-of-scope-play',
    question: 'What numbers should I play?',
    patterns: ['should play', 'what play', 'which numbers pick', 'numbers should', 'give me numbers', 'pick for me', 'numbers choose', 'what numbers pick'],
    answer:
      'Nobody can tell you that, because every line is equally likely to win. If you want six at random, surprise me on the Pick page will choose them.',
    routes: [],
  },
  {
    id: 'out-of-scope-predict',
    question: 'Can you predict the next draw?',
    patterns: ['predict', 'prediction', 'forecast', 'will win', 'win next', 'next winning'],
    answer:
      'No one can: each draw is independent of every draw before it, and every line has the same chance.',
    routes: [],
  },
  {
    id: 'out-of-scope-memory',
    question: 'Is a cold number going to come up soon?',
    patterns: ['due', 'overdue', 'going come up', 'bound come up', 'come up soon', 'about come up'],
    answer:
      'The balls have no memory: a number that has not come up for months is exactly as likely in the next draw as one that came up last time.',
    routes: [],
  },
  {
    id: 'out-of-scope-system',
    question: 'Is there a system to beat the lottery?',
    patterns: ['beat lottery', 'beat lotto', 'strategy', 'system win', 'increase chance', 'better odds', 'raise chance'],
    answer:
      'No system changes the odds: every line of six has the same 1 in 10,737,573 chance of the jackpot. What a line can change is how often a win is shared, which is why the site shows how many numbers are 32 or above.',
    routes: [],
  },
  {
    id: RATING_ID,
    question: 'Would you rate this line?',
    patterns: ['rate line', 'rate number', 'rating'],
    answer:
      'The site does not rate lines or numbers. It says whether a line looks typical, uncommon or unusual next to past draws, and every line is equally likely to win.',
    routes: [],
  },
  {
    id: 'out-of-scope-tickets',
    question: 'Where can I buy a ticket?',
    patterns: ['buy ticket', 'where buy', 'ticket cost', 'ticket price'],
    answer:
      'This site does not sell tickets; the National Lottery does, in shops and online.',
    routes: [],
  },
  {
    id: 'out-of-scope-other',
    question: 'Can you tell me about EuroMillions?',
    patterns: ['euromillions', 'euro millions', 'powerball', 'weather', 'joke'],
    answer: 'I only answer questions about this site and the Irish Lotto draws it shows.',
    routes: [],
  },
];

/** What the panel offers on opening, per destination. Each is answered without a model. */
export const SUGGESTED: Record<ChatRoute, string[]> = {
  '/': [
    'What was the last draw?',
    'When is the next draw?',
    'What do hot, medium and cold mean?',
    'Where do the numbers come from?',
    'What is this site for?',
  ],
  '/pick': [
    'How do I build a line?',
    'What do hot, medium and cold mean?',
    'What is freshness?',
    'What do typical, uncommon and unusual mean?',
    'What are the odds of winning?',
  ],
  '/explore': [
    'What does this table show?',
    'Why does the spread band 20-25 stop at 24?',
    'What are the six-ball and seven-ball figures?',
    'What is freshness?',
    'Which numbers are hot right now?',
  ],
  '/numbers': [
    'What does this table show?',
    'What is volatility?',
    'What is momentum?',
    'What does often drawn with mean?',
    'Which numbers are cold right now?',
  ],
  '/review': [
    'What does the review page show?',
    'What does the category on a past draw mean?',
    'What was the last draw?',
    'When is the next draw?',
  ],
};

/**
 * On /pick the questions follow the way of picking on screen: someone shaking the bag is
 * looking at its filters, not at the wheels.
 */
export const METHOD_SUGGESTED: Record<PickMethod, string[]> = {
  wheels: [
    'How do the wheels work?',
    'What do hot, medium and cold mean?',
    'Which numbers are hot right now?',
    'Is a cold number going to come up soon?',
  ],
  hand: [
    'What do the colours on the grid mean?',
    'Which numbers are cold right now?',
    'Why does the site count numbers 32 and above?',
    'How many times has 7 come up?',
  ],
  shake: [
    'What does shaking the bag do?',
    'What is freshness?',
    'Why take out numbers drawn a lot lately?',
    'Why take out numbers not drawn lately?',
    'Why take out numbers that were a bonus ball?',
  ],
  shape: [
    'What does follow a shape do?',
    'What does the odd and even check mean?',
    'Why does the spread band 20-25 stop at 24?',
    'Why does the site count numbers 32 and above?',
  ],
  surprise: [
    'What does surprise me do?',
    'What are the odds of winning?',
    'Is a cold number going to come up soon?',
    'Can I save my line?',
  ],
};

/** Asked of the tray's line once it is complete; answered from the data (intents.ts). */
export const LINE_QUESTION = 'How does my line compare with past draws?';

/** What the panel offers on opening: the page's questions, or the picking method's. */
export function suggestionsFor(
  route: ChatRoute,
  method?: PickMethod,
  lineComplete = false,
): string[] {
  if (route !== '/pick') return SUGGESTED[route];
  const questions = method ? METHOD_SUGGESTED[method] : SUGGESTED['/pick'];
  return lineComplete ? [LINE_QUESTION, ...questions] : questions;
}
