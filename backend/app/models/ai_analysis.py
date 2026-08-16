from typing import Optional

from pydantic import BaseModel


class AIRisk(BaseModel):
    story_id: Optional[str] = None
    type: str
    message: str
    label: Optional[str] = None


class AIAnalysis(BaseModel):
    summary: str
    risks: list[AIRisk]
    recommendations: list[str]
