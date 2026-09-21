/** Date and number formatting, shared by every page so they cannot drift. */

const LONG = new Intl.DateTimeFormat('en-IE', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

const SHORT = new Intl.DateTimeFormat('en-IE', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

function asDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

/** "Wednesday 16 September 2026" */
export function longDate(iso: string): string {
  return LONG.format(asDate(iso));
}

/** "16 Sep 2026" */
export function shortDate(iso: string): string {
  return SHORT.format(asDate(iso));
}

/** A share of draws, e.g. 13.63 -> "14%". Keeps one decimal below 10%. */
export function percent(value: number): string {
  return value >= 10 ? `${Math.round(value)}%` : `${value.toFixed(1)}%`;
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}
