"""
기록 저장 단위 테스트 (test_record_persistence.py)

ViolationEngine, AuditLogger, WorkflowRunModel의 DB 저장 동작을 인메모리 SQLite로 검증합니다.

커버 범위:
  - ViolationEngine: judge FAIL → Violation 생성 및 필드 정합성
  - ViolationEngine: judge PASS → None 반환 (기록 미생성)
  - ViolationEngine: rule 트리거 → source="rule" Violation 생성
  - ViolationModel: DB 저장 및 조회
  - EvidenceSpanModel: ViolationModel과 연결 저장
  - AuditLogger.log(): AuditLogModel 저장
  - AuditLogger.log_policy_evaluation(): 정책 평가 이벤트 저장
  - AuditLogger.log_run_summary(): WorkflowRunModel 저장
  - 동일 run_id 다중 이벤트 저장
  - context_json 직렬화 정합성
"""

import json

import pytest
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from src.database import models as _models_module  # noqa: F401 — 테이블 등록을 위해 임포트 필요
from src.database.connection import Base
from src.database.models import AuditLogModel, EvidenceSpanModel, ViolationModel, WorkflowRunModel
from src.engines.violation_engine import ViolationEngine
from src.schemas.audit import AuditLogCreate
from src.schemas.judge import JudgeResult
from src.schemas.policy import (
    Policy,
    PolicyAction,
    PolicyEvaluationResult,
    PolicyJudgeConfig,
)
from src.schemas.workflow import EvaluateRequest
from src.services.audit_logger import AuditLogger


# ──────────────────────────────────────────────────────────────────────────────
# 공용 픽스처
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    """각 테스트마다 독립된 인메모리 SQLite 세션을 제공합니다."""
    _engine = sa_create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(_engine)
    Session = sessionmaker(bind=_engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(_engine)


# ──────────────────────────────────────────────────────────────────────────────
# 공용 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_policy(
    policy_id: str = "GROUND_001",
    category: str = "groundedness",
    action_type: str = "LOG",
) -> Policy:
    return Policy(
        id=policy_id,
        name=f"test_{policy_id.lower()}",
        type="judge",
        judge_required="always",
        severity="medium",
        category=category,
        action=PolicyAction(type=action_type, message="violation detected"),
        judge=PolicyJudgeConfig(enabled=True, criteria="Test criteria"),
    )


def _make_eval_result(
    policy: Policy,
    triggered: bool = False,
    judge_required: bool = True,
    recommended_action: str = "LOG",
    evidence_spans: list | None = None,
) -> PolicyEvaluationResult:
    return PolicyEvaluationResult(
        policy_id=policy.id,
        policy_name=policy.name,
        triggered=triggered,
        judge_required=judge_required,
        judge_result=None,
        recommended_action=recommended_action,
        severity=policy.severity,
        reason="Judge evaluation required." if not triggered else "Rule matched.",
        evidence_spans=evidence_spans or [],
    )


def _persist_violation(session, violation) -> ViolationModel:
    """Violation 도메인 객체를 ViolationModel로 변환하여 DB에 저장합니다."""
    record = ViolationModel(
        violation_id=violation.id,
        run_id=violation.run_id,
        policy_id=violation.policy_id,
        policy_name=violation.policy_name,
        reason=violation.reason,
        source=violation.source,
        risk_score=violation.risk_score,
        recommended_action=violation.recommended_action,
        judge_verdict=violation.judge_verdict,
        judge_confidence=violation.judge_confidence,
    )
    session.add(record)
    session.commit()
    return record


# ──────────────────────────────────────────────────────────────────────────────
# 1. ViolationEngine — 도메인 객체 생성 검증
# ──────────────────────────────────────────────────────────────────────────────

def test_violation_engine_judge_fail_creates_violation():
    """judge FAIL → Violation 객체가 정확한 필드로 생성되어야 합니다."""
    policy = _make_policy("GROUND_001", category="groundedness")
    judge_result = JudgeResult(verdict="FAIL", confidence=0.72, reason="응답이 컨텍스트와 불일치합니다.")
    eval_result = _make_eval_result(policy)

    violation = ViolationEngine().from_policy_result(
        run_id="run_ve_001",
        policy=policy,
        result=eval_result,
        judge_result=judge_result,
        response="관련 없는 응답",
    )

    assert violation is not None
    assert violation.run_id == "run_ve_001"
    assert violation.policy_id == "GROUND_001"
    assert violation.source == "judge"
    assert violation.judge_verdict == "FAIL"
    assert violation.judge_confidence == pytest.approx(0.72)
    assert violation.risk_score == pytest.approx(0.72)
    assert violation.id.startswith("vio_")


def test_violation_engine_judge_pass_returns_none():
    """judge PASS → Violation이 생성되지 않아야 합니다."""
    policy = _make_policy("GROUND_001")
    judge_result = JudgeResult(verdict="PASS", confidence=0.85, reason="컨텍스트와 일치합니다.")
    eval_result = _make_eval_result(policy)

    violation = ViolationEngine().from_policy_result(
        run_id="run_ve_002",
        policy=policy,
        result=eval_result,
        judge_result=judge_result,
        response="정상 응답",
    )

    assert violation is None


def test_violation_engine_rule_trigger_creates_violation_with_rule_source():
    """rule 트리거 → source="rule"인 Violation이 생성되어야 합니다."""
    policy = _make_policy("CONTENT_001", category="content_safety", action_type="BLOCK")
    eval_result = _make_eval_result(
        policy,
        triggered=True,
        judge_required=False,
        recommended_action="BLOCK",
        evidence_spans=[{"text": "금지 단어", "source": "rule", "condition": "keyword_match"}],
    )

    violation = ViolationEngine().from_policy_result(
        run_id="run_ve_003",
        policy=policy,
        result=eval_result,
    )

    assert violation is not None
    assert violation.source == "rule"
    assert violation.recommended_action == "BLOCK"
    assert violation.judge_verdict is None


def test_violation_engine_evidence_text_fallback_uses_response_slice():
    """judge_result에 evidence_text가 없으면 response 앞 120자를 사용해야 합니다."""
    policy = _make_policy("GROUND_001")
    judge_result = JudgeResult(verdict="FAIL", confidence=0.6, reason="불일치", evidence_text=None)
    long_response = "응답 " * 100
    eval_result = _make_eval_result(policy)

    violation = ViolationEngine().from_policy_result(
        run_id="run_ve_004",
        policy=policy,
        result=eval_result,
        judge_result=judge_result,
        response=long_response,
    )

    assert violation is not None
    assert violation.evidence_span is not None
    assert len(violation.evidence_span.text) <= 120


# ──────────────────────────────────────────────────────────────────────────────
# 2. ViolationModel — DB 저장/조회
# ──────────────────────────────────────────────────────────────────────────────

def test_violation_model_saved_and_retrieved(db_session):
    """ViolationModel이 DB에 저장되고 올바르게 조회되어야 합니다."""
    policy = _make_policy("GROUND_001")
    judge_result = JudgeResult(verdict="FAIL", confidence=0.7, reason="불일치")
    eval_result = _make_eval_result(policy)

    violation = ViolationEngine().from_policy_result(
        run_id="run_db_001",
        policy=policy,
        result=eval_result,
        judge_result=judge_result,
        response="테스트 응답",
    )
    assert violation is not None
    _persist_violation(db_session, violation)

    saved = db_session.query(ViolationModel).filter_by(run_id="run_db_001").first()
    assert saved is not None
    assert saved.judge_verdict == "FAIL"
    assert saved.policy_id == "GROUND_001"
    assert saved.source == "judge"
    assert saved.violation_id == violation.id


def test_violation_model_multiple_violations_for_same_run(db_session):
    """동일 run_id에 대해 여러 위반이 독립적으로 저장되어야 합니다."""
    policy_ids = ["GROUND_001", "CONTENT_001"]
    for pid in policy_ids:
        policy = _make_policy(pid)
        judge_result = JudgeResult(verdict="FAIL", confidence=0.6, reason=f"{pid} 위반")
        eval_result = _make_eval_result(policy)
        violation = ViolationEngine().from_policy_result(
            run_id="run_db_multi",
            policy=policy,
            result=eval_result,
            judge_result=judge_result,
            response="응답",
        )
        assert violation is not None
        _persist_violation(db_session, violation)

    records = db_session.query(ViolationModel).filter_by(run_id="run_db_multi").all()
    assert len(records) == 2
    saved_policy_ids = {r.policy_id for r in records}
    assert saved_policy_ids == set(policy_ids)


# ──────────────────────────────────────────────────────────────────────────────
# 3. EvidenceSpanModel — Violation과 연결 저장
# ──────────────────────────────────────────────────────────────────────────────

def test_evidence_span_model_linked_to_violation(db_session):
    """EvidenceSpanModel이 violation_id로 ViolationModel과 연결 저장되어야 합니다."""
    policy = _make_policy("GROUND_001")
    judge_result = JudgeResult(
        verdict="FAIL", confidence=0.8, reason="모순 발견", evidence_text="위반 증거 텍스트"
    )
    eval_result = _make_eval_result(policy)

    violation = ViolationEngine().from_policy_result(
        run_id="run_span_001",
        policy=policy,
        result=eval_result,
        judge_result=judge_result,
        response="응답",
    )
    assert violation is not None
    _persist_violation(db_session, violation)

    span = EvidenceSpanModel(
        violation_id=violation.id,
        text=violation.evidence_span.text,
        source=violation.evidence_span.source,
        policy_id=violation.policy_id,
        confidence=violation.evidence_span.confidence,
        human_reason=violation.evidence_span.human_reason,
    )
    db_session.add(span)
    db_session.commit()

    saved_span = db_session.query(EvidenceSpanModel).filter_by(violation_id=violation.id).first()
    assert saved_span is not None
    assert saved_span.text == violation.evidence_span.text
    assert saved_span.policy_id == "GROUND_001"


# ──────────────────────────────────────────────────────────────────────────────
# 4. AuditLogger — 이벤트 기록
# ──────────────────────────────────────────────────────────────────────────────

def test_audit_logger_log_saves_audit_log_model(db_session):
    """AuditLogger.log()가 AuditLogModel을 DB에 저장해야 합니다."""
    logger = AuditLogger(db=db_session)
    logger.log(AuditLogCreate(
        run_id="run_audit_001",
        event_type="judge_evaluation",
        entity_type="policy",
        entity_id="GROUND_001",
        reason="Judge가 FAIL을 반환했습니다.",
        context_json={"verdict": "FAIL", "confidence": 0.72},
    ))

    record = db_session.query(AuditLogModel).filter_by(run_id="run_audit_001").first()
    assert record is not None
    assert record.event_type == "judge_evaluation"
    assert record.entity_id == "GROUND_001"
    assert "FAIL" in record.reason


def test_audit_logger_log_policy_evaluation(db_session):
    """AuditLogger.log_policy_evaluation()이 AuditLogModel을 저장해야 합니다."""
    logger = AuditLogger(db=db_session)
    logger.log_policy_evaluation(
        run_id="run_audit_002",
        has_violation=True,
        context={"policy_id": "CONTENT_001", "action": "BLOCK"},
    )

    record = db_session.query(AuditLogModel).filter_by(run_id="run_audit_002").first()
    assert record is not None
    assert record.event_type == "policy_evaluation"
    assert record.entity_type == "run"
    assert "Violation detected" in record.reason


def test_audit_logger_log_policy_evaluation_no_violation(db_session):
    """위반 없을 때 log_policy_evaluation()이 올바른 reason을 저장해야 합니다."""
    logger = AuditLogger(db=db_session)
    logger.log_policy_evaluation(
        run_id="run_audit_003",
        has_violation=False,
        context={},
    )

    record = db_session.query(AuditLogModel).filter_by(run_id="run_audit_003").first()
    assert record is not None
    assert "No violation" in record.reason


def test_audit_logger_log_context_json_serialized_correctly(db_session):
    """context_json이 dict로 전달될 때 JSON 문자열로 직렬화되어야 합니다."""
    logger = AuditLogger(db=db_session)
    context = {"verdict": "PASS", "confidence": 0.85, "policy": "GROUND_001"}
    logger.log(AuditLogCreate(
        run_id="run_audit_json",
        event_type="judge_evaluation",
        entity_type="policy",
        reason="테스트",
        context_json=context,
    ))

    record = db_session.query(AuditLogModel).filter_by(run_id="run_audit_json").first()
    assert record is not None
    parsed = json.loads(record.context_json)
    assert parsed["verdict"] == "PASS"
    assert parsed["confidence"] == pytest.approx(0.85)


def test_audit_logger_multiple_events_same_run(db_session):
    """동일 run_id에 대해 여러 감사 이벤트가 독립적으로 저장되어야 합니다."""
    logger = AuditLogger(db=db_session)
    event_types = ["judge_evaluation", "policy_evaluation", "action_applied"]
    for etype in event_types:
        logger.log(AuditLogCreate(
            run_id="run_audit_multi",
            event_type=etype,
            entity_type="policy",
            reason=f"{etype} 완료",
            context_json={},
        ))

    records = db_session.query(AuditLogModel).filter_by(run_id="run_audit_multi").all()
    assert len(records) == 3
    saved_types = {r.event_type for r in records}
    assert saved_types == set(event_types)


# ──────────────────────────────────────────────────────────────────────────────
# 5. WorkflowRunModel — 실행 요약 저장
# ──────────────────────────────────────────────────────────────────────────────

def test_audit_logger_log_run_summary_saves_workflow_run(db_session):
    """AuditLogger.log_run_summary()가 WorkflowRunModel을 DB에 저장해야 합니다."""
    logger = AuditLogger(db=db_session)
    request = EvaluateRequest(
        run_id="run_wf_001",
        input="테스트 입력",
        context={"user_id": "user_001"},
    )
    logger.log_run_summary(
        request=request,
        final_output="정상 처리된 응답입니다.",
        final_action="LOG",
    )

    record = db_session.query(WorkflowRunModel).filter_by(run_id="run_wf_001").first()
    assert record is not None
    assert record.input == "테스트 입력"
    assert record.output == "정상 처리된 응답입니다."
    assert record.final_action == "LOG"
    assert record.has_violation is False


def test_audit_logger_log_run_summary_block_sets_has_violation(db_session):
    """final_action이 BLOCK이면 has_violation=True로 저장되어야 합니다."""
    logger = AuditLogger(db=db_session)
    request = EvaluateRequest(
        run_id="run_wf_002",
        input="위반 입력",
        context={},
    )
    logger.log_run_summary(
        request=request,
        final_output="차단 메시지",
        final_action="BLOCK",
    )

    record = db_session.query(WorkflowRunModel).filter_by(run_id="run_wf_002").first()
    assert record is not None
    assert record.has_violation is True
    assert record.final_action == "BLOCK"


# ──────────────────────────────────────────────────────────────────────────────
# 6. 전체 파이프라인 기록 흐름: judge FAIL → Violation 저장 → AuditLog 저장
# ──────────────────────────────────────────────────────────────────────────────

def test_full_pipeline_judge_fail_records_violation_and_audit(db_session):
    """judge FAIL 판정이 ViolationModel과 AuditLogModel 양쪽에 모두 기록되어야 합니다."""
    run_id = "run_pipeline_001"
    policy = _make_policy("GROUND_001")
    judge_result = JudgeResult(verdict="FAIL", confidence=0.75, reason="컨텍스트와 불일치")
    eval_result = _make_eval_result(policy)

    violation = ViolationEngine().from_policy_result(
        run_id=run_id,
        policy=policy,
        result=eval_result,
        judge_result=judge_result,
        response="불일치 응답",
    )
    assert violation is not None
    _persist_violation(db_session, violation)

    logger = AuditLogger(db=db_session)
    logger.log(AuditLogCreate(
        run_id=run_id,
        event_type="judge_evaluation",
        entity_type="policy",
        entity_id=policy.id,
        reason=f"Judge FAIL: {judge_result.reason}",
        context_json={"verdict": "FAIL", "confidence": judge_result.confidence},
    ))

    saved_violation = db_session.query(ViolationModel).filter_by(run_id=run_id).first()
    saved_audit = db_session.query(AuditLogModel).filter_by(run_id=run_id).first()

    assert saved_violation is not None
    assert saved_violation.judge_verdict == "FAIL"

    assert saved_audit is not None
    assert saved_audit.event_type == "judge_evaluation"
    assert saved_audit.entity_id == "GROUND_001"
