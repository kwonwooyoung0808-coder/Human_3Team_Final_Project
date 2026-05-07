from typing import Literal

from pydantic import BaseModel


class ActionResult(BaseModel):
    run_id: str
<<<<<<< Updated upstream
    action_type: Literal["BLOCK", "LOG"]
=======
    action_type: Literal["BLOCK", "LOG", "PASS"]
>>>>>>> Stashed changes
    status: Literal["applied", "skipped"] = "applied"
    message: str
    delivered_response: str

