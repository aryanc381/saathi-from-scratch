"""Responsible for one row of the Renewal Radar worklist."""
from pydantic import BaseModel


# One customer on the worklist. score is the chance of renewing; top_factors are what moved it most.
class RadarRow(BaseModel):
    customer_id: str
    name: str
    days_to_renewal: int
    score: float
    top_factors: list[str]
    status: str
