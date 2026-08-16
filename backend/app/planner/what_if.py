from backend.app.models.story import Story
from backend.app.models.what_if import WhatIfResult
from backend.app.planner.simulation import simulate_story_removal


def build_what_if_result(
    stories: list[Story],
    capacity: int,
    story_id: str,
) -> WhatIfResult:
    result = simulate_story_removal(
        stories,
        capacity,
        story_id,
    )

    return WhatIfResult(
        removed_story_id=result["removed_story_id"],
        original_story_ids=result["original"]["story_ids"],
        simulated_story_ids=result["simulated"]["story_ids"],
        original_points=result["original"]["total_points"],
        simulated_points=result["simulated"]["total_points"],
        remaining_capacity=result["simulated"]["remaining_capacity"],
        original_risk=result["original"]["risk"]["overall_level"],
        simulated_risk=result["simulated"]["risk"]["overall_level"],
        added_stories=result["changes"]["added_stories"],
        removed_stories=result["changes"]["removed_stories"],
        explanation=result["changes"]["explanation"],
    )
