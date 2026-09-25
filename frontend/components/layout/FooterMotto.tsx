'use client';

import { usePathname } from 'next/navigation';

/** The site's motto, on every page but the home page, which carries its own tagline. */
export function FooterMotto() {
  if (usePathname() === '/') return null;

  return (
    <p className="text-base font-light italic text-foreground">
      Taming pure chance is impossible. Mapping it is fascinating.{' '}
      <span className="not-italic font-normal text-gold">
        Welcome to the observatory of coincidences.
      </span>
    </p>
  );
}
