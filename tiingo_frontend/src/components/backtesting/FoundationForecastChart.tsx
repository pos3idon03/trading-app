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
import type { FoundationForecastPoint } from '../../api/foundationBacktestTypes';

interface FoundationForecastChartProps {
  contextPoints: FoundationForecastPoint[];
  forecastPoints: FoundationForecastPoint[];
  title?: string;
}

function buildChartRows(
  contextPoints: FoundationForecastPoint[],
  forecastPoints: FoundationForecastPoint[],
) {
  const rows = contextPoints.map((point) => ({
    date: point.date,
    actual: point.actual ?? undefined,
    forecast: point.forecast ?? undefined,
    lower: point.lower ?? undefined,
    upper: point.upper ?? undefined,
  }));
  for (const point of forecastPoints) {
    rows.push({
      date: point.date,
      actual: point.actual ?? undefined,
      forecast: point.forecast ?? undefined,
      lower: point.lower ?? undefined,
      upper: point.upper ?? undefined,
    });
  }
  return rows;
}

export default function FoundationForecastChart({
  contextPoints,
  forecastPoints,
  title = 'Forecast preview',
}: FoundationForecastChartProps) {
  const data = buildChartRows(contextPoints, forecastPoints);
  if (data.length === 0) {
    return (
      <p className="text-sm text-slate-500 border border-dashed border-slate-800 rounded-lg p-4">
        No forecast data to display.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-slate-300">{title}</h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual"
              stroke="#38bdf8"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="#a78bfa"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="lower"
              name="Lower"
              stroke="#64748b"
              strokeDasharray="4 4"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="upper"
              name="Upper"
              stroke="#64748b"
              strokeDasharray="4 4"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
