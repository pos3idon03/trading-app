const statusStyles: Record<string, string> = {
  done: 'bg-green-900/50 text-green-400 border-green-700',
  completed: 'bg-green-900/50 text-green-400 border-green-700',
  running: 'bg-blue-900/50 text-blue-400 border-blue-700',
  pending: 'bg-slate-700/50 text-slate-400 border-slate-600',
  error: 'bg-red-900/50 text-red-400 border-red-700',
  partial_error: 'bg-yellow-900/50 text-yellow-400 border-yellow-700',
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = statusStyles[status] ?? statusStyles.pending;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-mono ${cls}`}>
      {status}
    </span>
  );
}
