from fastapi import APIRouter, HTTPException, Query
from app.schemas.common import APIResponse
from app.services.terrain_science import get_terrain_science_service, CATALOG
from app.services.hazard_evaluation import (
    evaluate_hazard_indicators,
    evaluate_region_indicators,
    classify_mobility_difficulty,
    RISK_CATEGORIES,
    finite,
    SLOPE_THRESHOLDS,
)
from app.services.path_planning import (
    TerrainMap, AStarPlanner, plan_route, 
    PLANNING_STRATEGIES, get_strategy_description
)


router = APIRouter(tags=["terrain-science"])


@router.get("/terrain/metadata", response_model=APIResponse[dict])
def terrain_metadata():
    return {"data": get_terrain_science_service().terrain_metadata()}


@router.get("/terrain/point", response_model=APIResponse[dict])
def terrain_point(
    x: float | None = Query(default=None, allow_inf_nan=False),
    z: float | None = Query(default=None, allow_inf_nan=False),
    latitude: float | None = Query(default=None, ge=-90, le=90, allow_inf_nan=False),
    longitude: float | None = Query(default=None, ge=-180, le=180, allow_inf_nan=False),
    mars_year: int | None = Query(default=None, ge=1, le=99),
    sol: int | None = Query(default=None, ge=1, le=669),
):
    local = x is not None and z is not None and latitude is None and longitude is None
    geographic = (
        latitude is not None and longitude is not None and x is None and z is None
    )
    if not (local or geographic):
        raise HTTPException(
            422,
            "Provide x and z OR latitude and longitude, without mixing coordinate systems.",
        )
    if (mars_year is None) != (sol is None):
        raise HTTPException(422, "Mars year and sol-of-year must be provided together.")
    service = get_terrain_science_service()
    if geographic:
        return {"data": service.geographic_point(latitude, longitude, mars_year, sol)}
    return {"data": service.point(x, z, mars_year, sol)}


@router.get("/science/sources", response_model=APIResponse[list[dict]])
def science_sources():
    return {"data": get_terrain_science_service().sources()}


@router.get("/science/variables", response_model=APIResponse[list[dict]])
def science_variables():
    return {"data": get_terrain_science_service().variables()}


@router.get("/mission/scenarios", response_model=APIResponse[list[dict]])
def mission_scenarios():
    service = get_terrain_science_service()
    items = []
    for item in CATALOG["scenarios"]:
        current = dict(item)
        if item["id"] == "static-topography" and not service.metadata:
            current["availability"] = "Unavailable"
        if item["id"] == "my36-observed-dust" and service.dust is None:
            current["availability"] = "Unavailable"
        items.append(current)
    return {"data": items}


@router.get("/hazard/indicators", response_model=APIResponse[dict])
def hazard_indicators(
    x: float = Query(..., description="Local X coordinate"),
    z: float = Query(..., description="Local Z coordinate"),
    mars_year: int = Query(..., description="Mars year (e.g., 36)"),
    sol: int = Query(..., description="Sol of year (1-669)"),
    thermal_min: float = Query(default=-40, ge=-100, le=50, description="Minimum safe temperature (°C)"),
    thermal_max: float = Query(default=30, ge=-100, le=100, description="Maximum safe temperature (°C)"),
    max_slope: float = Query(default=25, ge=0, le=90, description="Maximum allowed slope (degrees)"),
    mission_type: str = Query(default="exploration", description="Mission type: scientific|exploration|survey"),
    displacement: str = Query(default="foot", description="Displacement type: foot|rover"),
    velocity: str = Query(default="medium", description="Estimated velocity: low|medium|high"),
):
    """Evaluate hazard indicators for a terrain position.

    Returns scientific hazard assessment based on terrain and environmental conditions.
    Thresholds are configurable per mission configuration, not arbitrary NASA limits.
    """
    service = get_terrain_science_service()
    position_data = service.point(x, z, mars_year, sol)
    
    if position_data["coverage"] == "Unavailable":
        return {"data": {"warnings": [], "coverage": "Unavailable", "note": "No validated terrain coverage at this position"}}
    
    # Extract relevant values from the point data
    variables = position_data["variables"]
    
    # Get topographic variables
    slope_degrees = None
    slope_normalized = None
    roughness_value = None
    temperature_surface = None
    temperature_atmospheric = None
    dust_optical_depth = None
    wind_speed = None
    mobility_index = None
    
    for var_id, var_data in variables.items():
        if var_id == "slope":
            slope_degrees = finite(var_data.get("value"))
            slope_normalized = slope_degrees / max(SLOPE_THRESHOLDS["steep"], 1) if slope_degrees is not None else None
        elif var_id == "roughness":
            roughness_value = finite(var_data.get("value"))
        elif var_id == "scientific_elevation":
            temperature_surface = finite(var_data.get("value"))  # Using elevation as proxy; real temp needs separate data
        elif var_id == "dust_optical_depth":
            dust_optical_depth = finite(var_data.get("value"))
        elif var_id == "wind_speed":
            wind_speed = finite(var_data.get("value"))
        elif var_id == "mobility_difficulty":
            mobility_index = finite(var_data.get("value"))
    
    # Build mission config from query parameters
    mission_config = {
        "thermal_min": thermal_min,
        "thermal_max": thermal_max,
        "max_slope": max_slope,
        "mission_type": mission_type,
        "displacement": displacement,
        "velocity": velocity,
    }
    
    # Evaluate hazard indicators
    warnings = evaluate_hazard_indicators(
        slope_degrees=slope_degrees,
        slope_value=slope_normalized,
        roughness_value=roughness_value,
        temperature_surface=temperature_surface,
        temperature_atmospheric=temperature_atmospheric,
        dust_optical_depth=dust_optical_depth,
        wind_speed=wind_speed,
        mobility_index=mobility_index,
        mission_config=mission_config,
    )
    
    # Also evaluate region indicators
    grid_cell = service.model_to_grid(x, z, service.metadata) if service.metadata else None
    if grid_cell and position_data["coverage"] == "Available":
        row, column = grid_cell
        region_result = evaluate_region_indicators(
            row, column, service.metadata, service, mission_config
        )
    else:
        region_result = {"individual": [], "clusters": [], "note": "Cannot evaluate region without grid coverage"}
    
    result = {
        "warnings": warnings,
        "coverage": position_data["coverage"],
        "position": position_data["position"],
        "region_analysis": region_result,
        "mission_config": mission_config,
        "notice": position_data.get("notice", ""),
    }
    
    return {"data": result}


@router.get("/plan/strategies", response_model=APIResponse[dict])
def get_planning_strategies():
    """Get available planning strategies and their descriptions."""
    return {
        "data": {
            "strategies": PLANNING_STRATEGIES,
            "default": "balanced",
            "description": {
                "shortest": "Prioriza distancia minima; puede tener pendientes mas pronunciadas",
                "low_slope": "Prioriza pendientes suaves; recorrido mas largo pero mas seguro",
                "environmental": "Prioriza condiciones ambientales favorables cuando hay datos",
                "balanced": "Combina distancia, topografia y factores ambientales",
            }
        }
    }


@router.post("/plan/route", response_model=APIResponse[dict])
def plan_route(
    start_x: float = Query(..., description="Start X coordinate (local)"),
    start_z: float = Query(..., description="Start Z coordinate (local)"),
    goal_x: float = Query(..., description="Goal X coordinate (local)"),
    goal_z: float = Query(..., description="Goal Z coordinate (local)"),
    mars_year: int = Query(default=36, ge=1, le=99, description="Mars year"),
    sol: int = Query(default=1, ge=1, le=669, description="Sol of year"),
    displacement: str = Query(default="foot", description="Displacement: foot|rover"),
    velocity: float = Query(default=1.0, ge=0.1, le=10.0, description="Estimated velocity (m/s)"),
    max_slope: float = Query(default=25, ge=0, le=90, description="Maximum allowed slope (degrees)"),
    strategy: str = Query(default="balanced", description="Planning strategy: shortest|low_slope|environmental|balanced"),
    avoid_no_data: bool = Query(default=True, description="Avoid NoData cells"),
    ):
    """Plan an expedition route using A* pathfinding.

    Finds optimal routes across the Martian terrain considering:
    - Topographic factors: slope, roughness, elevation changes
    - Environmental factors: when data available (temperature, dust, wind)
    - Movement constraints: NoData avoidance, slope limits, terrain boundaries

    Returns the planned path with analysis of topographic and environmental factors.
    """
    service = get_terrain_science_service()

    # Validate strategy
    valid_strategies = ["shortest", "low_slope", "environmental", "balanced"]
    if strategy not in valid_strategies:
        raise HTTPException(
            422,
            f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}"
        )

    # Build mission configuration
    mission_config = {
        "displacement": displacement,
        "velocity": velocity,
        "max_slope": max_slope,
        "planning_strategy": strategy,
        "avoid_no_data": avoid_no_data,
    }

    # Plan the route
    result = plan_route(
        start_x=start_x,
        start_z=start_z,
        goal_x=goal_x,
        goal_z=goal_z,
        science_service=service,
        mission_config=mission_config,
    )

    # Add strategy info and mission config
    result["data"]["strategy"] = strategy
    result["data"]["strategy_description"] = get_strategy_description(strategy)
    result["data"]["mission_config"] = mission_config

    return {"data": result}