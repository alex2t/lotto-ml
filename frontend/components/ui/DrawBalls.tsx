import { Ball, type BallSize } from './Ball';
import type { DrawEntry } from '@/lib/data/types';

/**
 * A draw's six main numbers and its bonus, each tinted by the category in force
 * BEFORE that draw (F-27) - never today's.
 */
export function DrawBalls({
  draw,
  size = 'md',
  showCategory = true,
  stagger = false,
}: {
  draw: DrawEntry;
  size?: BallSize;
  showCategory?: boolean;
  stagger?: boolean;
}) {
  const detail = (n: number) =>
    draw.winning_numbers_details.find((b) => b.number === n && !b.is_bonus);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {draw.main_numbers.map((n, i) => (
        <Ball
          key={n}
          number={n}
          category={detail(n)?.category}
          size={size}
          showCategory={showCategory}
          className={stagger ? 'ball-enter' : ''}
          {...(stagger ? { style: { animationDelay: `${i * 60}ms` } } : {})}
        />
      ))}
      <span className="px-1 text-muted" aria-hidden>
        +
      </span>
      <Ball
        number={draw.bonus_number}
        isBonus
        size={size}
        className={stagger ? 'ball-enter' : ''}
        {...(stagger ? { style: { animationDelay: '360ms' } } : {})}
      />
    </div>
  );
}
