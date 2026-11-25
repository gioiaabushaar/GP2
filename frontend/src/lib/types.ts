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

export type LabSession = { id: number; challenge_id: number; status: string; started_at: string };
