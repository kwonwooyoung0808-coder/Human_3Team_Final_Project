from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import AuditLogModel
from src.schemas.audit import AuditLogResponse, AuditReportResponse # 스키마 2개 임포트

# PRD 명세에 맞춰 prefix를 깔끔하게 다듬습니다.
router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

# ==========================================
# 1. 기존: 전체 감사 로그 목록 조회 (PRD 필드명 반영)
# ==========================================
@router.get("/logs", response_model=list[AuditLogResponse])
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(limit)))
    result = []
    
    for row in rows:
        result.append({
            "id": row.id,
            "run_id": row.run_id,
            "event_type": row.event_type,
            "input_text": row.input_text, # PRD: 질의/응답 내용
            "risk_score": row.risk_score, # PRD: 위험도 점수
            "reason": row.reason,
            # JSONB 필드이므로 파싱 에러 걱정 없이 바로 딕셔너리로 꺼냅니다.
            "risk_reasons": row.risk_reasons or {}, 
            "created_at": row.created_at,
        })
    return result


# ==========================================
# 2. 신규: 특정 감사 로그의 '상세 레포트' 출력 (PRD 요구사항)
# ==========================================
@router.get("/{audit_id}/report", response_model=AuditReportResponse)
def get_audit_report(audit_id: int, db: Session = Depends(get_db)):
    log = db.get(AuditLogModel, audit_id)
    if not log:
        raise HTTPException(status_code=404, detail="감사 로그를 찾을 수 없습니다.")

    return {
        "audit_id": log.id,
        "run_id": log.run_id,
        "event_type": log.event_type,
        "content": log.input_text or "",
        "risk_score": log.risk_score,
        "violation_details": log.risk_reasons or {},
        "detected_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S KST") # 한국 시간 포맷팅!
    }