/** Format indicator readings for live terminal / execution UI. */
export function formatIndicatorReading(
  value: number | null | undefined,
  label: string | null | undefined,
): string {
  if (value == null) return '—';
  if (label == null || label === '') {
    return Number(value.toFixed(4)).toString();
  }
  const formatted = Number(value.toFixed(4)).toString();
  return `${label}: ${formatted}`;
}
