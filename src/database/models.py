from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.connection import Base


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True, index=True)
    input: Mapped[str] = mapped_column(Text)
    output: Mapped[str] = mapped_column(Text)
    final_status: Mapped[str] = mapped_column(String(40), default="completed")
    final_action: Mapped[str] = mapped_column(String(20), default="LOG")
    has_violation: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow_name: Mapped[str] = mapped_column(String(120), default="governance_workflow")
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ViolationModel(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    violation_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    policy_id: Mapped[str] = mapped_column(String(80), index=True)
    policy_name: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommended_action: Mapped[str] = mapped_column(String(20))
    judge_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    judge_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class EvidenceSpanModel(Base):
    __tablename__ = "evidence_spans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    violation_id: Mapped[str] = mapped_column(String(80), ForeignKey("violations.violation_id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20))
    condition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ExecutionTraceModel(Base):
    __tablename__ = "execution_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    workflow_name: Mapped[str] = mapped_column(String(120))
    node_name: Mapped[str] = mapped_column(String(120))
    node_type: Mapped[str] = mapped_column(String(80))
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────────────────────
# PRD 8.1 신규 테이블 — Feature 1/2/3 전용 (기존 테이블과 독립)
# ──────────────────────────────────────────────────────────────


class AgentModel(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("policies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class PolicyModel(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(50), default="1.0")
    yaml_path: Mapped[str] = mapped_column(String(512))
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    original_docx_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class QueryAuditLogModel(Base):
    __tablename__ = "query_audit_logs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(80), ForeignKey("agents.id"), index=True)
    policy_id: Mapped[str] = mapped_column(String(80), ForeignKey("policies.id"), index=True)
    query: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50))
    risk_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # GET /api/agents/{id}/audit 쿼리 최적화: agent_id 필터 + created_at DESC 정렬
    __table_args__ = (
        Index("ix_query_audit_agent_created", "agent_id", "created_at"),
    )


class ResponseAuditLogModel(Base):
    __tablename__ = "response_audit_logs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, index=True)
    query_audit_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("query_audit_logs.id"), nullable=True, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(80), ForeignKey("agents.id"), index=True)
    policy_id: Mapped[str] = mapped_column(String(80), ForeignKey("policies.id"), index=True)
    query: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50))
    violations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_response_audit_agent_created", "agent_id", "created_at"),
    )


class PolicyConversionLogModel(Base):
    __tablename__ = "policy_conversion_logs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, index=True)
    # 실패 케이스에는 policy_id 가 없을 수 있음 (정책 미생성).
    # 추적용 fail-marker 는 fail_marker 컬럼에 별도 저장.
    policy_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("policies.id"), nullable=True, index=True
    )
    fail_marker: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    parsed_rules_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_status: Mapped[str] = mapped_column(String(50))
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
