import type { NextConfig } from 'next';
import path from 'node:path';

const nextConfig: NextConfig = {
  // A small Docker image: the runner stage copies .next/standalone only.
  output: 'standalone',
  // frontend/ is a project of its own inside the repo; without this Turbopack looks upwards
  // for a lockfile and finds the one in the user's home directory.
  turbopack: { root: path.resolve(import.meta.dirname) },
};

export default nextConfig;
