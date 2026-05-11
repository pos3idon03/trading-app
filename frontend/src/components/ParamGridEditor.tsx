interface ParamGridEditorProps {
  grid: Record<string, number[]>;
  onChange: (g: Record<string, number[]>) => void;
}

function parseNumbers(raw: string): number[] {
  return raw
    .split(',')
    .map((s) => parseFloat(s.trim()))
    .filter((n) => !isNaN(n));
}

export default function ParamGridEditor({ grid, onChange }: ParamGridEditorProps) {
  const handleValueChange = (key: string, raw: string) => {
    onChange({ ...grid, [key]: parseNumbers(raw) });
  };

  return (
    <div className="space-y-2">
      {Object.entries(grid).map(([key, values]) => (
        <div key={key} className="flex items-center gap-3">
          <span className="text-slate-300 text-xs font-mono w-28 shrink-0">{key}</span>
          <input
            type="text"
            className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-brand-500 flex-1"
            value={values.join(', ')}
            onChange={(e) => handleValueChange(key, e.target.value)}
            placeholder="comma-separated values"
          />
        </div>
      ))}
    </div>
  );
}
