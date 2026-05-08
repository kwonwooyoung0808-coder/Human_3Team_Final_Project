from collections.abc import Generator
from uuid import uuid4

from fastapi import Header
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_trace_id(x_trace_id: str | None = Header(default=None)) -> str:
    """PRD §6 trace_id 체인.

    클라이언트가 X-Trace-Id 헤더를 주면 그 값을 그대로 사용,
    없으면 서버에서 새 UUID 발급.

    같은 사용자 요청이 F1 → SovereignAI → F2 → audit → violation_report
    까지 흐르는 동안 동일 trace_id 가 유지되어 사후 추적이 가능하다.
    """
    if x_trace_id and x_trace_id.strip():
        return x_trace_id.strip()[:80]  # 컬럼 길이 보호
    return str(uuid4())

