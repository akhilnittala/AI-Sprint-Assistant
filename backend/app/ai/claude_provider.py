import json
import os

from anthropic import Anthropic

from backend.app.models.sprint_context import SprintContext


class ClaudeAIProvider:

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not configured"
            )

        self.client = Anthropic(
            api_key=api_key,
            timeout=60.0,
        )

        self.model = os.getenv(
            "ANTHROPIC_MODEL",
            "claude-sonnet-4-6",
        )

    def analyze_sprint(
        self,
        sprint_context: SprintContext,
    ) -> dict:

        prompt = f"""
You are a senior Agile Engineering Manager.

Analyze this proposed sprint.

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
3. Vague or incomplete requirements
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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=(
                "You are a senior Agile engineering planning "
                "assistant. Return only valid JSON."
            ),
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        text = ""

        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text

        text = text.strip()

        if text.startswith("```"):
            text = text.replace("```json", "", 1)
            text = text.replace("```", "")
            text = text.strip()

        return json.loads(text)
