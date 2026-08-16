from pydantic import BaseModel


class PlanningRecommendation(BaseModel):
    recommendation: str
    rationale: list[str]
    preferred_story_ids: list[str]
    avoided_story_ids: list[str]
