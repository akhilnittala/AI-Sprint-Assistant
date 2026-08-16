from backend.app.models.story import Story


def calculate_story_risk(story: Story) -> dict:
    score = 0
    reasons = []

    if story.story_points >= 8:
        score += 3
        reasons.append("Large story")

    elif story.story_points >= 5:
        score += 1
        reasons.append("Medium-sized story")

    if story.dependencies:
        score += 2
        reasons.append("Has dependencies")

    if story.priority == "HIGH":
        score += 1
        reasons.append("High priority")

    if len(story.labels) >= 3:
        score += 1
        reasons.append("Multiple work areas")

    if score >= 5:
        level = "HIGH"
    elif score >= 3:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "story_id": story.id,
        "score": score,
        "level": level,
        "reasons": reasons,
    }
