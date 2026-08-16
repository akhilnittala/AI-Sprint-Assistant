from typing import Any

from pydantic import BaseModel


class SprintContext(BaseModel):
    team: str
    planning_capacity: int
    total_story_points: int
    remaining_capacity: int
    selected_stories: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    risk_analysis: dict[str, Any]
