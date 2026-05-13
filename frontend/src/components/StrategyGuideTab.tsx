import { useState, type ReactNode } from 'react';
import { STRATEGIES, STRATEGY_GROUPS, DEFAULT_PARAMS_MAP } from '../constants/strategies';
import { STRATEGY_GUIDE } from '../constants/strategyGuide';
import type { StrategyGuideContent } from '../constants/strategyGuide';

// ── Group filter ───────────────────────────────────────────────────────────

const ALL_GROUPS = 'All';

function GroupFilter({
  active,
  onChange,
}: {
  active: string;
  onChange: (g: string) => void;
}) {
  const groups = [ALL_GROUPS, ...STRATEGY_GROUPS];
  return (
    <div className="flex flex-wrap gap-2">
      {groups.map((g) => (
        <button
          key={g}
          onClick={() => onChange(g)}
          className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors ${
            active === g
              ? 'bg-brand-500 border-brand-500 text-white'
              : 'border-slate-600 text-slate-400 hover:text-slate-200 hover:border-slate-400'
          }`}
        >
          {g}
        </button>
      ))}
    </div>
  );
}

// ── Param row ─────────────────────────────────────────────────────────────

function ParamRow({ name, description, defaultValue }: { name: string; description: string; defaultValue: number }) {
  return (
    <div className="flex gap-3 items-start py-2 border-b border-slate-700/50 last:border-0">
      <div className="min-w-[130px]">
        <span className="font-mono text-xs text-brand-400">{name}</span>
        <span className="ml-2 font-mono text-xs text-slate-500">= {defaultValue}</span>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
    </div>
  );
}

// ── Strategy card ─────────────────────────────────────────────────────────

function StrategyGuideCard({
  strategyValue,
  label,
  group,
}: {
  strategyValue: string;
  label: string;
  group: string;
}) {
  const [open, setOpen] = useState(false);

  const guide: StrategyGuideContent | undefined = STRATEGY_GUIDE[strategyValue];
  const defaults = DEFAULT_PARAMS_MAP[strategyValue] ?? {};

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-surface-800 hover:bg-surface-700 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-slate-100">{label}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400 border border-slate-600">
            {group}
          </span>
        </div>
        <span className="text-slate-500 text-xs ml-4 shrink-0">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="bg-surface-900 px-4 py-4 space-y-4">
          {!guide ? (
            <p className="text-slate-500 text-sm italic">Documentation not yet available for this strategy.</p>
          ) : (
            <>
              <Section title="Overview">{guide.overview}</Section>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <SignalBox color="green" label="When it buys">{guide.whenBuy}</SignalBox>
                <SignalBox color="red" label="When it sells">{guide.whenSell}</SignalBox>
              </div>

              <Section title="Value & caveats">{guide.valueAndCaveats}</Section>

              {Object.keys(defaults).length > 0 && (
                <div>
                  <h4 className="metric-label mb-2">Parameters</h4>
                  <div className="rounded-lg border border-slate-700 divide-y divide-slate-700/0 px-3">
                    {Object.entries(defaults).map(([key, defaultValue]) => (
                      <ParamRow
                        key={key}
                        name={key}
                        description={guide.paramDescriptions[key] ?? '—'}
                        defaultValue={defaultValue}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Small presentational helpers ──────────────────────────────────────────

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h4 className="metric-label mb-1">{title}</h4>
      <p className="text-sm text-slate-300 leading-relaxed">{children}</p>
    </div>
  );
}

function SignalBox({
  color,
  label,
  children,
}: {
  color: 'green' | 'red';
  label: string;
  children: ReactNode;
}) {
  const accent = color === 'green'
    ? 'border-green-500/30 bg-green-950/20'
    : 'border-red-500/30 bg-red-950/20';
  const labelColor = color === 'green' ? 'text-green-400' : 'text-red-400';
  return (
    <div className={`rounded-lg border p-3 ${accent}`}>
      <h4 className={`text-xs font-semibold uppercase tracking-wide mb-1 ${labelColor}`}>{label}</h4>
      <p className="text-xs text-slate-300 leading-relaxed">{children}</p>
    </div>
  );
}

// ── Tab root ──────────────────────────────────────────────────────────────

export default function StrategyGuideTab() {
  const [activeGroup, setActiveGroup] = useState(ALL_GROUPS);

  const visible = activeGroup === ALL_GROUPS
    ? STRATEGIES
    : STRATEGIES.filter((s) => s.group === activeGroup);

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-slate-200 font-semibold">Strategy guide</h2>
            <p className="text-slate-400 text-xs mt-1">
              Educational reference for all available algorithmic strategies. For informational purposes only — not financial advice.
            </p>
          </div>
          <span className="shrink-0 text-xs text-slate-500">{STRATEGIES.length} strategies</span>
        </div>
        <GroupFilter active={activeGroup} onChange={setActiveGroup} />
      </div>

      <div className="space-y-2">
        {visible.map((s) => (
          <StrategyGuideCard
            key={s.value}
            strategyValue={s.value}
            label={s.label}
            group={s.group}
          />
        ))}
      </div>
    </div>
  );
}
