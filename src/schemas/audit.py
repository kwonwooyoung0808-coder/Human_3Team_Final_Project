from datetime import datetime, timezone, timedelta
from typing import Any
from pydantic import BaseModel, field_serializer

# 🇰🇷 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 1. 생성용 스키마 (PRD 새 필드에 맞게 수정)
class AuditLogCreate(BaseModel):
    run_id: str
    event_type: str
    input_text: str | None = None
    risk_score: float = 0.0
    reason: str
    risk_reasons: dict | str

# 2. 목록 조회 응답용 스키마 (PRD 새 필드 및 KST 적용)
class AuditLogResponse(BaseModel):
    id: int
    run_id: str
    event_type: str
    input_text: str | None
    risk_score: float
    reason: str
    risk_reasons: dict[str, Any]
    created_at: datetime

    # 🚨 목록 조회 시에도 한국 시간(KST)으로 출력되도록 마법의 코드 추가
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")

# 3. 단건 상세 보고서 응답 스키마 (작성하신 내용 완벽 유지)
class AuditReportResponse(BaseModel):
    """최종 보고서 형태로 출력될 데이터 규격"""
    audit_id: int
    run_id: str
    event_type: str
    content: str # 질의문 또는 응답문 내용
    risk_score: float
    violation_details: dict[str, Any] # AI가 분석한 상세 위반 내역 (JSON 데이터)
    detected_at: str # KST 변환된 시간

    class Config:
        from_attributes = True

# --- [여기서부터 맨 아래에 추가] ---
class PolicyConversionLogResponse(BaseModel):
    id: str
    policy_id: str
    original_filename: str
    parsed_rules_count: int
    conversion_status: str
    warnings: dict | None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")