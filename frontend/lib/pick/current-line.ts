/**
 * The picker's state that the chat panel needs: the line in the tray, sent with a question
 * on /pick, and the way of picking on screen, which chooses the suggested questions.
 *
 * Both are client state inside Picker, and the panel lives in the nav, so the picker
 * publishes them here and the panel reads them when it opens or a question is asked.
 */
export type PickMethod = 'wheels' | 'hand' | 'shake' | 'shape' | 'surprise';

let current: number[] = [];
let method: PickMethod | undefined;

export function setCurrentLine(line: number[]): void {
  current = line;
}

export function currentLine(): number[] {
  return current;
}

export function setCurrentMethod(value: PickMethod | undefined): void {
  method = value;
}

export function currentMethod(): PickMethod | undefined {
  return method;
}
