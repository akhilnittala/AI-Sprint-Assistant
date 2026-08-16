
import hashlib
import json
import os

import requests

from backend.app.models.story import Story
from backend.app.services.story_estimation_cache import (
    get_cached,
    save_cached,
)


FIBONACCI_POINTS = [1, 2, 3, 5, 8, 13]


class QwenStoryEstimator:

    def __init__(self):
        self.url = os.getenv(
            "OLLAMA_URL",
            "http://127.0.0.1:11434",
        ).rstrip("/")

        self.model = os.getenv(
            "OLLAMA_MODEL",
            "qwen3:8b",
        )

    @staticmethod
    def _content_hash(story):
        content = json.dumps(
            {
                "title": story.title,
                "description": story.description,
                "priority": story.priority,
                "labels": story.labels,
                "team": story.team,
            },
            sort_keys=True,
        )

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    def estimate(self, story: Story):

        content_hash = self._content_hash(story)

        # =====================================================
        # CACHE LOOKUP
        # =====================================================

        cached = get_cached(
            story.id,
            content_hash,
        )

        if cached:

            return {
                "estimated_points": cached["estimated_points"],
                "confidence": cached["confidence"],
                "reason": cached["reason"],
                "cached": True,
            }

        # =====================================================
        # QWEN ESTIMATION
        # =====================================================

        prompt = f"""
You are an expert Agile software engineering manager.

Estimate the Jira story points for this engineering story.

JIRA ISSUE:
{story.id}

TITLE:
{story.title}

DESCRIPTION:
{story.description}

PRIORITY:
{story.priority}

LABELS:
{json.dumps(story.labels)}

TEAM:
{story.team}

Use ONLY these Fibonacci values:

1, 2, 3, 5, 8, 13

Consider:

- implementation complexity
- testing effort
- integration effort
- uncertainty
- number of components involved
- operational/deployment impact
- security/infrastructure complexity
- ambiguity

Return ONLY valid JSON:

{{
  "estimated_points": 1,
  "confidence": 80,
  "reason": "short explanation"
}}

Rules:

- estimated_points MUST be 1, 2, 3, 5, 8, or 13
- confidence MUST be between 0 and 100
- reason must be concise
"""

        response = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Agile story point "
                            "estimation assistant. Return only JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        text = data["message"]["content"].strip()

        if text.startswith("```"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "")
            text = text.strip()

        result = json.loads(text)

        points = int(
            result.get(
                "estimated_points",
                3,
            )
        )

        if points not in FIBONACCI_POINTS:
            points = min(
                FIBONACCI_POINTS,
                key=lambda x: abs(x - points),
            )

        confidence = int(
            result.get(
                "confidence",
                50,
            )
        )

        confidence = max(
            0,
            min(100, confidence),
        )

        reason = str(
            result.get(
                "reason",
                "Estimated by Qwen based on Jira story complexity.",
            )
        )

        # =====================================================
        # SAVE CACHE
        # =====================================================

        save_cached(
            story.id,
            content_hash,
            points,
            confidence,
            reason,
        )

        return {
            "estimated_points": points,
            "confidence": confidence,
            "reason": reason,
            "cached": False,
        }


def estimate_missing_story_points(stories):

    estimator = QwenStoryEstimator()

    estimated_count = 0
    cached_count = 0

    for story in stories:

        # =====================================================
        # Jira estimate exists
        # =====================================================

        if story.jira_story_points is not None:

            story.story_points = (
                story.jira_story_points
            )

            story.story_points_source = "JIRA"

            continue

        # =====================================================
        # Missing Jira estimate
        # =====================================================

        result = estimator.estimate(story)

        story.ai_estimated_points = (
            result["estimated_points"]
        )

        story.ai_estimation_confidence = (
            result["confidence"]
        )

        story.ai_estimation_reason = (
            result["reason"]
        )

        story.story_points = (
            result["estimated_points"]
        )

        story.story_points_source = "AI_ESTIMATED"

        estimated_count += 1

        if result.get("cached"):
            cached_count += 1

    return stories, estimated_count, cached_count
