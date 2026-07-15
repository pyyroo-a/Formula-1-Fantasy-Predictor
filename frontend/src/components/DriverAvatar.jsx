import { useState } from "react";

export default function DriverAvatar({ abbreviation, size = "md" }) {
  const [failed, setFailed] = useState(false);
  const cls = size === "sm" ? "w-8 h-8 text-xs"
    : size === "lg" ? "w-14 h-14 text-sm"
    : "w-10 h-10 text-xs";

  if (!failed) {
    return (
      <img
        src={`/drivers/${abbreviation}.avif`}
        alt={abbreviation}
        className={`${cls} rounded-full object-cover object-top bg-gray-700 flex-shrink-0`}
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <div className={`${cls} rounded-full bg-gray-700 flex items-center justify-center font-bold text-gray-400 flex-shrink-0`}>
      {abbreviation}
    </div>
  );
}
