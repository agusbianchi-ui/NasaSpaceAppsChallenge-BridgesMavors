import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from app.services import tes_thermal as tes


def test_quality_nodata_and_antimeridian(tmp_path, monkeypatch):
    monkeypatch.setattr(tes, 'ROOT', tmp_path)
    out = tmp_path / 'numeric'
    out.mkdir()
    profile = dict(driver='GTiff', width=4, height=2, count=1, dtype='int16',
                   transform=from_origin(-180,90,90,90), crs='+proj=longlat +R=3396000', nodata=-32768)
    with rasterio.open(out/'tes_thermal_inertia_day.tif','w',**profile) as ds:
        ds.write(np.array([[100,200,-32768,400],[100,200,300,400]],dtype='int16'),1)
    with rasterio.open(out/'tes_thermal_inertia_day_quality.tif','w',**{**profile,'dtype':'uint8','nodata':255}) as ds:
        ds.write(np.array([[1,0,255,1],[1,1,1,1]],dtype='uint8'),1)
    assert tes.thermal_at(45,-180,'day')['value'] == 100
    assert tes.thermal_at(45,180,'day')['value'] == 100
    assert tes.thermal_at(45,-45,'day')['reason'] == 'interpolated_cell_excluded'
    assert tes.thermal_at(45,-45,'day',True)['value'] == 200
    assert tes.thermal_at(45,45,'day')['value'] is None
    with pytest.raises(ValueError): tes.thermal_at(float('nan'),0)


def test_actual_tes_samples_match_originals():
    from app.services.terrain_science import TerrainScienceService
    service = TerrainScienceService()
    for x,z in [(24875,-55625),(8375,-20625),(-50000,0)]:
        result = service.point(x,z)
        for period in ['day','night']:
            datum = result['variables'][f'thermal_inertia_{period}']
            assert datum['classification'] == 'Derived'
            cell=datum['sample']['cell']; r,c=cell['row'],cell['column']
            raw=np.memmap(tes.ROOT/'raw/thermal'/f'global_ti_{period}_2007.img',dtype='>i2',shape=(3600,7200),mode='r')
            mask=np.memmap(tes.ROOT/'raw/thermal'/f'global_ti_msk_{period}_2007.img',dtype='i1',shape=(3600,7200),mode='r')
            assert datum['value'] == int(raw[r,c])
            assert mask[r,c] != 0
