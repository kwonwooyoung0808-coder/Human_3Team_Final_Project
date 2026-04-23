from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship # relationship 추가

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

    # [추가] 자식 테이블들과의 1:N 관계 설정
    violations: Mapped[list["ViolationModel"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLogModel"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    traces: Mapped[list["ExecutionTraceModel"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ViolationModel(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    violation_id: Mapped[str] = mapped_column(String(80), index=True)
    # [수정] ForeignKey("workflow_runs.run_id") 추가
    run_id: Mapped[str] = mapped_column(String(80), ForeignKey("workflow_runs.run_id"), index=True)
    policy_id: Mapped[str] = mapped_column(String(80), index=True)
    policy_name: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommended_action: Mapped[str] = mapped_column(String(20))
    judge_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    judge_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # [추가] 부모(Run) 및 자식(EvidenceSpan)과의 관계 설정
    run: Mapped["WorkflowRunModel"] = relationship(back_populates="violations")
    evidence_spans: Mapped[list["EvidenceSpanModel"]] = relationship(back_populates="violation", cascade="all, delete-orphan")


class EvidenceSpanModel(Base):
    __tablename__ = "evidence_spans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ForeignKey는 이미 잘 작성하셨습니다!
    violation_id: Mapped[str] = mapped_column(String(80), ForeignKey("violations.violation_id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20))
    condition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # [추가] 부모(Violation) 역참조 설정
    violation: Mapped["ViolationModel"] = relationship(back_populates="evidence_spans")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # [수정] ForeignKey("workflow_runs.run_id") 추가
    run_id: Mapped[str] = mapped_column(String(80), ForeignKey("workflow_runs.run_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # [추가] 부모(Run) 역참조 설정
    run: Mapped["WorkflowRunModel"] = relationship(back_populates="audit_logs")


class ExecutionTraceModel(Base):
    __tablename__ = "execution_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # [수정] ForeignKey("workflow_runs.run_id") 추가
    run_id: Mapped[str] = mapped_column(String(80), ForeignKey("workflow_runs.run_id"), index=True)
    workflow_name: Mapped[str] = mapped_column(String(120))
    node_name: Mapped[str] = mapped_column(String(120))
    node_type: Mapped[str] = mapped_column(String(80))
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # [추가] 부모(Run) 역참조 설정
    run: Mapped["WorkflowRunModel"] = relationship(back_populates="traces")