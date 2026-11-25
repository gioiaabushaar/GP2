# NEXIS frontend

The NEXIS website for students and instructors, ported from the team's demo prototype and wired to the FastAPI backend in `../backend`.

Stack (from the GP2 implementation plan): Next.js 16 (App Router), TypeScript, Tailwind CSS 4, TanStack Query.

## Run it locally

1. Start the backend on port 8000 (see the root `README.md`), for example:
   ```bash
   cd backend && .venv/bin/uvicorn app.main:app --port 8000
   ```
2. In another terminal:
   ```bash
   cd frontend
   npm install
   npm run dev -- -p 3100
   ```
3. Open http://localhost:3100.

The website forwards every `/api/*` request to the backend (see `next.config.ts`), so the backend needs no CORS change. To use another backend address, set `NEXIS_API_URL`, for example `NEXIS_API_URL=http://127.0.0.1:9000 npm run dev`.

## Screens

| Role | Page | Data |
|---|---|---|
| Both | `/login`, `/register` | `POST /api/auth/login`, `POST /api/auth/register` |
| Student | `/dashboard` | score, solved list, hints, attempts, lab sessions |
| Student | `/challenges` | challenge library with category, difficulty and status filters |
| Student | `/lab/[id]` | lab start/stop/restart, countdown, behaviour panel, AI mentor chat, flag submission |
| Student | `/reports`, `/reports/[id]` | post-challenge report from `GET /api/ai/reports/{id}` |
| Student | `/web-labs` | the course's timed web lab exams and the full PortSwigger lab library (`/api/web-labs`) |
| Student | `/web-labs/exam/[quizId]` | exam: instructions, 3 random labs, server-side countdown, lock screen when time is over |
| Instructor | `/instructor` | platform overview, success rate, students at risk, top students |
| Instructor | `/instructor/insights` | every student's progress and risk, with a profile panel |
| Instructor | `/instructor/deploy` | one-click deploy, **simulated** until the lab manager deploy API (FR6) exists |
| Instructor | `/instructor/content` | create a challenge (`POST /api/challenges`) |
| Instructor | `/instructor/web-exams` | live list of exam attempts with the labs each student marked solved, and Unlock |

The role in the login response decides which side a user sees.

## Not backed by the server yet

These demo features need backend work first, so the page shows a dash or a short note instead of made-up numbers:

- Learning pattern per student and strength/weakness per category (needs per-student behaviour events, FR7).
- Most failed challenges (needs per-challenge metrics, FR8).
- Real one-click deployment (FR6). The deploy page shows the planned flow, including the capacity check (32 GB host, 4 GB reserved, 256 MB per lab, so at most 112 labs).
- The lab target inside the Active Lab page. Lab containers currently have no network service to show.

The learning pattern on the student's own lab and report pages is computed in the browser with the rules from the GP2 plan.

## Notes for developers

- The login token is kept in `localStorage`; the plan's httpOnly cookie needs a backend change first.
- Pages render in the browser only, because they depend on the stored login. `next.config.ts` therefore runs the dev-time "instant navigation" check only on segments that opt in.
- `npm run lint` and `npx tsc --noEmit` must pass before a pull request.
