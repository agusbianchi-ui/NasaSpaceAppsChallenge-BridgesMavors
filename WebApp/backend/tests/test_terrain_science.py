import math
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.terrain_geospatial import (
    model_to_geographic,
    geographic_to_model,
    model_to_grid,
    grid_to_model,
    GEOD,
    topographic_metrics,
    intercell_slope,
)
from app.services.terrain_science import (
    TerrainScienceService,
    get_terrain_science_service,
)


@pytest.fixture(scope="module")
def science():
    return get_terrain_science_service()


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as client:
        yield client


def test_registration_and_separate_scientific_elevation(science):
    assert science.metadata["georeference_verified"]
    assert (
        science.metadata["source_sha256"]
        == "8786642ea6461b4c62ee5b0f9a3b190a962e84ef1e3844dd293a73494068ab48"
    )
    result = science.point(125, 125)
    assert result["position"]["visual_elevation"] == 6264
    assert result["position"]["scientific_elevation"] == pytest.approx(-2412.146484375)
    assert result["variables"]["scientific_elevation"]["classification"] == "Derived"


def test_known_center_and_coordinate_roundtrips():
    center = model_to_geographic(0, 0, 0)
    assert (center["latitude"], center["longitude"], center["elevation"]) == (
        17.5,
        77,
        -4500,
    )
    for x, y, z in [
        (24875, 5790, -55625),
        (8375, 7350, -20625),
        (-27875, 7548, -27875),
    ]:
        geo = model_to_geographic(x, y, z)
        back = geographic_to_model(geo["latitude"], geo["longitude"], geo["elevation"])
        assert [back["x"], back["y"], back["z"]] == pytest.approx([x, y, z], abs=1e-6)
    with pytest.raises(ValueError):
        geographic_to_model(91, 77, 0)
    with pytest.raises(ValueError):
        model_to_geographic(float("nan"), 0, 0)


def test_centers_edges_and_nodata(science):
    metadata = science.metadata
    assert model_to_grid(-100000, -101000, metadata) == (0, 0)
    assert model_to_grid(100000, 0, metadata) is None
    assert model_to_grid(0, 101000, metadata) is None
    assert grid_to_model(0, 0, metadata) == (-99875, -100875)
    result = science.point(-99875, -100875)
    assert result["coverage"] == "Unavailable"
    assert all(v["value"] is None for v in result["variables"].values())
    for row, column in [(404, 400), (181, 499), (321, 433)]:
        x, z = grid_to_model(row, column, metadata)
        assert model_to_grid(x, z, metadata) == (row, column)


def test_geodesic_gradient_aspect_roughness_and_nodata():
    lon = np.zeros((5, 5))
    lat = lon.copy()
    height = lon.copy()
    for row in range(5):
        for column in range(5):
            east = (column - 2) * 250
            north = (2 - row) * 250
            longitude, latitude, _ = GEOD.fwd(
                77, 17.5, math.degrees(math.atan2(east, north)), math.hypot(east, north)
            )
            lon[row, column] = longitude
            lat[row, column] = latitude
            height[row, column] = 0.1 * east + 0.2 * north - 2000
    metrics = topographic_metrics(height, lon, lat)
    assert metrics["slope"][2, 2] == pytest.approx(
        math.degrees(math.atan(math.hypot(0.1, 0.2))), abs=1e-5
    )
    assert metrics["aspect"][2, 2] == pytest.approx(
        math.degrees(math.atan2(-0.1, -0.2)) % 360, abs=1e-4
    )
    assert metrics["roughness"][2, 2] < 1e-6
    height[1, 1] = np.nan
    assert math.isnan(topographic_metrics(height, lon, lat)["slope"][2, 2])
    flat = topographic_metrics(np.ones((5, 5)), lon, lat)
    assert flat["slope"][2, 2] == 0 and math.isnan(flat["aspect"][2, 2])


def test_intercell_slope():
    lon, lat, _ = GEOD.fwd(77, 17.5, 90, 250)
    assert intercell_slope((77, 17.5, -2000), (lon, lat, -1975)) == pytest.approx(
        math.degrees(math.atan2(25, 250))
    )


def test_dust_native_cell_shared_value_explicit_time_and_gaps(science):
    a = science.point(24875, -55625, 36, 1)["variables"]["dust_optical_depth"]
    b = science.point(8375, -20625, 36, 1)["variables"]["dust_optical_depth"]
    assert a["value"] == b["value"] == pytest.approx(0.16697147)
    assert a["sample"]["native_cell_center"] == [78, 17.5]
    assert a["uncertainty"]["value"] == pytest.approx(0.02927452)
    assert (
        science.point(24875, -55625)["variables"]["dust_optical_depth"]["value"] is None
    )
    missing = science.point(24875, -55625, 36, 37)["variables"]["dust_optical_depth"]
    assert missing["availability"] == "Unavailable" and missing["value"] is None
    assert (
        science.point(24875, -55625, 35, 1)["variables"]["dust_optical_depth"]["value"]
        is None
    )
    assert (
        science.point(24875, -55625, 36, 1)["variables"]["ionizing_radiation"]["value"]
        is None
    )


def test_api_validation_and_endpoints(client):
    for endpoint in [
        "/terrain/metadata",
        "/science/sources",
        "/science/variables",
        "/mission/scenarios",
    ]:
        assert client.get("/api/v1" + endpoint).status_code == 200
    for query in [
        "x=0",
        "latitude=91&longitude=77",
        "x=nan&z=0",
        "x=inf&z=0",
        "x=0&z=0&latitude=17&longitude=77",
        "x=0&z=0&sol=1",
        "x=0&z=0&mars_year=36&sol=670",
    ]:
        assert client.get("/api/v1/terrain/point?" + query).status_code == 422
    a = client.get("/api/v1/terrain/point?x=0&z=0").json()["data"]
    b = client.get("/api/v1/terrain/point?latitude=17.5&longitude=77").json()["data"]
    assert a["position"] == b["position"]
    assert (
        client.get("/api/v1/terrain/point?x=999999&z=0").json()["data"]["coverage"]
        == "Unavailable"
    )


def test_missing_files_remain_unavailable(tmp_path):
    service = TerrainScienceService(tmp_path)
    assert service.terrain_metadata()["availability"] == "Unavailable"
    result = service.point(100, 200, 36, 1)
    assert result["position"]["geographic"] is None
    assert all(v["value"] is None for v in result["variables"].values())


def test_corrupt_cache_rejected(tmp_path, science):
    (tmp_path / "terrain_metadata.json").write_text(json.dumps(science.metadata))
    (tmp_path / "scientific_elevation.bin").write_bytes(b"bad")
    service = TerrainScienceService(tmp_path)
    assert service.metadata is None and "Incorrect size" in service.error


def test_real_dem_gradient_against_independent_least_squares(science):
    row, column = 404, 400
    height = science.arrays["scientific_elevation"]
    x, z = grid_to_model(row, column, science.metadata)
    center = model_to_geographic(x, 0, z)
    offsets, differences = [], []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == dc == 0:
                continue
            nx, nz = grid_to_model(row + dr, column + dc, science.metadata)
            neighbor = model_to_geographic(nx, 0, nz)
            azimuth, _, distance = GEOD.inv(center["longitude"], center["latitude"], neighbor["longitude"], neighbor["latitude"])
            offsets.append([distance * math.sin(math.radians(azimuth)), distance * math.cos(math.radians(azimuth))])
            differences.append(float(height[row + dr, column + dc]) - float(height[row, column]))
    gradient = np.linalg.lstsq(offsets, differences, rcond=None)[0]
    expected = math.degrees(math.atan(float(np.linalg.norm(gradient))))
    assert float(science.arrays["slope"][row, column]) == pytest.approx(expected, abs=1e-5)
