import os

from backend.app.ai.mock_provider import MockAIProvider
from backend.app.ai.qwen_provider import QwenAIProvider


def get_ai_provider():

    provider = os.getenv(
        "AI_PROVIDER",
        "mock",
    ).strip().lower()

    if provider == "qwen":
        return QwenAIProvider()

    if provider == "mock":
        return MockAIProvider()

    raise ValueError(
        f"Unsupported AI_PROVIDER: {provider}"
    )
