"""Verify distributed source samples against the official GeoTIFF using HTTP ranges."""

from pathlib import Path
from urllib.request import Request, urlopen
import io, json, hashlib
import tifffile, rasterio, numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/science"
URL = "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif"


def fetch(start, end):
    with urlopen(
        Request(URL, headers={"Range": f"bytes={start}-{end}"}), timeout=45
    ) as response:
        if response.status != 206:
            raise ValueError("Server did not honor the byte range.")
        data = response.read()
        if len(data) != end - start + 1:
            raise ValueError("Incomplete source range.")
        return data


headpath = CACHE / "hrsc-tiff-header.bin"
if not headpath.exists():
    headpath.write_bytes(fetch(0, 1048575))
head = headpath.read_bytes()
page = tifffile.TiffFile(io.BytesIO(head)).pages[0]
assert (
    page.compression == 1 and page.dtype == np.dtype("int16") and page.rowsperstrip == 1
)
with rasterio.io.MemoryFile(head) as memory:
    with memory.open() as global_dem:
        global_transform = global_dem.transform
checks = []
with rasterio.open(ROOT / "data/raw/ez-hrsc200.tif") as crop:
    row_offset = round((crop.transform.f - global_transform.f) / global_transform.e)
    column_offset = round((crop.transform.c - global_transform.c) / global_transform.a)
    array = crop.read(1)
    for row, column in [(10, 10), (300, 400), (600, 600), (900, 1000), (1200, 1170)]:
        gr, gc = row + row_offset, column + column_offset
        start = page.dataoffsets[gr] + gc * 2
        path = CACHE / f"hrsc-sample-{gr}-{gc}.bin"
        if not path.exists():
            path.write_bytes(fetch(start, start + 1))
        value = int(np.frombuffer(path.read_bytes(), "<i2")[0])
        assert value == int(array[row, column])
        x, y = crop.xy(row, column)
        gx, gy = global_transform * (gc + 0.5, gr + 0.5)
        assert max(abs(x - gx), abs(y - gy)) < 1e-9
        checks.append(
            {
                "crop_row": row,
                "crop_column": column,
                "global_row": gr,
                "global_column": gc,
                "longitude": x,
                "latitude": y,
                "remote_raw_value": value,
                "local_raw_value": int(array[row, column]),
                "byte_start": start,
            }
        )
report = {
    "source_url": URL,
    "checks": checks,
    "result": "all five distributed source pixels and their center coordinates match",
    "scope": "source sample verification, not checksum of global file",
    "header_sha256": hashlib.sha256(head).hexdigest(),
}
(ROOT / "output-stage4/remote-source-check.json").write_text(
    json.dumps(report, indent=2)
)
print(json.dumps(report))
