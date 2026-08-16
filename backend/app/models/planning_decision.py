from typing import Optional

from pydantic import BaseModel


class PlanningDecision(BaseModel):
    story_id: str
    selected: bool
    reason: str
    remaining_capacity: int
    blocked_by: Optional[list[str]] = None
