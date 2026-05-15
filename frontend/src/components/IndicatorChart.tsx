import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

type IndicatorRow = Record<string, string | number | null>;

interface SeriesConfig {
  key: string;
  color: string;
  yAxisId: string;
  label: string;
}

interface ReferenceLineConfig {
  value: number;
  color: string;
  label: string;
  yAxisId: string;
}

interface AxisConfig {
  id: string;
  label: string;
  domain?: [number | string, number | string];
  orientation: 'left' | 'right';
  tickFormatter?: (v: number) => string;
}

interface IndicatorMeta {
  title: string;
  series: SeriesConfig[];
  referenceLines?: ReferenceLineConfig[];
  axes: AxisConfig[];
}

const priceFmt = (v: number) => `$${v.toFixed(0)}`;
const decFmt = (v: number) => v.toFixed(2);
const pctFmt = (v: number) => `${v.toFixed(1)}%`;

const INDICATOR_META: Record<string, IndicatorMeta> = {
  ma_crossover: {
    title: 'Moving Averages',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'fast_ma', color: '#38bdf8', yAxisId: 'price', label: 'Fast MA' },
      { key: 'slow_ma', color: '#f97316', yAxisId: 'price', label: 'Slow MA' },
    ],
  },
  sma_cross: {
    title: 'SMA Lines',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'fast_sma', color: '#38bdf8', yAxisId: 'price', label: 'Fast SMA' },
      { key: 'slow_sma', color: '#f97316', yAxisId: 'price', label: 'Slow SMA' },
    ],
  },
  ema_cross: {
    title: 'EMA Lines',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'fast_ema', color: '#38bdf8', yAxisId: 'price', label: 'Fast EMA' },
      { key: 'slow_ema', color: '#f97316', yAxisId: 'price', label: 'Slow EMA' },
    ],
  },
  sma_break: {
    title: 'SMA Level',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'sma', color: '#f97316', yAxisId: 'price', label: 'SMA' },
    ],
  },
  macd: {
    title: 'MACD',
    axes: [{ id: 'macd', label: 'MACD', orientation: 'left', tickFormatter: decFmt }],
    series: [
      { key: 'macd', color: '#38bdf8', yAxisId: 'macd', label: 'MACD' },
      { key: 'signal', color: '#f97316', yAxisId: 'macd', label: 'Signal' },
    ],
    referenceLines: [
      { value: 0, color: '#475569', label: 'Zero', yAxisId: 'macd' },
    ],
  },
  rsi: {
    title: 'RSI',
    axes: [{ id: 'rsi', label: 'RSI', orientation: 'left', domain: [0, 100], tickFormatter: (v) => `${v}` }],
    series: [
      { key: 'rsi', color: '#a78bfa', yAxisId: 'rsi', label: 'RSI' },
    ],
    referenceLines: [
      { value: 70, color: '#ef4444', label: 'OB 70', yAxisId: 'rsi' },
      { value: 30, color: '#22c55e', label: 'OS 30', yAxisId: 'rsi' },
    ],
  },
  lrsi: {
    title: 'Laguerre RSI',
    axes: [{ id: 'lrsi', label: 'LRSI', orientation: 'left', domain: [0, 1], tickFormatter: decFmt }],
    series: [
      { key: 'lrsi', color: '#a78bfa', yAxisId: 'lrsi', label: 'LRSI' },
    ],
    referenceLines: [
      { value: 0.8, color: '#ef4444', label: 'OB 0.8', yAxisId: 'lrsi' },
      { value: 0.2, color: '#22c55e', label: 'OS 0.2', yAxisId: 'lrsi' },
    ],
  },
  stoch_rsi: {
    title: 'Stochastic RSI',
    axes: [{ id: 'stochrsi', label: 'Stoch RSI', orientation: 'left', domain: [0, 1], tickFormatter: decFmt }],
    series: [
      { key: 'stoch_k', color: '#38bdf8', yAxisId: 'stochrsi', label: '%K' },
      { key: 'stoch_d', color: '#f97316', yAxisId: 'stochrsi', label: '%D' },
    ],
    referenceLines: [
      { value: 0.8, color: '#ef4444', label: 'OB 0.8', yAxisId: 'stochrsi' },
      { value: 0.2, color: '#22c55e', label: 'OS 0.2', yAxisId: 'stochrsi' },
    ],
  },
  aroon: {
    title: 'Aroon',
    axes: [{ id: 'aroon', label: 'Aroon', orientation: 'left', domain: [0, 100], tickFormatter: (v) => `${v}` }],
    series: [
      { key: 'aroon_up', color: '#22c55e', yAxisId: 'aroon', label: 'Aroon Up' },
      { key: 'aroon_down', color: '#ef4444', yAxisId: 'aroon', label: 'Aroon Down' },
    ],
    referenceLines: [
      { value: 50, color: '#475569', label: '50', yAxisId: 'aroon' },
    ],
  },
  momentum_rotation: {
    title: 'Momentum Returns (%)',
    axes: [{ id: 'ret', label: 'Return %', orientation: 'left', tickFormatter: pctFmt }],
    series: [
      { key: 'short_ret_pct', color: '#38bdf8', yAxisId: 'ret', label: 'Short Return' },
      { key: 'long_ret_pct', color: '#f97316', yAxisId: 'ret', label: 'Long Return' },
    ],
    referenceLines: [
      { value: 0, color: '#475569', label: 'Zero', yAxisId: 'ret' },
    ],
  },
  new_high_low: {
    title: 'Period High / Low',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'period_high', color: '#22c55e', yAxisId: 'price', label: 'Period High' },
      { key: 'period_low', color: '#ef4444', yAxisId: 'price', label: 'Period Low' },
    ],
  },
  mean_reversion: {
    title: 'Z-Score',
    axes: [{ id: 'z', label: 'Z-Score', orientation: 'left', tickFormatter: decFmt }],
    series: [
      { key: 'z_score', color: '#a78bfa', yAxisId: 'z', label: 'Z-Score' },
    ],
    referenceLines: [
      { value: 2, color: '#ef4444', label: '+2σ', yAxisId: 'z' },
      { value: -2, color: '#22c55e', label: '-2σ', yAxisId: 'z' },
      { value: 0, color: '#475569', label: 'Mean', yAxisId: 'z' },
    ],
  },
  mean_reversion_trend: {
    title: 'Z-Score & ADX',
    axes: [
      { id: 'z', label: 'Z-Score', orientation: 'left', tickFormatter: decFmt },
      { id: 'adx', label: 'ADX', orientation: 'right', domain: [0, 100], tickFormatter: (v) => `${v}` },
    ],
    series: [
      { key: 'z_score', color: '#a78bfa', yAxisId: 'z', label: 'Z-Score' },
      { key: 'adx', color: '#fbbf24', yAxisId: 'adx', label: 'ADX' },
    ],
    referenceLines: [
      { value: 0, color: '#475569', label: 'Mean', yAxisId: 'z' },
    ],
  },
  mean_reversion_range: {
    title: 'BB % & ADX',
    axes: [
      { id: 'bb', label: 'BB %', orientation: 'left', tickFormatter: decFmt },
      { id: 'adx', label: 'ADX', orientation: 'right', domain: [0, 100], tickFormatter: (v) => `${v}` },
    ],
    series: [
      { key: 'bb_pct', color: '#a78bfa', yAxisId: 'bb', label: 'BB %' },
      { key: 'adx', color: '#fbbf24', yAxisId: 'adx', label: 'ADX' },
    ],
    referenceLines: [
      { value: 0, color: '#475569', label: 'Mid', yAxisId: 'bb' },
    ],
  },
  reverting_market: {
    title: 'RSI & ADX',
    axes: [
      { id: 'rsi', label: 'RSI', orientation: 'left', domain: [0, 100], tickFormatter: (v) => `${v}` },
      { id: 'adx', label: 'ADX', orientation: 'right', domain: [0, 100], tickFormatter: (v) => `${v}` },
    ],
    series: [
      { key: 'rsi', color: '#a78bfa', yAxisId: 'rsi', label: 'RSI' },
      { key: 'adx', color: '#fbbf24', yAxisId: 'adx', label: 'ADX' },
    ],
  },
  breakout: {
    title: 'Bollinger / Donchian Bands',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'bb_upper', color: '#38bdf8', yAxisId: 'price', label: 'BB Upper' },
      { key: 'bb_lower', color: '#f97316', yAxisId: 'price', label: 'BB Lower' },
      { key: 'donchian_high', color: '#22c55e', yAxisId: 'price', label: 'Donchian High' },
      { key: 'donchian_low', color: '#ef4444', yAxisId: 'price', label: 'Donchian Low' },
    ],
  },
  range_breakout: {
    title: 'Range High / Low',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'range_high', color: '#22c55e', yAxisId: 'price', label: 'Range High' },
      { key: 'range_low', color: '#ef4444', yAxisId: 'price', label: 'Range Low' },
    ],
  },
  trend_pullback: {
    title: 'ADX & Stochastic %K',
    axes: [
      { id: 'adx', label: 'ADX', orientation: 'left', domain: [0, 100], tickFormatter: (v) => `${v}` },
      { id: 'stoch', label: 'Stoch %K', orientation: 'right', domain: [0, 100], tickFormatter: (v) => `${v}` },
    ],
    series: [
      { key: 'adx', color: '#fbbf24', yAxisId: 'adx', label: 'ADX' },
      { key: 'stoch_k', color: '#38bdf8', yAxisId: 'stoch', label: 'Stoch %K' },
    ],
    referenceLines: [
      { value: 25, color: '#475569', label: 'ADX 25', yAxisId: 'adx' },
    ],
  },
  atr_trailing_stop: {
    title: 'ATR & Trend MA',
    axes: [
      { id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt },
      { id: 'atr', label: 'ATR', orientation: 'right', tickFormatter: decFmt },
    ],
    series: [
      { key: 'trend_ma', color: '#f97316', yAxisId: 'price', label: 'Trend MA' },
      { key: 'atr', color: '#fbbf24', yAxisId: 'atr', label: 'ATR' },
    ],
  },
  vwap_cross: {
    title: 'VWAP',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'vwap', color: '#a78bfa', yAxisId: 'price', label: 'VWAP' },
    ],
  },
  grid_trading: {
    title: 'Grid Levels',
    axes: [{ id: 'price', label: 'Price', orientation: 'left', tickFormatter: priceFmt }],
    series: [
      { key: 'baseline', color: '#94a3b8', yAxisId: 'price', label: 'Baseline' },
      { key: 'upper_grid', color: '#22c55e', yAxisId: 'price', label: 'Upper Grid' },
      { key: 'lower_grid', color: '#ef4444', yAxisId: 'price', label: 'Lower Grid' },
    ],
  },
  wedge_compression: {
    title: 'ATR Compression',
    axes: [{ id: 'atr', label: 'ATR', orientation: 'left', tickFormatter: decFmt }],
    series: [
      { key: 'atr', color: '#fbbf24', yAxisId: 'atr', label: 'ATR' },
      { key: 'atr_mean', color: '#94a3b8', yAxisId: 'atr', label: 'ATR Mean' },
    ],
  },
  vrp_harvest: {
    title: 'VRP Z-Score',
    axes: [
      { id: 'z', label: 'VRP Z', orientation: 'left', tickFormatter: decFmt },
      { id: 'vol', label: 'Vol', orientation: 'right', tickFormatter: decFmt },
    ],
    series: [
      { key: 'vrp_z', color: '#a78bfa', yAxisId: 'z', label: 'VRP Z' },
      { key: 'rv', color: '#38bdf8', yAxisId: 'vol', label: 'RV' },
      { key: 'iv_proxy', color: '#f97316', yAxisId: 'vol', label: 'IV Proxy' },
    ],
    referenceLines: [
      { value: 0, color: '#475569', label: 'Zero', yAxisId: 'z' },
    ],
  },
};

const LINE_COLORS = [
  '#38bdf8', '#f97316', '#a78bfa', '#fbbf24',
  '#22c55e', '#ef4444', '#f472b6', '#34d399',
];

function buildFallbackMeta(keys: string[]): IndicatorMeta {
  const indicatorKeys = keys.filter((k) => k !== 'time');
  return {
    title: 'Indicators',
    axes: [{ id: 'val', label: '', orientation: 'left', tickFormatter: decFmt }],
    series: indicatorKeys.map((key, i) => ({
      key,
      color: LINE_COLORS[i % LINE_COLORS.length],
      yAxisId: 'val',
      label: key,
    })),
  };
}

function renderLegend(series: SeriesConfig[]) {
  return (
    <div className="flex flex-wrap items-center gap-3 justify-end mb-1 text-xs">
      {series.map((s) => (
        <span key={s.key} className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5" style={{ background: s.color }} />
          <span className="text-slate-400">{s.label}</span>
        </span>
      ))}
    </div>
  );
}

interface IndicatorChartProps {
  data: IndicatorRow[];
  strategyName: string;
  strategyParams?: Record<string, number>;
  syncId?: string;
}

export default function IndicatorChart({
  data,
  strategyName,
  strategyParams = {},
  syncId,
}: IndicatorChartProps) {
  if (!data || data.length === 0) return null;

  const allKeys = Object.keys(data[0] ?? {});
  const indicatorKeys = allKeys.filter((k) => k !== 'time');
  if (indicatorKeys.length === 0) return null;

  const meta = INDICATOR_META[strategyName] ?? buildFallbackMeta(allKeys);

  const overrideRefs = buildOverrideRefs(strategyName, strategyParams, meta);
  const effectiveRefs = overrideRefs ?? meta.referenceLines ?? [];

  const hasRight = meta.axes.some((a) => a.orientation === 'right');

  return (
    <div>
      <p className="text-slate-400 text-xs font-medium mb-1">{meta.title}</p>
      {renderLegend(meta.series)}
      <ResponsiveContainer width="100%" height={160}>
        <ComposedChart data={data} margin={{ top: 4, right: hasRight ? 40 : 10, bottom: 4, left: 0 }} syncId={syncId}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#475569"
            tick={{ fontSize: 8, fill: '#64748b' }}
            tickFormatter={(v: string) => v.substring(0, 10)}
          />
          {meta.axes.map((axis) => (
            <YAxis
              key={axis.id}
              yAxisId={axis.id}
              orientation={axis.orientation}
              stroke="#475569"
              tick={{ fontSize: 8, fill: '#64748b' }}
              tickFormatter={axis.tickFormatter}
              domain={axis.domain}
              width={axis.orientation === 'left' ? 38 : 30}
            />
          ))}
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }}
            labelStyle={{ color: '#94a3b8' }}
            labelFormatter={(v: string) => v.substring(0, 10)}
            formatter={(v: number | null, name: string) => {
              const s = meta.series.find((x) => x.key === name);
              const label = s?.label ?? name;
              return [v !== null && v !== undefined ? v.toFixed(4) : '—', label];
            }}
          />
          {effectiveRefs.map((ref, i) => (
            <ReferenceLine
              key={i}
              yAxisId={ref.yAxisId}
              y={ref.value}
              stroke={ref.color}
              strokeDasharray="4 2"
              label={{ value: ref.label, fill: ref.color, fontSize: 8, position: 'insideTopRight' }}
            />
          ))}
          {meta.series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              yAxisId={s.yAxisId}
              stroke={s.color}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
              connectNulls={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildOverrideRefs(
  strategy: string,
  params: Record<string, number>,
  meta: IndicatorMeta,
): ReferenceLineConfig[] | null {
  const primaryAxisId = meta.axes[0]?.id ?? 'val';

  if ((strategy === 'rsi' || strategy === 'reverting_market') && (params.overbought || params.rsi_upper)) {
    const ob = params.overbought ?? params.rsi_upper ?? 70;
    const os = params.oversold ?? params.rsi_lower ?? 30;
    return [
      { value: ob, color: '#ef4444', label: `OB ${ob}`, yAxisId: primaryAxisId },
      { value: os, color: '#22c55e', label: `OS ${os}`, yAxisId: primaryAxisId },
    ];
  }
  if (strategy === 'lrsi' && (params.overbought || params.oversold)) {
    const ob = params.overbought ?? 0.8;
    const os = params.oversold ?? 0.2;
    return [
      { value: ob, color: '#ef4444', label: `OB ${ob}`, yAxisId: primaryAxisId },
      { value: os, color: '#22c55e', label: `OS ${os}`, yAxisId: primaryAxisId },
    ];
  }
  if (strategy === 'stoch_rsi' && (params.overbought || params.oversold)) {
    const ob = params.overbought ?? 0.8;
    const os = params.oversold ?? 0.2;
    return [
      { value: ob, color: '#ef4444', label: `OB ${ob}`, yAxisId: primaryAxisId },
      { value: os, color: '#22c55e', label: `OS ${os}`, yAxisId: primaryAxisId },
    ];
  }
  if ((strategy === 'mean_reversion') && params.z_threshold) {
    const z = params.z_threshold;
    return [
      { value: z, color: '#ef4444', label: `+${z}σ`, yAxisId: primaryAxisId },
      { value: -z, color: '#22c55e', label: `-${z}σ`, yAxisId: primaryAxisId },
      { value: 0, color: '#475569', label: 'Mean', yAxisId: primaryAxisId },
    ];
  }
  return null;
}
