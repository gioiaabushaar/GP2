# NEXIS Backend — Local starter v0.1

A runnable **local backend MVP** inspired by the NEXIS GP1 proposal (FR1–FR11). It is **not** a fully implemented cybersecurity learning system; advanced behavioral telemetry, vector RAG, real CTF scenarios, multi-course tenancy, and capacity guarantees remain future work.

## Windows quickstart
1. Run `NEXIS_Setup.ps1` in Windows PowerShell. Python 3.11+ must be installed.
2. Run `./run-backend.ps1`, then visit `http://127.0.0.1:8000/docs`.
3. Open `local-instructor-credentials.txt` on your own computer for generated demo instructor credentials. Do not share that file.
4. Register a student using `POST /api/auth/register`, login via `POST /api/auth/login`, and paste `Bearer <token>` into Swagger Authorize.
5. `GET /api/challenges`, `POST /api/challenges/1/submit`, `POST /api/ai/hint`, and `GET /api/analytics/me`.
6. For an instructor, login with local credentials, then call `/api/analytics/instructor/overview` and `POST /api/challenges`.

Demo flags for local testing: `NEXIS{demo_sql_injection}` and `NEXIS{demo_network}`.

## Docker demo (optional)
Install Docker Desktop with Linux containers running. Execute `./build-demo-lab.ps1`, change `NEXIS_ALLOW_DOCKER=false` to `true` in `backend/.env`, and restart the API. Then call `POST /api/labs/start/1`, `GET /api/labs/mine`, `DELETE /api/labs/{session_id}`. The demo container is network-disabled, read-only, and no challenge web service is exposed. **Do not treat this as a production-grade hostile-code sandbox.**

## RAG note
Without an API key, `/api/ai/hint` uses local keyword retrieval (not generative AI). With `NEXIS_OPENAI_API_KEY` set in `backend/.env`, it performs retrieval-grounded LLM generation. The lexical retrieval is a deliberately small MVP, not a vector database. Never commit API keys or the .env file.

## Team modules
- Ali: `backend/app/modules/auth`, `backend/app/core/db.py`, `backend/app/core/models.py`
- Sura: `backend/app/modules/challenges`
- Gioia: `backend/app/modules/ai_mentor`
- Hussam: `backend/app/modules/labs`, `docker/`
- Team-shared: `backend/app/main.py`, `backend/app/modules/analytics`, `backend/tests`, CI and docs.

## Git workflow
Create one private GitHub repo, commit this scaffold to `main`, and create branches `feature/auth`, `feature/challenges`, `feature/ai-mentor`, `feature/lab-engine`. Merge small Pull Requests after review and tests. Never commit `.env`, `.venv`, keys, or local credentials.

## Current storage
SQLite locally for zero-dependency startup. For later PostgreSQL use, configure `NEXIS_DATABASE_URL` and install the corresponding driver; add Alembic migrations before altering the schema. A production deployment needs rate limits, audit logging, isolated worker infrastructure, backups, robust secrets, and sandbox security review.