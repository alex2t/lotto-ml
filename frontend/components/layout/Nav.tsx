'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ThemeToggle } from './ThemeToggle';

const LINKS = [
  { href: '/pick', label: 'Pick' },
  { href: '/explore', label: 'Explore' },
  { href: '/numbers', label: 'Numbers' },
  { href: '/review', label: 'Review' },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center gap-2 px-4 py-3">
        <Link href="/" className="mr-auto text-sm font-semibold tracking-wide">
          IRISH LOTTO
        </Link>
        <ul className="flex items-center gap-1 text-sm">
          {LINKS.map((link) => {
            const active =
              pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={active ? 'page' : undefined}
                  className={`rounded-full px-3 py-1.5 ${
                    active
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted hover:text-foreground'
                  }`}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
        <ThemeToggle />
      </nav>
    </header>
  );
}
