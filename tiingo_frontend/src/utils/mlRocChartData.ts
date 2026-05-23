import type { MlRocCurve } from '../api/mlBacktestTypes';

export const RANDOM_ROC_AUC = 0.5;

export function buildRocChartData(curves: MlRocCurve[]): Record<string, number>[] {
  if (!curves.length) {
    return [];
  }

  const maxLen = Math.max(...curves.map((curve) => curve.fpr.length));
  return Array.from({ length: maxLen }, (_, index) => {
    const fpr =
      curves[0].fpr[index] ??
      curves[0].fpr[curves[0].fpr.length - 1] ??
      index / Math.max(maxLen - 1, 1);
    const point: Record<string, number> = { fpr, random: fpr };
    for (const curve of curves) {
      point[`tpr_${curve.class_label}`] =
        curve.tpr[index] ?? curve.tpr[curve.tpr.length - 1] ?? 0;
    }
    return point;
  });
}
