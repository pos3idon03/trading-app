import type { MlLabelMode, MlShapImportanceItem } from '../api/mlBacktestTypes';

export const SHAP_CLASS_COLORS: Record<string, string> = {
  '0': '#a3a366',
  '1': '#60a5fa',
  '2': '#f472b6',
};

export function getMlClassDisplayName(
  classLabel: string,
  labelMode: MlLabelMode,
): string {
  if (labelMode === 'ternary') {
    if (classLabel === '0') return 'Ranging';
    if (classLabel === '1') return 'Sell';
    if (classLabel === '2') return 'Buy';
    return `Class ${classLabel}`;
  }
  if (classLabel === '0') return 'Down';
  if (classLabel === '1') return 'Up';
  return `Class ${classLabel}`;
}

export function discoverShapClassLabels(items: MlShapImportanceItem[]): string[] {
  const labels = new Set(items.map((item) => item.class_label));
  return [...labels].sort((left, right) => Number(left) - Number(right));
}

export function buildShapChartData(
  items: MlShapImportanceItem[],
  classLabels: string[],
  topN = 12,
): Record<string, number | string>[] {
  const byFeature: Record<string, Record<string, number | string>> = {};
  for (const item of items) {
    if (!byFeature[item.feature]) {
      byFeature[item.feature] = { feature: item.feature };
    }
    byFeature[item.feature][`class_${item.class_label}`] = item.mean_abs_shap;
  }

  return Object.values(byFeature)
    .map((row) => ({
      ...row,
      total: classLabels.reduce(
        (sum, classLabel) => sum + Number(row[`class_${classLabel}`] ?? 0),
        0,
      ),
    }))
    .sort((left, right) => Number(right.total) - Number(left.total))
    .slice(0, topN);
}
