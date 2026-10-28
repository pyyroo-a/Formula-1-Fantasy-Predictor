// Confidence = how much to trust a driver's practice spot (project 4, src/confidence.py
// on the backend). These helpers live outside the components so the cards can share them.

export const CONFIDENCE_LEGEND = "Confidence = how much to trust a driver's practice spot. It's never a guarantee.";

// A top 3 predicted driver (Safe) with low confidence reads like a contradiction, so the
// tag says CONSIDER instead. Display only, the driver is still Safe for the team rules.
export function displayCategory(driver) {
  if (driver?.PickCategory === "Safe" && driver?.Confidence === "low") return "Consider";
  return driver?.PickCategory;
}

export function hasConfidence(drivers) {
  return (drivers || []).some(d => d?.Confidence);
}
