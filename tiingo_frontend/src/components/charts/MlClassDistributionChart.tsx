import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface MlClassDistributionChartProps {
  distribution: Record<string, number>;
}

const CLASS_LABELS: Record<string, string> = {
  '0': 'Down (0)',
  '1': 'Up (1)',
  '2': 'Buy (2)',
};

export default function MlClassDistributionChart({
  distribution,
}: MlClassDistributionChartProps) {
  const data = Object.entries(distribution).map(([label, count]) => ({
    label: CLASS_LABELS[label] ?? `Class ${label}`,
    count,
  }));

  if (!data.length) {
    return <p className="text-sm text-slate-500">No label distribution available.</p>;
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
          <Bar dataKey="count" fill="#34d399" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
