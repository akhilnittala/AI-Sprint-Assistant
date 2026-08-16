import math


def calculate_planning_capacity(
    average_velocity: float,
    capacity_factor: float = 0.85,
) -> int:
    if average_velocity < 0:
        raise ValueError("average_velocity cannot be negative")

    if not 0 < capacity_factor <= 1:
        raise ValueError("capacity_factor must be between 0 and 1")

    return math.floor(average_velocity * capacity_factor)
