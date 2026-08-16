from backend.app.models.planning_recommendation import PlanningRecommendation
from backend.app.models.story import Story
from backend.app.planner.planning_recommendation import compare_story_removals
from backend.app.planner.risk import calculate_story_risk


RISK_SCORE = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}


def recommend_sprint_change(
    stories: list[Story],
    capacity: int,
) -> PlanningRecommendation:
    selected = [
        story
        for story in stories
        if story.status == "TODO"
    ]

    comparisons = compare_story_removals(
        stories,
        capacity,
        [story.id for story in selected],
    )

    best = None
    best_score = float("-inf")

    for comparison in comparisons:
        original_risk = RISK_SCORE[
            comparison["original_risk"]
        ]

        simulated_risk = RISK_SCORE[
            comparison["simulated_risk"]
        ]

        risk_improvement = (
            original_risk - simulated_risk
        )

        capacity_gain = (
            comparison["remaining_capacity"]
        )

        story = next(
            story
            for story in stories
            if story.id == comparison["story_id"]
        )

        score = (
            risk_improvement * 10
            + capacity_gain
            + story.story_points * 0.1
        )

        if score > best_score:
            best_score = score
            best = comparison

    if best is None:
        return PlanningRecommendation(
            recommendation="Keep current sprint.",
            rationale=[
                "No sprint changes were available for evaluation."
            ],
            preferred_story_ids=[],
            avoided_story_ids=[],
        )

    selected_story = next(
        story
        for story in stories
        if story.id == best["story_id"]
    )

    story_risk = calculate_story_risk(selected_story)

    rationale = [
        (
            f"{selected_story.id} is a "
            f"{story_risk['level']}-risk story "
            f"with {selected_story.story_points} story points."
        ),
        (
            f"Removing {selected_story.id} leaves "
            f"{best['remaining_capacity']} points of capacity."
        ),
        (
            f"The simulated sprint contains "
            f"{best['simulated_points']} points."
        ),
        (
            f"Stories removed from the sprint: "
            f"{', '.join(best['removed_stories'])}."
        ),
        (
            f"Stories added by the planner: "
            f"{', '.join(best['added_stories']) or 'none'}."
        ),
        (
            f"Overall risk changes from "
            f"{best['original_risk']} to "
            f"{best['simulated_risk']}."
        ),
    ]

    return PlanningRecommendation(
        recommendation=(
            f"Consider removing {best['story_id']} "
            "from the sprint."
        ),
        rationale=rationale,
        preferred_story_ids=best["added_stories"],
        avoided_story_ids=best["removed_stories"],
    )
