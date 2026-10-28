// While we wait for the free server: say so plainly, with grey blocks where the
// answer will go
export default function Loading({ text = "Loading. The free server can take up to 30 seconds to wake up.", rows = 3 }) {
  return (
    <div className="my-3" role="status">
      <p className="text-sm text-pw-muted mb-3">{text}</p>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-10 rounded-lg bg-pw-raised mb-2 animate-pulse" />
      ))}
    </div>
  );
}

// an error from fetchJson, said plainly
export function ErrorLine({ text }) {
  if (!text) return null;
  return <p className="text-sm text-pw-low my-3">{text}</p>;
}
