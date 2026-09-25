'use client';

import { useSyncExternalStore } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'light' | 'dark';

const CHANGED = 'themechange';

/** The theme lives on <html data-theme>, so React subscribes to it rather than mirroring it. */
function subscribe(onChange: () => void): () => void {
  window.addEventListener(CHANGED, onChange);
  return () => window.removeEventListener(CHANGED, onChange);
}

function current(): Theme {
  return (document.documentElement.dataset.theme as Theme) ?? 'dark';
}

/** Light or dark, stored per viewer. Dark - the Observatory palette - until someone chooses. */
export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, current, () => 'dark' as Theme);

  function toggle() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem('theme', next);
    } catch {
      // A blocked storage API must not break the toggle for this visit.
    }
    window.dispatchEvent(new Event(CHANGED));
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="rounded-full border border-border p-2 text-muted hover:text-foreground"
      aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {theme === 'dark' ? (
        <Sun className="h-4 w-4" aria-hidden />
      ) : (
        <Moon className="h-4 w-4" aria-hidden />
      )}
    </button>
  );
}

/** Applies the stored theme before first paint, so there is no flash of the wrong one. */
export const THEME_SCRIPT = `(function(){try{document.documentElement.dataset.theme=localStorage.getItem('theme')==='light'?'light':'dark';}catch(e){document.documentElement.dataset.theme='dark';}})();`;
