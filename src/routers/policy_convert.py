from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.schemas.doc_parser import PolicyConvertResponse

router = APIRouter(prefix="/v1/policy", tags=["policy-convert"])


@router.post("/convert", response_model=PolicyConvertResponse)
async def policy_convert(
    file: UploadFile = File(...),
    policy_name: str = Form(...),
    effective_date: str = Form(...),
) -> PolicyConvertResponse:
    _ = (file, policy_name, effective_date)
    raise HTTPException(status_code=501, detail="Feature 3 policy convert is not implemented yet.")
