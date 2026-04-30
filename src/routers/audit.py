from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.core.dependencies import get_db
from src.database.models import QueryAuditLogModel, ResponseAuditLogModel, PolicyConversionLogModel
from src.schemas.audit import (
    QueryAuditLogResponse, 
    ResponseAuditLogResponse, 
    PolicyConversionLogResponse,
    BlockedReportItem # 추가된 스키마, Block 처리 보고서 형식 출력.
)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

# ==========================================
# 1. Feature 1: 질의 위험 감지 로그 목록 조회
# ==========================================
@router.get("/query", response_model=list[QueryAuditLogResponse])
def list_query_audits(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(QueryAuditLogModel)
        .order_by(QueryAuditLogModel.created_at.desc())
        .limit(limit)
    ).all()
    return rows

@router.get("/query/{audit_id}", response_model=QueryAuditLogResponse)
def get_query_audit_detail(audit_id: str, db: Session = Depends(get_db)):
    log = db.get(QueryAuditLogModel, audit_id)
    if not log:
        raise HTTPException(status_code=404, detail="질의 감사 로그를 찾을 수 없습니다.")
    return log

# ==========================================
# 2. Feature 2: 응답 내규 검증 로그 목록 조회
# ==========================================
@router.get("/response", response_model=list[ResponseAuditLogResponse])
def list_response_audits(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ResponseAuditLogModel)
        .order_by(ResponseAuditLogModel.created_at.desc())
        .limit(limit)
    ).all()
    return rows

@router.get("/response/{audit_id}", response_model=ResponseAuditLogResponse)
def get_response_audit_detail(audit_id: str, db: Session = Depends(get_db)):
    log = db.get(ResponseAuditLogModel, audit_id)
    if not log:
        raise HTTPException(status_code=404, detail="응답 감사 로그를 찾을 수 없습니다.")
    return log

# ==========================================
# 3. Feature 3: 정책 문서 변환 로그 조회
# ==========================================
@router.get("/conversions", response_model=list[PolicyConversionLogResponse])
def list_policy_conversions(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PolicyConversionLogModel)
        .order_by(PolicyConversionLogModel.created_at.desc())
        .limit(limit)
    ).all()
    return rows

# ==========================================
# 4. Feature 1 & 2 통합: 차단 내역 종합 보고서
# ==========================================
@router.get("/reports/blocked", response_model=list[BlockedReportItem])
def get_blocked_audit_report(limit: int = 50, db: Session = Depends(get_db)):
    """
    관리자용 종합 보고서: 
    질의 중 차단(BLOCKED)된 건과 응답 중 차단(REJECTED)된 건을 
    최신 시간순으로 통합하여 보고서 형태로 출력합니다.
    """
    # 1. BLOCKED 상태인 질의(Query) 가져오기
    blocked_queries = db.scalars(
        select(QueryAuditLogModel)
        .where(QueryAuditLogModel.status == "BLOCKED")
        .order_by(QueryAuditLogModel.created_at.desc())
        .limit(limit)
    ).all()

    # 2. REJECTED 상태인 응답(Response) 가져오기
    rejected_responses = db.scalars(
        select(ResponseAuditLogModel)
        .where(ResponseAuditLogModel.status == "REJECTED")
        .order_by(ResponseAuditLogModel.created_at.desc())
        .limit(limit)
    ).all()

    # 3. 두 데이터를 프론트엔드가 요구하는 '보고서 규격(BlockedReportItem)'으로 통일
    report = []
    
    for q in blocked_queries:
        report.append({
            "audit_id": q.id,
            "event_type": "질의(Query) 차단",
            "agent_id": q.agent_id,
            "policy_id": q.policy_id,
            "content": q.query,
            "risk_score": q.risk_score,
            "violation_details": q.risk_reasons if isinstance(q.risk_reasons, dict) else {},
            "detected_at": q.created_at
        })

    for r in rejected_responses:
        report.append({
            "audit_id": r.id,
            "event_type": "응답(Response) 차단",
            "agent_id": r.agent_id,
            "policy_id": r.policy_id,
            "content": r.response,
            "risk_score": r.compliance_score, # 응답은 컴플라이언스 점수 사용
            "violation_details": r.violations if isinstance(r.violations, dict) else {},
            "detected_at": r.created_at
        })

    # 4. 질의와 응답이 섞여 있으므로, 시간을 기준으로 다시 최신순 정렬
    report.sort(key=lambda x: x["detected_at"], reverse=True)

    return report[:limit]