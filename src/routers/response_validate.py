from fastapi import APIRouter, HTTPException

from src.schemas.compliance import ResponseValidateRequest, ResponseValidateResponse

router = APIRouter(prefix="/v1/response", tags=["response-compliance"])


@router.post("/validate", response_model=ResponseValidateResponse)
def response_validate(_: ResponseValidateRequest) -> ResponseValidateResponse:
    raise HTTPException(status_code=501, detail="Feature 2 response validate routing is not implemented yet.")
