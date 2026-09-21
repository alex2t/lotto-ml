/**
 * A distribution as bars, rendered on the server.
 *
 * Every chart has the numbers behind it a click away, which is both the accessible route
 * and the honest one (web.md 5.4). No client JavaScript: these distributions are static
 * for a given set of artifacts.
 */
export interface Bar {
  key: string;
  label: string;
  value: number;
  /** A second value drawn as an outline, e.g. what a fair draw would give (F-38). */
  reference?: number;
  highlight?: boolean;
}

export function BarChart({
  bars,
  caption,
  unit = '%',
  referenceLabel,
}: {
  bars: Bar[];
  caption: string;
  unit?: string;
  referenceLabel?: string;
}) {
  const max = Math.max(...bars.map((b) => Math.max(b.value, b.reference ?? 0)), 1);

  return (
    <figure className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        {bars.map((bar) => (
          <div key={bar.key} className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-2">
            <span className="truncate text-xs text-muted" title={bar.label}>
              {bar.label}
            </span>
            <span className="relative flex h-4 items-center">
              <span
                className={`h-3 rounded-sm ${bar.highlight ? 'bg-accent' : 'bg-cold'}`}
                style={{ width: `${(bar.value / max) * 100}%` }}
              />
              {bar.reference !== undefined && (
                <span
                  className="absolute top-0 h-4 border-l-2 border-hot"
                  style={{ left: `${(bar.reference / max) * 100}%` }}
                  title={`${referenceLabel ?? 'reference'}: ${bar.reference.toFixed(1)}${unit}`}
                />
              )}
            </span>
            <span className="text-right text-xs tabular-nums text-muted">
              {bar.value.toFixed(1)}
              {unit}
            </span>
          </div>
        ))}
      </div>

      <figcaption className="text-xs text-muted">
        {caption}
        {referenceLabel && (
          <>
            {' '}
            The vertical mark is {referenceLabel}.
          </>
        )}
      </figcaption>

      <details className="text-xs">
        <summary className="cursor-pointer text-muted">Show the numbers</summary>
        <table className="mt-2 w-full text-left">
          <thead>
            <tr className="text-muted">
              <th className="py-1 font-medium">Value</th>
              <th className="py-1 font-medium">Share</th>
              {referenceLabel && <th className="py-1 font-medium">{referenceLabel}</th>}
            </tr>
          </thead>
          <tbody>
            {bars.map((bar) => (
              <tr key={bar.key} className="border-t border-border">
                <td className="py-1">{bar.label}</td>
                <td className="py-1 tabular-nums">
                  {bar.value.toFixed(2)}
                  {unit}
                </td>
                {referenceLabel && (
                  <td className="py-1 tabular-nums">
                    {bar.reference === undefined ? '-' : `${bar.reference.toFixed(2)}${unit}`}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
