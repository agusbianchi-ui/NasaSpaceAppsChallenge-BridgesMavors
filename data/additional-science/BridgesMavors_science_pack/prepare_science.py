"""Acquire original scientific products. No RGB-to-science conversion."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
import shutil
import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "science_catalog.json").read_text(encoding="utf-8"))
RAW = ROOT / "raw"
OUT = ROOT / "numeric"

def digest(path, algorithm):
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def acquire(item, directory, expected_bytes=None):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / item["name"]
    def valid(p):
        return p.is_file() and p.stat().st_size > 0 and (
            expected_bytes is None or p.stat().st_size == expected_bytes
        ) and ("md5" not in item or digest(p, "md5") == item["md5"])
    if not valid(path):
        temp = path.with_suffix(path.suffix + ".part")
        try:
            req = urllib.request.Request(item["url"], headers={"User-Agent": "BridgesMavors-science/1.0"})
            with urllib.request.urlopen(req, timeout=90) as response, temp.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            if not valid(temp):
                raise ValueError(f"Unexpected size/checksum: {item['name']}")
            if path.suffix == ".pdf" and temp.open("rb").read(5) != b"%PDF-":
                raise ValueError("Not a PDF")
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    print(f"OK {path.name}: {path.stat().st_size} bytes")
    return path

def validate_label(path, period, mask):
    label = path.read_text(encoding="ascii", errors="strict")
    expected_name = f"GLOBAL_TI_{'MSK_' if mask else ''}{period.upper()}_2007"
    import re
    for key, pattern in {
        "PRODUCT_ID": f'"{expected_name}"',
        "LINES": "3600",
        "LINE_SAMPLES": "7200",
        "SAMPLE_TYPE": "MSB_INTEGER",
        "SAMPLE_BITS": "8" if mask else "16",
        "MAP_RESOLUTION": r"20(?:\.0+)?\s*<pix/deg>",
        "CENTER_LONGITUDE": r"0(?:\.0+)?\s*<deg>",
        "CENTER_LATITUDE": r"0(?:\.0+)?\s*<deg>",
        "WESTERNMOST_LONGITUDE": r"-180(?:\.0+)?\s*<deg>",
        "EASTERNMOST_LONGITUDE": r"180(?:\.0+)?\s*<deg>",
        "LINE_PROJECTION_OFFSET": r"1800\.5",
        "SAMPLE_PROJECTION_OFFSET": r"3600\.5",
        "POSITIVE_LONGITUDE_DIRECTION": '"EAST"',
        "COORDINATE_SYSTEM_NAME": '"PLANETOCENTRIC"',
    }.items():
        if not re.search(r"(?mi)^\s*" + key + r"\s*=\s*" + pattern + r"\s*$", label):
            raise ValueError(f"Unexpected label {key}: {path.name}. Inspect source manually.")
    return label

def prepare_thermal(period):
    dataset = CATALOG["datasets"][0]
    directory = RAW / "thermal"
    items = {f["name"]: f for f in dataset["files"]}
    inputs = {}
    for mask in (False, True):
        stem = f"global_ti_{'msk_' if mask else ''}{period}_2007"
        label = acquire(items[stem+".lbl"], directory)
        validate_label(label, period, mask)
        image = acquire(items[stem+".img"], directory, 3600*7200*(1 if mask else 2))
        inputs[mask] = image

    # Original PDS: spherical Mars radius 3396 km, planetocentric latitude,
    # east longitude, north-up, pixel edges -180..180 and 90..-90.
    # The offsets 1800.5 and 3600.5 are pixel-center based.
    values = np.memmap(inputs[False], dtype=">i2", mode="r", shape=(3600, 7200))
    interp = np.memmap(inputs[True], dtype="i1", mode="r", shape=(3600, 7200))
    OUT.mkdir(exist_ok=True)
    profile = dict(driver="GTiff", height=3600, width=7200, count=1, dtype="int16",
                   crs=rasterio.crs.CRS.from_string("+proj=longlat +R=3396000 +no_defs +type=crs"),
                   transform=from_origin(-180, 90, .05, .05),
                   nodata=-32768, compress="deflate", tiled=True, blockxsize=256, blockysize=256)
    output = OUT / f"tes_thermal_inertia_{period}.tif"
    quality = OUT / f"tes_thermal_inertia_{period}_quality.tif"
    qprofile = dict(profile, dtype="uint8", nodata=255)
    hashes = {p.name: digest(p, "sha256") for p in inputs.values()}
    valid_count = interpolated_count = 0
    with rasterio.open(output, "w", **profile) as dst, rasterio.open(quality, "w", **qprofile) as q:
        dst.set_band_description(1, "TES-derived apparent thermal inertia")
        dst.set_band_unit(1, dataset["unit"])
        dst.update_tags(product_id=dataset["product_id"], period=period,
                        source_url=dataset["source_url"], latitude_convention="planetocentric",
                        longitude_convention="east", observation_period=dataset["observation_period"],
                        source_sha256=json.dumps(hashes), quality_file=quality.name)
        q.set_band_description(1, "Quality: 1 not infilled, 0 interpolated, 255 invalid")
        for _, window in dst.block_windows(1):
            r,c,h,w = map(int,(window.row_off,window.col_off,window.height,window.width))
            raw = np.asarray(values[r:r+h,c:c+w],dtype=np.int16)
            flag = interp[r:r+h,c:c+w]
            ok = (raw >= 5) & (raw <= 5000)
            out = np.where(ok,raw,-32768).astype(np.int16)
            qual = np.where(ok, np.where(flag==0,0,1),255).astype(np.uint8)
            dst.write(out,1,window=window)
            q.write(qual,1,window=window)
            valid_count += int(ok.sum())
            interpolated_count += int((ok & (flag==0)).sum())
    with rasterio.open(output) as ds, rasterio.open(quality) as qs:
        assert ds.shape == (3600,7200) and ds.transform == qs.transform
        assert ds.crs == qs.crs and ds.count == 1
        for r,c in ((0,0),(1800,3600),(900,1800),(3599,7199)):
            raw = int(values[r,c])
            sample = int(ds.read(1, window=rasterio.windows.Window(c,r,1,1))[0,0])
            assert sample == (raw if 5 <= raw <= 5000 else -32768)
    print(json.dumps({"output":str(output),"valid_cells":valid_count,
                      "interpolated_valid_cells":interpolated_count},indent=2))

def prepare_roughness():
    dataset = CATALOG["datasets"][1]
    for item in dataset["files"]:
        acquire(item, RAW / "roughness")
    print("Original raw files verified by author MD5. Read _read_me.pdf and implement its")
    print("documented decoding, units, scale, NoData and projection before use. No numeric")
    print("GeoTIFF is generated automatically for this dataset.")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--thermal", choices=["day","night","both"])
    parser.add_argument("--roughness", action="store_true")
    args=parser.parse_args()
    if not args.thermal and not args.roughness:
        parser.error("Select --thermal night/day/both and/or --roughness")
    if args.thermal:
        for p in (["day","night"] if args.thermal=="both" else [args.thermal]):
            prepare_thermal(p)
    if args.roughness:
        prepare_roughness()
