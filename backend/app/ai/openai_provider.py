import json
import os

from openai import OpenAI

from backend.app.models.ai_analysis import AIAnalysis
from backend.app.models.sprint_context import SprintContext


class OpenAIProvider:
    def __init__(self, model: str = "gpt-5-mini"):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not configured."
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze_sprint(
        self,
        sprint_context: SprintContext,
    ) -> dict:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an Agile sprint planning assistant. "
                        "Analyze the proposed sprint for delivery risks, "
                        "dependencies, workload concentration, and "
                        "capacity concerns. Return valid JSON with "
                        "summary, risks, and recommendations."
                    ),
                },
                {
                    "role": "user",
                    "content": sprint_context.model_dump_json(),
                },
            ],
        )

        data = json.loads(response.output_text)

        return AIAnalysis(**data).model_dump()
