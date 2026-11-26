export type Role = "student" | "instructor";

export type User = { id: number; email: string; full_name: string; role: Role };

export type LoginResponse = { access_token: string; token_type: string; user: User };

export const CATEGORIES = ["Web", "Network", "Forensics", "Cryptography", "Reverse Engineering"] as const;
export const DIFFICULTIES = ["Easy", "Medium", "Hard"] as const;
export type Category = (typeof CATEGORIES)[number];
export type Difficulty = (typeof DIFFICULTIES)[number];

export type Challenge = {
  id: number;
  title: string;
  description: string;
  category: Category;
  difficulty: Difficulty;
  points: number;
  solved?: boolean;
};

export type MyScore = {
  user_id: number;
  total_score: number;
  solved_count: number;
  solved: { challenge_id: number; title: string; points: number; solved_at: string }[];
};

export type LeaderboardRow = { rank: number; user_id: number; full_name: string; total_score: number; solved_count: number };

export type SubmitResult = {
  correct: boolean;
  already_solved: boolean;
  points_awarded: number;
  total_score: number;
  attempt_number: number;
  message: string;
};

export type MyActivity = { user_id: number; attempts: number; solved_challenges: number; hints_used: number };

export type InstructorOverview = {
  students: number;
  challenges: number;
  submissions: number;
  correct_submissions: number;
  hints_requested: number;
};

export type HintResponse = {
  challenge_id: number;
  hint: string;
  hint_level: number;
  max_unlocked_level: number;
  attempts: number;
  previous_hints: number;
  source: string;
  mode: string;
  retrieval_mode: string;
};

export type ChallengeReport = {
  challenge_id: number;
  title: string;
  solved: boolean;
  attempts: number;
  hints_used: number;
  feedback: string;
  next_steps: string[];
  progress_status: "solved" | "attempted" | "not_attempted";
  learning_reference: string | null;
  report_mode: string;
};

export type LabStart = {
  session_id: number;
  status: string;
  container_id: string;
  provision_seconds: number;
  expires_in_minutes: number;
  note: string;
};

export type LabSession = { id: number; challenge_id: number; status: string; started_at: string; expires_at: string };

// ---------- Web Labs (PortSwigger library and timed exams) ----------

export type WebLab = { id: number; title: string; url: string };

export type WebLibrary = { source: string; total: number; topics: { name: string; labs: WebLab[] }[] };

export type WebExam = {
  id: string;
  title: string;
  description: string;
  duration_minutes: number;
  labs_per_attempt: number;
  pool_size: number;
  rules: string[];
  active: boolean;
  pool?: WebLab[];
};

export type WebExamInput = {
  title: string;
  description: string;
  duration_minutes: number;
  labs_per_attempt: number;
  rules: string; // one rule per line
  active: boolean;
};

export type LibraryLab = WebLab & { topic: string };

export type WebAttempt = {
  id: number;
  quiz_id: string;
  quiz_title: string;
  status: "active" | "locked" | "reset";
  started_at: string;
  ends_at: string;
  seconds_left: number;
  labs: { index: number; title: string; url: string; solved: boolean }[];
  solved_count: number;
  reset_at: string | null;
  student?: { id: number; full_name: string; email: string };
};

// ---------- Courses and deployments (instructor) ----------

export type Course = { id: number; name: string };

export type Deployment = {
  id: number;
  course_id: number | null;
  course_name: string;
  challenge_id: number | null;
  challenge_title: string;
  students: number;
  status: "running" | "refused";
  reason: string;
  created_at: string;
};

export type Capacity = { host_ram_gb: number; reserved_gb: number; lab_memory_mb: number; max_labs: number };
