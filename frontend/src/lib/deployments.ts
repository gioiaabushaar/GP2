// One-click deploy is simulated in the browser until the lab manager's deploy API (FR6) exists.
// The history is kept in this browser so the instructor dashboard can list recent runs.

export type Deployment = { id: string; course: string; module: string; students: number; at: string; status: "Running" | "Refused" };

const KEY = "nexis.deployments";

// Capacity rule from the GP2 plan: 32 GB host, 4 GB kept for the platform, 256 MB per lab.
export const HOST_RAM_GB = 32;
export const RESERVED_GB = 4;
export const LAB_MEMORY_MB = 256;
export const MAX_LABS = Math.floor(((HOST_RAM_GB - RESERVED_GB) * 1024) / LAB_MEMORY_MB);

export const deployments = {
  list(): Deployment[] {
    try {
      return JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as Deployment[];
    } catch {
      return [];
    }
  },
  add(d: Deployment) {
    const next = [d, ...deployments.list()].slice(0, 10);
    window.localStorage.setItem(KEY, JSON.stringify(next));
    return next;
  },
};
