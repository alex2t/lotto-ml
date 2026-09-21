import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { Nav } from '@/components/layout/Nav';
import { Footer } from '@/components/layout/Footer';
import { THEME_SCRIPT } from '@/components/layout/ThemeToggle';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Irish Lotto - pick a line, informed by past draws',
  description:
    'What past Irish Lotto draws looked like, and a playful way to choose six numbers. Every line is equally likely to win.',
};

/**
 * The layout reads no artifacts on purpose.
 *
 * Anything it read would be needed by every route, including the error pages Next
 * prerenders at build time - and data/ is a runtime mount, absent while the image builds.
 * The draw count that belongs in the footer is passed in by the pages that have it.
 */
export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html
      lang="en"
      data-theme="light"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col font-sans">
        <Nav />
        <div className="flex-1">{children}</div>
        <Footer />
      </body>
    </html>
  );
}
