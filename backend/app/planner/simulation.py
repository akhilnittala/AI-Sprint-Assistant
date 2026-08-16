from backend.app.models.story import Story
from backend.app.planner.planner import plan_sprint
from backend.app.planner.sprint_risk import analyze_sprint_risk


def simulate_story_removal(
    stories: list[Story],
    capacity: int,
    story_id: str,
) -> dict:
    original_selected = plan_sprint(
        stories,
        capacity,
    )

    remaining_stories = [
        story
        for story in stories
        if story.id != story_id
    ]

    new_selected = plan_sprint(
        remaining_stories,
        capacity,
    )

    original_risk = analyze_sprint_risk(
        original_selected
    )

    new_risk = analyze_sprint_risk(
        new_selected
    )

    original_points = sum(
        story.story_points
        for story in original_selected
    )

    new_points = sum(
        story.story_points
        for story in new_selected
    )

    original_ids = {
        story.id
        for story in original_selected
    }

    new_ids = {
        story.id
        for story in new_selected
    }

    added_stories = sorted(
        new_ids - original_ids
    )

    removed_stories = sorted(
        original_ids - new_ids
    )

    explanation = (
        f"Removing {story_id} changes the sprint from "
        f"{original_points} to {new_points} points. "
        f"The simulated sprint has "
        f"{capacity - new_points} points remaining capacity. "
        f"Stories removed from the original sprint: "
        f"{', '.join(removed_stories) or 'none'}. "
        f"Stories added by the planner: "
        f"{', '.join(added_stories) or 'none'}. "
        f"Overall risk changes from "
        f"{original_risk['overall_level']} to "
        f"{new_risk['overall_level']}."
    )

    return {
        "removed_story_id": story_id,
        "original": {
            "story_ids": [
                story.id
                for story in original_selected
            ],
            "total_points": original_points,
            "risk": original_risk,
        },
        "simulated": {
            "story_ids": [
                story.id
                for story in new_selected
            ],
            "total_points": new_points,
            "remaining_capacity": capacity - new_points,
            "risk": new_risk,
        },
        "changes": {
            "added_stories": added_stories,
            "removed_stories": removed_stories,
            "explanation": explanation,
        },
    }
