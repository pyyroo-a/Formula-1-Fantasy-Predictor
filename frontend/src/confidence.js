// Confidence = how much to trust a driver's practice spot (project 4, src/confidence.py
// on the backend). The pill and the key are in ui/Confidence.jsx, the rule for when the
// key shows is showConfidenceKey in lib/overview.js.

// A top 3 predicted driver (Safe) with low confidence reads like a contradiction, so the
// tag says CONSIDER instead. Display only, the driver is still Safe for the team rules.
export function displayCategory(driver) {
  if (driver?.PickCategory === "Safe" && driver?.Confidence === "low") return "Consider";
  return driver?.PickCategory;
}
