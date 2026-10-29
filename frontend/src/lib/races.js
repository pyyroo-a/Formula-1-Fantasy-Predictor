// Which race Manual team and the Garage work on: the one you picked, or else the next
// one. ready = App has heard back about the race list (worked or not), so an empty list
// can say "loading" while the free server wakes up and "failed" if it never came
export function raceToUse(chosen, upcoming, ready) {
  const name = chosen || upcoming?.[0]?.race_name || "";
  if (name) return { name, state: "ok" };
  return { name: "", state: ready ? "failed" : "loading" };
}

export const RACE_LIST_FAILED = "Couldn't load the race list. The free server might be waking up, reload in a minute.";
