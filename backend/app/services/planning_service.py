import json
from pathlib import Path

from backend.app.models.historical_sprint import HistoricalSprint
from backend.app.models.story import Story
from backend.app.services.jira_service import JiraService
from backend.app.models.team import Team
from backend.app.planner.capacity import calculate_planning_capacity
from backend.app.planner.planner import plan_sprint_with_decisions
from backend.app.planner.velocity import calculate_average_velocity
from backend.app.ai.qwen_story_estimator import estimate_missing_story_points


def generate_sprint_plan(
    project_root: Path,
):
    team_path = project_root / "data" / "team.json"
    history_path = project_root / "data" / "historical_sprints.json"

    with open(team_path) as file:
        team_data = json.load(file)

    with open(history_path) as file:
        history_data = json.load(file)

    stories = JiraService().get_backlog()

    # AI estimation happens ONLY during planning.
    # The /backlog endpoint remains fast.
    stories, ai_estimated_count, cached_count = (
        estimate_missing_story_points(stories)
    )

    print(
        f"Story estimation: "
        f"AI estimated={ai_estimated_count}, "
        f"cache hits={cached_count}"
    )

    team = Team(**team_data)

    historical_sprints = [
        HistoricalSprint(**sprint)
        for sprint in history_data
    ]

    average_velocity = calculate_average_velocity(
        historical_sprints
    )

    planning_capacity = team.planning_capacity

    selected, decisions = plan_sprint_with_decisions(
        stories,
        planning_capacity,
    )

    total_points = sum(
        story.story_points
        for story in selected
    )

    return {
        "team": team.name,
        "average_velocity": average_velocity,
        "capacity_factor": 0.85,
        "planning_capacity": planning_capacity,
        "selected_story_count": len(selected),
        "total_story_points": total_points,
        "remaining_capacity": planning_capacity - total_points,
        "selected_stories": [
            story.model_dump()
            for story in selected
        ],
        "decisions": [
            decision.model_dump()
            for decision in decisions
        ],
    }
