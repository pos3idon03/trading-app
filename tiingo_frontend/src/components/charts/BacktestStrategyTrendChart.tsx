import type { ReactNode } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { OHLCVBar } from '../../api/types';
import {
  bandsSeriesLabels,
  boundedSeriesLabel,
  buildStrategyTrendChartData,
  channelSeriesLabels,
  maSeriesLabels,
  momentumSeriesLabel,
  strategyTrendChartMode,
  strategyTrendChartSubtitle,
} from '../../utils/backtestStrategyTrend';

interface BacktestStrategyTrendChartProps {
  strategyId: string;
  params: Record<string, number>;
  records: OHLCVBar[];
  signalTimeframe?: string;
}

function TrendChartShell({ subtitle, children }: { subtitle: string | null; children: ReactNode }) {
  return (
    <div className="space-y-1">
      {subtitle && <p className="text-xs text-slate-500 px-1">{subtitle}</p>}
      {children}
    </div>
  );
}

export default function BacktestStrategyTrendChart({
  strategyId,
  params,
  records,
  signalTimeframe = '1d',
}: BacktestStrategyTrendChartProps) {
  const mode = strategyTrendChartMode(strategyId);
  const data = buildStrategyTrendChartData(strategyId, params, records, signalTimeframe);
  const subtitle = strategyTrendChartSubtitle(records, signalTimeframe, strategyId, params);

  if (!mode || !data?.length) {
    return null;
  }

  if (mode === 'rsi') {
    const seriesLabel = boundedSeriesLabel(strategyId, params);
    const oversold = params.oversold ?? (strategyId === 'rsi_reversion' ? 30 : 20);
    const overbought = params.overbought ?? (strategyId === 'rsi_reversion' ? 70 : 80);

    return (
      <TrendChartShell subtitle={subtitle}>
      <div className="h-64 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#e2e8f0' }}
              formatter={(value: number) => [value.toFixed(2), '']}
            />
            <Legend />
            <ReferenceLine y={oversold} stroke="#22c55e" strokeDasharray="4 4" label={`Oversold ${oversold}`} />
            <ReferenceLine y={overbought} stroke="#ef4444" strokeDasharray="4 4" label={`Overbought ${overbought}`} />
            <Line
              type="monotone"
              dataKey="rsi"
              name={seriesLabel}
              stroke="#60a5fa"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      </TrendChartShell>
    );
  }

  if (mode === 'channel') {
    const labels = channelSeriesLabels(params);

    return (
      <TrendChartShell subtitle={subtitle}>
      <div className="h-64 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#e2e8f0' }}
              formatter={(value: number) => [value.toFixed(2), '']}
            />
            <Legend />
            <Line type="monotone" dataKey="close" name={labels.close} stroke="#64748b" dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="upper" name={labels.upper} stroke="#22c55e" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="lower" name={labels.lower} stroke="#ef4444" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      </TrendChartShell>
    );
  }

  if (mode === 'bands') {
    const labels = bandsSeriesLabels(params);

    return (
      <TrendChartShell subtitle={subtitle}>
      <div className="h-64 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#e2e8f0' }}
              formatter={(value: number) => [value.toFixed(2), '']}
            />
            <Legend />
            <Line type="monotone" dataKey="close" name={labels.close} stroke="#64748b" dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="middle" name={labels.middle} stroke="#94a3b8" dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="upper" name={labels.upper} stroke="#22c55e" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="lower" name={labels.lower} stroke="#ef4444" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      </TrendChartShell>
    );
  }

  if (mode === 'momentum') {
    const label = momentumSeriesLabel(params);

    return (
      <TrendChartShell subtitle={subtitle}>
      <div className="h-64 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#e2e8f0' }}
              formatter={(value: number) => [`${value.toFixed(2)}%`, '']}
            />
            <Legend />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" label="0%" />
            <Line
              type="monotone"
              dataKey="momentum"
              name={label}
              stroke="#60a5fa"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      </TrendChartShell>
    );
  }

  const labels = maSeriesLabels(strategyId, params);

  return (
    <TrendChartShell subtitle={subtitle}>
    <div className="h-64 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#e2e8f0' }}
            formatter={(value: number) => [value.toFixed(2), '']}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="close"
            name={labels.close}
            stroke="#64748b"
            dot={false}
            strokeWidth={1.5}
          />
          <Line
            type="monotone"
            dataKey="fast"
            name={labels.fast}
            stroke="#60a5fa"
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="slow"
            name={labels.slow}
            stroke="#f472b6"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
    </TrendChartShell>
  );
}
