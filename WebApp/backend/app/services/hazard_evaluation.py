"""One source for mission hazards; never use visual heights as environmental data."""

import math
from functools import lru_cache
import numpy as np
from scipy.ndimage import label, find_objects
from app.schemas.planning import MissionConfig
from app.services.terrain_geospatial import (
    model_to_grid,
    grid_to_model,
    topographic_metrics,
    model_to_geographic,
    geographic_to_model,
    intercell_slope,
)

RISK_CATEGORIES = {
    "steep_slope": "Steep slope",
    "extreme_heat": "Extreme heat",
    "extreme_cold": "Extreme cold",
    "atmospheric_dust": "Atmospheric dust",
    "strong_winds": "Strong winds",
    "mobility_risk": "Mobility risk",
    "radiation_exposure": "Radiation exposure",
    "unknown_conditions": "Unknown conditions",
}
ENVIRONMENTAL_VARIABLES = (
    "surface_temperature",
    "atmospheric_temperature",
    "wind_speed",
    "dust_optical_depth",
    "solar_flux",
    "ionizing_radiation",
)


def finite(value):
    try:
        return (
            float(value) if value is not None and math.isfinite(float(value)) else None
        )
    except (ValueError, TypeError):
        return None


def environment_snapshot(service, mission):
    """Current registered environmental coverage is ONE native dust cell for the whole model."""
    valid = np.argwhere(service.arrays["valid_mask"] == 1)
    if not len(valid):
        return {}
    row, col = map(int, valid[len(valid) // 2])
    x, z = grid_to_model(row, col, service.metadata)
    return service.point(
        x,
        z,
        36 if mission.dust_scenario == "my36" else None,
        mission.sol if mission.dust_scenario == "my36" else None,
    )["variables"]


def evaluate_variables(variables, mission):
    mission = (
        MissionConfig.model_validate(mission) if isinstance(mission, dict) else mission
    )
    warnings = []

    def value(name):
        return finite(variables.get(name, {}).get("value"))

    def add(category, key, limit, condition, unit=None):
        v = value(key)
        if v is None or not condition(v, limit):
            return
        data = variables[key]
        warnings.append(
            {
                "category": category,
                "label": RISK_CATEGORIES[category],
                "severity": "high"
                if category in ("extreme_heat", "extreme_cold")
                or abs(v) > abs(limit) * 1.25
                else "medium",
                "value": v,
                "unit": unit or data.get("unit"),
                "threshold": limit,
                "cause": f"{data.get('name', key)} {v:.3g} {unit or data.get('unit', '')} crosses mission limit {limit}.",
                "source": data.get("source"),
                "product": data.get("product"),
                "classification": data.get("classification"),
                "spatial_resolution": data.get("spatial_resolution"),
                "temporal_reference": data.get("date_or_scenario"),
                "limitations": "User mission assumption; not an official safety limit.",
            }
        )

    add("steep_slope", "slope", mission.max_slope, lambda a, b: a > b)
    # All science service temperatures are Kelvin. Convert explicitly for Celsius mission limits.
    converted = dict(variables)
    for key in ("surface_temperature", "atmospheric_temperature"):
        data = variables.get(key, {})
        if finite(data.get("value")) is not None and data.get("unit") == "K":
            converted[key] = {**data, "value": data["value"] - 273.15, "unit": "°C"}
    original = variables
    variables = converted
    add("extreme_heat", "surface_temperature", mission.thermal_max, lambda a, b: a > b)
    add("extreme_cold", "surface_temperature", mission.thermal_min, lambda a, b: a < b)
    add("strong_winds", "wind_speed", mission.high_wind, lambda a, b: a > b)
    add("atmospheric_dust", "dust_optical_depth", mission.high_dust, lambda a, b: a > b)
    variables = original
    unknown = [key for key in ENVIRONMENTAL_VARIABLES if value(key) is None]
    if unknown:
        warnings.append(
            {
                "category": "unknown_conditions",
                "label": "Unknown conditions",
                "severity": "unknown",
                "cause": "Unavailable: "
                + ", ".join(unknown)
                + ". Unknown mobility conditions: rock abundance and geology are not registered; TES inertia alone cannot establish mobility.",
                "variables": unknown,
                "classification": "Unavailable",
                "limitations": "Unknown is not safe; no ionizing-radiation alert inferred from shade or RAD at Gale.",
            }
        )
    return warnings


def point_assessment(service, x, z, mission):
    data = service.point(
        x,
        z,
        36 if mission.dust_scenario == "my36" else None,
        mission.sol if mission.dust_scenario == "my36" else None,
    )
    data["warnings"] = (
        evaluate_variables(data["variables"], mission)
        if data["coverage"] == "Available"
        else []
    )
    data["mission_config"] = mission.model_dump()
    data["mobility_difficulty"] = {
        "value": None,
        "classification": "Unavailable",
        "reason": "Unknown mobility conditions; missing validated rock abundance/geology and a calibrated mobility model.",
    }
    return data


def region_assessment(service, mission):
    if service.metadata is None:
        return {"coverage": "Unavailable", "regions": [], "reason": service.error}
    return _region_cached(service, mission.model_dump_json())


@lru_cache(maxsize=12)
def _region_cached(service, mission_json):
    mission = MissionConfig.model_validate_json(mission_json)
    meta = service.metadata
    valid = service.arrays["valid_mask"] == 1
    slope = service.arrays["slope"]
    regions = []
    labels, count = label(valid & np.isfinite(slope) & (slope > mission.max_slope))
    for index, slices in enumerate(find_objects(labels), start=1):
        if slices is None:
            continue
        rr, cc = np.where(labels[slices] == index)
        rr += slices[0].start
        cc += slices[1].start
        values = slope[rr, cc]
        pick = int(np.argmax(values))
        row, col = int(rr[pick]), int(cc[pick])
        x, z = grid_to_model(row, col, meta)
        # Actual region boundary cell centers, not its bounding rectangle. Sampling is explicit.
        member = set(zip(rr.tolist(), cc.tolist()))
        boundary = [
            (r, c)
            for r, c in member
            if any(
                (r + dr, c + dc) not in member
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            )
        ]
        regions.append(
            {
                "id": f"slope-{index}",
                "category": "steep_slope",
                "label": "Steep slope",
                "icon": "△",
                "severity": "high"
                if float(values.max()) > mission.max_slope * 1.25
                else "medium",
                "x": x,
                "z": z,
                "y": float(service.arrays["visual_elevation"][row, col]),
                "cell_count": len(rr),
                "max_value": float(values.max()),
                "unit": "degree",
                "threshold": mission.max_slope,
                "cause": "Scientific 3×3 gradient exceeds configured slope limit. Region is connected with four neighbors.",
                "source": "HRSC/MOLA processed scientific elevation",
                "classification": "Derived",
                "bounds": [int(rr.min()), int(cc.min()), int(rr.max()), int(cc.max())],
                "boundary": [
                    {
                        "x": grid_to_model(int(r), int(c), meta)[0],
                        "z": grid_to_model(int(r), int(c), meta)[1],
                        "y": float(service.arrays["visual_elevation"][r, c]),
                    }
                    for r, c in boundary[:: max(1, math.ceil(len(boundary) / 256))]
                ],
                "boundary_total_cells": len(boundary),
                "resolution_m": 250,
            }
        )
    environment = environment_snapshot(service, mission)
    environment_warnings = evaluate_variables(environment, mission)
    row, col = map(int, np.argwhere(valid)[len(np.argwhere(valid)) // 2])
    x, z = grid_to_model(row, col, meta)
    for warning in environment_warnings:
        if warning["category"] == "steep_slope":
            continue
        regions.append(
            {
                **warning,
                "id": warning["category"] + "-regional",
                "icon": "?" if warning["category"] == "unknown_conditions" else "≋",
                "x": x,
                "y": float(service.arrays["visual_elevation"][row, col]),
                "z": z,
                "cell_count": int(valid.sum()),
                "scope": "entire terrain / shared native environmental cell",
                "bounds": [0, 0, meta["rows"] - 1, meta["columns"] - 1],
            }
        )
    regions.sort(key=lambda item: item.get("cell_count", 0), reverse=True)
    return {
        "coverage": "Available",
        "regions": regions,
        "total_regions": len(regions),
        "category_availability": {
            "steep_slope": "Available",
            "unknown_conditions": "Available",
            "atmospheric_dust": "Available"
            if finite(environment.get("dust_optical_depth", {}).get("value"))
            is not None
            else "Unavailable",
            "extreme_heat": "Unavailable",
            "extreme_cold": "Unavailable",
            "strong_winds": "Unavailable",
            "mobility_risk": "Unavailable",
            "radiation_exposure": "Unavailable",
        },
        "mission_config": mission.model_dump(),
        "unknown_variables": [
            k
            for k in ENVIRONMENTAL_VARIABLES
            if finite(environment.get(k, {}).get("value")) is None
        ],
        "notice": "Mission thresholds are hypotheses; environmental warnings use native resolution and historical scenario only.",
    }
