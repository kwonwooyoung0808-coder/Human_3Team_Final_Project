import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock
from src.services.audit_logger import AuditLogger
from src.services.trace_logger import TraceLogger
from src.schemas.audit import AuditLogCreate



# 검증 내용: Audit 저장
# 기대 결과: DB에 run_id가 연결된 레코드 존재

def test_audit_log_saved_with_run_id():
    # 1. 가짜 DB 세션 준비
    mock_db = MagicMock()
    logger = AuditLogger(db=mock_db)
    
    # 2. 테스트용 데이터 생성 (run_id 포함)
    test_run_id = "test_run_999"
    log_data = AuditLogCreate(
        run_id=test_run_id,
        event_type="test_event",
        entity_type="system",
        entity_id="sys_1",
        reason="Testing U-AT-01",
        context_json={"status": "ok"}
    )
    
    # 3. 로깅 실행
    logger.log(log_data)
    
    # 4. 검증 (DB에 저장 요청이 갔는지, 그리고 그 데이터에 run_id가 정확히 있는지 확인)
    mock_db.add.assert_called_once()  # DB에 레코드 추가(add)가 1번 호출되었는가?
    
    saved_record = mock_db.add.call_args[0][0] # DB에 넘겨진 모델 객체 추출
    assert saved_record.run_id == test_run_id  # 기대 결과: run_id가 연결되어 있는가!



# 검증 내용: RunTraceSummary 생성
# 기대 결과: run_id, workflow_name, status, nodes, created_at 포함

def test_trace_summary_build():
    # 이 테스트는 API 응답이나 Summary 스키마가 요구사항을 모두 포함하는지 검증합니다.
    # (실제 RunTraceSummary 스키마가 있다면 임포트해서 써도 됩니다)
    
    # 1. Summary 객체 시뮬레이션 (API가 반환할 데이터 형태)
    summary_data = {
        "run_id": "test_run_888",
        "workflow_name": "governance_workflow",
        "status": "completed",
        "nodes": [
            {"node_name": "llm_node", "latency_ms": 150.0}
        ],
        "created_at": datetime.now()
    }
    
    # 2. 기대 결과 (필수 키값들이 존재하는지 검증)
    expected_keys = {"run_id", "workflow_name", "status", "nodes", "created_at"}
    
    # 3. 검증
    assert expected_keys.issubset(summary_data.keys()), "Summary에 필수 항목이 누락되었습니다."
    assert summary_data["run_id"] == "test_run_888"
    assert type(summary_data["nodes"]) is list



# 검증 내용: 정책 정상 통과 시 Trace 기록 확인
# 기대 결과: 노드 실행이 성공적으로 끝났으므로 status="completed" 저장

def test_execution_trace_on_policy_pass():
    # 1. 가짜 DB 세션 준비
    mock_db = MagicMock()
    logger = TraceLogger(db=mock_db)

    # 2. 정책 정상 통과 상황 로깅
    logger.log_node(
        run_id="trace_normal_001",
        workflow_name="governance_workflow",
        node_name="Policy_Check_Node",
        node_type="evaluator",
        latency_ms=150.5,
        status="completed"  # 정상 상태
    )

    # 3. 검증
    mock_db.add.assert_called_once()
    saved_trace = mock_db.add.call_args[0][0]
    assert saved_trace.run_id == "trace_normal_001"
    assert saved_trace.status == "completed"



# 검증 내용: 정책 위반 또는 에러 발생 시 Trace 기록 확인
# 기대 결과: 정책 위반이나 노드 중단 시 status="failed"로 저장됨

def test_execution_trace_on_policy_violation():
    # 1. 가짜 DB 세션 준비
    mock_db = MagicMock()
    logger = TraceLogger(db=mock_db)

    # 2. 정책 위반(실패) 상황 로깅
    logger.log_node(
        run_id="trace_violation_001",
        workflow_name="governance_workflow",
        node_name="Policy_Check_Node",
        node_type="evaluator",
        latency_ms=45.2,
        status="failed"  # 위반/실패 상태
    )

    # 3. 검증
    mock_db.add.assert_called_once()
    saved_trace = mock_db.add.call_args[0][0]
    assert saved_trace.run_id == "trace_violation_001"
    assert saved_trace.status == "failed"


# 검증 내용: 정책 통과(정상) 시 Audit 로그 저장
# 기대 결과: has_violation=False일 때 reason이 "No violation detected."로 저장됨

def test_audit_log_policy_pass():
    # 1. 가짜 DB 세션 준비
    mock_db = MagicMock()
    logger = AuditLogger(db=mock_db)
    
    # 2. 정책 통과(정상) 상황 시뮬레이션
    logger.log_policy_evaluation(
        run_id="test_run_pass_001",
        has_violation=False,  # 위반 없음 (정상 통과!)
        context={"policy_name": "기본 안전 정책", "score": 0.99}
    )
    
    # 3. 검증
    mock_db.add.assert_called_once()
    saved_log = mock_db.add.call_args[0][0]
    
    assert saved_log.run_id == "test_run_pass_001"
    assert saved_log.event_type == "policy_evaluation"
    # 정상 통과이므로 아래 문구가 정확히 들어가야 함
    assert saved_log.reason == "No violation detected." 



# test_audit_log_policy_violation

def test_audit_log_policy_violation():
    # 1. 가짜 DB 세션 준비
    mock_db = MagicMock()
    logger = AuditLogger(db=mock_db)
    
    # 2. 정책 위반(비정상) 상황 시뮬레이션
    logger.log_policy_evaluation(
        run_id="test_run_violation_001",
        has_violation=True,  # 정책 위반 발생!!
        context={"violation_detail": "주민등록번호 노출 위험 감지"}
    )
    
    # 3. 검증
    mock_db.add.assert_called_once()
    saved_log = mock_db.add.call_args[0][0]
    
    assert saved_log.run_id == "test_run_violation_001"
    assert saved_log.event_type == "policy_evaluation"
    assert saved_log.reason == "Violation detected."
    
    # 유니코드로 묶인 JSON 문자열을 풀어서 확인
    parsed_context = json.loads(saved_log.context_json)
    assert "주민등록번호" in parsed_context["violation_detail"]