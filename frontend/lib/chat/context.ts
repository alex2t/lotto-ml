/**
 * The page fact sheet (chat.md 4): a small, typed summary of what the page a question was
 * asked on is showing, built from the same lib/data/ readers the page used.
 *
 * It is never a dump of the artifacts. The model is handed these figures, already correct,
 * and asked only to put them in a sentence - so if the panel and the page ever disagree,
 * the bug is here. The focus it carries also makes the data answers route-aware: "how often
 * has it come up?" on /numbers/12 is about 12.
 */
import { latest } from '@/lib/data/draws';
import { dossier } from '@/lib/data/dossier';
import { highNumbers, oddEvenPatterns, totalDraws } from '@/lib/data/distributions';
import { pool } from '@/lib/data/pool';
import { staleness } from '@/lib/data/staleness';
import { applyRail, numberRows, railFromParams } from '@/lib/data/table';
import { describeLine, validateLine } from '@/lib/scoring/line';
import { longDate, percent } from '@/lib/format';
import type { ChatRoute } from './prepared';
import { routeOf } from './match';
import type { PageFocus } from './intents';

export interface PageContext {
  route: ChatRoute;
  focus: PageFocus;
  /** One fact per line, "- label: value". */
  sheet: string;
}

export interface PageInput {
  pathname: string;
  /** The page's query string, e.g. "?tab=statistics". */
  search?: string;
  /** The picker's tray, sent only when it holds a complete line. */
  line?: number[];
}

function facts(entries: Array<[string, string | number]>): string {
  return entries.map(([label, value]) => `- ${label}: ${value}`).join('\n');
}

function homeSheet(): string {
  const draw = latest();
  const state = staleness();
  return facts([
    ['latest draw', `${longDate(draw.draw_date)}: ${draw.main_numbers.join(', ')}, bonus ${draw.bonus_number}`],
    ['data state', state.state === 'current' ? 'up to date' : `${state.missing} draw(s) not in yet`],
    ['next draw', longDate(state.nextDraw)],
    ['draws on file', totalDraws()],
  ]);
}

function lineSheet(line: number[] | undefined): string {
  if (!line) return facts([['line in the tray', 'none complete yet'], ['draws compared', totalDraws()]]);
  const shape = describeLine(line);
  return facts([
    ['line in the tray', shape.line.join(', ')],
    ['verdict', shape.verdict],
    ...shape.checks.map((c): [string, string] => [c.title, `${c.value} - ${c.comparison}`]),
    ['draws compared', shape.drawsCompared],
  ]);
}

function exploreSheet(params: URLSearchParams): string {
  const tab = params.get('tab') ?? 'draws';
  const head: Array<[string, string | number]> = [['tab', tab], ['draws on file', totalDraws()]];
  if (tab === 'statistics') {
    const split = Object.entries(oddEvenPatterns()).map(
      ([key, b]) => `${key.replace('_', ' odd ')} even ${percent(b.percentage)}`,
    );
    const high = highNumbers();
    const byHigh = Object.entries(high.byCount).map(
      ([k, b]) => `${k}: ${percent(b.percentage)} (fair ${percent(b.fair_percentage as number)})`,
    );
    return facts([...head, ['odd/even splits', split.join('; ')], [`main numbers at ${high.highFrom} or above`, byHigh.join('; ')]]);
  }
  if (tab === 'freshness') {
    const bins = new Map<number, number[]>();
    for (const n of pool().numbers) bins.set(n.freshnessBin, [...(bins.get(n.freshnessBin) ?? []), n.number]);
    return facts([
      ...head,
      ...[...bins.entries()]
        .sort(([a], [b]) => a - b)
        .map(([bin, ns]): [string, string] => [`bin C${bin}`, ns.join(', ')]),
    ]);
  }
  const filters = [...params.entries()].filter(([k]) => k !== 'tab').map(([k, v]) => `${k}=${v}`);
  return facts([...head, ['filters', filters.length ? filters.join(', ') : 'none']]);
}

function numbersSheet(params: URLSearchParams): string {
  const filters = railFromParams((key) => params.get(key) ?? undefined);
  const active = Object.entries(filters).filter(([, v]) => v !== undefined && v !== false);
  const rows = applyRail(numberRows(), filters);
  return facts([
    ['filters', active.length ? active.map(([k, v]) => `${k}=${v}`).join(', ') : 'none'],
    ['numbers shown', rows.length === 47 ? 'all 47' : rows.map((r) => r.number).join(', ')],
  ]);
}

function dossierSheet(n: number): string {
  const d = dossier(n);
  const recent = Object.entries(d.profile.recent).map(([w, c]) => `${c} in the last ${w}`);
  return facts([
    ['number', n],
    ['category', d.profile.category],
    ['last drawn', longDate(d.profile.lastSeen.replaceAll('/', '-'))],
    ['total appearances, bonus included', d.profile.totalCount],
    ['as a main number', recent.join(', ')],
    ['freshness bin', `C${d.profile.freshnessBin}`],
    ['average gap', d.gaps.averageDraws === null ? 'none' : `${d.gaps.averageDraws.toFixed(1)} draws`],
    ['current gap', `${d.gaps.currentDraws} draws`],
    ['most often drawn with', d.partners.top.slice(0, 3).map((p) => `${p.number} (${p.count})`).join(', ')],
    ['fair-draw expectation per pair', d.partners.expected.toFixed(1)],
  ]);
}

function reviewSheet(): string {
  const draw = latest();
  return `${facts([['draw', longDate(draw.draw_date)], ['bonus', draw.bonus_number]])}\n${lineSheet(draw.main_numbers)
    .replace('line in the tray', 'main numbers')}`;
}

/** The route, focus and fact sheet for the page a question was asked on. */
export function pageContext(input: PageInput): PageContext {
  const route = routeOf(input.pathname);
  const params = new URLSearchParams(input.search ?? '');
  const line = input.line ? validateLine(input.line) : undefined;
  const numberPage = input.pathname.match(/^\/numbers\/(\d{1,2})$/);
  const number = numberPage ? Number(numberPage[1]) : undefined;
  const focusNumber = number !== undefined && number >= 1 && number <= 47 ? number : undefined;

  const sheet = {
    '/': homeSheet,
    '/pick': () => lineSheet(line),
    '/explore': () => exploreSheet(params),
    '/numbers': () => (focusNumber ? dossierSheet(focusNumber) : numbersSheet(params)),
    '/review': reviewSheet,
  }[route]();

  return { route, focus: { number: focusNumber, line: route === '/pick' ? line : undefined }, sheet };
}
