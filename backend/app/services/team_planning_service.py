from pathlib import Path

from backend.app.services.jira_service import JiraService
from backend.app.planner.planner import plan_sprint_with_decisions


ALLOWED_TEAMS = {"Tangerine", "Crimson", "Scarlet"}


def _calculate_capacity(config):
    """
    Calculate sprint capacity for one team.

    staffing_capacity = people × capacity_per_person
    planning_capacity = min(staffing_capacity, velocity)

    If velocity is zero/not supplied, staffing capacity is used.
    """
    people = int(config.get("people", 0))
    capacity_per_person = int(
        config.get("capacity_per_person", 0)
    )
    velocity = float(config.get("velocity", 0))

    if people <= 0:
        return 0

    if capacity_per_person <= 0:
        return 0

    staffing_capacity = people * capacity_per_person

    if velocity > 0:
        return min(
            staffing_capacity,
            int(velocity),
        )

    return staffing_capacity


def generate_team_plans(
    project_root: Path,
    team_configs: dict | None = None,
):
    """
    Generate an independent sprint plan for each team.

    team_configs comes from the Streamlit UI:

    {
        "Tangerine": {
            "developers": 3,
            "qa_engineers": 1,
            "people": 4,
            "capacity_per_person": 8,
            "velocity": 28
        },
        ...
    }
    """

    stories = JiraService().get_backlog()

    if not team_configs:
        team_configs = {}

    teams = {
        "Tangerine": [],
        "Crimson": [],
        "Scarlet": [],
    }

    for story in stories:
        if story.team in ALLOWED_TEAMS:
            teams[story.team].append(story)

    result = []
    total_capacity = 0
    total_backlog_points = 0

    for team_name in (
        "Tangerine",
        "Crimson",
        "Scarlet",
    ):
        team_stories = teams[team_name]

        config = team_configs.get(
            team_name,
            {},
        )

        capacity = _calculate_capacity(config)

        total_capacity += capacity

        backlog_points = sum(
            story.story_points
            for story in team_stories
            if story.status == "TODO"
        )

        total_backlog_points += backlog_points

        if capacity > 0:
            selected, decisions = (
                plan_sprint_with_decisions(
                    team_stories,
                    capacity,
                )
            )
        else:
            selected = []
            decisions = []

        selected_points = sum(
            story.story_points
            for story in selected
        )

        result.append(
            {
                "team": team_name,

                "developers": int(
                    config.get("developers", 0)
                ),

                "qa_engineers": int(
                    config.get("qa_engineers", 0)
                ),

                "people": int(
                    config.get("people", 0)
                ),

                "capacity_per_person": int(
                    config.get(
                        "capacity_per_person",
                        0,
                    )
                ),

                "velocity": float(
                    config.get("velocity", 0)
                ),

                "staffing_capacity": (
                    int(config.get("people", 0))
                    * int(
                        config.get(
                            "capacity_per_person",
                            0,
                        )
                    )
                ),

                "planning_capacity": capacity,

                "backlog_story_count": len(
                    team_stories
                ),

                "backlog_points": backlog_points,

                "selected_story_count": len(
                    selected
                ),

                "selected_points": selected_points,

                "remaining_capacity": (
                    capacity - selected_points
                ),

                "selected_stories": [
                    story.model_dump()
                    for story in selected
                ],

                "decisions": [
                    decision.model_dump()
                    for decision in decisions
                ],
            }
        )

    return {
        "total_capacity": total_capacity,
        "total_backlog_points": total_backlog_points,
        "team_count": len(result),
        "teams": result,
    }
