"""Shared mission assumptions. These are user planning limits, never NASA safety limits."""

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class MissionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    displacement: Literal["foot", "rover"] = "foot"
    velocity: float = Field(default=1, ge=0.1, le=10)
    max_slope: float = Field(default=25, ge=0, le=60)
    max_descent_slope: float = Field(default=25, ge=0, le=60)
    thermal_min: float = Field(default=-40, ge=-150, le=100)
    thermal_max: float = Field(default=30, ge=-150, le=150)
    high_dust: float = Field(default=0.3, gt=0, le=10)
    high_wind: float = Field(default=15, gt=0, le=150)
    roughness_scale: float = Field(default=50, gt=0, le=1000)
    unknown_policy: Literal["topography_only", "penalize", "avoid"] = "topography_only"
    dust_scenario: Literal["none", "my36"] = "none"
    mars_year: Literal[36] = 36
    sol: int = Field(default=1, ge=1, le=669)
    climate_scenario: Literal["unavailable"] = "unavailable"
    ls: float | None = Field(default=None, ge=0, lt=360)
    local_time: float | None = Field(default=None, ge=0, lt=24)
    slope_weight: float = Field(default=2, ge=0, le=20)
    roughness_weight: float = Field(default=1, ge=0, le=20)
    environment_weight: float = Field(default=2, ge=0, le=20)
    unknown_weight: float = Field(default=1, ge=0, le=20)

    @model_validator(mode="after")
    def thermal_order(self):
        if self.thermal_min >= self.thermal_max:
            raise ValueError("Thermal minimum must be below maximum.")
        if self.ls is not None or self.local_time is not None:
            raise ValueError(
                "Ls/local time unavailable: no validated climate model installed. Select a historical sol for dust."
            )
        return self


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x: float
    z: float


class RegionRequest(BaseModel):
    mission: MissionConfig = Field(default_factory=MissionConfig)


class PlanRequest(RegionRequest):
    points: list[Position] = Field(min_length=2, max_length=200)
    strategy: Literal["shortest", "low_slope", "environmental", "balanced"] = "balanced"
    excluded_cells: list[tuple[int, int]] = Field(
        default_factory=list, max_length=20000
    )
    compare: bool = False
