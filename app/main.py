from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routers import analysis, health, history, jobs, strategy
from app.core.config import settings
from app.db import models as db_models  # noqa: F401
from app.db.base import Base
from app.db.session import engine
from app.middleware.request_logging import RequestLoggingMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


async def _wait_for_mysql(max_attempts: int = 20, delay_seconds: float = 1.5) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("MySQL is ready")
            return
        except Exception as exc:
            logger.warning("Waiting for MySQL (%s/%s): %s", attempt, max_attempts, exc)
            await asyncio.sleep(delay_seconds)
    raise RuntimeError("MySQL is not ready after retries")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _wait_for_mysql()
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.project_name,
    version=settings.app_version,
    description="FastAPI backend for JD parsing, strategy generation, and export workflows",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.include_router(health.router)
app.include_router(analysis.router)
app.include_router(history.router)
app.include_router(jobs.router)
app.include_router(strategy.router)

