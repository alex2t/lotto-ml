import path from 'node:path';
import { clearArtifactCache } from '@/lib/data/artifacts';

export const FIXTURE_DIR = path.join(import.meta.dirname, 'fixtures');

/** Points the data layer at the committed fixture artifacts. */
export function useFixtures(dir: string = FIXTURE_DIR): void {
  process.env.DATA_DIR = dir;
  clearArtifactCache();
}
