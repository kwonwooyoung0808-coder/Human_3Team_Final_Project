from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_settings
from src.database.connection import init_db
from src.routers import (
    agents,
    audit,
    evaluate,
    input_guard,
    inquiry,
    policy_compiler,
    policy_groups,
    proxy,
    response_guard,
    runs,
    violation_reports,
    violations,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db_available = init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["health"])
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "db_available": getattr(app.state, "db_available", False),
    }


app.include_router(evaluate.router)
app.include_router(runs.router)
app.include_router(violations.router)
app.include_router(audit.router)
app.include_router(audit.query_audit_router)  # /v1/audit/query/{id}, /v1/audit/response/{id}

# Feature 1/2/3 신규 라우터 (PRD §3 명명규칙 정합)
app.include_router(input_guard.router)
app.include_router(response_guard.router)
app.include_router(policy_compiler.router)

# PRD 9 Agent Management + Proxy 편의 엔드포인트
app.include_router(agents.router)
app.include_router(proxy.router)
app.include_router(inquiry.router)
app.include_router(violation_reports.router)
app.include_router(policy_groups.router)
