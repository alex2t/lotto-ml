import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, '.') },
  },
  test: {
    environment: 'node',
    include: ['test/**/*.test.ts'],
    // The integration test runs drawpick.py and takes about 40s; it has its own config.
    exclude: ['test/integration/**'],
  },
});
