import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

interface BacktestEquityCurveProps {
  data: { time: string; value: number }[];
  gradientId: string;
  compact?: boolean;
}

export default function BacktestEquityCurve({ data, gradientId, compact = false }: BacktestEquityCurveProps) {
  const height = compact ? 180 : 320;

  return (
    <div className="card">
      {!compact && <h2 className="text-slate-200 font-semibold mb-4">Equity Curve</h2>}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#475569"
            tick={{ fontSize: 9, fill: '#64748b' }}
            tickFormatter={(v) => v.substring(0, 10)}
          />
          <YAxis
            stroke="#475569"
            tick={{ fontSize: 9, fill: '#64748b' }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(v: number) => [`$${v.toFixed(2)}`, 'Portfolio Value']}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#22c55e"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
