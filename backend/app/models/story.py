from pydantic import BaseModel, Field
from typing import List


class Story(BaseModel):
    id: str
    title: str
    description: str
    story_points: int = Field(default=0, ge=0)

    # Original Jira estimate, if available.
    jira_story_points: int | None = Field(
        default=None,
        ge=0,
    )

    # Qwen estimate when Jira has no estimate.
    ai_estimated_points: int | None = Field(
        default=None,
        ge=0,
    )

    # JIRA or AI_ESTIMATED
    story_points_source: str = "JIRA"

    # AI confidence from 0-100.
    ai_estimation_confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    # Why Qwen selected the estimate.
    ai_estimation_reason: str | None = None

    priority: str
    status: str
    team: str = "Unassigned"
    dependencies: List[str] = []
    labels: List[str] = []
    active_sprint: str | None = None

    pull_requests: list[dict] = []


class SprintReview(BaseModel):
    sprint_id: str
    sprint_name: str
    done: list[dict] = []
    in_review: list[dict] = []
    in_progress: list[dict] = []
