from datetime import datetime, timezone, timedelta
from typing import Any
from pydantic import BaseModel, field_serializer

# 🇰🇷 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# 1. Feature 1: 질의 위험 감지용 스키마
class QueryAuditLogCreate(BaseModel):
    id: str # UUID
    agent_id: str
    policy_id: str
    query: str
    context: str | None = None
    risk_score: float = 0.0
    status: str
    risk_reasons: dict | str
    action_taken: str

class QueryAuditLogResponse(BaseModel):
    id: str
    agent_id: str
    policy_id: str
    query: str
    risk_score: float
    status: str
    risk_reasons: dict[str, Any]
    action_taken: str
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")

# 2. Feature 2: 응답 내규 검증용 스키마
class ResponseAuditLogCreate(BaseModel):
    id: str # UUID
    query_audit_id: str | None = None
    agent_id: str
    policy_id: str
    query: str
    response: str
    compliance_score: float = 0.0
    status: str
    violations: dict | str

class ResponseAuditLogResponse(BaseModel):
    id: str
    query_audit_id: str | None
    agent_id: str
    policy_id: str
    query: str
    response: str
    compliance_score: float
    status: str
    violations: dict[str, Any]
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")

# 3. Feature 3: 정책 문서 변환 기록
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
    

# 4. 차단(BLOCKED/REJECTED) 내역 종합 보고서 스키마
class BlockedReportItem(BaseModel):
    """위험 감지로 인해 차단된 질의/응답 종합 보고서 포맷"""
    audit_id: str
    event_type: str            # "질의(Query) 차단" 또는 "응답(Response) 차단"
    agent_id: str
    policy_id: str
    content: str               # 차단된 질문 또는 AI 응답 내용
    risk_score: float          # 위험도 또는 컴플라이언스 점수
    violation_details: dict[str, Any] # AI가 분석한 상세 위반 내역 (JSON)
    detected_at: datetime

    @field_serializer('detected_at')
    def serialize_datetime(self, dt: datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")