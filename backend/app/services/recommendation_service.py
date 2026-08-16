import json
from pathlib import Path

from backend.app.models.historical_sprint import HistoricalSprint
from backend.app.models.story import Story
from backend.app.services.jira_service import JiraService
from backend.app.planner.capacity import calculate_planning_capacity
from backend.app.planner.recommendation import recommend_sprint_change
from backend.app.planner.velocity import calculate_average_velocity


def generate_planning_recommendation(
    project_root: Path,
):
    historical_path = project_root / "data" / "historical_sprints.json"

    historical_data = json.loads(
        historical_path.read_text()
    )

    stories = JiraService().get_backlog()

    historical_sprints = [
        HistoricalSprint(**item)
        for item in historical_data
    ]

    average_velocity = calculate_average_velocity(
        historical_sprints
    )

    capacity = calculate_planning_capacity(
        average_velocity
    )

    recommendation = recommend_sprint_change(
        stories,
        capacity,
    )

    return {
        "average_velocity": average_velocity,
        "planning_capacity": capacity,
        "recommendation": recommendation.model_dump(),
    }
