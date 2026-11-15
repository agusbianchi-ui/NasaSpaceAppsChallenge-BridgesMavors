"""A* on registered scientific cells. Visual Y is only returned for rendering."""

import heapq, math, time
from functools import lru_cache
import numpy as np
from app.schemas.planning import MissionConfig
from app.services.terrain_geospatial import (
    GEOD,
    cell_coordinates,
    model_to_grid,
    grid_to_model,
)
from app.services.hazard_evaluation import (
    environment_snapshot,
    ENVIRONMENTAL_VARIABLES,
    finite,
)

PLANNING_STRATEGIES = {
    "shortest": "Minimum horizontal distance subject to constraints",
    "low_slope": "Distance plus normalized ascent/descent and roughness",
    "environmental": "Available environmental penalty; may be spatially uniform",
    "balanced": "Normalized topographic and available environmental costs",
}


def get_strategy_description(name):
    return PLANNING_STRATEGIES.get(name, "Unknown strategy")


@lru_cache(maxsize=2)
def coordinates(service):
    return cell_coordinates(service.metadata)


class TerrainMap:
    def __init__(self, service, mission=None, excluded=()):
        if service.metadata is None:
            raise ValueError("Validated scientific terrain unavailable.")
        self.service = service
        self.metadata = service.metadata
        self.arrays = service.arrays
        self.rows, self.cols = service.arrays["valid_mask"].shape
        self.mission = mission or MissionConfig()
        self.excluded = set(excluded)
        self.height = self.arrays["scientific_elevation"]
        self.slope = self.arrays["slope"]
        self.roughness = self.arrays["roughness"]
        self.valid = (self.arrays["valid_mask"] == 1) & np.isfinite(self.height)
        self.longitude, self.latitude = coordinates(service)
        self.environment = environment_snapshot(service, self.mission)
        self.unknown = [
            key
            for key in ENVIRONMENTAL_VARIABLES
            if finite(self.environment.get(key, {}).get("value")) is None
        ]
        self.dust = finite(self.environment.get("dust_optical_depth", {}).get("value"))

    def valid_cell(self, r, c):
        if (
            not (0 <= r < self.rows and 0 <= c < self.cols)
            or not self.valid[r, c]
            or (r, c) in self.excluded
        ):
            return False
        gradient = float(self.slope[r, c])
        return not math.isfinite(gradient) or gradient <= max(
            self.mission.max_slope, self.mission.max_descent_slope
        )

    def distance(self, a, b):
        return float(
            GEOD.inv(
                self.longitude[a], self.latitude[a], self.longitude[b], self.latitude[b]
            )[2]
        )

    def basic_edge(self, a, b):
        if not self.valid_cell(*a) or not self.valid_cell(*b):
            return None
        distance = self.distance(a, b)
        delta = float(self.height[b]) - float(self.height[a])
        signed = math.degrees(math.atan2(delta, distance))
        if (
            signed > self.mission.max_slope + 1e-9
            or -signed > self.mission.max_descent_slope + 1e-9
        ):
            return None
        return distance, delta, signed

    def edge(self, a, b):
        edge = self.basic_edge(a, b)
        if edge is None:
            return None
        if a[0] != b[0] and a[1] != b[1]:
            # Supercover of a diagonal: both corner cells and their connecting edges must pass.
            for side in [(a[0], b[1]), (b[0], a[1])]:
                if self.basic_edge(a, side) is None or self.basic_edge(side, b) is None:
                    return None
        return edge

    def minimum_factor(self, strategy):
        """Provable regional lower bound; topographic penalties are non-negative."""
        if strategy == "shortest":
            return 1.0
        mission = self.mission
        unknown = (
            mission.unknown_weight * len(self.unknown) / len(ENVIRONMENTAL_VARIABLES)
            if mission.unknown_policy == "penalize"
            else 0.0
        )
        dust = (
            mission.environment_weight * min(1, self.dust / mission.high_dust)
            if self.dust is not None
            and strategy in ("environmental", "balanced")
            and mission.unknown_policy != "topography_only"
            else 0.0
        )
        return 1.0 + unknown + dust

    def factor(self, b, signed, strategy):
        if strategy == "shortest":
            return 1.0
        m = self.mission
        slope = min(
            1,
            abs(signed)
            / max(m.max_slope if signed >= 0 else m.max_descent_slope, 0.001),
        )
        rough = finite(self.roughness[b])
        rough_norm = min(1, rough / m.roughness_scale) if rough is not None else 0
        topo = m.slope_weight * slope * slope + m.roughness_weight * rough_norm
        dust = min(1, self.dust / m.high_dust) if self.dust is not None else 0
        # Dust is a scenario-native regional constant, never invented per-cell.
        environment = (
            m.environment_weight * dust
            if strategy in ("environmental", "balanced")
            and m.unknown_policy != "topography_only"
            else 0
        )
        unknown = (
            m.unknown_weight * len(self.unknown) / len(ENVIRONMENTAL_VARIABLES)
            if m.unknown_policy == "penalize"
            else 0
        )
        return (
            1
            + (topo if strategy in ("low_slope", "balanced") else 0)
            + environment
            + unknown
        )


class SearchStopped(Exception):
    pass


class AStarPlanner:
    def __init__(self, terrain):
        self.terrain = terrain

    def plan(
        self,
        start,
        goal,
        strategy="balanced",
        cancel=None,
        deadline=None,
        heuristic=True,
    ):
        terrain = self.terrain
        if not terrain.valid_cell(*start) or not terrain.valid_cell(*goal):
            return None, None, 0
        if terrain.mission.unknown_policy == "avoid" and terrain.unknown:
            return None, None, 0
        if strategy == "environmental" and (
            terrain.dust is None or terrain.mission.unknown_policy == "topography_only"
        ):
            raise ValueError(
                "Environmental strategy requires an explicit available historical dust scenario and a policy allowing environmental evaluation."
            )
        estimate = lambda cell: (
            terrain.distance(cell, goal) * terrain.minimum_factor(strategy)
            if heuristic
            else 0
        )
        frontier = [(estimate(start), 0, start)]
        cost = {start: 0.0}
        parent = {}
        expanded = 0
        while frontier:
            _, g, current = heapq.heappop(frontier)
            if g != cost.get(current):
                continue
            if current == goal:
                path = [current]
                while current in parent:
                    current = parent[current]
                    path.append(current)
                return path[::-1], g, expanded
            expanded += 1
            if expanded % 128 == 0:
                if cancel and cancel.is_set():
                    raise SearchStopped("Calculation cancelled.")
                if expanded > 150000 or (deadline and time.monotonic() > deadline):
                    raise SearchStopped(
                        "Resource limit reached; narrow the route or relax constraints."
                    )
            for dr, dc in [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ]:
                neighbor = (current[0] + dr, current[1] + dc)
                edge = terrain.edge(current, neighbor)
                if edge is None:
                    continue
                distance, _, signed = edge
                candidate = g + distance * terrain.factor(neighbor, signed, strategy)
                if candidate < cost.get(neighbor, math.inf):
                    cost[neighbor] = candidate
                    parent[neighbor] = current
                    heapq.heappush(
                        frontier, (candidate + estimate(neighbor), candidate, neighbor)
                    )
        return None, None, expanded


def analyze_path(terrain, path):
    distances = []
    slopes = []
    gain = loss = 0.0
    surface = 0.0
    profile = []
    distance_so_far = 0
    for index, cell in enumerate(path):
        if index:
            previous = path[index - 1]
            distance = terrain.distance(previous, cell)
            delta = float(terrain.height[cell]) - float(terrain.height[previous])
            signed = math.degrees(math.atan2(delta, distance))
            distances.append(distance)
            slopes.append(signed)
            gain += max(0, delta)
            loss += max(0, -delta)
            surface += math.hypot(distance, delta)
            distance_so_far += distance
        profile.append(
            {"distance_m": distance_so_far, "elevation_m": float(terrain.height[cell])}
        )
    rough = [finite(terrain.roughness[cell]) for cell in path]
    rough = [v for v in rough if v is not None]
    return {
        "horizontal_distance_m": sum(distances),
        "surface_distance_m": surface,
        "estimated_duration_s": surface / terrain.mission.velocity,
        "elevation_gain_m": gain,
        "elevation_loss_m": loss,
        "max_slope_deg": max(map(abs, slopes), default=0),
        "mean_slope_deg": sum(d * abs(s) for d, s in zip(distances, slopes))
        / sum(distances)
        if distances
        else 0,
        "max_ascent_deg": max(slopes, default=0) if any(s > 0 for s in slopes) else 0,
        "max_descent_deg": abs(min(slopes, default=0))
        if any(s < 0 for s in slopes)
        else 0,
        "mean_roughness_m": sum(rough) / len(rough) if rough else None,
        "mobility_difficulty": None,
        "temperature": None,
        "solar_exposure": None,
        "ionizing_exposure": None,
        "dust_optical_depth": terrain.dust
        if terrain.mission.unknown_policy != "topography_only"
        else None,
        "dust_value_meaning": "9.3 micron absorption normalized to 610 Pa; static historical daily regional value",
        "unknown_environment_fraction": 1.0 if terrain.unknown else 0.0,
        "unknown_variable_fraction": len(terrain.unknown)
        / len(ENVIRONMENTAL_VARIABLES),
        "unknown_variables": terrain.unknown,
        "used_variables": ["scientific_elevation", "slope", "roughness"]
        + (
            ["dust_optical_depth"]
            if terrain.dust is not None
            and terrain.mission.unknown_policy != "topography_only"
            else []
        ),
        "profile": profile,
        "temporal_optimization": False,
        "scenario_note": "Static historical snapshot; duration assumes user speed, no time-varying climate or irradiance model.",
    }


def solve_request(service, request, cancel=None):
    terrain = TerrainMap(service, request.mission, request.excluded_cells)
    cells = []
    snaps = []
    for p in request.points:
        cell = model_to_grid(p.x, p.z, terrain.metadata)
        if cell is None or not terrain.valid_cell(*cell):
            return {
                "success": False,
                "error": "No valid route found. An endpoint or waypoint is outside valid terrain, excluded or above the slope limit.",
                "routes": [],
            }
        cells.append(cell)
        x, z = grid_to_model(*cell, terrain.metadata)
        snaps.append(
            {
                "requested": p.model_dump(),
                "snapped": {"x": x, "z": z},
                "changed": abs(x - p.x) > 1e-6 or abs(z - p.z) > 1e-6,
            }
        )
    strategies = list(PLANNING_STRATEGIES) if request.compare else [request.strategy]
    routes = []
    deadline = time.monotonic() + 25
    for strategy in strategies:
        if strategy == "environmental" and (
            terrain.dust is None or request.mission.unknown_policy == "topography_only"
        ):
            routes.append(
                {
                    "strategy": strategy,
                    "success": False,
                    "error": "Environmental strategy unavailable: select historical dust with an environmental policy. Other environmental variables remain unknown.",
                }
            )
            continue
        path = []
        total = 0
        expanded = 0
        for start, goal in zip(cells, cells[1:]):
            segment, cost, count = AStarPlanner(terrain).plan(
                start, goal, strategy, cancel, deadline
            )
            expanded += count
            if segment is None:
                path = []
                break
            path.extend(segment if not path else segment[1:])
            total += cost
        if not path:
            routes.append(
                {
                    "strategy": strategy,
                    "success": False,
                    "error": "No valid route found. Constraints or unknown-data policy block the route.",
                }
            )
            continue
        local = []
        for r, c in path:
            x, z = grid_to_model(r, c, terrain.metadata)
            local.append(
                {
                    "x": x,
                    "z": z,
                    "y": float(terrain.arrays["visual_elevation"][r, c]),
                    "row": r,
                    "column": c,
                }
            )
        routes.append(
            {
                "strategy": strategy,
                "success": True,
                "path_local": local,
                "path_cells": path,
                "total_cost": total,
                "cost_unit": "metre-equivalent normalized objective",
                "expanded": expanded,
                "analysis": analyze_path(terrain, path),
                "partial_environment": bool(terrain.unknown),
                "explanation": PLANNING_STRATEGIES[strategy]
                + "; user limits and unknown-data policy applied.",
            }
        )
    return {
        "success": any(route["success"] for route in routes),
        "routes": routes,
        "snapping": snaps,
        "mission_config": request.mission.model_dump(),
        "input_points": [p.model_dump() for p in request.points],
        "source_sha256": service.metadata["source_sha256"],
        "notice": "Hypothetical assistance, not certified navigation. Strategies may legitimately coincide; regional dust cannot create local gradients.",
    }
