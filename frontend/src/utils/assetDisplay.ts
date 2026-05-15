/** Label for asset `<select>` options: symbol, plus name only when it adds information. */
export function formatAssetOptionLabel(asset: {
  symbol: string;
  name: string | null;
}): string {
  const raw = asset.name?.trim();
  if (!raw) return asset.symbol;
  if (raw.toUpperCase() === asset.symbol.toUpperCase()) return asset.symbol;
  return `${asset.symbol} — ${raw}`;
}
