from pydantic import BaseModel, Field
from typing import List


class Sprint(BaseModel):
    id: str
    name: str
    duration_days: int = Field(gt=0)
    capacity_points: int = Field(gt=0)
    selected_story_ids: List[str] = []
