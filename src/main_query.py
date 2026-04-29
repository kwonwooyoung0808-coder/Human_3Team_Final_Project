from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_settings
from src.database.connection import init_db
from src.routers import audit, query_check, response_validate, runs, violations

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title=f"{settings.app_name} - Query/Response Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(query_check.router)
app.include_router(response_validate.router)
app.include_router(runs.router)
app.include_router(violations.router)
app.include_router(audit.router)
