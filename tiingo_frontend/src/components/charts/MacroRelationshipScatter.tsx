import { memo, useMemo } from 'react';
import {
  CartesianGrid,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import {
  formatScatterTooltipLines,
  type PeriodChangePoint,
} from '../../utils/macroStandaloneData';

interface MacroRelationshipScatterProps {
  changeSeries: PeriodChangePoint[];
  selectedIndex: number;
  macroId: string;
  assetId: string;
  height?: number;
}

interface ScatterTooltipProps {
  active?: boolean;
  payload?: { payload: PeriodChangePoint & { z?: number } }[];
  macroId: string;
  assetId: string;
}

function ScatterTooltip({ active, payload, macroId, assetId }: ScatterTooltipProps) {
  if (!active || !payload?.length) return null;

  const point = payload[0].payload;
  const lines = formatScatterTooltipLines(point, macroId, assetId);

  return (
    <div className="rounded-lg border border-slate-600 bg-surface-800 px-3 py-2 text-xs shadow-lg">
      <p className="font-medium text-slate-100 mb-1">Period: {lines.period}</p>
      <p className="text-slate-300">{lines.macroLine}</p>
      <p className="text-slate-300">{lines.assetLine}</p>
    </div>
  );
}

function MacroRelationshipScatter({
  changeSeries,
  selectedIndex,
  macroId,
  assetId,
  height = 360,
}: MacroRelationshipScatterProps) {
  const historyData = useMemo(
    () => changeSeries.map((p) => ({ ...p, z: 40 })),
    [changeSeries],
  );

  const selectedPoint = changeSeries[selectedIndex] ?? null;

  if (changeSeries.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        Add an asset to explore period-over-period relationship.
      </div>
    );
  }

  return (
    <section className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
      <h3 className="text-sm font-semibold text-slate-200 mb-1">Macro vs asset relationship</h3>
      <p className="text-xs text-slate-500 mb-3">
        Period-over-period % change. Move the slider to see how the point shifts through history.
      </p>
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 8, right: 16, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            type="number"
            dataKey="macroChange"
            name={`${macroId} change`}
            tick={{ fill: '#64748b', fontSize: 11 }}
            label={{
              value: `${macroId} Δ%`,
              position: 'insideBottom',
              offset: -12,
              fill: '#94a3b8',
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="assetChange"
            name={`${assetId} change`}
            tick={{ fill: '#64748b', fontSize: 11 }}
            width={56}
            label={{
              value: `${assetId} Δ%`,
              angle: -90,
              position: 'insideLeft',
              fill: '#94a3b8',
              fontSize: 11,
            }}
          />
          <ZAxis type="number" dataKey="z" range={[40, 40]} />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={<ScatterTooltip macroId={macroId} assetId={assetId} />}
          />
          <ReferenceLine x={0} stroke="#475569" strokeDasharray="4 4" />
          <ReferenceLine y={0} stroke="#475569" strokeDasharray="4 4" />
          <Scatter
            name="History"
            data={historyData}
            fill="#64748b"
            fillOpacity={0.35}
            isAnimationActive={false}
          />
          {selectedPoint && (
            <ReferenceDot
              x={selectedPoint.macroChange}
              y={selectedPoint.assetChange}
              r={8}
              fill="#22c55e"
              stroke="#ffffff"
              strokeWidth={1.5}
              isFront
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>
    </section>
  );
}

export default memo(MacroRelationshipScatter);
