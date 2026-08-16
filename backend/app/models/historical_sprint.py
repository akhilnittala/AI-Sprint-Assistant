from pydantic import BaseModel, Field


class HistoricalSprint(BaseModel):
    id: str
    name: str
    committed_points: int = Field(ge=0)
    completed_points: int = Field(ge=0)
