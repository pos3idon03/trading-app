import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { FundamentalFormat } from '../../constants/fundamentalsMetrics';
import {
  formatFundamentalValue,
  type FundamentalChartPoint,
} from '../../utils/fundamentalsChartData';

interface FundamentalsMetricChartProps {
  label: string;
  data: FundamentalChartPoint[];
  format: FundamentalFormat;
  height?: number;
}

export default function FundamentalsMetricChart({
  label,
  data,
  format,
  height = 200,
}: FundamentalsMetricChartProps) {
  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-xs border border-slate-800 rounded-lg bg-surface-900">
        No data for this metric
      </div>
    );
  }

  return (
    <div className="border border-slate-800 rounded-lg bg-surface-900 p-3">
      <p className="text-xs font-medium text-slate-300 mb-2">{label}</p>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="period"
            tick={{ fill: '#64748b', fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10 }}
            width={52}
            tickFormatter={(v: number) => formatFundamentalValue(v, format)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number) => [formatFundamentalValue(value, format), label]}
            labelFormatter={(period: string) => period}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#22c55e"
            dot={{ r: 2, fill: '#22c55e' }}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
