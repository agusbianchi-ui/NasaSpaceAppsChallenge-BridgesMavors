from fastapi import APIRouter, HTTPException, Query
from app.schemas.common import APIResponse
from app.services.terrain_science import get_terrain_science_service, CATALOG
from app.services.hazard_evaluation import point_assessment, region_assessment
from app.schemas.planning import MissionConfig, PlanRequest, RegionRequest
from app.services.path_planning import PLANNING_STRATEGIES
from app.services import planning_jobs
from fastapi import Body

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
    x: float = Query(allow_inf_nan=False),
    z: float = Query(allow_inf_nan=False),
    mars_year: int | None = Query(default=None),
    sol: int | None = Query(default=None, ge=1, le=669),
    max_slope: float = Query(default=25, ge=0, le=60),
    thermal_min: float = -40,
    thermal_max: float = 30,
):
    if mars_year not in (None, 36) or (mars_year is None) != (sol is None):
        raise HTTPException(422, "Select MY36 and sol together, or omit both.")
    try:
        mission = MissionConfig(
            max_slope=max_slope,
            thermal_min=thermal_min,
            thermal_max=thermal_max,
            dust_scenario="my36" if sol else "none",
            sol=sol or 1,
        )
    except ValueError as error:
        raise HTTPException(422, str(error))
    return {"data": point_assessment(get_terrain_science_service(), x, z, mission)}


@router.post("/science/inspect", response_model=APIResponse[dict])
def inspect_position(request: PlanRequest):
    p = request.points[0]
    return {
        "data": point_assessment(
            get_terrain_science_service(), p.x, p.z, request.mission
        )
    }


@router.post("/hazard/regions", response_model=APIResponse[dict])
def hazard_regions(request: RegionRequest):
    return {"data": region_assessment(get_terrain_science_service(), request.mission)}


@router.get("/plan/strategies", response_model=APIResponse[dict])
def strategies():
    return {
        "data": {
            "strategies": PLANNING_STRATEGIES,
            "default": "balanced",
            "environmental_requirements": "Explicit available historical dust and non-topography-only policy; other variables remain unavailable.",
        }
    }


@router.post("/plan/route", response_model=APIResponse[dict])
def plan_route(request: PlanRequest):
    service = get_terrain_science_service()
    if service.metadata is None:
        raise HTTPException(
            503, "Scientific terrain unavailable; manual geometry remains available."
        )
    try:
        result = planning_jobs.submit(service, request)
    except ValueError as error:
        raise HTTPException(429, str(error))
    return {"data": result}


@router.get("/plan/jobs/{job_id}", response_model=APIResponse[dict])
def plan_job(job_id: str):
    result = planning_jobs.get(job_id)
    if result is None:
        raise HTTPException(404, "Planning job not found.")
    return {"data": result}


@router.delete("/plan/jobs/{job_id}", response_model=APIResponse[dict])
def cancel_plan(job_id: str):
    result = planning_jobs.cancel(job_id)
    if result is None:
        raise HTTPException(404, "Planning job not found.")
    return {"data": result}
