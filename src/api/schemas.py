"""
Request bodies the endpoints accept. Kept in one place so every file uses the same ones.
"""
from pydantic import BaseModel


class RaceRequest(BaseModel):
    race_name: str


class UpcomingRaceRequest(BaseModel):
    year: int
    race_name: str
    session: str = "FP3"


class BudgetRequest(BaseModel):
    race_name: str
    budget: float = 100.0


class PracticeRequest(BaseModel):
    race_name: str
    session: str = ""  # empty = auto-pick the final practice session that exists


class ChipAdvisorRequest(BaseModel):
    race_name: str
    my_drivers: list[str]
    my_constructors: list[str]
