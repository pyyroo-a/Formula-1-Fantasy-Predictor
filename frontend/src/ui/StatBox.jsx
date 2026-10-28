// A small label over a big narrow number, like "Expected points / 144.0"
export default function StatBox({ label, value, sub, accent = "" }) {
  return (
    <div className="flex-1 min-w-0 bg-pw-raised rounded-lg px-3 py-2">
      <div className="text-xs text-pw-muted truncate">{label}</div>
      <div className={`cond-x font-extrabold text-2xl leading-tight num ${accent}`}>{value}</div>
      {sub && <div className="text-xs text-pw-muted">{sub}</div>}
    </div>
  );
}
