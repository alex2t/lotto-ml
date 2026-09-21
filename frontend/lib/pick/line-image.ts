/**
 * Draws a line as a PNG, in the browser, so someone can keep or send it.
 *
 * Canvas rather than a screenshot library: six balls and two lines of text do not need one,
 * and nothing about the page needs to be serialised to draw them. Colours are read from the
 * live CSS custom properties, so the image follows the theme the viewer is actually in.
 */
import type { Category } from '../data/types';

const BALL = 96;
const GAP = 16;
const PADDING = 32;
const TITLE = 34;
const CAPTION = 30;

function cssColour(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export interface LineImage {
  numbers: number[];
  categoryOf: (n: number) => Category | undefined;
  verdict: string;
  drawDate: string;
}

/** Renders the line and hands back a blob, or null if canvas is unavailable. */
export async function drawLineImage(line: LineImage): Promise<Blob | null> {
  const width = PADDING * 2 + line.numbers.length * BALL + (line.numbers.length - 1) * GAP;
  const height = PADDING * 2 + TITLE + BALL + CAPTION + GAP * 2;

  const canvas = document.createElement('canvas');
  const scale = Math.min(window.devicePixelRatio || 1, 3);
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.scale(scale, scale);

  const background = cssColour('--background', '#ffffff');
  const foreground = cssColour('--foreground', '#171717');
  const muted = cssColour('--muted', '#5f6169');
  const tones: Record<Category | 'none', [string, string]> = {
    hot: [cssColour('--hot-soft', '#ffedd5'), cssColour('--hot', '#c2410c')],
    medium: [cssColour('--medium-soft', '#eceef1'), cssColour('--medium', '#6b6f76')],
    cold: [cssColour('--cold-soft', '#dbeafe'), cssColour('--cold', '#1d4ed8')],
    none: [cssColour('--surface', '#f6f6f7'), foreground],
  };

  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = muted;
  ctx.font = '600 16px system-ui, sans-serif';
  ctx.textBaseline = 'top';
  ctx.fillText('MY IRISH LOTTO LINE', PADDING, PADDING);

  const top = PADDING + TITLE + GAP;
  line.numbers.forEach((n, i) => {
    const [fill, stroke] = tones[line.categoryOf(n) ?? 'none'];
    const x = PADDING + i * (BALL + GAP);
    ctx.beginPath();
    ctx.arc(x + BALL / 2, top + BALL / 2, BALL / 2 - 3, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = stroke;
    ctx.stroke();

    ctx.fillStyle = stroke;
    ctx.font = '700 34px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(n).padStart(2, '0'), x + BALL / 2, top + BALL / 2);
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
  });

  ctx.fillStyle = muted;
  ctx.font = '400 14px system-ui, sans-serif';
  ctx.fillText(
    `${line.verdict} - every line is equally likely to win. Draws to ${line.drawDate}.`,
    PADDING,
    top + BALL + GAP,
  );

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), 'image/png'));
}

/** Saves the blob under a self-describing name. */
export function saveImage(blob: Blob, numbers: number[]): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `lotto-line-${numbers.join('-')}.png`;
  link.click();
  URL.revokeObjectURL(url);
}
