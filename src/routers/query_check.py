from fastapi import APIRouter, HTTPException

from src.schemas.query_risk import QueryCheckRequest, QueryCheckResponse

router = APIRouter(prefix="/v1/query", tags=["query-risk"])


@router.post("/check", response_model=QueryCheckResponse)
def query_check(_: QueryCheckRequest) -> QueryCheckResponse:
    raise HTTPException(status_code=501, detail="Feature 1 query check is not implemented yet.")
