import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MacroObservation } from '../../api/types';

interface MacroTimelineChartProps {
  observations: MacroObservation[];
  seriesId: string;
  height?: number;
}

export default function MacroTimelineChart({
  observations,
  seriesId,
  height = 420,
}: MacroTimelineChartProps) {
  const data = [...observations]
    .sort((a, b) => a.obs_date.localeCompare(b.obs_date))
    .map((o) => ({
      date: o.obs_date,
      value: o.value,
    }));

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
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#22c55e"
            dot={false}
            strokeWidth={2}
            name={seriesId}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
