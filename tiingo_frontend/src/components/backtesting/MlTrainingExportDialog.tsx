import { useState } from 'react';
import { mlBacktestApi } from '../../api/endpoints';
import type {
  MlCompareResult,
  MlDataPreviewResponse,
  MlExportFormat,
  MlLabelSearchResult,
  MlParams,
  MlThresholdSearchResult,
  MlTrainingExportScope,
} from '../../api/mlBacktestTypes';
import Spinner from '../Spinner';

interface MlTrainingExportDialogProps {
  symbol: string;
  modelType: string;
  params: MlParams;
  timeframe: string;
  start?: string;
  end?: string;
  disabled?: boolean;
  dataPreview?: MlDataPreviewResponse | null;
  labelSearchResults?: MlLabelSearchResult[];
  thresholdResults?: MlThresholdSearchResult[];
  compareResults?: MlCompareResult[];
  configSnapshot?: Record<string, unknown>;
  runId?: string;
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
  dataPreview = null,
  labelSearchResults = [],
  thresholdResults = [],
  compareResults = [],
  configSnapshot,
  runId,
}: MlTrainingExportDialogProps) {
  const [exportFormat, setExportFormat] = useState<MlExportFormat>('training_only');
  const [scope, setScope] = useState<MlTrainingExportScope>('all_labeled');
  const [sampleSize, setSampleSize] = useState(500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [sheetSummary, setSheetSummary] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    setMessage(null);
    setSheetSummary(null);
    try {
      if (exportFormat === 'full_workbook') {
        const response = await mlBacktestApi.workbookExport({
          symbol,
          model_type: modelType,
          params,
          timeframe,
          start,
          end,
          training_scope: scope,
          sample_size: sampleSize,
          run_id: runId,
          data_preview: dataPreview ?? undefined,
          label_search_results: labelSearchResults.length > 0 ? labelSearchResults : undefined,
          threshold_search_results: thresholdResults.length > 0 ? thresholdResults : undefined,
          compare_results: compareResults.length > 0 ? compareResults : undefined,
          config_snapshot: configSnapshot,
        });
        downloadBase64Excel(response.filename, response.content_base64);
        const sheetNames = response.sheets.map((sheet) => sheet.name).join(', ');
        setMessage(`Exported workbook with ${response.sheets.length} sheets.`);
        setSheetSummary(sheetNames);
        if (response.warnings?.length) {
          setMessage(`${response.sheets.length} sheets exported. ${response.warnings.join(' ')}`);
        }
        return;
      }

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
      <h4 className="text-sm font-medium text-slate-200">Export data (Excel)</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Export format</span>
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as MlExportFormat)}
            disabled={disabled || loading}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            <option value="training_only">Training data only</option>
            <option value="full_workbook">Full workbook</option>
          </select>
        </label>
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
      {exportFormat === 'full_workbook' && (
        <p className="text-xs text-slate-500">
          Includes an Overview tab plus one sheet per completed wizard step. Steps you skipped are
          omitted.
        </p>
      )}
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
          {exportFormat === 'full_workbook' ? 'Building workbook…' : 'Building feature matrix…'}
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
      {message && <p className="text-xs text-emerald-300">{message}</p>}
      {sheetSummary && <p className="text-xs text-slate-500">Sheets: {sheetSummary}</p>}
    </div>
  );
}
