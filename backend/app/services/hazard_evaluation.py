"""Common hazard evaluation engine for generating warnings and assessing conditions.

This reusable engine evaluates terrain and environmental conditions to generate
hazard indicators that can feed the route planner and scientific inspection system.
Thresholds depend on configured mission conditions, not arbitrary NASA limits.
"""

import math
from pathlib import Path
from functools import lru_cache
import os, json, hashlib, math
import numpy as np
from pyproj import CRS, Transformer, Geod

# Mars constants
RADIUS = 3396190.0
GEOGRAPHIC = CRS.from_proj4(f"+proj=longlat +R={RADIUS} +no_defs")
PROJECTED = CRS.from_proj4(f"+proj=aeqd +lat_0=17.5 +lon_0=77 +R={RADIUS} +units=m +no_defs")
TO_GEO = Transformer.from_crs(PROJECTED, GEOGRAPHIC, always_xy=True)
TO_MODEL = Transformer.from_crs(GEOGRAPHIC, PROJECTED, always_xy=True)
GEOD = Geod(a=RADIUS, b=RADIUS)

# Evaluation thresholds (configurable per mission conditions)
SLOPE_THRESHOLDS = {
    "steep": 25,  # degrees - above this is "steep slope" indicator
    "extreme_heat": 35,  # °C - extreme heat threshold
    "extreme_cold": -80,  # °C - extreme cold threshold
    "high_wind": 15,  # m/s - strong wind threshold
    "high_dust": 0.3,  # Pa/Pa - atmospheric dust threshold (CDOD normalized)
    "mobility_lower": 0.3,  # estimated mobility index lower bound
    "mobility_moderate": 0.6,  # estimated mobility index moderate bound
    "mobility_high": 0.8,  # estimated mobility index high bound
}

# Risk categories matching the stage 5 spec
RISK_CATEGORIES = {
    "steep_slope": "Steep slope",
    "extreme_heat": "Extreme heat",
    "extreme_cold": "Extreme cold",
    "atmospheric_dust": "Atmospheric dust",
    "strong_winds": "Strong winds",
    "mobility_risk": "Mobility risk",
    "radiation_exposure": "Radiation exposure",
    "unknown_conditions": "Unknown conditions"
}


def verify(path, expected):
    """Verify file integrity via SHA-256."""
    with path.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"Integrity mismatch: {path.name}")


def finite(value):
    """Safely convert to finite float."""
    return float(value) if value is not None and math.isfinite(float(value)) else None


def model_to_grid(x, z, metadata):
    """Convert local X/Z coordinates to grid row/column."""
    if not math.isfinite(x) or not math.isfinite(z):
        return None
    row = math.floor((z - metadata["originZ"]) / metadata["cellSize"])
    column = math.floor((x - metadata["originX"]) / metadata["cellSize"])
    return (
        (row, column)
        if 0 <= row < metadata["rows"] and 0 <= column < metadata["columns"]
        else None
    )


def grid_to_model(row, column, metadata):
    """Convert grid row/column to local X/Z coordinates."""
    if (
        not isinstance(row, int)
        or not isinstance(column, int)
        or not 0 <= row < metadata["rows"]
        or not 0 <= column < metadata["columns"]
    ):
        return None
    return metadata["originX"] + (column + 0.5) * metadata["cellSize"], metadata[
        "originZ"
    ] + (row + 0.5) * metadata["cellSize"]


def model_to_geographic(x, y, z):
    """Convert local ENU coordinates to geographic (lon, lat, elev)."""
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ValueError("Coordinates must be finite.")
    longitude, latitude = TO_GEO.transform(x, -z)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "elevation": y / 3 - 4500,
        "elevation_meaning": "inverse visual transform; quantized elevation",
    }


def geographic_to_model(latitude, longitude, elevation):
    """Convert geographic coordinates to local ENU x/y/z."""
    if (
        not all(math.isfinite(v) for v in (latitude, longitude, elevation))
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise ValueError(
            "Expected planetocentric latitude [-90,90], east longitude [-180,180], finite elevation."
        )
    x, north = TO_MODEL.transform(longitude, latitude)
    if not math.isfinite(x) or not math.isfinite(north):
        raise ValueError("Position cannot be projected.")
    return {"x": x, "y": 3 * (elevation + 4500), "z": -north}


def intercell_slope(a, b):
    """Slope between two geodetic points.
    
    a,b = (longitude, latitude, scientific elevation metres).
    """
    distance = GEOD.inv(a[0], a[1], b[0], b[1])[2]
    if distance <= 0:
        return None
    return math.degrees(math.atan2(abs(b[2] - a[2]), distance))


def calculate_topographic_metrics(height, longitude, latitude):
    """Calculate slope, aspect, roughness, and local relief using 3x3 neighborhood.
    
    Uses geodetic offsets on Mars sphere. Requires all nine samples valid.
    Roughness is RMS residual, not mechanical stability.
    """
    rows, cols = height.shape
    values = np.pad(height, 1, constant_values=np.nan)
    lon = np.pad(longitude, 1, constant_values=np.nan)
    lat = np.pad(latitude, 1, constant_values=np.nan)
    xx = np.zeros_like(height, dtype="f8")
    xy = xx.copy()
    yy = xx.copy()
    bx = xx.copy()
    by = xx.copy()
    good = np.isfinite(height)
    neighbors = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == dc == 0:
                continue
            neighbor = values[1 + dr : 1 + dr + rows, 1 + dc : 1 + dc + cols]
            az, _, distance = GEOD.inv(
                longitude,
                latitude,
                lon[1 + dr : 1 + dr + rows, 1 + dc : 1 + dc + cols],
                lat[1 + dr : 1 + dr + rows, 1 + dc : 1 + dc + cols],
            )
            east = distance * math.sin(math.radians(az))
            north = distance * math.cos(math.radians(az))
            delta = neighbor - height
            xx += east * east
            xy += east * north
            yy += north * north
            bx += east * delta
            by += north * delta
            good &= np.isfinite(neighbor)
            neighbors.append((east, north, delta, neighbor))
    det = xx * yy - xy * xy
    with np.errstate(invalid="ignore", divide="ignore"):
        ge = (bx * yy - by * xy) / det
        gn = (by * xx - bx * xy) / det
        slope = np.degrees(np.arctan(np.hypot(ge, gn)))
        aspect = np.degrees(np.arctan2(-ge, -gn)) % 360
        aspect[np.hypot(ge, gn) < 1e-10] = np.nan
        roughness = np.sqrt(
            sum((dh - ge * e - gn * n) ** 2 for e, n, dh, _ in neighbors) / 9
        )
    stack = np.stack([height] + [n[3] for n in neighbors])
    relief = np.max(stack, axis=0) - np.min(stack, axis=0)
    result = {
        "slope": slope,
        "aspect": aspect,
        "roughness": roughness,
        "local_relief": relief,
    }
    for name, array in result.items():
        array[~good] = np.nan
        result[name] = array.astype("<f4")
    return result


def classify_mobility_difficulty(estimated_index):
    """Classify estimated mobility difficulty index into categories.
    
    Index is estimated from slope, roughness, rock abundance, thermal inertia,
    surface dust, and geology. Higher values = more difficulty.
    
    Categories:
    - Lower estimated mobility difficulty: index < 0.3
    - Moderate mobility difficulty: 0.3 <= index < 0.6
    - High mobility difficulty: 0.6 <= index < 0.8
    - Possible loose terrain: index >= 0.8
    - Unknown mobility conditions: insufficient data
    """
    if estimated_index is None:
        return "Unknown mobility conditions"
    elif estimated_index < SLOPE_THRESHOLDS["mobility_lower"]:
        return "Lower estimated mobility difficulty"
    elif estimated_index < SLOPE_THRESHOLDS["mobility_moderate"]:
        return "Moderate mobility difficulty"
    elif estimated_index < SLOPE_THRESHOLDS["mobility_high"]:
        return "High mobility difficulty"
    else:
        return "Possible loose terrain"


def evaluate_hazard_indicators(
    slope_degrees,
    slope_value,  # normalized 0-1
    roughness_value,  # m RMS
    temperature_surface,  # °C
    temperature_atmospheric,  # °C
    dust_optical_depth,  # Pa/Pa normalized
    wind_speed,  # m/s
    mobility_index,  # estimated 0-1
    mission_config=None,
):
    """Evaluate hazard indicators and return list of active warnings.
    
    mission_config optional dict with:
    - thermal_min: minimum safe temperature (°C)
    - thermal_max: maximum safe temperature (°C)
    - max_slope: maximum allowed slope (degrees)
    - mission_type: "scientific"|"exploration"|"survey"
    - displacement: "foot"|"rover"
    - velocity: "low"|"medium"|"high"
    """
    if mission_config is None:
        mission_config = {}
    
    thermal_min = mission_config.get("thermal_min", -40)
    thermal_max = mission_config.get("thermal_max", 30)
    max_slope = mission_config.get("max_slope", 25)
    mission_type = mission_config.get("mission_type", "exploration")
    displacement = mission_config.get("displacement", "foot")
    velocity = mission_config.get("velocity", "medium")
    
    warnings = []
    
    # Steep slope indicator
    if slope_degrees is not None and slope_degrees > SLOPE_THRESHOLDS["steep"]:
        warnings.append({
            "category": RISK_CATEGORIES["steep_slope"],
            "cause": f"Slope of {slope_degrees:.1f}° exceeds {SLOPE_THRESHOLDS['steep']}° threshold",
            "severity": "high" if slope_degrees > 35 else "medium",
            "scientific_value": round(slope_degrees, 1),
            "configured_threshold": SLOPE_THRESHOLDS["steep"],
            "source": "HRSC/MOLA blended DEM",
            "resolution": "250 m processed grid",
            "temporal_scenario": "Static source composite",
            "extension_approx": "Cell-level or connected region",
            "limitations": "3x3 neighborhood gradient; aspect undefined on flat terrain; does not guarantee mechanical stability",
            "possible_mission_effects": [
                "Vehicle rollover risk",
                "Slippage on inclined surfaces",
                "EVA traversal difficulty",
            ],
        })
    
    # Extreme heat
    if temperature_surface is not None and temperature_surface > SLOPE_THRESHOLDS["extreme_heat"]:
        warnings.append({
            "category": RISK_CATEGORIES["extreme_heat"],
            "cause": f"Surface temperature of {temperature_surface:.1f}°C exceeds {SLOPE_THRESHOLDS['extreme_heat']}°C threshold",
            "severity": "high",
            "scientific_value": round(temperature_surface, 1),
            "configured_threshold": SLOPE_THRESHOLDS["extreme_heat"],
            "source": "HRSC/MOLA blended DEM composite",
            "resolution": "250 m processed grid",
            "temporal_scenario": "Static source composite",
            "extension_approx": "Per-cell or regional",
            "limitations": "Do not invent thermal differences between voxels when resolution < terrain detail",
            "possible_mission_effects": [
                "Thermal overload of instruments",
                "EGE risk for astronauts",
                "Reduced operational time",
            ],
        })
    
    # Extreme cold
    if temperature_surface is not None and temperature_slope < SLOPE_THRESHOLDS["extreme_cold"]:
        warnings.append({
            "category": RISK_CATEGORIES["extreme_cold"],
            "cause": f"Surface temperature of {temperature_surface:.1f}°C below {SLOPE_THRESHOLDS['extreme_cold']}°C threshold",
            "severity": "high",
            "scientific_value": round(temperature_surface, 1),
            "configured_threshold": SLOPE_THRESHOLDS["extreme_cold"],
            "source": "HRSC/MOLA blended DEM composite",
            "resolution": "250 m processed grid",
            "temporal_scenario": "Static source composite",
            "extension_approx": "Per-cell or regional",
            "limitations": "Do not invent thermal differences between voxels when resolution < terrain detail",
            "possible_mission_effects": [
                "Hypothermia risk",
                "Instrument operation limits",
                "Power system constraints",
            ],
        })
    
    # Strong winds
    if wind_speed is not None and wind_speed > SLOPE_THRESHOLDS["high_wind"]:
        warnings.append({
            "category": RISK_CATEGORIES["strong_winds"],
            "cause": f"Wind speed of {wind_speed:.1f} m/s exceeds {SLOPE_THRESHOLDS['high_wind']} m/s threshold",
            "severity": "medium" if wind_speed < 25 else "high",
            "scientific_value": round(wind_speed, 1),
            "configured_threshold": SLOPE_THRESHOLDS["high_wind"],
            "source": "Not available in current dust cache; see MCD limitations",
            "resolution": "Regional (6°×5° grid)",
            "temporal_scenario": "Static climatology, not current weather",
            "extension_approx": "Regional, not local instantaneous",
            "limitations": "Climatological average, not real-time wind data; MCD does not provide local instantaneous winds",
            "possible_mission_effects": [
                "Aerosol suspension",
                "Solar panel dust accumulation",
                "EVA visibility reduction",
            ],
        })
    
    # Atmospheric dust
    if dust_optical_depth is not None and dust_optical_depth > SLOPE_THRESHOLDS["high_dust"]:
        warnings.append({
            "category": RISK_CATEGORIES["atmospheric_dust"],
            "cause": f"Atmospheric dust (CDOD) of {dust_optical_depth:.3f} Pa/Pa exceeds {SLOPE_THRESHOLDS['high_dust']} threshold",
            "severity": "high" if dust_optical_depth > 0.6 else "medium",
            "scientific_value": round(dust_optical_depth, 3),
            "configured_threshold": SLOPE_THRESHOLDS["high_dust"],
            "source": "MRO/MCS MY36 v2.5 climatology",
            "resolution": "6°×5° regional grid",
            "temporal_scenario": "Mars Year 36, diurnal mean",
            "extension_approx": "Regional cell, not local storm",
            "limitations": "Does not represent visible extinction, surface dust, or local instantaneous opacity; no storm forecast",
            "possible_mission_effects": [
                "Reduced solar panel efficiency",
                "Instrument contamination",
                "Visibility reduction for EVA",
            ],
        })
    
    # Mobility risk
    mobility_category = classify_mobility_difficulty(mobility_index)
    if mobility_index is not None:
        warnings.append({
            "category": RISK_CATEGORIES["mobility_risk"],
            "cause": f"Estimated mobility difficulty: {mobility_category.lower().replace(' ', ' ')} (index: {mobility_index:.3f})",
            "severity": mobility_category.split()[0].lower(),
            "scientific_value": round(mobility_index, 3),
            "configured_threshold": SLOPE_THRESHOLDS["mobility_high"],
            "source": "Estimated from slope, roughness, rock abundance, thermal inertia, surface dust, geology",
            "resolution": "250 m processed grid",
            "temporal_scenario": "Static source composite",
            "extension_approx": "Per-cell or connected region",
            "limitations": "Estimated index NOT a measurement of bearing capacity or stability guarantee; see scientific limitations",
            "possible_mission_effects": [
                "Traversability reduction",
                "Slippage risk",
                "Getting stuck in loose terrain",
            ],
        })
    
    # Radiation exposure (solar)
    # Note: ionizing radiation not available as global map; solar exposure calculated topographically
    if slope_value is not None:
        # Slopes facing the sun receive more solar exposure
        # This is a simplified topographic model - real calculations need sun ephemeris
        if mission_type == "scientific" and displacement == "foot":
            # Scientific missions may tolerate reduced solar exposure for thermal objectives
            warnings.append({
                "category": "solar_exposure_note",
                "cause": "Solar exposure varies with slope orientation; reduced exposure may favor thermal objectives but perjudice energy availability",
                "severity": "medium",
                "scientific_value": "topographic variation",
                "configured_threshold": None,
                "source": "Topographic illumination model",
                "resolution": "250 m processed grid",
                "temporal_scenario": "Depends on Ls and local hour",
                "extension_approx": "Per-cell",
                "limitations": "Do not assume shadow protects from all ionizing radiation; separate solar vs ionizing",
                "possible_mission_effects": [
                    "Power system constraints",
                    "Thermal objective favorability",
                ],
            })
    
    # Unknown conditions - when data is missing
    missing_data = []
    if slope_degrees is None:
        missing_data.append("slope")
    if temperature_surface is None:
        missing_data.append("surface temperature")
    if dust_optical_depth is None:
        missing_data.append("atmospheric dust")
    
    if missing_data:
        warnings.append({
            "category": RISK_CATEGORIES["unknown_conditions"],
            "cause": f"Insufficient data for: {', '.join(missing_data)}",
            "severity": "medium",
            "scientific_value": None,
            "configured_threshold": None,
            "source": "Various scientific datasets",
            "resolution": "Variable; see individual variable resolutions",
            "temporal_scenario": "See individual variable temporal references",
            "extension_approx": "N/A - data gaps",
            "limitations": "Show only available variables when data is missing; do not present unknown as zero",
            "possible_mission_effects": [
                "Cannot assess risk without complete data",
            ],
        })
    
    # Sort by severity: high first, then medium, then low
    severity_order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    warnings.sort(key=lambda w: severity_order.get(w.get("severity", "medium"), 1))
    
    return warnings


def evaluate_region_indicators(
    grid_row, grid_column, metadata, science_service, mission_config=None
):
    """Evaluate hazard indicators for a region around a grid cell.
    
    Uses connected-component clustering to group contiguous dangerous cells.
    Returns individual indicators and clustered region summary.
    """
    if mission_config is None:
        mission_config = {}
    
    # Get topographic metrics for 3x3 neighborhood
    height = science_service.arrays.get("scientific_elevation")
    slope_data = science_service.arrays.get("slope")
    roughness_data = science_service.arrays.get("roughness")
    
    if height is None or slope_data is None or roughness_data is None:
        return {
            "individual": [],
            "clusters": [],
            "note": "Topographic data unavailable for region evaluation",
        }
    
    row, column = grid_row, grid_column
    
    # Extract 5x5 neighborhood (center + 2 cells outward)
    neighborhood_rows = slice(max(0, row - 2), min(metadata["rows"], row + 3))
    neighborhood_cols = slice(max(0, column - 2), min(metadata["columns"], column + 3))
    
    local_height = height[neighborhood_rows, neighborhood_cols]
    local_slope = slope_data[neighborhood_rows, neighborhood_cols]
    local_roughness = roughness_data[neighborhood_rows, neighborhood_cols]
    
    # Check coverage - all cells must be valid
    valid_mask = local_height > -1e30  # NaN check; actual valid depends on mask
    
    # Build per-cell indicators
    individual_indicators = []
    dangerous_cells = []  # (row, col) pairs with hazards
    
    for r_local in range(local_height.shape[0]):
        for c_local in range(local_height.shape[1]):
            abs_row = neighborhood_rows.start + r_local
            abs_col = neighborhood_cols.start + c_local
            
            if not valid_mask[r_local, c_local]:
                continue
            
            slope_val = finite(local_slope[r_local, c_local]) if slope_data is not None else None
            roughness_val = finite(local_roughness[r_local, c_local]) if roughness_data is not None else None
            
            # Check slope
            if slope_val is not None and slope_val > SLOPE_THRESHOLDS["steep"]:
                dangerous_cells.append((abs_row, abs_col))
                individual_indicators.append({
                    "position": {"row": abs_row, "column": abs_col},
                    "category": RISK_CATEGORIES["steep_slope"],
                    "severity": "high" if slope_val > 35 else "medium",
                    "value": round(slope_val, 1),
                })
            
            # TODO: Add other indicators when data available
    
    # Connected-component clustering for dangerous cells
    clusters = []
    visited = set()
    
    # 4-connectivity (up, down, left, right)
    def get_neighbors(r, c):
        neighbors = []
        if r > 0:
            neighbors.append((r - 1, c))
        if r < local_height.shape[0] - 1:
            neighbors.append((r + 1, c))
        if c > 0:
            neighbors.append((r, c - 1))
        if c < local_height.shape[1] - 1:
            neighbors.append((r, c + 1))
        return neighbors
    
    def bfs_cluster(start_r, start_c):
        """Find connected component starting from (start_r, start_c)."""
        queue = [(start_r, start_c)]
        component = []
        visited.add((start_r, start_c))
        
        while queue:
            r, c = queue.pop(0)
            component.append((r, c))
            
            for nr, nc in get_neighbors(r, c):
                if (nr, nc) not in visited and (nr, nc) in dangerous_cells_set:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        
        return component
    
    dangerous_cells_set = set(dangerous_cells)
    
    # Only proceed if we have dangerous cells
    if dangerous_cells_set:
        for cell in dangerous_cells:
            if cell not in visited:
                cluster = bfs_cluster(cell[0], cell[1])
                if len(cluster) > 0:
                    # Calculate cluster properties
                    cluster_slopes = []
                    cluster_positions = []
                    for cr, cc in cluster:
                        r_local = cr - neighborhood_rows.start
                        c_local = cc - neighborhood_cols.start
                        s = finite(local_slope[r_local, c_local]) if slope_data is not None else None
                        if s is not None:
                            cluster_slopes.append(s)
                            cluster_positions.append({"row": cr, "column": cc})
                    
                    max_slope = max(cluster_slopes) if cluster_slopes else 0
                    min_slope = min(cluster_slopes) if cluster_slopes else 0
                    avg_slope = sum(cluster_slopes) / len(cluster_slopes) if cluster_slopes else 0
                    
                    clusters.append({
                        "size": len(cluster),
                        "max_slope": round(max_slope, 1),
                        "min_slope": round(min_slope, 1),
                        "avg_slope": round(avg_slope, 1),
                        "positions": cluster_positions,
                        "center": {
                            "row": sum(p[0] for p in cluster_positions) / len(cluster_positions),
                            "column": sum(p[1] for p in cluster_positions) / len(cluster_positions),
                        },
                        "category": RISK_CATEGORIES["steep_slope"],
                        "severity": "high" if max_slope > 35 else "medium",
                    })
    
    return {
        "individual": individual_indicators,
        "clusters": clusters,
        "note": f"Evaluated {len(dangerous_cells)} dangerous cells in {len(clusters)} clusters" if dangerous_cells else "No significant hazards detected in region",
    }


# Backward compatibility: expose topographic_metrics from terrain_geospatial
# This is a re-export for use by other modules
topographic_metrics = calculate_topographic_metrics