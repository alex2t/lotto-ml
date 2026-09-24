/**
 * The line in the picker's tray, for the chat panel to send with a question on /pick.
 *
 * The tray is client state inside Picker, and the panel lives in the nav, so the picker
 * publishes its line here and the panel reads it when a question is asked.
 */
let current: number[] = [];

export function setCurrentLine(line: number[]): void {
  current = line;
}

export function currentLine(): number[] {
  return current;
}
