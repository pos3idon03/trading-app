interface FoundationScopeBannerProps {
  contextLength?: number;
  forecastHorizon?: number;
  warmupBars?: number;
}

export default function FoundationScopeBanner({
  contextLength,
  forecastHorizon,
  warmupBars,
}: FoundationScopeBannerProps) {
  return (
    <div className="rounded-lg border border-violet-700/50 bg-violet-950/30 px-3 py-2 text-sm text-violet-100">
      <p className="font-medium">Zero-shot walk-forward</p>
      <p className="mt-1 text-xs opacity-90">
        Each bar uses only past prices as context. No training or saved checkpoints — forecasts are
        generated fresh by the foundation model at every step (separate from ML classification).
      </p>
      {(contextLength != null || forecastHorizon != null) && (
        <p className="mt-1 text-xs opacity-75">
          Context {contextLength ?? '—'} bars · horizon {forecastHorizon ?? '—'} · warmup{' '}
          {warmupBars ?? contextLength ?? '—'} bars held before trading.
        </p>
      )}
    </div>
  );
}
