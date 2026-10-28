// The segmented control: Team 1/2/3, FP1 to Race, 1/2/3 free transfers.
// options: [{ id, label, sub? }]. sub is a small second line (like "141.5 pts").
export default function Switcher({ options, value, onChange, className = "" }) {
  return (
    <div role="tablist" className={`flex bg-pw-raised rounded-lg p-[3px] ${className}`}>
      {options.map(o => {
        const on = o.id === value;
        return (
          <button
            key={o.id}
            role="tab"
            aria-selected={on}
            disabled={o.disabled}
            onClick={() => onChange(o.id)}
            className={`flex-1 min-w-0 py-1.5 px-2 rounded-md text-sm font-semibold leading-tight transition-colors ${
              on ? "bg-pw-red text-pw-bg" : o.disabled ? "text-pw-muted/40" : "text-pw-muted hover:text-pw-text"
            }`}
          >
            <span className="block truncate">{o.label}</span>
            {o.sub && <span className={`block text-[11px] font-normal num ${on ? "text-pw-bg/80" : "text-pw-muted"}`}>{o.sub}</span>}
          </button>
        );
      })}
    </div>
  );
}
