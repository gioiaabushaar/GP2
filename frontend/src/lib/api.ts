import type {
  Challenge,
  ChallengeReport,
  HintResponse,
  InstructorOverview,
  LabSession,
  LabStart,
  LeaderboardRow,
  LoginResponse,
  MyActivity,
  MyScore,
  SubmitResult,
  User,
} from "./types";

const TOKEN_KEY = "nexis.token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const tokenStore = {
  get: () => (typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY)),
  set: (token: string) => window.localStorage.setItem(TOKEN_KEY, token),
  clear: () => window.localStorage.removeItem(TOKEN_KEY),
};

// Called when the backend rejects the token (expired or invalid), so the app can log out.
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

// FastAPI errors come as {"detail": "text"} or, for validation, {"detail": [{msg, loc}]}.
function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: { msg?: string; loc?: (string | number)[] }) => {
        const field = d.loc?.filter((x) => x !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  if (status === 503) return "The service is not available right now.";
  return `Request failed (${status}).`;
}

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const token = auth ? tokenStore.get() : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the NEXIS server. Is the backend running?");
  }
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!res.ok) {
    if (res.status === 401 && auth && token) onUnauthorized();
    if ((res.status === 500 || res.status === 502 || res.status === 504) && !body) {
      throw new ApiError(res.status, "Cannot reach the NEXIS server. Is the backend running?");
    }
    throw new ApiError(res.status, errorMessage(body, res.status));
  }
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false),
  register: (full_name: string, email: string, password: string) =>
    request<User>("/api/auth/register", { method: "POST", body: JSON.stringify({ full_name, email, password }) }, false),
  me: () => request<User>("/api/auth/me"),

  challenges: (filters: { category?: string; difficulty?: string } = {}) => {
    const q = new URLSearchParams(Object.entries(filters).filter(([, v]) => v) as [string, string][]);
    return request<Challenge[]>(`/api/challenges${q.size ? `?${q}` : ""}`);
  },
  challenge: (id: number) => request<Challenge>(`/api/challenges/${id}`),
  submitFlag: (id: number, flag: string) => post<SubmitResult>(`/api/challenges/${id}/submit`, { flag }),
  myScore: () => request<MyScore>("/api/challenges/my-score"),
  leaderboard: () => request<LeaderboardRow[]>("/api/challenges/leaderboard"),
  createChallenge: (data: Record<string, unknown>) => post<Challenge>("/api/challenges", data),

  myActivity: () => request<MyActivity>("/api/analytics/me"),
  instructorOverview: () => request<InstructorOverview>("/api/analytics/instructor/overview"),

  hint: (challenge_id: number, question: string) => post<HintResponse>("/api/ai/hint", { challenge_id, question }),
  report: (challenge_id: number) => request<ChallengeReport>(`/api/ai/reports/${challenge_id}`),

  startLab: (challenge_id: number) => post<LabStart>(`/api/labs/start/${challenge_id}`),
  myLabs: () => request<LabSession[]>("/api/labs/mine"),
  stopLab: (session_id: number) => request<{ status: string }>(`/api/labs/${session_id}`, { method: "DELETE" }),
};
