"""Sample verified numeric products; call from the existing backend.
Coordinates MUST already be planetocentric and east-positive.
No local-model-to-geographic conversion is attempted here.
"""
from pathlib import Path
import argparse
import json
import math
import rasterio
from rasterio.windows import Window

ROOT=Path(__file__).resolve().parents[4]/"data/additional-science/BridgesMavors_science_pack"
def thermal_at(lat, lon, period="night", allow_interpolated=False):
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 < lat <= 90:
        raise ValueError("Expected finite planetocentric latitude in (-90,90] and east longitude")
    if period not in ("day","night"):
        raise ValueError("period must be day or night")
    lon=(lon+180)%360-180
    path=ROOT/"numeric"/f"tes_thermal_inertia_{period}.tif"
    qpath=ROOT/"numeric"/f"tes_thermal_inertia_{period}_quality.tif"
    result={"value":None,"unit":"J m^-2 K^-1 s^-1/2",
            "source":"MGS-M-TES-5-TIMAP-V1.0",
            "source_url":"https://pds-geosciences.wustl.edu/missions/mgs/tes-timap.html",
            "resolution_degrees":0.05,"resolution_equator_km":2.96,
            "observation_period":"1999-02 to 2004-04",
            "kind":"derived","period":period,"status":"unavailable"}
    if not path.exists() or not qpath.exists():
        return dict(result,reason="numeric_product_missing")
    with rasterio.open(path) as ds, rasterio.open(qpath) as qs:
        if ds.count!=1 or ds.transform!=qs.transform or ds.shape!=qs.shape or ds.crs!=qs.crs:
            raise ValueError("Raster/quality mismatch")
        r,c=ds.index(lon,lat)
        if not (0<=r<ds.height and 0<=c<ds.width):
            return dict(result,reason="outside_coverage")
        win=Window(c,r,1,1)
        value=ds.read(1,window=win,masked=True)[0,0]
        flag=int(qs.read(1,window=win)[0,0])
        center_lon,center_lat=ds.xy(r,c)
        result.update(cell={"row":r,"column":c,"latitude":center_lat,"longitude_east":center_lon},
                      interpolated=(flag==0))
        if flag==255 or np_masked(value):
            return dict(result,reason="nodata")
        if flag==0 and not allow_interpolated:
            return dict(result,reason="interpolated_cell_excluded")
        if flag not in (0,1) or not 5<=float(value)<=5000:
            return dict(result,reason="invalid_value_or_quality")
        return dict(result,value=float(value),status="available",kind="estimated" if flag==0 else "derived")
def np_masked(value):
    import numpy as np
    return bool(np.ma.is_masked(value))
def inspect_point(lat,lon,allow_interpolated=False):
    return {"thermal_inertia_night":thermal_at(lat,lon,"night",allow_interpolated),
            "thermal_inertia_day":thermal_at(lat,lon,"day",allow_interpolated),
            "mola_roughness":{"value":None,"status":"unavailable","reason":"raw_product_not_decoded_and_validated"},
            "surface_dust":{"value":None,"status":"unavailable","reason":"numeric_product_not_validated"}}
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("latitude",type=float)
    parser.add_argument("longitude_east",type=float)
    parser.add_argument("--allow-interpolated",action="store_true")
    a=parser.parse_args()
    print(json.dumps(inspect_point(a.latitude,a.longitude_east,a.allow_interpolated),indent=2,allow_nan=False))
