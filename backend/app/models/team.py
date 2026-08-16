from pydantic import BaseModel, Field


class Team(BaseModel):
    id: str
    name: str

    developers: int = Field(default=0, ge=0)
    qa_engineers: int = Field(default=0, ge=0)

    people: int = Field(default=1, ge=1)
    capacity_per_person: int = Field(default=8, ge=1)
    velocity: float = Field(default=0, ge=0)

    sprint_duration_days: int = Field(default=21, ge=1)

    @property
    def calculated_people(self) -> int:
        return self.people

    @property
    def capacity_points(self) -> int:
        """
        Maximum capacity based on available people.
        """
        return self.people * self.capacity_per_person

    @property
    def planning_capacity(self) -> int:
        """
        Effective sprint planning capacity.

        Never schedule more work than the team's available
        staffing capacity or historical velocity.
        """
        if self.velocity > 0:
            return min(
                self.capacity_points,
                int(self.velocity),
            )

        return self.capacity_points
