// Rule-based labels from the GP2 plan ("Behaviour analytics", section 4). They are
// computed in the browser from the counts the backend already returns.

export type Pattern = "Active Exploration" | "Guided Problem Solver" | "Trial-and-Error" | "Systematic Explorer" | "Steady Solver";

export function learningPattern({ solved, attempts, hints }: { solved: boolean; attempts: number; hints: number }): Pattern {
  if (hints >= 3) return "Guided Problem Solver";
  if (attempts - (solved ? 1 : 0) >= 5) return "Trial-and-Error";
  if (!solved) return "Active Exploration";
  if (hints <= 1 && attempts <= 2) return "Systematic Explorer";
  return "Steady Solver";
}

export function levelFor(score: number) {
  if (score >= 1500) return "Advanced";
  if (score >= 500) return "Intermediate";
  return "Beginner";
}

export type Risk = "Low" | "Moderate" | "High";

/** High = under 40% of published challenges solved (GP2 plan); Moderate = under 60%. */
export function riskFor(solved: number, total: number): Risk {
  if (total === 0) return "Low";
  const ratio = solved / total;
  if (ratio < 0.4) return "High";
  if (ratio < 0.6) return "Moderate";
  return "Low";
}

export const riskTone = (r: Risk) => (r === "High" ? "bad" : r === "Moderate" ? "warn" : "ok");

/** SQLite drops the time zone, so a timestamp without one is treated as UTC (what the backend stores). */
export function parseServerDate(iso: string) {
  return new Date(/Z$|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
}

export function formatDate(iso: string) {
  return parseServerDate(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
