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
import { mergeMacroSeries, type MacroCompareSeries } from '../../utils/macroChartData';

interface MacroTimelineChartProps {
  observations: MacroObservation[];
  seriesId: string;
  seriesTitle?: string;
  compareSeries?: MacroCompareSeries | null;
  height?: number;
}

export default function MacroTimelineChart({
  observations,
  seriesId,
  seriesTitle,
  compareSeries,
  height = 420,
}: MacroTimelineChartProps) {
  const isCompareMode = Boolean(compareSeries);
  const data = mergeMacroSeries(observations, compareSeries?.observations);
  const primaryLabel = seriesTitle ? `${seriesId} — ${seriesTitle}` : seriesId;
  const compareLabel = compareSeries
    ? `${compareSeries.seriesId} — ${compareSeries.title}`
    : undefined;

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No observations available. Backfill this series from Ingestion → FRED Macro.
      </div>
    );
  }

  return (
    <div className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            domain={['dataMin', 'dataMax']}
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(0, 7)}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#64748b', fontSize: 11 }}
            width={60}
          />
          {compareSeries && (
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: '#64748b', fontSize: 11 }}
              width={60}
            />
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number, name: string) =>
              value == null ? ['—', name] : [value, name]
            }
          />
          {compareSeries && <Legend />}
          <Line
            type="monotone"
            dataKey="primary"
            yAxisId="left"
            stroke="#22c55e"
            dot={false}
            strokeWidth={2}
            name={primaryLabel}
            connectNulls={isCompareMode}
          />
          {compareSeries && (
            <Line
              type="monotone"
              dataKey="compare"
              yAxisId="right"
              stroke={compareSeries.color}
              dot={false}
              strokeWidth={2}
              name={compareLabel}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
