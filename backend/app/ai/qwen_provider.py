import json
import os
import requests

from backend.app.models.sprint_context import SprintContext


class QwenAIProvider:

    def __init__(self):
        self.url = os.getenv(
            "OLLAMA_URL",
            "http://127.0.0.1:11434",
        ).rstrip("/")

        self.model = os.getenv(
            "OLLAMA_MODEL",
            "qwen3:8b",
        )

    def analyze_sprint(
        self,
        sprint_context: SprintContext,
    ) -> dict:

        prompt = f"""
You are an expert Agile Engineering Manager.

Analyze the proposed sprint below.

TEAM:
{sprint_context.team}

PLANNING CAPACITY:
{sprint_context.planning_capacity}

TOTAL STORY POINTS:
{sprint_context.total_story_points}

REMAINING CAPACITY:
{sprint_context.remaining_capacity}

SELECTED STORIES:
{json.dumps(sprint_context.selected_stories, indent=2)}

PLANNING DECISIONS:
{json.dumps(sprint_context.decisions, indent=2)}

Analyze:
1. Large or risky stories
2. Dependency risks
3. Vague requirements
4. Work concentration
5. Delivery risks
6. Practical sprint recommendations

Rules:
- Do not change capacity.
- Do not select or remove stories.
- Do not invent story points.
- Analyze only supplied data.

Return ONLY valid JSON:

{{
  "summary": "short sprint summary",
  "risks": [
    {{
      "story_id": "GITOPS-123",
      "type": "RISK_TYPE",
      "message": "explanation"
    }}
  ],
  "recommendations": [
    "recommendation"
  ]
}}
"""

        response = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a senior Agile engineering "
                            "planning assistant. Return only valid JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        text = response.json()["message"]["content"].strip()

        if text.startswith("```"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "")
            text = text.strip()

        return json.loads(text)
