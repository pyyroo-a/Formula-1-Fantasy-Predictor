"""
Request bodies the endpoints accept. Kept in one place so every file uses the same ones.
"""
from pydantic import BaseModel, Field

from src.planner import MAX_FREE_TRANSFERS


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

class TransferLadderRequest(BaseModel):
    """Your team for the planner. Exactly 5 drivers and 2 constructors, 1 to 3 free transfers."""
    race_name: str
    drivers: list[str] = Field(min_length=5, max_length=5)
    constructors: list[str] = Field(min_length=2, max_length=2)
    budget: float = Field(gt=0)
    free_transfers: int = Field(ge=1, le=MAX_FREE_TRANSFERS)
