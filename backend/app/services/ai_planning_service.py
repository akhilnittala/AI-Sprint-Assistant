from pathlib import Path

from backend.app.ai.factory import get_ai_provider
from backend.app.models.ai_analysis import AIAnalysis
from backend.app.models.sprint_context import SprintContext
from backend.app.models.story import Story
from backend.app.planner.sprint_risk import analyze_sprint_risk
from backend.app.services.planning_service import generate_sprint_plan


def generate_ai_sprint_plan(
    project_root: Path,
):
    sprint_plan = generate_sprint_plan(
        project_root
    )

    selected_stories = [
        Story(**story)
        for story in sprint_plan["selected_stories"]
    ]

    risk_analysis = analyze_sprint_risk(
        selected_stories
    )

    sprint_context = SprintContext(
        team=sprint_plan["team"],
        planning_capacity=sprint_plan["planning_capacity"],
        total_story_points=sprint_plan["total_story_points"],
        remaining_capacity=sprint_plan["remaining_capacity"],
        selected_stories=sprint_plan["selected_stories"],
        decisions=sprint_plan["decisions"],
        risk_analysis=risk_analysis,
    )

    provider = get_ai_provider()

    analysis = AIAnalysis(
        **provider.analyze_sprint(sprint_context)
    )

    return {
        "planning": sprint_plan,
        "risk_analysis": risk_analysis,
        "ai_analysis": analysis.model_dump(),
    }
