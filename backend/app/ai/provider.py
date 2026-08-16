from typing import Protocol

from backend.app.models.sprint_context import SprintContext


class AIProvider(Protocol):
    def analyze_sprint(
        self,
        sprint_context: SprintContext,
    ) -> dict:
        ...
