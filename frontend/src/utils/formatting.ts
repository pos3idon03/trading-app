export function fmt(v: number | undefined | null, decimals = 4, suffix = ''): string {
  if (v === null || v === undefined) return '—';
  return `${v.toFixed(decimals)}${suffix}`;
}

export function fmtPct(v: number | undefined | null): string {
  if (v === null || v === undefined) return '—';
  return `${(v * 100).toFixed(2)}%`;
}
