import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MarketSentimentChartPoint } from '../../utils/marketSentimentChart';
import {
  formatChartTime,
  formatMarketSentimentScore,
  MARKET_SENTIMENT_NEUTRAL,
} from '../../utils/marketSentimentChart';

interface MarketSentimentChartProps {
  data: MarketSentimentChartPoint[];
  emptyMessage: string;
  height?: number;
}

export default function MarketSentimentChart({
  data,
  emptyMessage,
  height = 280,
}: MarketSentimentChartProps) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="time"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickFormatter={formatChartTime}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#64748b', fontSize: 11 }}
            width={48}
            allowDecimals={false}
          />
          <ReferenceLine y={MARKET_SENTIMENT_NEUTRAL} stroke="#475569" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#94a3b8' }}
            labelFormatter={(value) => formatChartTime(String(value))}
            formatter={(value: number, name: string, item) => {
              if (name !== 'score') return [value, name];
              const payload = item.payload as MarketSentimentChartPoint;
              return [
                `${formatMarketSentimentScore(value)} (${payload.bullish_count}↑ ${payload.neutral_count}→ ${payload.bearish_count}↓)`,
                'Sentiment score',
              ];
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#22c55e"
            dot={false}
            strokeWidth={2}
            name="score"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
