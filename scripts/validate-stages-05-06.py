"""Reproduce the real-terrain audit checks without touching source models or AI."""

from pathlib import Path
import sys, json, time, hashlib, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "WebApp/backend"))
from app.services.terrain_science import get_terrain_science_service
from app.schemas.planning import MissionConfig, PlanRequest
from app.services.path_planning import solve_request, analyze_path, TerrainMap
from app.services.terrain_geospatial import model_to_grid
from app.services.hazard_evaluation import region_assessment, point_assessment

OUT = ROOT / "docs/stages/05-06-evidence"
service = get_terrain_science_service()
assert service.metadata and service.metadata["georeference_verified"]
reference = json.loads((ROOT / "ruta_marte_preliminar.json").read_text())
cells = [model_to_grid(p["x"], p["z"], service.metadata) for p in reference["points"]]
preliminary = analyze_path(TerrainMap(service), cells)
request = PlanRequest(
    points=[{"x": 24875, "z": -55625}, {"x": 8375, "z": -20625}],
    compare=True,
    mission=MissionConfig(
        dust_scenario="my36", unknown_policy="penalize", high_dust=0.1
    ),
)
started = time.perf_counter()
result = solve_request(service, request)
result["calculation_seconds"] = time.perf_counter() - started
result["preliminary_reference_statistics"] = preliminary
(OUT / "real-route-validation.json").write_text(
    json.dumps(result, indent=2), encoding="utf8"
)
regions = region_assessment(service, request.mission)
(OUT / "real-hazard-validation.json").write_text(
    json.dumps(regions, indent=2), encoding="utf8"
)
points = []
# Three actual science positions: lowest/highest available height and a low-gradient sample.
import numpy as np

height = service.arrays["scientific_elevation"]
slope = service.arrays["slope"]
valid = service.arrays["valid_mask"] == 1
interior_height = np.where(valid & np.isfinite(slope), height, np.nan)
for name, index in [
    ("high", np.nanargmax(interior_height)),
    ("low", np.nanargmin(interior_height)),
    ("gentle", np.nanargmin(slope)),
]:
    row, column = map(int, np.unravel_index(index, height.shape))
    x = service.metadata["originX"] + (column + 0.5) * 250
    z = service.metadata["originZ"] + (row + 0.5) * 250
    point = point_assessment(service, x, z, request.mission)
    points.append({"sample": name, **point})
(OUT / "three-point-validation.json").write_text(
    json.dumps(points, indent=2), encoding="utf8"
)
for array in (
    "scientific_elevation",
    "visual_elevation",
    "valid_mask",
    "slope",
    "aspect",
    "roughness",
):
    path = ROOT / "output-stage4" / f"{array}.bin"
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert digest == service.metadata[path.name]["sha256"]
original = ROOT / "recursosU/MapaMarteN.glb"
with original.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
assert digest == service.metadata["source_sha256"]
print(
    json.dumps(
        {
            "original_sha256": digest,
            "regions": regions["total_regions"],
            "calculation_seconds": result["calculation_seconds"],
            "reference_distance_m": preliminary["horizontal_distance_m"],
            "reference_max_slope_deg": preliminary["max_slope_deg"],
            "routes": [
                {k: r.get(k) for k in ("strategy", "success", "total_cost")}
                for r in result["routes"]
            ],
        }
    )
)
