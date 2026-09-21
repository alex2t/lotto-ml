/**
 * Serves the standalone build - exactly what Dockerfile.web runs in production.
 *
 * `next start` does not serve an `output: 'standalone'` build (Next says so on every
 * build), so the e2e suite runs the real server with its static files copied beside it,
 * the same two copies the Dockerfile makes.
 */
import { cpSync, existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';

const root = path.join(import.meta.dirname, '..');
const standalone = path.join(root, '.next', 'standalone');

if (!existsSync(standalone)) {
  console.error('No standalone build. Run: npm run build');
  process.exit(1);
}

cpSync(path.join(root, '.next', 'static'), path.join(standalone, '.next', 'static'), {
  recursive: true,
});
if (existsSync(path.join(root, 'public'))) {
  cpSync(path.join(root, 'public'), path.join(standalone, 'public'), { recursive: true });
}

const server = spawn(process.execPath, [path.join(standalone, 'server.js')], {
  stdio: 'inherit',
  env: process.env,
});
server.on('exit', (code) => process.exit(code ?? 0));
