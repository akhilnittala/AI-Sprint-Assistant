import json
from pathlib import Path

from backend.app.ai.factory import get_ai_provider
from backend.app.models.historical_sprint import HistoricalSprint
from backend.app.models.sprint_context import SprintContext
from backend.app.models.story import Story
from backend.app.services.jira_service import JiraService
from backend.app.planner.capacity import calculate_planning_capacity
from backend.app.planner.planner import plan_sprint_with_decisions
from backend.app.planner.recommendation import recommend_sprint_change
from backend.app.planner.sprint_risk import analyze_sprint_risk
from backend.app.planner.velocity import calculate_average_velocity


def generate_sprint_assistant_result(
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

    planning_capacity = calculate_planning_capacity(
        average_velocity
    )

    selected_stories, decisions = plan_sprint_with_decisions(
        stories,
        planning_capacity,
    )

    total_story_points = sum(
        story.story_points
        for story in selected_stories
    )

    remaining_capacity = (
        planning_capacity - total_story_points
    )

    risk_analysis = analyze_sprint_risk(
        selected_stories
    )

    recommendation = recommend_sprint_change(
        stories,
        planning_capacity,
    )

    context = SprintContext(
        team="GitOps Engineering Team",
        planning_capacity=planning_capacity,
        total_story_points=total_story_points,
        remaining_capacity=remaining_capacity,
        selected_stories=[
            story.model_dump()
            for story in selected_stories
        ],
        decisions=[
            decision.model_dump()
            for decision in decisions
        ],
        risk_analysis=risk_analysis,
    )

    provider = get_ai_provider()

    ai_analysis = provider.analyze_sprint(
        context
    )

    return {
        "planning": {
            "team": "GitOps Engineering Team",
            "average_velocity": average_velocity,
            "planning_capacity": planning_capacity,
            "selected_story_count": len(
                selected_stories
            ),
            "total_story_points": total_story_points,
            "remaining_capacity": remaining_capacity,
            "selected_stories": [
                story.model_dump()
                for story in selected_stories
            ],
            "decisions": [
                decision.model_dump()
                for decision in decisions
            ],
        },
        "risk_analysis": risk_analysis,
        "recommendation": recommendation.model_dump(),
        "ai_analysis": ai_analysis,
    }
