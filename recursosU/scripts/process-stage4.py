"""Recover source identity and scientific elevations; never modify original models."""

from pathlib import Path
import json, hashlib, sys, importlib.util
import numpy as np, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops_mars-main/backend"))
spec = importlib.util.spec_from_file_location(
    "terrain_geospatial",
    ROOT / "ops_mars-main/backend/app/services/terrain_geospatial.py",
)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)
PROJECTED, TO_MODEL, TO_GEO, GEOD = geo.PROJECTED, geo.TO_MODEL, geo.TO_GEO, geo.GEOD
cell_coordinates, topographic_metrics = geo.cell_coordinates, geo.topographic_metrics
model_to_geographic, geographic_to_model = (
    geo.model_to_geographic,
    geo.geographic_to_model,
)
OUT = ROOT / "output-stage4"
OUT.mkdir(exist_ok=True)


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    visual_meta = json.loads((ROOT / "output-stage3/terrain_metadata.json").read_text())
    if sha(ROOT / "MapaMarteN.glb") != visual_meta["source_sha256"]:
        raise ValueError("Original changed; revalidate before processing.")
    visual = np.fromfile(ROOT / "output-stage3/visual_elevation.bin", "<f4").reshape(
        visual_meta["rows"], visual_meta["columns"]
    )
    prior = json.loads((ROOT / "output-visual/metadata.json").read_text())
    raw = ROOT / "data/raw/ez-hrsc200.tif"
    if sha(raw) != prior["sha256"]:
        raise ValueError("Historical source hash mismatch.")
    with rasterio.open(raw) as source:
        source_info = {
            "wkt": source.crs.to_wkt(),
            "transform": list(source.transform)[:6],
            "shape": list(source.shape),
            "nodata": source.nodata,
            "scale": source.scales[0],
            "offset": source.offsets[0],
            "bounds": list(source.bounds),
        }
        rebuilt = np.full((1024, 1024), np.nan, "f4")
        affine = from_origin(-128000, 128000, 250, 250)
        reproject(
            rasterio.band(source, 1),
            rebuilt,
            src_transform=source.transform,
            src_crs=source.crs,
            dst_transform=affine,
            dst_crs=PROJECTED,
            src_nodata=source.nodata,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    boundary = json.loads((ROOT / "data/raw/ez-layer4.json").read_text())["features"][0]
    rings = [
        [TO_MODEL.transform(*point) for point in ring]
        for ring in boundary["geometry"]["rings"]
    ]
    mask = geometry_mask(
        [{"type": "Polygon", "coordinates": rings}],
        out_shape=rebuilt.shape,
        transform=affine,
        invert=True,
    ) & np.isfinite(rebuilt)
    rebuilt[~mask] = np.nan
    with rasterio.open(ROOT / "output-visual/ez-dem.tif") as historic:
        old = historic.read(1)
    assert np.array_equal(np.isfinite(old), mask)
    reprojection_error = float(np.nanmax(abs(rebuilt - old)))
    assert reprojection_error < 1e-5
    row0 = round((visual_meta["originZ"] + 128000) / 250)
    col0 = round((visual_meta["originX"] + 128000) / 250)
    scientific = rebuilt[
        row0 : row0 + visual.shape[0], col0 : col0 + visual.shape[1]
    ].copy()
    assert np.array_equal(np.isfinite(scientific), np.isfinite(visual))
    expected = 3 * (np.round(scientific / 2) * 2 + 4500)
    error = float(np.nanmax(abs(expected - visual)))
    assert error == 0
    scientific.astype("<f4").tofile(OUT / "scientific_elevation.bin")
    visual.astype("<f4").tofile(OUT / "visual_elevation.bin")
    np.isfinite(scientific).astype("u1").tofile(OUT / "valid_mask.bin")
    lon, lat = cell_coordinates(visual_meta)
    metrics = topographic_metrics(scientific, lon, lat)
    for name, array in metrics.items():
        array.tofile(OUT / f"{name}.bin")
    profile = {
        "driver": "GTiff",
        "width": visual.shape[1],
        "height": visual.shape[0],
        "count": 1,
        "dtype": "float32",
        "crs": PROJECTED,
        "transform": from_origin(
            visual_meta["originX"], -visual_meta["originZ"], 250, 250
        ),
        "nodata": np.nan,
        "compress": "deflate",
    }
    with rasterio.open(OUT / "scientific_elevation.tif", "w", **profile) as destination:
        destination.write(scientific, 1)
    controls = []
    for oldrow, oldcol in [(512, 512), (400, 400), (650, 650), (350, 600), (600, 350)]:
        row, col = oldrow - row0, oldcol - col0
        x = visual_meta["originX"] + (col + 0.5) * 250
        z = visual_meta["originZ"] + (row + 0.5) * 250
        geographic = model_to_geographic(x, float(visual[row, col]), z)
        inverse = geographic_to_model(
            geographic["latitude"], geographic["longitude"], geographic["elevation"]
        )
        controls.append(
            {
                "row": row,
                "column": col,
                "x": x,
                "z": z,
                "visual_y": float(visual[row, col]),
                "scientific_elevation": float(scientific[row, col]),
                "longitude": geographic["longitude"],
                "latitude": geographic["latitude"],
                "roundtrip_error_model_units": max(
                    abs(inverse["x"] - x), abs(inverse["z"] - z)
                ),
            }
        )
    finite = np.isfinite(scientific)
    dist = GEOD.inv(lon[:, :-1], lat[:, :-1], lon[:, 1:], lat[:, 1:])[2]
    pair = finite[:, :-1] & finite[:, 1:]
    metadata = {
        **visual_meta,
        "stage": 4,
        "georeference_verified": True,
        "classification": "Registered visual/scientific bundle; variable classifications are separate",
        "verticalScale": "Visual exaggeration 3x with -4500 m reference and 2 m quantization; scientific grid unexaggerated",
        "georeference_scope": "complete geometry and mask match to georeferenced source pipeline; not independent surveyed positional accuracy",
        "crs_wkt": PROJECTED.to_wkt(),
        "radius_m": 3396190,
        "latitude_type": "planetocentric",
        "longitude_direction": "positive east",
        "longitude_domain": [-180, 180],
        "region": "NASA EMC Jezero Crater EZ buffer FID27 and surrounding terrain; region is not only Jezero crater",
        "projection_center": [77, 17.5],
        "axes": "X east, Y visual up, Z south",
        "horizontal_unit": "metre",
        "horizontal_scale": 1,
        "rotation_degrees": 0,
        "visual_transform": {
            "formula": "Y=3*(round(h/2)*2+4500)",
            "vertical_exaggeration": 3,
            "reference_elevation_m": -4500,
            "quantization_m": 2,
            "inverse_unquantized_formula": "h=Y/3-4500",
            "inverse_limitation": "recovers quantized h only, ±1 m relative to processed DEM",
        },
        "vertical_reference": "HRSC/MOLA blended product elevations preserved; exact areoid realization not identified in retrieved labels; not ellipsoidal height",
        "scientific_elevation_unit": "m",
        "source_id": "hrsc-mola-v2",
        "source_info": source_info,
        "source_resolution": {
            "nominal_m": 200,
            "degrees": source_info["transform"][0],
            "effective": "blend of differing source resolutions; not uniformly 200 m measured detail",
        },
        "scientific_grid_method": "bilinear source reprojection, no exaggeration, mask by official polygon cell centers",
        "historical_grid_offset": [row0, col0],
        "coverage_lon_lat": [
            float(lon[finite].min()),
            float(lat[finite].min()),
            float(lon[finite].max()),
            float(lat[finite].max()),
        ],
        "gradient_method": "3x3 plane through central elevation; 8 neighbor geodesic east/north offsets on Mars sphere; requires all nine valid",
        "roughness_method": "RMS plane residual across 9 samples, not mechanical stability",
        "local_relief_method": "maximum minus minimum in 3x3; all samples required",
        "aspect_method": "downhill clockwise from geographic north; null for flat/invalid",
        "geodesic_adjacent_x_distance_m": [
            float(dist[pair].min()),
            float(dist[pair].max()),
        ],
    }
    for path in OUT.glob("*.bin"):
        metadata[path.name] = {
            "bytes": path.stat().st_size,
            "sha256": sha(path),
            "dtype": "uint8"
            if path.name == "valid_mask.bin"
            else "float32 little-endian",
        }
    lineage_paths = [
        "MapaMarteN.glb",
        "MapaMarte1.blend",
        "data/raw/ez-hrsc200.tif",
        "data/raw/ez-viking.tif",
        "data/raw/ez-layer4.json",
        "output-visual/ez-dem.tif",
        "output-visual/elevation.f32",
        "output-visual/metadata.json",
        "scripts/build_visual.py",
        "scripts/download_visual.py",
        "scripts/extract-stage3.py",
    ]
    metadata["lineage"] = [
        {"file": p, "sha256": sha(ROOT / p), "bytes": (ROOT / p).stat().st_size}
        for p in lineage_paths
    ]
    report = {
        "all_top_cells_compared": int(finite.sum()),
        "max_visual_difference": error,
        "max_rebuilt_dem_difference_m": reprojection_error,
        "control_points": controls,
        "control_type": "source grid checkpoints plus published projection center; no independent ground survey",
        "projection_center_check": TO_GEO.transform(0, 0),
        "quantization_max_error_m": float(
            np.nanmax(abs(visual / 3 - 4500 - scientific))
        ),
        "source_pixels_remote_check": "see remote-source-check.json",
    }
    (OUT / "terrain_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf8"
    )
    (OUT / "georeference-validation.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
