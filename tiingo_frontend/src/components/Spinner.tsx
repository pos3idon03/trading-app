export default function Spinner({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const cls = size === 'sm' ? 'h-4 w-4' : 'h-6 w-6';
  return (
    <div
      className={`${cls} border-2 border-slate-600 border-t-brand-500 rounded-full animate-spin`}
      role="status"
    />
  );
}
