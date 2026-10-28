// Little rules the main page follows, kept out of the component so they're tested.

// the confidence key only shows when at least one driver has a confidence. Sprint
// weekends and old locks don't have one, then there's no key and no pills at all
export function showConfidenceKey(drivers) {
  return (drivers || []).some(d => d?.Confidence);
}

// one line of the predicted finish. The real result only shows once the Monday job
// has saved it (results_available), same rule as Insights > Predicted finishes.
// close = we were within 1 place
export function finishLine(p, resultsAvailable) {
  const spot = `P${p.model_pos}`;
  if (!resultsAvailable) return { spot, finished: null, close: false };
  if (p.actual_pos != null) {
    return { spot, finished: `finished P${p.actual_pos}`, close: Math.abs(p.model_pos - p.actual_pos) <= 1 };
  }
  return { spot, finished: p.actual_status ? "DNF" : null, close: false };
}
