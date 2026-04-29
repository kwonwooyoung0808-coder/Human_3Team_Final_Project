from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_settings
from src.database.connection import init_db
from src.routers import policy_convert

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title=f"{settings.app_name} - Policy Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(policy_convert.router)
