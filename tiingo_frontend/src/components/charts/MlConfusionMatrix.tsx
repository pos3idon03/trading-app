import { confusionMatrixLabels, confusionMatrixMaxValue } from '../../utils/mlBacktestEvaluation';

interface MlConfusionMatrixProps {
  matrix: number[][];
}

export default function MlConfusionMatrix({ matrix }: MlConfusionMatrixProps) {
  const { rows, cols } = confusionMatrixLabels();
  const maxValue = confusionMatrixMaxValue(matrix);

  if (!matrix.length || matrix.every((row) => row.every((cell) => cell === 0))) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-xs border border-slate-800 rounded-lg bg-surface-900">
        No classification labels available for confusion matrix.
      </div>
    );
  }

  const cellColor = (value: number) => {
    const intensity = value / maxValue;
    const alpha = 0.15 + intensity * 0.65;
    return `rgba(99, 102, 241, ${alpha})`;
  };

  return (
    <div className="border border-slate-800 rounded-lg bg-surface-900 p-3">
      <p className="text-xs font-medium text-slate-300 mb-2">Confusion matrix</p>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border-collapse">
          <thead>
            <tr>
              <th className="p-2" />
              {cols.map((label) => (
                <th key={label} className="p-2 text-xs text-slate-400 font-normal text-center">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, rowIndex) => (
              <tr key={rows[rowIndex]}>
                <th className="p-2 text-xs text-slate-400 font-normal text-left whitespace-nowrap">
                  {rows[rowIndex]}
                </th>
                {row.map((value, colIndex) => (
                  <td
                    key={`${rowIndex}-${colIndex}`}
                    className="p-2 text-center text-slate-100 font-medium border border-slate-800"
                    style={{ backgroundColor: cellColor(value) }}
                  >
                    {value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
