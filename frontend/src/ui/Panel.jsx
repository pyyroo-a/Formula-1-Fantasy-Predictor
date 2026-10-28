// A quiet panel with an optional title, for the side bits (prices, predicted finish)
export default function Panel({ title, aside, children, className = "" }) {
  return (
    <section className={`bg-pw-panel rounded-xl px-3.5 py-3 ${className}`}>
      {title && (
        <div className="flex items-baseline justify-between gap-2 mb-2">
          <h3 className="cond font-bold text-[15px]">{title}</h3>
          {aside && <span className="text-xs text-pw-muted text-right">{aside}</span>}
        </div>
      )}
      {children}
    </section>
  );
}
