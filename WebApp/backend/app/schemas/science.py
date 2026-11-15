from typing import Literal
from pydantic import BaseModel, Field


class ScienceDatum(BaseModel):
    name: str
    value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str | None = None
    source: str | None = None
    product: str | None = None
    spatial_resolution: dict | None = None
    temporal_resolution: str | None = None
    date_or_scenario: dict | str | None = None
    method: str | None = None
    uncertainty: dict | None = None
    availability: Literal["Available", "Unavailable", "Error"] = "Unavailable"
    classification: Literal[
        "Observed", "Derived", "Modeled", "Estimated", "Unavailable"
    ] = "Unavailable"
    reason: str | None = None
    sample: dict | None = None
