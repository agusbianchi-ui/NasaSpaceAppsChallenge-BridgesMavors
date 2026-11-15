"""Small analytical fixtures are test-only, never served as scientific terrain."""

from types import SimpleNamespace
from threading import Event
import math, time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas.planning import MissionConfig, PlanRequest
from app.services.path_planning import (
    TerrainMap,
    AStarPlanner,
    analyze_path,
    solve_request,
    SearchStopped,
)
from app.services.hazard_evaluation import (
    evaluate_variables,
    point_assessment,
    region_assessment,
)
from app.services.terrain_science import get_terrain_science_service
from app.services import planning_jobs


def fixture(height, mask=None):
    h = np.array(height, dtype="f4")
    shape = h.shape
    meta = {
        "rows": shape[0],
        "columns": shape[1],
        "cellSize": 250,
        "originX": 0,
        "originZ": 0,
        "source_sha256": "test-only",
    }
    arrays = {
        "scientific_elevation": h,
        "visual_elevation": 3 * (h + 4500),
        "valid_mask": np.ones(shape, "u1") if mask is None else np.array(mask, "u1"),
        "slope": np.zeros(shape, "f4"),
        "roughness": np.zeros(shape, "f4"),
    }

    class Service:
        metadata = meta

        def __init__(self):
            self.arrays = arrays

        def point(self, *args):
            return {
                "variables": {
                    "dust_optical_depth": {
                        "value": 0.2,
                        "unit": "Pa/Pa",
                        "classification": "Derived",
                        "name": "Test dust",
                    }
                }
            }

    return Service()


def test_temperature_uses_kelvin_not_elevation_and_configured_limits():
    variables = {
        "scientific_elevation": {"value": -2500, "unit": "m"},
        "surface_temperature": {
            "value": 300,
            "unit": "K",
            "name": "Surface temperature",
        },
        "slope": {"value": 12, "unit": "degree", "name": "Slope"},
    }
    warnings = evaluate_variables(
        variables, MissionConfig(thermal_max=20, max_slope=10)
    )
    assert {w["category"] for w in warnings} >= {
        "steep_slope",
        "extreme_heat",
        "unknown_conditions",
    }
    assert not any(w["category"] == "extreme_cold" for w in warnings)
    cold = evaluate_variables(
        {"surface_temperature": {"value": 200, "unit": "K"}},
        MissionConfig(thermal_min=-60),
    )
    assert any(w["category"] == "extreme_cold" for w in cold)
    assert not any(
        w["category"].startswith("extreme_")
        for w in evaluate_variables(
            {"scientific_elevation": {"value": -2500, "unit": "m"}}, MissionConfig()
        )
    )


def test_astar_matches_dijkstra_and_cost_weights_change_objective():
    s = fixture([[0, 0, 0, 0], [0, 70, 80, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    terrain = TerrainMap(s, MissionConfig(max_slope=40, max_descent_slope=40))
    for strategy in ("shortest", "low_slope", "balanced"):
        path, cost, _ = AStarPlanner(terrain).plan((1, 0), (1, 3), strategy)
        reference, optimal, _ = AStarPlanner(terrain).plan(
            (1, 0), (1, 3), strategy, heuristic=False
        )
        assert path and reference
        assert cost == pytest.approx(optimal, abs=1e-6)
    short, _, _ = AStarPlanner(terrain).plan((1, 0), (1, 3), "shortest")
    low, _, _ = AStarPlanner(terrain).plan((1, 0), (1, 3), "low_slope")
    assert (
        analyze_path(terrain, low)["max_slope_deg"]
        <= analyze_path(terrain, short)["max_slope_deg"]
    )
    a = TerrainMap(s, MissionConfig(slope_weight=0))
    b = TerrainMap(s, MissionConfig(slope_weight=10))
    assert b.factor((1, 1), 10, "low_slope") > a.factor((1, 1), 10, "low_slope")
    assert a.factor((1, 1), 10, "shortest") == b.factor((1, 1), 10, "shortest") == 1


def test_diagonal_no_corner_cut_nodata_and_exclusions():
    s = fixture([[0, 0], [0, 0]], [[1, 0], [0, 1]])
    terrain = TerrainMap(s)
    assert AStarPlanner(terrain).plan((0, 0), (1, 1))[0] is None
    s = fixture([[0, np.nan], [0, 0]])
    terrain = TerrainMap(s, excluded=[(1, 0)])
    assert AStarPlanner(terrain).plan((0, 0), (1, 1))[0] is None
    assert terrain.edge((-1, 0), (0, 0)) is None


def test_ascent_descent_hard_limits_and_unknown_policy():
    s = fixture([[0, 100]])
    terrain = TerrainMap(s, MissionConfig(max_slope=10, max_descent_slope=40))
    assert terrain.edge((0, 0), (0, 1)) is None
    assert terrain.edge((0, 1), (0, 0)) is not None
    terrain = TerrainMap(s, MissionConfig(unknown_policy="avoid"))
    assert AStarPlanner(terrain).plan((0, 0), (0, 1))[0] is None
    penalized = TerrainMap(
        s, MissionConfig(unknown_policy="penalize", dust_scenario="my36")
    )
    assert penalized.factor((0, 0), 0, "balanced") > 1


def test_stats_diagonals_gain_loss_duration_and_null_exposures():
    s = fixture([[0, 0], [0, 10]])
    terrain = TerrainMap(s, MissionConfig(velocity=2))
    stats = analyze_path(terrain, [(0, 0), (1, 1), (1, 0)])
    distance = terrain.distance((0, 0), (1, 1)) + terrain.distance((1, 1), (1, 0))
    assert stats["horizontal_distance_m"] == pytest.approx(distance)
    assert stats["elevation_gain_m"] == stats["elevation_loss_m"] == 10
    assert stats["estimated_duration_s"] == stats["surface_distance_m"] / 2
    assert stats["ionizing_exposure"] is None and stats["solar_exposure"] is None


def test_waypoints_invalid_endpoint_and_snapping():
    s = fixture(np.zeros((4, 4)))
    request = PlanRequest(
        points=[{"x": 125, "z": 125}, {"x": 625, "z": 125}, {"x": 625, "z": 625}],
        strategy="shortest",
    )
    result = solve_request(s, request)
    assert result["success"] and [0, 2] in [
        list(c) for c in result["routes"][0]["path_cells"]
    ]
    assert not any(p["changed"] for p in result["snapping"])
    invalid = request.model_copy(
        update={"points": [SimpleNamespace(x=-1, z=0), request.points[-1]]}
    )
    assert not solve_request(s, invalid)["success"]


def test_cluster_absolute_positions_and_mission_threshold():
    s = fixture(np.zeros((10, 10)))
    s.arrays["slope"][7:9, 6:8] = 30
    regions = region_assessment(s, MissionConfig(max_slope=25))["regions"]
    steep = [r for r in regions if r["category"] == "steep_slope"]
    assert (
        len(steep) == 1
        and steep[0]["cell_count"] == 4
        and steep[0]["bounds"] == [7, 6, 8, 7]
    )
    assert steep[0]["x"] >= 1625 and steep[0]["z"] >= 1875
    assert not any(
        r["category"] == "steep_slope"
        for r in region_assessment(s, MissionConfig(max_slope=40))["regions"]
    )


def test_cancellation_and_resource_budget():
    terrain = TerrainMap(fixture(np.zeros((40, 40))))
    cancel = Event()
    cancel.set()
    with pytest.raises(SearchStopped):
        AStarPlanner(terrain).plan(
            (0, 0), (39, 39), "shortest", cancel, time.monotonic() - 1, heuristic=False
        )


def test_real_sources_clusters_and_three_different_positions():
    service = get_terrain_science_service()
    vals = []
    for x, z in [(125, 125), (24875, -55625), (8375, -20625)]:
        result = point_assessment(service, x, z, MissionConfig())
        assert result["coverage"] == "Available"
        vals.append(result["position"]["scientific_elevation"])
        assert not any(
            w["category"] in ("extreme_heat", "extreme_cold", "radiation_exposure")
            for w in result["warnings"]
        )
    assert len(set(vals)) == 3
    regions = region_assessment(service, MissionConfig())
    assert any(r["category"] == "steep_slope" for r in regions["regions"])


def test_api_contract_jobs_validation_and_cancel():
    with TestClient(create_app()) as client:
        assert (
            client.get("/api/v1/hazard/indicators?x=24875&z=-55625").status_code == 200
        )
        assert client.get("/api/v1/hazard/indicators?x=nan&z=0").status_code == 422
        body = {
            "points": [{"x": 24875, "z": -55625}, {"x": 8375, "z": -20625}],
            "mission": {"unknown_policy": "avoid"},
        }
        response = client.post("/api/v1/plan/route", json=body)
        assert response.status_code == 200
        job = response.json()["data"]["id"]
        for _ in range(100):
            result = client.get("/api/v1/plan/jobs/" + job).json()["data"]
            if result["status"] in ("complete", "error", "cancelled"):
                break
            time.sleep(0.02)
        assert result["status"] == "complete" and not result["result"]["success"]
        assert client.delete("/api/v1/plan/jobs/" + job).status_code == 200
        assert (
            client.post(
                "/api/v1/hazard/regions", json={"mission": {"ls": 90}}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/plan/route",
                json={
                    "points": body["points"],
                    "mission": {"thermal_min": 40, "thermal_max": 20},
                },
            ).status_code
            == 422
        )


def test_regional_environment_heuristic_matches_dijkstra():
    service = fixture([[0, 20, 0], [0, 0, 0], [0, 30, 0]])
    terrain = TerrainMap(
        service, MissionConfig(dust_scenario="my36", unknown_policy="penalize")
    )
    for strategy in ("low_slope", "environmental", "balanced"):
        path, cost, _ = AStarPlanner(terrain).plan((0, 0), (2, 2), strategy)
        reference, optimal, _ = AStarPlanner(terrain).plan(
            (0, 0), (2, 2), strategy, heuristic=False
        )
        assert path and reference and cost == pytest.approx(optimal, abs=1e-6)
        assert terrain.minimum_factor(strategy) >= 1
