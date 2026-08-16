from backend.app.models.story import Story
from backend.app.planner.risk import calculate_story_risk


def analyze_sprint_risk(stories: list[Story]) -> dict:
    story_risks = [
        calculate_story_risk(story)
        for story in stories
    ]

    high_risk_count = sum(
        1 for risk in story_risks
        if risk["level"] == "HIGH"
    )

    medium_risk_count = sum(
        1 for risk in story_risks
        if risk["level"] == "MEDIUM"
    )

    if high_risk_count >= 2:
        overall_level = "HIGH"
    elif high_risk_count == 1 or medium_risk_count >= 2:
        overall_level = "MEDIUM"
    else:
        overall_level = "LOW"

    return {
        "overall_level": overall_level,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "story_risks": story_risks,
    }
