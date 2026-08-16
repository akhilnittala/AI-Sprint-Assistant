from pydantic import BaseModel


class WhatIfResult(BaseModel):
    removed_story_id: str

    original_story_ids: list[str]
    simulated_story_ids: list[str]

    original_points: int
    simulated_points: int

    remaining_capacity: int

    original_risk: str
    simulated_risk: str

    added_stories: list[str]
    removed_stories: list[str]

    explanation: str
