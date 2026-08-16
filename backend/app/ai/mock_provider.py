from backend.app.models.sprint_context import SprintContext


class MockAIProvider:
    def analyze_sprint(
        self,
        sprint_context: SprintContext,
    ) -> dict:
        selected_stories = sprint_context.selected_stories
        planning_capacity = sprint_context.planning_capacity
        total_points = sprint_context.total_story_points
        risk_analysis = sprint_context.risk_analysis

        risks = []
        recommendations = []

        # Identify large stories.
        for story in selected_stories:
            if story["story_points"] >= 8:
                risks.append({
                    "story_id": story["id"],
                    "type": "LARGE_STORY",
                    "message": (
                        f"{story['id']} is an {story['story_points']}-point "
                        "story and may carry significant delivery risk."
                    ),
                })

        # Identify dependency chains.
        for story in selected_stories:
            if story["dependencies"]:
                risks.append({
                    "story_id": story["id"],
                    "type": "DEPENDENCY",
                    "message": (
                        f"{story['id']} depends on "
                        f"{', '.join(story['dependencies'])}."
                    ),
                })

        # Identify remaining capacity.
        remaining_capacity = (
            planning_capacity - total_points
        )

        if remaining_capacity <= 1:
            recommendations.append(
                "Sprint is close to full capacity. "
                "Avoid adding additional work."
            )
        else:
            recommendations.append(
                f"Sprint has {remaining_capacity} points "
                "of remaining capacity."
            )

        # Use sprint-level risk analysis.
        if risk_analysis["overall_level"] == "HIGH":
            recommendations.append(
                "Sprint risk is HIGH. Consider removing or splitting "
                "high-risk stories before committing."
            )

        elif risk_analysis["overall_level"] == "MEDIUM":
            recommendations.append(
                "Sprint risk is MEDIUM. Review high-risk stories "
                "and their dependencies before committing."
            )

        # Identify concentration by label.
        label_points = {}

        for story in selected_stories:
            for label in story["labels"]:
                label_points[label] = (
                    label_points.get(label, 0)
                    + story["story_points"]
                )

        for label, points in label_points.items():
            if points / total_points >= 0.5:
                risks.append({
                    "type": "WORK_CONCENTRATION",
                    "label": label,
                    "message": (
                        f"{points} of {total_points} points are "
                        f"related to '{label}' work."
                    ),
                })

        return {
            "summary": (
                f"Proposed sprint contains {total_points} story points "
                f"against a planning capacity of {planning_capacity}. "
                f"Overall sprint risk is "
                f"{risk_analysis['overall_level']}."
            ),
            "risks": risks,
            "recommendations": recommendations,
        }
