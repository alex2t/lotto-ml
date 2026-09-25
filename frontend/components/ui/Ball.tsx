import type { Category } from '@/lib/data/types';

/**
 * The lottery ball - the atom of the UI, at three sizes.
 *
 * Category is never conveyed by colour alone: the ball carries its initial (H/M/C) and
 * a text label for screen readers (web.md 5.4).
 */
export type BallSize = 'sm' | 'md' | 'lg';

const SIZES: Record<BallSize, string> = {
  sm: 'h-9 w-9 text-sm',
  md: 'h-12 w-12 text-base',
  lg: 'h-16 w-16 text-2xl sm:h-20 sm:w-20 sm:text-3xl',
};

/**
 * A solid fill with the category's ink for the number - shared by the ball, the 1-47 grid and
 * the bag, so every number on the site reads the same way.
 */
export const BALL_TONE: Record<Category | 'bonus' | 'none', string> = {
  hot: 'bg-hot text-hot-ink border-hot',
  medium: 'bg-medium text-medium-ink border-medium',
  cold: 'bg-cold text-cold-ink border-cold',
  bonus: 'bg-bonus text-bonus-ink border-bonus',
  none: 'bg-surface-raised text-foreground border-border',
};

export const CATEGORY_INITIAL: Record<Category, string> = {
  hot: 'H',
  medium: 'M',
  cold: 'C',
};

interface BallProps {
  number: number;
  category?: Category;
  isBonus?: boolean;
  size?: BallSize;
  /** Shows the H/M/C initial under the number. */
  showCategory?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export function Ball({
  number,
  category,
  isBonus = false,
  size = 'md',
  showCategory = false,
  className = '',
  style,
}: BallProps) {
  const tone = isBonus ? 'bonus' : (category ?? 'none');
  const label = isBonus
    ? `bonus ball ${number}`
    : category
      ? `${number}, ${category}`
      : String(number);

  return (
    <span
      className={`inline-flex flex-col items-center justify-center rounded-full border-2 font-bold tabular-nums ball-shade ${SIZES[size]} ${BALL_TONE[tone]} ${className}`}
      style={style}
      aria-label={label}
    >
      <span aria-hidden>{String(number).padStart(2, '0')}</span>
      {showCategory && category && (
        <span className="text-[0.6em] font-medium leading-none opacity-80" aria-hidden>
          {CATEGORY_INITIAL[category]}
        </span>
      )}
    </span>
  );
}
