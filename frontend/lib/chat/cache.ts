/**
 * Layer 2 of the chat panel: model answers already given (chat.md 3).
 *
 * Keyed on the page, the question, the fact sheet and history the model was given, and the
 * artifacts' mtime - the same invalidation lib/data/artifacts.ts uses, so a drawpick.py
 * rebuild drops every answer about the old numbers. That is correctness, not an optimisation.
 */
import { artifactsVersion } from '@/lib/data/artifacts';
import { normalise } from './match';
import type { Turn } from './prompt';

export const MAX_ENTRIES = 300;

const answers = new Map<string, string>();

export function cacheKey(route: string, question: string, sheet: string, history: Turn[]): string {
  return JSON.stringify([route, normalise(question), sheet, history, artifactsVersion()]);
}

export function cachedAnswer(key: string): string | undefined {
  return answers.get(key);
}

/** Stores an answer, dropping the oldest once the cache is full. */
export function remember(key: string, answer: string): void {
  answers.set(key, answer);
  if (answers.size > MAX_ENTRIES) answers.delete(answers.keys().next().value!);
}

export function clearChatCache(): void {
  answers.clear();
}
