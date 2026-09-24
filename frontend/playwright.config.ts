import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

// Playwright loads this file as CommonJS, so __dirname is the portable choice here.

/**
 * End-to-end tests against a real build, reading the real artifacts.
 *
 * The site must be provable on the PC before it is deployed (web.md 7), so this starts the
 * production server itself rather than assuming one is running.
 */
const PORT = Number(process.env.E2E_PORT ?? 3210);

export default defineConfig({
  testDir: './test/e2e',
  fullyParallel: true,
  // More browsers than this starve each other on a laptop and turn real assertions into
  // timeouts; the server itself serves every page in under 0.2s at this concurrency.
  workers: process.env.CI ? 2 : 2,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? 'list' : [['list']],
  // A loaded laptop - a container serving, a build running - pushes a page past the 5s
  // default and turns a real assertion into a timeout. Ten seconds still fails fast.
  expect: { timeout: 10_000 },
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: 'node scripts/e2e-server.mjs',
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      PORT: String(PORT),
      HOSTNAME: '127.0.0.1',
      DATA_DIR: process.env.DATA_DIR ?? path.resolve(__dirname, '..', 'data'),
      SESSION_SECRET: process.env.SESSION_SECRET ?? 'e2e-secret-e2e-secret-e2e-secret-abc',
      ADMIN_USERNAME: 'e2e',
      // No model in e2e: the chat panel must answer from its free layers alone, with no
      // request leaving the box (chat.md 9).
      OPENROUTER_API_KEY: '',
      // bcrypt hash of "e2e-password", cost 10.
      ADMIN_PASSWORD_HASH:
        process.env.E2E_PASSWORD_HASH ??
        '$2b$10$.Ulx3mAsobvcUL2l4gHXvuptPwKJ.M3TFSMM3Z7gMxReOEy1d1iHC',
    },
  },
});
