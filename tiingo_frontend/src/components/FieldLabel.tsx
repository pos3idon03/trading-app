interface FieldLabelProps {
  label: string;
  help: string;
  htmlFor?: string;
}

export default function FieldLabel({ label, help, htmlFor }: FieldLabelProps) {
  return (
    <span className="flex items-center gap-1.5 text-slate-400">
      {htmlFor ? (
        <label htmlFor={htmlFor} className="cursor-default">
          {label}
        </label>
      ) : (
        <span>{label}</span>
      )}
      <span className="relative group inline-flex shrink-0">
        <span
          className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 text-[10px] leading-none text-slate-400 cursor-help"
          aria-label={`More information about ${label}`}
        >
          i
        </span>
        <span
          role="tooltip"
          className="pointer-events-none absolute left-1/2 top-full z-10 mt-1.5 w-60 -translate-x-1/2 rounded-lg border border-slate-700 bg-surface-950 px-3 py-2 text-xs leading-relaxed text-slate-200 opacity-0 shadow-lg transition-opacity group-hover:opacity-100"
        >
          {help}
        </span>
      </span>
    </span>
  );
}
