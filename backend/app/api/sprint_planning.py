from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.models.what_if_request import WhatIfRequest
from backend.app.planner.what_if import build_what_if_result
from backend.app.services.ai_planning_service import generate_ai_sprint_plan
from backend.app.services.planning_service import generate_sprint_plan
from backend.app.services.jira_service import JiraService

from backend.app.services.recommendation_service import (
    generate_planning_recommendation,
)
from backend.app.services.assistant_service import (
    generate_sprint_assistant_result,
)
from backend.app.services.story_estimation_cache import cache_stats

from backend.app.services.sprint_review_service import SprintReviewService
from backend.app.services.team_planning_service import (
    generate_team_plans,
)
router = APIRouter(
    prefix="/api/v1/sprint-planning",
    tags=["sprint-planning"],
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@router.get("/backlog")
def get_backlog():
    stories = JiraService().get_backlog()

    return {
        "count": len(stories),
        "stories": [
            story.model_dump()
            for story in stories
        ],
    }


@router.post("/plan")
def plan_sprint():
    return generate_sprint_plan(PROJECT_ROOT)


@router.post("/ai-plan")
def ai_plan_sprint():
    return generate_ai_sprint_plan(PROJECT_ROOT)


@router.post("/what-if")
def what_if_sprint(request: WhatIfRequest):
    stories = JiraService().get_backlog()

    story_ids = {
        story.id
        for story in stories
    }

    if request.story_id not in story_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Story '{request.story_id}' was not found.",
        )

    plan = generate_sprint_plan(PROJECT_ROOT)

    result = build_what_if_result(
        stories=stories,
        capacity=plan["planning_capacity"],
        story_id=request.story_id,
    )

    return result

@router.post("/recommendation")
def recommend_sprint():
    return generate_planning_recommendation(PROJECT_ROOT)

@router.post("/assistant")
def sprint_assistant():
    return generate_sprint_assistant_result(PROJECT_ROOT)


@router.post("/team-plan")
def team_plan(config: dict | None = None):
    """
    Generate independent sprint plans using the
    per-team configuration supplied by the UI.
    """
    team_configs = {}

    if config:
        team_configs = config.get(
            "teams",
            {},
        )

    return generate_team_plans(
        PROJECT_ROOT,
        team_configs,
    )


@router.get("/estimation-cache")
def estimation_cache():
    return cache_stats()


@router.get("/active-sprints")
def active_sprints():
    return {
        "sprints": SprintReviewService().get_active_sprints()
    }


@router.get("/sprint-review/{sprint_id}")
def sprint_review(sprint_id: int):
    return SprintReviewService().generate_review(
        sprint_id
    )


@router.get("/sprint-review/{sprint_id}/markdown")
def sprint_review_markdown(sprint_id: int):
    service = SprintReviewService()

    report = service.generate_review(
        sprint_id
    )

    return {
        "filename": (
            f"{report['sprint']['name']}"
            ".replace(' ', '_')"
            ".replace('/', '_')"
            ".md"
        ),
        "content": service.generate_markdown(
            report
        ),
    }
