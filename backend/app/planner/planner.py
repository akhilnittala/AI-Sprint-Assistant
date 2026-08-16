from typing import List, Tuple

from backend.app.models.planning_decision import PlanningDecision
from backend.app.models.story import Story


PRIORITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


def _sort_stories(stories: List[Story]) -> List[Story]:
    return sorted(
        stories,
        key=lambda story: (
            PRIORITY_ORDER.get(story.priority, 99),
            story.story_points,
        ),
    )


def plan_sprint(
    stories: List[Story],
    capacity_points: int,
) -> List[Story]:
    selected, _ = plan_sprint_with_decisions(
        stories,
        capacity_points,
    )
    return selected


def plan_sprint_with_decisions(
    stories: List[Story],
    capacity_points: int,
) -> Tuple[List[Story], List[PlanningDecision]]:
    if capacity_points <= 0:
        raise ValueError("capacity_points must be greater than 0")

    available_stories = [
        story
        for story in stories
        if (
            story.status == "TODO"
            and not getattr(
                story,
                "active_sprint",
                None,
            )
        )
    ]

    available_stories = _sort_stories(available_stories)

    selected: List[Story] = []
    selected_ids = set()
    decisions = []

    remaining_capacity = capacity_points

    while True:
        progress = False

        for story in available_stories:
            if story.id in selected_ids:
                continue

            if story.story_points > remaining_capacity:
                continue

            dependencies_satisfied = all(
                dependency in selected_ids
                for dependency in story.dependencies
            )

            if not dependencies_satisfied:
                continue

            selected.append(story)
            selected_ids.add(story.id)
            remaining_capacity -= story.story_points
            progress = True

        if not progress or remaining_capacity == 0:
            break

    for story in available_stories:
        if story.id in selected_ids:
            decisions.append(
                PlanningDecision(
                    story_id=story.id,
                    selected=True,
                    reason="Selected because priority, dependencies, and capacity requirements were satisfied.",
                    remaining_capacity=remaining_capacity,
                )
            )
            continue

        blocked_dependencies = [
            dependency
            for dependency in story.dependencies
            if dependency not in selected_ids
        ]

        if blocked_dependencies:
            reason = "Not selected because required dependencies were not selected."
        elif remaining_capacity == 0:
            reason = (
                f"{story.title}: Not selected because there are no points "
                f"left in the sprint capacity."
            )
        elif story.story_points > remaining_capacity:
            reason = (
                f"{story.title}: Not selected because it requires "
                f"{story.story_points} points but only {remaining_capacity} "
                f"points remain."
            )
        else:
            reason = "Not selected because the planning capacity was exhausted."

        decisions.append(
            PlanningDecision(
                story_id=story.id,
                selected=False,
                reason=reason,
                remaining_capacity=remaining_capacity,
                blocked_by=blocked_dependencies or None,
            )
        )

    return selected, decisions
