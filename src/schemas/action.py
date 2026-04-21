from typing import Literal

from pydantic import BaseModel


class ActionResult(BaseModel):
    run_id: str
    action_type: Literal["BLOCK", "LOG"]
    status: Literal["applied", "skipped"] = "applied"
    message: str
    delivered_response: str

