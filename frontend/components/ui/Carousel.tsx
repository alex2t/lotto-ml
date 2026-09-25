'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react';

const AUTOPLAY_MS = 5000;
const SWIPE_PX = 50;

export interface CarouselSlide {
  id: string;
  label: string;
  /** Shows a dot on the slide's indicator - the filter on that slide is on. */
  marked?: boolean;
  content: React.ReactNode;
}

/**
 * A hero carousel: side arrows, indicator bars, arrow keys and swipe, wrapping at both
 * ends. It moves every 5 seconds until someone hovers, focuses or touches a control on a
 * slide - once they are using a slide it stays put. Reduced motion never autoplays.
 *
 * The slides share one grid cell, so the carousel is as tall as its tallest slide and
 * wrapping from the last to the first is the same cross-fade as any other step.
 */
export function Carousel({
  label,
  slides,
  start = 0,
}: {
  label: string;
  slides: CarouselSlide[];
  start?: number;
}) {
  const count = slides.length;
  const [index, setIndex] = useState(start);
  const [playing, setPlaying] = useState(true);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const touchX = useRef<number | null>(null);

  const go = useCallback((i: number) => setIndex(((i % count) + count) % count), [count]);

  const running = playing && !hovered && !focused;
  useEffect(() => {
    if (!running || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setTimeout(() => go(index + 1), AUTOPLAY_MS);
    return () => window.clearTimeout(timer);
  }, [running, index, go]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowLeft') go(index - 1);
    else if (e.key === 'ArrowRight') go(index + 1);
    else return;
    e.preventDefault();
  }

  function onTouchEnd(e: React.TouchEvent) {
    if (touchX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    touchX.current = null;
    if (Math.abs(dx) >= SWIPE_PX) go(dx < 0 ? index + 1 : index - 1);
  }

  const arrow = (step: -1 | 1, className: string) => {
    const Icon = step < 0 ? ChevronLeft : ChevronRight;
    return (
      <button
        type="button"
        onClick={() => go(index + step)}
        aria-label={step < 0 ? 'Previous card' : 'Next card'}
        className={`items-center justify-center rounded-full border border-border bg-surface-raised text-foreground shadow-md transition hover:scale-105 hover:border-foreground ${className}`}
      >
        <Icon className="h-5 w-5" aria-hidden />
      </button>
    );
  };

  return (
    <section
      aria-roledescription="carousel"
      aria-label={label}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);
      }}
      className="group relative flex flex-col gap-3 rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <div className="relative">
        <div
          className="grid overflow-hidden rounded-2xl border border-border shadow-sm"
          aria-live={running ? 'off' : 'polite'}
          onTouchStart={(e) => {
            touchX.current = e.touches[0].clientX;
          }}
          onTouchEnd={onTouchEnd}
          // Using a control on a slide means reading it: the carousel stops moving.
          onClickCapture={() => setPlaying(false)}
        >
          {slides.map((slide, i) => {
            const on = i === index;
            return (
              <div
                key={slide.id}
                role="group"
                aria-roledescription="slide"
                aria-label={`${i + 1} of ${count}: ${slide.label}`}
                inert={!on}
                className={`[grid-area:1/1] transition-[opacity,transform,visibility] duration-500 ease-out ${
                  on ? 'visible scale-100 opacity-100' : 'invisible scale-[0.98] opacity-0'
                }`}
              >
                {slide.content}
              </div>
            );
          })}
        </div>
        {arrow(-1, 'absolute top-1/2 -left-4 hidden h-10 w-10 -translate-y-1/2 sm:flex')}
        {arrow(1, 'absolute top-1/2 -right-4 hidden h-10 w-10 -translate-y-1/2 sm:flex')}
      </div>

      <div className="flex items-center gap-2">
        {arrow(-1, 'flex h-9 w-9 shrink-0 sm:hidden')}
        <div className="grid flex-1 gap-1.5" style={{ gridTemplateColumns: `repeat(${count}, 1fr)` }}>
          {slides.map((slide, i) => {
            const on = i === index;
            return (
              <button
                key={slide.id}
                type="button"
                onClick={() => go(i)}
                aria-label={`Show card ${i + 1}: ${slide.label}${slide.marked ? ' (on)' : ''}`}
                aria-current={on}
                className="flex flex-col gap-1.5 py-1 text-left"
              >
                <span className="relative h-1.5 w-full overflow-hidden rounded-full bg-border">
                  {on && (
                    <span
                      key={`${index}-${running}`}
                      className={`absolute inset-y-0 left-0 rounded-full bg-accent ${
                        running ? 'carousel-progress' : 'w-full'
                      }`}
                      style={{ animationDuration: `${AUTOPLAY_MS}ms` }}
                    />
                  )}
                </span>
                <span
                  className={`hidden items-center gap-1 truncate text-xs md:flex ${
                    on ? 'font-semibold text-foreground' : 'text-muted'
                  }`}
                  aria-hidden
                >
                  {slide.marked && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />}
                  {slide.label}
                </span>
              </button>
            );
          })}
        </div>
        {arrow(1, 'flex h-9 w-9 shrink-0 sm:hidden')}
        <button
          type="button"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? 'Stop the cards moving' : 'Move through the cards'}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border text-muted hover:border-foreground"
        >
          {playing ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
        </button>
      </div>
    </section>
  );
}
