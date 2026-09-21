import Link from 'next/link';

/**
 * The honest framing, on every page.
 *
 * The equal-chance sentence is the one tests/test_site_wording.py checks for, and it moves
 * across verbatim. It is a constant, not a figure read from an artifact, so the footer
 * renders on every route - including the ones Next prerenders before data/ is mounted.
 */
export function Footer() {
  return (
    <footer className="mt-auto border-t border-border">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 px-4 py-6 text-sm text-muted">
        <p>
          Every line is equally likely to win. This site shows what past draws looked
          like - nothing more.
        </p>
        <Link href="/login" className="underline w-fit">
          Admin
        </Link>
      </div>
    </footer>
  );
}
