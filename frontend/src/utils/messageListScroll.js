export const SCROLL_FOLLOW_THRESHOLD = 80;

export function isNearBottom(
  container,
  threshold = SCROLL_FOLLOW_THRESHOLD,
) {
  if (!container) return false;

  const distanceFromBottom =
    container.scrollHeight - container.clientHeight - container.scrollTop;

  return distanceFromBottom <= threshold;
}
