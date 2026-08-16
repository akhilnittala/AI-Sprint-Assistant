from typing import List

from backend.app.models.historical_sprint import HistoricalSprint


def calculate_average_velocity(
    sprints: List[HistoricalSprint],
) -> float:
    if not sprints:
        return 0.0

    total_completed = sum(
        sprint.completed_points for sprint in sprints
    )

    return total_completed / len(sprints)
