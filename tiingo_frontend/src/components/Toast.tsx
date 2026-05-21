import { useEffect } from 'react';

type ToastProps = {
  message: string;
  variant?: 'success' | 'error';
  onDismiss: () => void;
  durationMs?: number;
};

export default function Toast({
  message,
  variant = 'success',
  onDismiss,
  durationMs = 4000,
}: ToastProps) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, durationMs);
    return () => window.clearTimeout(timer);
  }, [onDismiss, durationMs]);

  const styles =
    variant === 'error'
      ? 'border-red-700 bg-red-900/40 text-red-200'
      : 'border-brand-600/50 bg-surface-900 text-brand-500';

  return (
    <div
      className={`fixed top-4 right-4 z-50 max-w-sm rounded-lg border px-4 py-3 text-sm shadow-lg ${styles}`}
      role="status"
    >
      {message}
    </div>
  );
}
