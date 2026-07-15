export const DRIVER_NAMES = {
  VER: "Max Verstappen",
  NOR: "Lando Norris",
  PIA: "Oscar Piastri",
  LEC: "Charles Leclerc",
  HAM: "Lewis Hamilton",
  RUS: "George Russell",
  SAI: "Carlos Sainz",
  ALO: "Fernando Alonso",
  STR: "Lance Stroll",
  GAS: "Pierre Gasly",
  ALB: "Alexander Albon",
  TSU: "Yuki Tsunoda",
  LAW: "Liam Lawson",
  HUL: "Nico Hülkenberg",
  BEA: "Oliver Bearman",
  ANT: "Andrea Kimi Antonelli",
  BOR: "Gabriel Bortoleto",
  DOO: "Jack Doohan",
  HAD: "Isack Hadjar",
  COL: "Franco Colapinto",
  PER: "Sergio Pérez",
  BOT: "Valtteri Bottas",
  OCO: "Esteban Ocon",
  LIN: "Arvid Lindblad",
};

export const BADGE_COLOR = {
  Safe:  "bg-green-500",
  Value: "bg-yellow-500",
  Risk:  "bg-orange-500",
  Avoid: "bg-red-500",
};

export const TEAM_COLORS = {
  "Red Bull Racing": "#3671C6",
  McLaren:           "#FF8000",
  Ferrari:           "#E8002D",
  Mercedes:          "#27F4D2",
  "Aston Martin":    "#229971",
  Alpine:            "#FF87BC",
  Williams:          "#64C4FF",
  "RB F1 Team":      "#6692FF",
  "Kick Sauber":     "#52E252",
  Haas:              "#B6BABD",
  Audi:              "#E8E234",
};

export const CHIP_META = {
  limitless:      { label: "Limitless",      color: "#E8002D", desc: "No budget cap — pick any 5 drivers + 2 constructors for one race." },
  triple_captain: { label: "Triple Captain", color: "#FF8000", desc: "Your captain scores 3× instead of 2× this race." },
  extra_drs:      { label: "Extra DRS",      color: "#27F4D2", desc: "A second driver scores 2× alongside your captain." },
  wildcard:       { label: "Wildcard",       color: "#6692FF", desc: "Rebuild your entire squad for free — transfers reset after." },
  no_negative:    { label: "No Negative",    color: "#52E252", desc: "Any negative score is floored at 0 — ideal for high-attrition circuits." },
  final_fix:      { label: "Final Fix",      color: "#FFD700", desc: "One free swap after qualifying locks in." },
  autopilot:      { label: "Autopilot",      color: "#6b7280", desc: "F1's auto-pick — PitWall already does this better. Save it." },
};

export const REC_STYLE = {
  PLAY:         "bg-green-500/20 text-green-400 border border-green-500/40",
  CONSIDER:     "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40",
  HOLD:         "bg-gray-700 text-gray-400 border border-gray-600",
  HEDGE:        "bg-orange-500/20 text-orange-400 border border-orange-500/40",
  "POST-QUALI": "bg-blue-500/20 text-blue-400 border border-blue-500/40",
  SAVE:         "bg-gray-700 text-gray-500 border border-gray-600",
};

export const BUDGET = 100.0;

export function teamAccent(teamName) {
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (teamName?.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return "#6b7280";
}
