'use client';

import { useState } from 'react';
import { Download, LogIn } from 'lucide-react';

/** The owner's login. It unlocks one thing: downloading the data bundle. */
export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [signedIn, setSignedIn] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    setBusy(false);
    if (response.ok) {
      setSignedIn(true);
      return;
    }
    setMessage(response.status === 429 ? 'Too many attempts' : 'Invalid credentials');
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-semibold">
        <LogIn className="h-6 w-6" aria-hidden />
        Admin
      </h1>
      {signedIn ? (
        <a
          className="flex items-center justify-center gap-2 rounded bg-neutral-900 p-2 text-white dark:bg-neutral-100 dark:text-neutral-900"
          href="/api/download/data"
        >
          <Download className="h-4 w-4" aria-hidden />
          Download the data bundle
        </a>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            Username
            <input
              className="rounded border border-neutral-300 p-2 dark:border-neutral-700 dark:bg-neutral-900"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Password
            <input
              className="rounded border border-neutral-300 p-2 dark:border-neutral-700 dark:bg-neutral-900"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button
            className="rounded bg-neutral-900 p-2 text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
            disabled={busy}
            type="submit"
          >
            {busy ? 'Signing in' : 'Sign in'}
          </button>
        </form>
      )}
      {message && <p role="alert" className="text-sm text-red-600">{message}</p>}
    </main>
  );
}
