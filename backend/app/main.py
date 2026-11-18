
import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import Base, engine
from app.core import models  # noqa: F401; register models
from app.core.config import settings
from app.modules.auth.router import router as auth
from app.modules.challenges.router import router as challenges
from app.modules.ai_mentor.router import router as ai
from app.modules.labs.router import router as labs, reaper_loop
from app.modules.analytics.router import router as analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # FR2: Start background cleanup of expired Docker labs.
    reaper = asyncio.create_task(reaper_loop())

    try:
        yield
    finally:
        # Shut down the background task gracefully.
        reaper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reaper


app = FastAPI(
    title="NEXIS | Cybersecurity Learning Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        x.strip() for x in settings.nexis_cors_origins.split(",")
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth, prefix="/api/auth")
app.include_router(challenges, prefix="/api/challenges")
app.include_router(ai, prefix="/api/ai")
app.include_router(labs, prefix="/api/labs")
app.include_router(analytics, prefix="/api/analytics")


@app.get("/api/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": "NEXIS Backend",
        "version": "0.1.0",
    }
