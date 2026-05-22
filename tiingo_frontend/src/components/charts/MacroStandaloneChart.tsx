import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MacroObservation } from '../../api/types';
import {
  TREND_COLORS,
  buildStandaloneChartData,
  trendSeriesKey,
  trendSeriesLabel,
  type TrendOverlayConfig,
} from '../../utils/technicalIndicators';

interface MacroStandaloneChartProps {
  observations: MacroObservation[];
  seriesId: string;
  seriesTitle?: string;
  overlays: TrendOverlayConfig[];
  onRemoveOverlay: (id: string) => void;
  onAddTrendClick: () => void;
  canAddTrend: boolean;
  height?: number;
}

export default function MacroStandaloneChart({
  observations,
  seriesId,
  seriesTitle,
  overlays,
  onRemoveOverlay,
  onAddTrendClick,
  canAddTrend,
  height = 420,
}: MacroStandaloneChartProps) {
  const data = buildStandaloneChartData(observations, overlays);
  const primaryLabel = seriesTitle ? `${seriesId} — ${seriesTitle}` : seriesId;

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No observations available. Backfill this series from Ingestion → FRED Macro.
      </div>
    );
  }

  return (
    <div className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onAddTrendClick}
          disabled={!canAddTrend}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50"
        >
          Add trend ({overlays.length}/3)
        </button>
        {overlays.map((overlay, idx) => (
          <span
            key={overlay.id}
            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-surface-800 border border-slate-700 text-slate-300"
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: TREND_COLORS[idx % TREND_COLORS.length] }}
            />
            {trendSeriesLabel(overlay.type, overlay.period)}
            <button
              type="button"
              onClick={() => onRemoveOverlay(overlay.id)}
              className="text-slate-500 hover:text-red-400"
              aria-label={`Remove ${trendSeriesLabel(overlay.type, overlay.period)}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            domain={['dataMin', 'dataMax']}
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(0, 7)}
          />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} width={60} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number, name: string) =>
              value == null ? ['—', name] : [value.toFixed(4), name]
            }
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="primary"
            stroke="#22c55e"
            dot={false}
            strokeWidth={2}
            name={primaryLabel}
          />
          {overlays.map((overlay, idx) => {
            const key = trendSeriesKey(overlay.type, overlay.period);
            return (
              <Line
                key={overlay.id}
                type="monotone"
                dataKey={key}
                stroke={TREND_COLORS[idx % TREND_COLORS.length]}
                dot={false}
                strokeWidth={1.5}
                name={trendSeriesLabel(overlay.type, overlay.period)}
                connectNulls
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
