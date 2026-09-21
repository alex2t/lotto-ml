export function Badge({
  children,
  tone = 'neutral',
}: {
  children: React.ReactNode;
  tone?: 'neutral' | 'hot' | 'medium' | 'cold' | 'bonus';
}) {
  const tones = {
    neutral: 'bg-surface text-muted border-border',
    hot: 'bg-hot-soft text-hot border-hot',
    medium: 'bg-medium-soft text-medium border-medium',
    cold: 'bg-cold-soft text-cold border-cold',
    bonus: 'bg-bonus-soft text-bonus border-bonus',
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
