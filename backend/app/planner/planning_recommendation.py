from backend.app.models.story import Story
from backend.app.planner.simulation import simulate_story_removal


def compare_story_removals(
    stories: list[Story],
    capacity: int,
    selected_story_ids: list[str],
) -> list[dict]:
    comparisons = []

    for story_id in selected_story_ids:
        result = simulate_story_removal(
            stories,
            capacity,
            story_id,
        )

        comparisons.append({
            "story_id": story_id,
            "original_points": result["original"]["total_points"],
            "simulated_points": result["simulated"]["total_points"],
            "remaining_capacity": result["simulated"]["remaining_capacity"],
            "original_risk": result["original"]["risk"]["overall_level"],
            "simulated_risk": result["simulated"]["risk"]["overall_level"],
            "added_stories": result["changes"]["added_stories"],
            "removed_stories": result["changes"]["removed_stories"],
            "explanation": result["changes"]["explanation"],
        })

    return comparisons
