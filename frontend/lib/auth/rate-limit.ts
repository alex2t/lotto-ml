/**
 * Login rate limiting. One account, one process - an in-memory counter is enough.
 */
const attempts = new Map<string, number[]>();

export const WINDOW_MS = 15 * 60 * 1000;
export const MAX_ATTEMPTS = 10;

/** Records an attempt and reports whether the caller is over the limit. */
export function tooManyAttempts(key: string, now = Date.now()): boolean {
  const recent = (attempts.get(key) ?? []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  attempts.set(key, recent);
  return recent.length > MAX_ATTEMPTS;
}

export function resetAttempts(key?: string): void {
  if (key === undefined) attempts.clear();
  else attempts.delete(key);
}
