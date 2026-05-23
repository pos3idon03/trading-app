import { useState } from 'react';
import { mlBacktestApi } from '../../api/endpoints';
import type { MlParams, MlTrainingExportScope } from '../../api/mlBacktestTypes';
import Spinner from '../Spinner';

interface MlTrainingExportDialogProps {
  symbol: string;
  modelType: string;
  params: MlParams;
  timeframe: string;
  start?: string;
  end?: string;
  disabled?: boolean;
}

function downloadBase64Excel(filename: string, contentBase64: string) {
  const binary = atob(contentBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const blob = new Blob([bytes], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function MlTrainingExportDialog({
  symbol,
  modelType,
  params,
  timeframe,
  start,
  end,
  disabled = false,
}: MlTrainingExportDialogProps) {
  const [scope, setScope] = useState<MlTrainingExportScope>('all_labeled');
  const [sampleSize, setSampleSize] = useState(500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await mlBacktestApi.trainingDataExport({
        symbol,
        model_type: modelType,
        params,
        timeframe,
        start,
        end,
        scope,
        sample_size: sampleSize,
      });
      downloadBase64Excel(response.filename, response.content_base64);
      setMessage(`Exported ${response.row_count} rows.`);
      if (response.warnings?.length) {
        setMessage(`${response.row_count} rows exported. ${response.warnings.join(' ')}`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Export failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-surface-950/50 p-4 space-y-3">
      <h4 className="text-sm font-medium text-slate-200">Export training data (Excel)</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Scope</span>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as MlTrainingExportScope)}
            disabled={disabled || loading}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            <option value="all_labeled">All labeled rows</option>
            <option value="sample">Random sample</option>
            <option value="oos_only">OOS walk-forward rows</option>
          </select>
        </label>
        {scope === 'sample' && (
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Sample size</span>
            <input
              type="number"
              min={50}
              max={10000}
              value={sampleSize}
              onChange={(e) => setSampleSize(Number(e.target.value))}
              disabled={disabled || loading}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        )}
      </div>
      <button
        type="button"
        onClick={handleExport}
        disabled={disabled || loading}
        className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white text-sm"
      >
        {loading ? 'Exporting…' : 'Download Excel'}
      </button>
      {loading && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Spinner />
          Building feature matrix…
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
      {message && <p className="text-xs text-emerald-300">{message}</p>}
    </div>
  );
}
