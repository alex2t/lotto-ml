/**
 * Sliding-window rate limits, in memory. One process serves the site, so a counter per key
 * is enough. Login uses one; the chat panel's model layer uses two (lib/chat/budget.ts).
 */

export interface Limiter {
  /** Records a hit and reports whether the key is now over the limit. */
  hit(key: string, now?: number): boolean;
  reset(key?: string): void;
}

export function limiter(windowMs: number, max: number): Limiter {
  const hits = new Map<string, number[]>();
  return {
    hit(key, now = Date.now()) {
      const recent = (hits.get(key) ?? []).filter((t) => now - t < windowMs);
      recent.push(now);
      hits.set(key, recent);
      return recent.length > max;
    },
    reset(key) {
      if (key === undefined) hits.clear();
      else hits.delete(key);
    },
  };
}

export const WINDOW_MS = 15 * 60 * 1000;
export const MAX_ATTEMPTS = 10;

const login = limiter(WINDOW_MS, MAX_ATTEMPTS);

/** Records a login attempt and reports whether the caller is over the limit. */
export function tooManyAttempts(key: string, now = Date.now()): boolean {
  return login.hit(key, now);
}

export function resetAttempts(key?: string): void {
  login.reset(key);
}
