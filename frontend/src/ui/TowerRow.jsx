// One timing tower row: spot, team colour stripe, name with a line under it, and the
// numbers on the right (price over points, or time over a tag). The right side never
// shrinks, so on a phone the name is what gives way, and only as a last resort.
export default function TowerRow({ spot, color, name, sub, right, rightSub, faded = false, spotClass = "", onClick, children }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      onClick={onClick}
      className={`w-full text-left flex items-center gap-2.5 py-2 border-b border-pw-line ${faded ? "opacity-55" : ""} ${onClick ? "hover:bg-white/[0.02]" : ""}`}
    >
      <span className={`w-9 flex-shrink-0 font-bold cond text-[17px] num ${spotClass || "text-pw-muted"}`}>{spot}</span>
      <span className="w-1 h-8 rounded-sm flex-shrink-0" style={{ background: color || "#5A6170" }} />
      <div className="flex-1 min-w-0">
        <div className="cond font-semibold text-[17px] leading-tight truncate">{name}</div>
        {sub && <div className="text-xs text-pw-muted truncate">{sub}</div>}
        {children}
      </div>
      {(right || rightSub) && (
        <div className="flex-shrink-0 text-right num">
          {right && <div className="cond font-semibold text-[16px] leading-tight">{right}</div>}
          {rightSub && <div className="text-xs text-pw-muted">{rightSub}</div>}
        </div>
      )}
    </Tag>
  );
}
