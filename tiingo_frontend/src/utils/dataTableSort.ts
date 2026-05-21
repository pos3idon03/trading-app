export type SortDirection = 'asc' | 'desc';

export type SortValue = string | number | null | undefined;

export function compareSortValues(a: SortValue, b: SortValue, direction: SortDirection): number {
  const aNull = a == null || (typeof a === 'number' && Number.isNaN(a));
  const bNull = b == null || (typeof b === 'number' && Number.isNaN(b));
  if (aNull && bNull) return 0;
  if (aNull) return 1;
  if (bNull) return -1;

  const cmp =
    typeof a === 'number' && typeof b === 'number'
      ? a - b
      : String(a).localeCompare(String(b), undefined, { sensitivity: 'base' });

  return direction === 'asc' ? cmp : -cmp;
}

export function sortRows<T>(
  rows: T[],
  sortValue: (row: T) => SortValue,
  direction: SortDirection,
): T[] {
  return [...rows].sort((a, b) => compareSortValues(sortValue(a), sortValue(b), direction));
}

export function maPositionSortValue(position: string): number {
  if (position === 'Above') return 2;
  if (position === 'At') return 1;
  if (position === 'Below') return 0;
  return -1;
}
