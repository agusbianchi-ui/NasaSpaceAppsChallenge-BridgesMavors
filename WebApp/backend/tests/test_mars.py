import pytest
from fastapi.testclient import TestClient

from app.api.v1 import mars as mars_api
from app.core.config import Settings
from app.services.mars_data_service import MarsDataService, MarsUpstreamError
from app.services.mars_wmts import (
    CTX_JEZERO_ID,
    CTX_JEZERO_PRELIM_ID,
    HIRISE_JEZERO_ID,
    MOLA_GLOBAL_ID,
)


def test_list_sources(client: TestClient) -> None:
    response = client.get("/api/v1/mars/sources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["data"], list)
    assert payload["data"]

    source_ids = {source["id"] for source in payload["data"]}
    assert {
        "nasa-mars-2020",
        "nasa-mro",
        "nasa-mars-odyssey",
        "nasa-mgs",
        "nasa-pds",
        "nasa-mars-trek",
    } <= source_ids

    assert all(
        source["url"].startswith("https://")
        for source in payload["data"]
    )

    trek = next(
        source for source in payload["data"] if source["id"] == "nasa-mars-trek"
    )
    assert HIRISE_JEZERO_ID in trek["layer_ids"]
    assert CTX_JEZERO_ID in trek["layer_ids"]
    assert MOLA_GLOBAL_ID in trek["layer_ids"]
    assert CTX_JEZERO_PRELIM_ID in trek["layer_ids"]

    mro = next(
        source for source in payload["data"] if source["id"] == "nasa-mro"
    )
    assert CTX_JEZERO_PRELIM_ID in mro["layer_ids"]

    mgs = next(
        source for source in payload["data"] if source["id"] == "nasa-mgs"
    )
    assert MOLA_GLOBAL_ID in mgs["layer_ids"]


def test_list_layers(client: TestClient) -> None:
    response = client.get("/api/v1/mars/layers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) == 13
    added = {item['id']: item for item in payload['data'] if item['id'] in ('TES_Thermal_Inertia', 'TES_Dust', 'mola_roughness')}
    assert len(added) == 3
    assert all(item['visualizable'] and len(item['wmts']['tile_matrices']) == 2 for item in added.values())

    layer_ids = {layer["id"] for layer in payload["data"]}
    assert layer_ids == {
        "TES_Thermal_Inertia", "TES_Dust", "mola_roughness",
        "hirise-imagery",
        "ctx-imagery",
        "crism-mineral-maps",
        "themis-thermal",
        "mola-elevation",
        "meda-environmental-monitoring",
        HIRISE_JEZERO_ID,
        CTX_JEZERO_ID,
        MOLA_GLOBAL_ID,
        CTX_JEZERO_PRELIM_ID,
    }

    for layer in payload["data"]:
        assert layer["mission"]
        assert layer["instrument"]
        assert layer["data_type"]
        assert layer["limitations"]
        assert layer["source_url"].startswith("https://")
        assert layer["attribution"]
        assert layer["status"] in {"available", "catalog_only", "planned"}

    visualizable = [layer for layer in payload["data"] if layer["visualizable"]]
    assert {layer["id"] for layer in visualizable} == {
        "TES_Thermal_Inertia", "TES_Dust", "mola_roughness",
        HIRISE_JEZERO_ID,
        CTX_JEZERO_ID,
        MOLA_GLOBAL_ID,
        CTX_JEZERO_PRELIM_ID,
    }
    assert all(layer["wmts"] is not None for layer in visualizable)


def test_get_layer(client: TestClient) -> None:
    response = client.get("/api/v1/mars/layers/hirise-imagery")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == "hirise-imagery"
    assert payload["data"]["source"] == "nasa-mro"


def test_get_verified_jezero_hirise_layer(client: TestClient) -> None:
    response = client.get(f"/api/v1/mars/layers/{HIRISE_JEZERO_ID}")

    assert response.status_code == 200
    layer = response.json()["data"]
    assert layer["name"] == "MRO HiRISE, Jezero Mosaic, Controlled"
    assert layer["mission"] == "Mars Reconnaissance Orbiter"
    assert layer["instrument"] == "HiRISE"
    assert layer["resolution"] == pytest.approx(0.25)
    assert layer["resolution_unit"] == "m/pixel"
    assert layer["bounding_box"] == pytest.approx(
        [77.2229331, 18.3067994, 77.583964, 18.669315]
    )
    assert layer["acquisition_date"] is None
    assert layer["processing_level"]
    assert layer["status"] == "available"
    assert layer["visualizable"] is True
    assert layer["spatial_reference"]["code"] == "IAU2000:104905"
    assert layer["provenance"]["verified"] is True
    assert layer["provenance"]["product_created_date"] == "2020-08-03"
    assert layer["wmts"]["tile_matrix_set"] == "default028mm"
    assert len(layer["wmts"]["tile_matrices"]) == 18


def test_get_verified_jezero_ctx_layer(client: TestClient) -> None:
    response = client.get(f"/api/v1/mars/layers/{CTX_JEZERO_ID}")

    assert response.status_code == 200
    layer = response.json()["data"]
    assert layer["instrument"] == "CTX"
    assert layer["resolution"] == pytest.approx(6.0)
    assert layer["bounding_box"] == pytest.approx(
        [77.1604655, 18.2110274, 77.6991776, 18.7211945]
    )
    assert layer["wmts"]["tile_matrix_set"] == "default028mm"
    assert len(layer["wmts"]["tile_matrices"]) == 14


def test_get_verified_global_mola_layer(client: TestClient) -> None:
    response = client.get(f"/api/v1/mars/layers/{MOLA_GLOBAL_ID}")

    assert response.status_code == 200
    layer = response.json()["data"]
    assert layer["instrument"] == "MOLA"
    assert layer["resolution"] == pytest.approx(463.0)
    assert layer["bounding_box"] == pytest.approx(
        [-180.0, -89.9991635, 179.9983271, 90.0]
    )
    assert layer["visualizable"] is True
    assert layer["wmts"]["format"] == "image/jpeg"
    assert layer["wmts"]["resource_url_template"].endswith(".jpg")
    assert len(layer["wmts"]["tile_matrices"]) == 8


def test_get_verified_jezero_preliminary_ctx_layer(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v1/mars/layers/{CTX_JEZERO_PRELIM_ID}"
    )

    assert response.status_code == 200
    layer = response.json()["data"]
    assert layer["instrument"] == "CTX"
    assert layer["resolution"] is None
    assert layer["bounding_box"] == pytest.approx(
        [75.1537692, 15.9058484, 78.8717121, 19.4453003]
    )
    assert layer["visualizable"] is True
    assert layer["wmts"]["format"] == "image/png"
    assert len(layer["wmts"]["tile_matrices"]) == 13


def test_get_unknown_layer_returns_standard_error(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/mars/layers/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {
            "code": "not_found",
            "message": "Layer 'does-not-exist' not found.",
        },
    }


def test_get_jezero_location(client: TestClient) -> None:
    response = client.get("/api/v1/mars/locations/jezero")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"] == "jezero"
    assert payload["data"]["name"] == "Jezero Crater"
    assert payload["data"]["latitude"] == pytest.approx(18.38)
    assert payload["data"]["longitude"] == pytest.approx(77.58)
    assert payload["data"]["source_ids"]
    assert payload["data"]["layer_ids"] == [HIRISE_JEZERO_ID, CTX_JEZERO_ID]
    assert payload["data"]["bounding_box"] == pytest.approx(
        [77.1604655, 18.2110274, 77.6991776, 18.7211945]
    )
    assert payload["data"]["spatial_reference"]["units"] == "degrees"


def test_layer_sources_exist_in_catalog() -> None:
    service = MarsDataService()
    source_ids = {source.id for source in service.list_sources()}

    assert all(
        layer.source in source_ids for layer in service.list_layers()
    )


def test_settings_parse_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS", "http://one.test, http://two.test"
    )
    monkeypatch.setenv("NASA_REQUEST_TIMEOUT_SECONDS", "7.5")

    settings = Settings.from_env()

    assert settings.cors_origins == [
        "http://one.test",
        "http://two.test",
    ]
    assert settings.nasa_request_timeout_seconds == 7.5


def test_openapi_documents_required_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/health" in paths
    assert "/api/v1/mars/sources" in paths
    assert "/api/v1/mars/layers" in paths
    assert "/api/v1/mars/layers/{layer_id}" in paths
    assert "/api/v1/mars/layers/{layer_id}/capabilities" in paths
    assert "/api/v1/mars/locations/jezero" in paths


def test_documentation_endpoints_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_cors_preflight_for_layers(client: TestClient) -> None:
    response = client.options(
        "/api/v1/mars/layers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )


def test_unknown_route_uses_standard_error(client: TestClient) -> None:
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_invalid_method_uses_standard_error(
    client: TestClient,
) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "method_not_allowed"


def test_capabilities_returns_verified_snapshot(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v1/mars/layers/{HIRISE_JEZERO_ID}/capabilities"
    )

    assert response.status_code == 200
    capabilities = response.json()["data"]
    assert capabilities["source"] == "verified_snapshot"
    assert capabilities["service"] == "OGC WMTS"
    assert capabilities["version"] == "1.0.0"
    assert capabilities["style"] == "default"
    assert capabilities["format"] == "image/png"
    assert capabilities["tile_matrix_set"] == "default028mm"
    assert (
        capabilities["supported_crs"]
        == "urn:ogc:def:crs:EPSG::104905"
    )
    assert capabilities["layer_identifier"] == HIRISE_JEZERO_ID
    assert capabilities["resource_url_template"].endswith(
        "{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"
    )
    matrices = capabilities["tile_matrices"]
    assert len(matrices) == 18
    assert matrices[0]["id"] == "0"
    assert matrices[0]["scale_denominator"] == pytest.approx(
        279227636.29807472
    )
    assert matrices[0]["resolution_degrees"] == pytest.approx(0.703125)
    assert matrices[-1]["id"] == "17"


def test_capabilities_are_independent_per_layer(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v1/mars/layers/{CTX_JEZERO_ID}/capabilities"
    )

    assert response.status_code == 200
    capabilities = response.json()["data"]
    assert capabilities["layer_identifier"] == CTX_JEZERO_ID
    assert len(capabilities["tile_matrices"]) == 14
    assert capabilities["tile_matrices"][-1]["id"] == "13"


def test_capabilities_for_mola_use_jpeg_tiles(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v1/mars/layers/{MOLA_GLOBAL_ID}/capabilities"
    )

    assert response.status_code == 200
    capabilities = response.json()["data"]
    assert capabilities["format"] == "image/jpeg"
    assert capabilities["resource_url_template"].endswith(".jpg")
    assert len(capabilities["tile_matrices"]) == 8
    assert capabilities["tile_matrices"][-1]["id"] == "7"


def test_capabilities_unknown_layer_returns_404(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/mars/layers/missing/capabilities")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Layer 'missing' not found.",
    }


def test_capabilities_without_wmts_returns_404(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/mars/layers/meda-environmental-monitoring/capabilities"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "No WMTS service" in response.json()["error"]["message"]


def test_capabilities_live_upstream_error_returns_502(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(_layer_id: str):
        raise MarsUpstreamError(
            "Unable to retrieve WMTS capabilities from NASA Mars Trek."
        )

    monkeypatch.setattr(
        mars_api._service, "fetch_live_capabilities", fail
    )

    response = client.get(
        f"/api/v1/mars/layers/{HIRISE_JEZERO_ID}/capabilities?live=true"
    )

    assert response.status_code == 502
    assert response.json() == {
        "success": False,
        "error": {
            "code": "upstream_unavailable",
            "message": (
                "Unable to retrieve WMTS capabilities from NASA Mars Trek."
            ),
        },
    }
