import { useMarketCountdowns, type MarketCountdown, type MarketStatus } from '../hooks/useMarketCountdowns';

const STATUS_DOT_CLASSES: Record<MarketStatus, string> = {
  open: 'bg-green-500',
  lunch: 'bg-yellow-400',
  closed: 'bg-red-500',
  holiday: 'bg-slate-500',
  weekend: 'bg-slate-500',
};

const STATUS_TEXT_CLASSES: Record<MarketStatus, string> = {
  open: 'text-green-400',
  lunch: 'text-yellow-400',
  closed: 'text-slate-400',
  holiday: 'text-slate-500',
  weekend: 'text-slate-500',
};

function ExchangePill({ item }: { item: MarketCountdown }) {
  const dotClass = STATUS_DOT_CLASSES[item.status];
  const textClass = STATUS_TEXT_CLASSES[item.status];
  const tooltipTitle = item.holidayName
    ? `${item.fullName} — ${item.holidayName}`
    : item.fullName;

  return (
    <div
      className="flex items-center gap-1.5 px-3 py-0.5 rounded-full border border-slate-700/60 bg-surface-800 shrink-0 select-none mx-2"
      title={tooltipTitle}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${dotClass} shrink-0`}
        aria-hidden="true"
      />
      <span className="text-slate-300 font-medium">{item.label}</span>
      <span className={`${textClass} tabular-nums`}>{item.countdown}</span>
    </div>
  );
}

function TickerTrack({ countdowns }: { countdowns: MarketCountdown[] }) {
  // Duplicate the list so the second copy seamlessly follows the first
  const items = [...countdowns, ...countdowns];

  return (
    <div
      className="flex items-center"
      style={{
        animation: 'ticker-scroll 30s linear infinite',
        willChange: 'transform',
      }}
    >
      {items.map((item, idx) => (
        <ExchangePill key={`${item.id}-${idx}`} item={item} />
      ))}
    </div>
  );
}

export default function MarketStatusBar() {
  const countdowns = useMarketCountdowns();

  return (
    <div
      className="w-full bg-surface-950 border-b border-slate-800/60 py-1 overflow-hidden text-xs"
      role="region"
      aria-label="Market hours"
    >
      <div className="flex items-center gap-3 px-4">
        <span className="text-slate-600 shrink-0 font-medium uppercase tracking-widest text-[10px] pr-1">
          Markets
        </span>
        {/* Left fade */}
        <div className="relative flex-1 overflow-hidden">
          <div
            className="pointer-events-none absolute left-0 top-0 h-full w-10 z-10"
            style={{ background: 'linear-gradient(to right, #020617, transparent)' }}
          />
          <TickerTrack countdowns={countdowns} />
          {/* Right fade */}
          <div
            className="pointer-events-none absolute right-0 top-0 h-full w-10 z-10"
            style={{ background: 'linear-gradient(to left, #020617, transparent)' }}
          />
        </div>
      </div>
    </div>
  );
}
