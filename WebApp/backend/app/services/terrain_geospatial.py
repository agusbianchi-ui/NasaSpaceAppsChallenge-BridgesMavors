"""Mars-only coordinate and DEM calculations, independent of HTTP and visualization."""

import math
import numpy as np
from pyproj import CRS, Transformer, Geod

RADIUS = 3396190.0
GEOGRAPHIC = CRS.from_proj4(f"+proj=longlat +R={RADIUS} +no_defs")
PROJECTED = CRS.from_proj4(
    f"+proj=aeqd +lat_0=17.5 +lon_0=77 +R={RADIUS} +units=m +no_defs"
)
TO_GEO = Transformer.from_crs(PROJECTED, GEOGRAPHIC, always_xy=True)
TO_MODEL = Transformer.from_crs(GEOGRAPHIC, PROJECTED, always_xy=True)
GEOD = Geod(a=RADIUS, b=RADIUS)


def model_to_geographic(x, y, z):
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ValueError("Coordinates must be finite.")
    longitude, latitude = TO_GEO.transform(x, -z)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "elevation": y / 3 - 4500,
        "elevation_meaning": "inverse visual transform; quantized elevation, not the unquantized DEM sample",
    }


def geographic_to_model(latitude, longitude, elevation):
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


def model_to_grid(x, z, metadata):
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


def cell_coordinates(metadata):
    x = (
        metadata["originX"]
        + (np.arange(metadata["columns"]) + 0.5) * metadata["cellSize"]
    )
    z = metadata["originZ"] + (np.arange(metadata["rows"]) + 0.5) * metadata["cellSize"]
    xx, zz = np.meshgrid(x, z)
    return TO_GEO.transform(xx, -zz)


def topographic_metrics(height, longitude, latitude):
    """Fit eight neighbor height differences in geodesic east/north coordinates.

    The plane passes through the central sample. All nine DEM samples required.
    Aspect is downhill clockwise from true north; flat aspect is undefined.
    Roughness is RMS residual of this plane over the nine samples, not soil stability.
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
            east = distance * np.sin(np.radians(az))
            north = distance * np.cos(np.radians(az))
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


def intercell_slope(a, b):
    """a,b = (longitude, latitude, scientific elevation metres)."""
    distance = GEOD.inv(a[0], a[1], b[0], b[1])[2]
    return (
        math.degrees(math.atan2(abs(b[2] - a[2]), distance)) if distance > 0 else None
    )
