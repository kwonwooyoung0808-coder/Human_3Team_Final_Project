from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class DocParserState(TypedDict, total=False):
    file_path: str
    policy_name: str
    effective_date: str
    raw_text: str
    raw_tables: list[dict]
    doc_structure: dict
    extracted_rules: dict
    yaml_content: str
    yaml_path: str
    validation_passed: bool
    warnings: list[str]
    policy_id: Optional[str]
    error_message: Optional[str]


class PolicyConvertResponse(BaseModel):
    policy_id: Optional[str]
    yaml_path: Optional[str]
    status: Literal["SUCCESS", "PARTIAL", "FAILED"]
    parsed_rules_count: int
    warnings: list[str]
