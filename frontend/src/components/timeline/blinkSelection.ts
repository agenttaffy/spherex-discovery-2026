/** Choose a pair around the selected observation, without inventing exposures. */
export function initialBlinkPair(index: number, count: number): [number, number] {
  if (count < 2) return [0, 0];
  const first = Math.max(0, Math.min(index, count - 1));
  return [first, first < count - 1 ? first + 1 : first - 1];
}

export function nextBlinkIndex(current: number, first: number, second: number): number {
  return current === first ? second : first;
}
