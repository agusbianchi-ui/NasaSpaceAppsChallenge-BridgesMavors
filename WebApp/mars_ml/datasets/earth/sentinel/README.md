# Copernicus Sentinel-2

Use the Copernicus Data Space Ecosystem. Access may require a free account.

- Portal: <https://dataspace.copernicus.eu/>
- STAC API used for verification: <https://catalogue.dataspace.copernicus.eu/stac/search>
- Collection: `sentinel-2-l2a` (surface reflectance, Level-2A)
- Documentation: <https://documentation.dataspace.copernicus.eu/>

## Verified query pattern

```json
{
  "collections": ["sentinel-2-l2a"],
  "bbox": [-4.1, 31.0, -3.8, 31.3],
  "datetime": "2019-01-01T00:00:00Z/2019-04-30T23:59:59Z",
  "limit": 20,
  "query": {"eo:cloud_cover": {"lt": 10}}
}
```

Results for 2019, 2021, 2024 and 2025 are recorded in
`../sahara/scene_catalog.json`. The scenes share MGRS tile `30RVV` and the same
April acquisition window, which reduces seasonal illumination differences but
does not eliminate them.

## Processing notes

- The 10 m assets are `B02`, `B03`, `B04` and `B08`.
- Level-2A products include a scene classification layer for cloud and shadow
  masking, but this stage does not download or evaluate it.
- Scene-level `eo:cloud_cover` is not a guarantee of clear conditions over the
  dune window.
- Keep the STAC item URL and retrieval timestamp with every local file.
