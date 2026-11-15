from datetime import datetime, timezone
from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings
from app.schemas.mars import (
    DataProvenance,
    MarsDataSource,
    MarsLayer,
    MarsLocation,
    SpatialReference,
    WMTSCapabilities,
)
from app.services.mars_wmts import (
    CTX_JEZERO_ID,
    CTX_JEZERO_PRELIM_ID,
    HIRISE_JEZERO_ID,
    MARS_EQUIRECTANGULAR_CRS,
    MARS_PROJECTION_CODE,
    MOLA_GLOBAL_ID,
    WMTSParseError,
    WMTS_VERIFIED_AT,
    build_verified_capabilities,
    parse_wmts_capabilities,
)

CATALOG_LIMITATION = (
    "Catalog reference only. Nominal resolution is representative; coverage, "
    "processing level and projection vary by product. Verify with the official "
    "source before scientific use."
)

VERIFIED_TILE_ACCESS_NOTE = (
    "GetCapabilities and sample tiles were retrieved from NASA Mars Trek on "
    f"{WMTS_VERIFIED_AT}. The tile endpoint returned image/png with "
    "Access-Control-Allow-Origin: *, so the browser can request tiles directly."
)

MARS_SPATIAL_REFERENCE = SpatialReference(
    code=MARS_PROJECTION_CODE,
    name="Mars 2000 Sphere / Equirectangular",
    units="degrees",
    extent=[-180.0, -90.0, 180.0, 90.0],
    notes=(
        f"WMTS SupportedCRS {MARS_EQUIRECTANGULAR_CRS}. Mars equirectangular "
        "degrees; this is not Earth WGS84."
    ),
)

_MARS_TREK_URL = "https://trek.nasa.gov/mars/"
_PDS_URL = "https://pds.nasa.gov/"
_MOLA_URL = "https://pds-geosciences.wustl.edu/missions/mgs/mola.html"
_MEDA_URL = (
    "https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?"
    "identifier=urn:nasa:pds:mars2020_meda&version=1.0"
)
_ASU_MARS_DATA_URL = "https://mars.asu.edu/data/"

_SOURCES: tuple[MarsDataSource, ...] = (
    MarsDataSource(
        id="nasa-mars-2020",
        name="NASA Mars 2020 Perseverance",
        agency="NASA",
        mission="Mars 2020",
        description=(
            "Mission that delivered the Perseverance rover to Jezero Crater; "
            "provides landing-site and mission context, including MEDA "
            "environmental measurements at the rover location."
        ),
        url="https://mars.nasa.gov/mars2020/",
        layer_ids=["meda-environmental-monitoring"],
    ),
    MarsDataSource(
        id="nasa-mro",
        name="NASA Mars Reconnaissance Orbiter",
        agency="NASA",
        mission="Mars Reconnaissance Orbiter",
        description=(
            "Orbiter carrying HiRISE, CTX and CRISM; supports high-resolution "
            "imaging and mineral mapping."
        ),
        url="https://mars.nasa.gov/mro/",
        layer_ids=[
            "hirise-imagery",
            "ctx-imagery",
            "crism-mineral-maps",
            HIRISE_JEZERO_ID,
            CTX_JEZERO_ID,
            CTX_JEZERO_PRELIM_ID,
        ],
    ),
    MarsDataSource(
        id="nasa-mars-odyssey",
        name="NASA Mars Odyssey",
        agency="NASA",
        mission="Mars Odyssey",
        description=(
            "Orbiter carrying THEMIS; provides thermal infrared observations "
            "of Mars."
        ),
        url="https://mars.nasa.gov/odyssey/",
        layer_ids=["themis-thermal"],
    ),
    MarsDataSource(
        id="nasa-mgs",
        name="NASA Mars Global Surveyor",
        agency="NASA",
        mission="Mars Global Surveyor",
        description=(
            "Orbiter that carried MOLA; provided global elevation and "
            "topography data."
        ),
        url="https://mars.nasa.gov/mgs/",
        layer_ids=["mola-elevation", MOLA_GLOBAL_ID],
    ),
    MarsDataSource(
        id="nasa-pds",
        name="NASA Planetary Data System",
        agency="NASA",
        mission="Multi-mission archive",
        description=(
            "Long-term archive for NASA planetary science data products, "
            "including calibrated MEDA products and MOLA topography."
        ),
        url=_PDS_URL,
    ),
    MarsDataSource(
        id="nasa-mars-trek",
        name="NASA Mars Trek",
        agency="NASA",
        mission="Visualization portal",
        description=(
            "Visualization portal and WMTS tile service for verified Mars "
            "orbital mosaics, including the Jezero Crater products used by "
            "MARS OPS."
        ),
        url=_MARS_TREK_URL,
        layer_ids=[
            HIRISE_JEZERO_ID,
            CTX_JEZERO_ID,
            MOLA_GLOBAL_ID,
            CTX_JEZERO_PRELIM_ID,
        ],
    ),
)

_LAYERS: tuple[MarsLayer, ...] = (
    MarsLayer(
        id="hirise-imagery",
        name="HiRISE High-Resolution Imagery",
        source="nasa-mro",
        mission="Mars Reconnaissance Orbiter",
        instrument="HiRISE",
        description=(
            "Generic catalog reference for visible imaging from the High "
            "Resolution Imaging Science Experiment on Mars Reconnaissance "
            "Orbiter. Use the verified Jezero product for map display."
        ),
        data_type="Visible imagery",
        region="Mars (targeted)",
        resolution=0.25,
        resolution_unit="m/pixel",
        source_url="https://mars.nasa.gov/mro/",
        attribution="NASA/JPL-Caltech/University of Arizona",
        status="catalog_only",
        limitations=CATALOG_LIMITATION,
    ),
    MarsLayer(
        id="ctx-imagery",
        name="CTX Context Imagery",
        source="nasa-mro",
        mission="Mars Reconnaissance Orbiter",
        instrument="CTX",
        description=(
            "Generic catalog reference for regional visible imagery from the "
            "Context Camera on Mars Reconnaissance Orbiter. Use the verified "
            "Jezero product for map display."
        ),
        data_type="Visible imagery",
        region="Mars (targeted)",
        resolution=6.0,
        resolution_unit="m/pixel",
        source_url="https://mars.nasa.gov/mro/",
        attribution="NASA/JPL-Caltech/MSSS",
        status="catalog_only",
        limitations=CATALOG_LIMITATION,
    ),
    MarsLayer(
        id="crism-mineral-maps",
        name="CRISM Mineral Maps",
        source="nasa-mro",
        mission="Mars Reconnaissance Orbiter",
        instrument="CRISM",
        description=(
            "Visible-infrared spectral observations from the Compact "
            "Reconnaissance Imaging Spectrometer for Mars."
        ),
        data_type="Spectral / mineralogy",
        region="Mars (targeted)",
        resolution=18.0,
        resolution_unit="m/pixel",
        source_url="https://mars.nasa.gov/mro/",
        attribution="NASA/JHUAPL",
        status="catalog_only",
        limitations=(
            "Catalog reference only. Targeted observations are about 18 "
            "m/pixel; mapping-mode coverage is coarser (about 200 m/pixel). "
            "No mineral map is currently integrated."
        ),
    ),
    MarsLayer(
        id="themis-thermal",
        name="THEMIS Thermal Infrared",
        source="nasa-mars-odyssey",
        mission="Mars Odyssey",
        instrument="THEMIS",
        description=(
            "Thermal infrared observations from the Thermal Emission Imaging "
            "System on Mars Odyssey."
        ),
        data_type="Thermal infrared imagery",
        region="Mars (global / targeted)",
        resolution=100.0,
        resolution_unit="m/pixel",
        source_url=_ASU_MARS_DATA_URL,
        attribution="NASA/JPL-Caltech/Arizona State University",
        status="catalog_only",
        limitations=(
            "Catalog reference only. Thermal mosaics and derived products are "
            "not downloaded or processed in this stage."
        ),
    ),
    MarsLayer(
        id="mola-elevation",
        name="MOLA Elevation",
        source="nasa-mgs",
        mission="Mars Global Surveyor",
        instrument="MOLA",
        description=(
            "Global elevation and topography from the Mars Orbiter Laser "
            "Altimeter on Mars Global Surveyor."
        ),
        data_type="Elevation / topography",
        region="Mars (global)",
        resolution=463.0,
        resolution_unit="m/pixel",
        source_url=_MOLA_URL,
        attribution="NASA/MOLA Science Team",
        status="catalog_only",
        limitations=(
            "Catalog reference only. Global topography is not downloaded or "
            "reprojected in this stage."
        ),
    ),
    MarsLayer(
        id="meda-environmental-monitoring",
        name="MEDA Environmental Monitoring",
        source="nasa-mars-2020",
        mission="Mars 2020",
        instrument="MEDA",
        description=(
            "Environmental measurements acquired by the Mars Environmental "
            "Dynamics Analyzer on the Perseverance rover at its operational "
            "location in Jezero Crater."
        ),
        data_type="In-situ environmental measurements (not a map)",
        region="Perseverance operational location, Jezero Crater, Mars",
        resolution=None,
        resolution_unit=None,
        source_url=_MEDA_URL,
        attribution="NASA/JPL-Caltech/CSIC-INTA",
        status="planned",
        limitations=(
            "MEDA is a point-measurement instrument at the rover location, "
            "not a global map. Calibrated PDS products are not yet downloaded, "
            "parsed or displayed. No current temperature, pressure, wind or "
            "radiation values are represented."
        ),
    ),
    MarsLayer(
        id=HIRISE_JEZERO_ID,
        name="MRO HiRISE, Jezero Mosaic, Controlled",
        source="nasa-mro",
        mission="Mars Reconnaissance Orbiter",
        instrument="HiRISE",
        description=(
            "High-resolution visible orthomosaic of Jezero Crater generated "
            "from HiRISE images and delivered through NASA Mars Trek as a WMTS "
            "layer. The product was produced by the USGS Astrogeology Science "
            "Center in support of the Mars 2020 terrain-relative navigation "
            "basemap."
        ),
        data_type="Visible optical imagery (orthomosaic)",
        region="Jezero Crater, Mars",
        resolution=0.25,
        resolution_unit="m/pixel",
        projection=(
            f"{MARS_PROJECTION_CODE} (Mars equirectangular, degrees)"
        ),
        bounding_box=[
            77.2229331,
            18.3067994,
            77.583964,
            18.669315,
        ],
        source_url=(
            "https://trek.nasa.gov/tiles/Mars/EQ/"
            f"{HIRISE_JEZERO_ID}/1.0.0/WMTSCapabilities.xml"
        ),
        acquisition_date=None,
        processing_level=(
            "Orthomosaic; controlled product (Mars 2020 terrain-relative "
            "navigation basemap)."
        ),
        limitations=(
            "The product label states 25 cm/pixel. Mars Trek catalog metadata "
            "lists data_created_date 2020-08-03 as the product creation date, "
            "not the acquisition date of every contributing HiRISE image; "
            "per-image acquisition dates are not exposed by this layer. "
            "Bounding box order is west, south, east, north in degrees. "
            "Verify the PDS product before scientific use."
        ),
        attribution=(
            "NASA/JPL-Caltech/University of Arizona · USGS Astrogeology "
            "Science Center · NASA Mars Trek"
        ),
        status="available",
        visualizable=True,
        spatial_reference=MARS_SPATIAL_REFERENCE,
        provenance=DataProvenance(
            provider="NASA Mars Trek (NASA/JPL)",
            source_url=_MARS_TREK_URL,
            citation=(
                "MRO HiRISE, Jezero Mosaic, Controlled "
                f"({HIRISE_JEZERO_ID}). NASA Mars Trek."
            ),
            attribution=(
                "NASA/JPL-Caltech/University of Arizona · USGS Astrogeology "
                "Science Center"
            ),
            verified=True,
            verified_at=WMTS_VERIFIED_AT,
            verification_notes=VERIFIED_TILE_ACCESS_NOTE,
            product_created_date="2020-08-03",
        ),
        wmts=build_verified_capabilities(HIRISE_JEZERO_ID),
    ),
    MarsLayer(
        id=CTX_JEZERO_ID,
        name="MRO CTX, Jezero Mosaic, Controlled",
        source="nasa-mro",
        mission="Mars Reconnaissance Orbiter",
        instrument="CTX",
        description=(
            "Visible orthomosaic of Jezero Crater generated from Context "
            "Camera images and delivered through NASA Mars Trek as a WMTS "
            "layer. The product is the Lander Vision System map built by the "
            "USGS Astrogeology Science Center for Mars 2020."
        ),
        data_type="Visible optical imagery (orthomosaic)",
        region="Jezero Crater, Mars",
        resolution=6.0,
        resolution_unit="m/pixel",
        projection=(
            f"{MARS_PROJECTION_CODE} (Mars equirectangular, degrees)"
        ),
        bounding_box=[
            77.1604655,
            18.2110274,
            77.6991776,
            18.7211945,
        ],
        source_url=(
            "https://trek.nasa.gov/tiles/Mars/EQ/"
            f"{CTX_JEZERO_ID}/1.0.0/WMTSCapabilities.xml"
        ),
        acquisition_date=None,
        processing_level=(
            "Orthomosaic; controlled product (Lander Vision System map)."
        ),
        limitations=(
            "The mosaic is sampled at approximately 6 m/pixel. Mars Trek "
            "catalog metadata lists data_created_date 2020-08-03 as the "
            "product creation date, not the acquisition date of every "
            "contributing CTX image. Bounding box order is west, south, east, "
            "north in degrees. Verify the PDS product before scientific use."
        ),
        attribution=(
            "NASA/JPL-Caltech/MSSS · USGS Astrogeology Science Center · "
            "NASA Mars Trek"
        ),
        status="available",
        visualizable=True,
        spatial_reference=MARS_SPATIAL_REFERENCE,
        provenance=DataProvenance(
            provider="NASA Mars Trek (NASA/JPL)",
            source_url=_MARS_TREK_URL,
            citation=(
                "MRO CTX, Jezero Mosaic, Controlled "
                f"({CTX_JEZERO_ID}). NASA Mars Trek."
            ),
            attribution=(
                "NASA/JPL-Caltech/MSSS · USGS Astrogeology Science Center"
            ),
            verified=True,
            verified_at=WMTS_VERIFIED_AT,
            verification_notes=VERIFIED_TILE_ACCESS_NOTE,
            product_created_date="2020-08-03",
        ),
        wmts=build_verified_capabilities(CTX_JEZERO_ID),
    ),
    MarsLayer(
        id=MOLA_GLOBAL_ID,
        name="MGS MOLA Color Shade, Global",
        source="nasa-mgs",
        mission="Mars Global Surveyor",
        instrument="MOLA",
        description=(
            "Global color-shaded relief mosaic derived from Mars Orbiter Laser "
            "Altimeter topography and delivered through NASA Mars Trek as a "
            "WMTS layer."
        ),
        data_type="Elevation / shaded relief",
        region="Mars (global)",
        resolution=463.0,
        resolution_unit="m/pixel",
        projection=(
            f"{MARS_PROJECTION_CODE} (Mars equirectangular, degrees)"
        ),
        bounding_box=[
            -180.0,
            -89.9991635,
            179.9983271,
            90.0,
        ],
        source_url=(
            "https://trek.nasa.gov/tiles/Mars/EQ/"
            f"{MOLA_GLOBAL_ID}/1.0.0/WMTSCapabilities.xml"
        ),
        acquisition_date=None,
        processing_level=(
            "Global color-shaded relief mosaic; the WMTS layer uses JPEG tiles."
        ),
        limitations=(
            "The layer identifier and Mars Trek product name indicate a "
            "463 m/pixel global mosaic. The WMTS document does not expose "
            "acquisition dates or per-pixel provenance. This is a visualization "
            "product, not a rover traverse surface model; verify the PDS "
            "topography product before scientific use."
        ),
        attribution="NASA/MOLA Science Team · NASA Mars Trek",
        status="available",
        visualizable=True,
        spatial_reference=MARS_SPATIAL_REFERENCE,
        provenance=DataProvenance(
            provider="NASA Mars Trek (NASA/JPL)",
            source_url=_MARS_TREK_URL,
            citation=(
                f"MGS MOLA Color Shade, Global ({MOLA_GLOBAL_ID}). "
                "NASA Mars Trek."
            ),
            attribution="NASA/MOLA Science Team",
            verified=True,
            verified_at=WMTS_VERIFIED_AT,
            verification_notes=VERIFIED_TILE_ACCESS_NOTE,
        ),
        wmts=build_verified_capabilities(MOLA_GLOBAL_ID),
    ),
    MarsLayer(
        id=CTX_JEZERO_PRELIM_ID,
        name="MRO CTX, Jezero Preliminary Mosaic",
        source="nasa-mro",
        mission="Mars Reconnaissance Orbiter",
        instrument="CTX",
        description=(
            "Preliminary block-adjusted CTX mosaic covering the broader Jezero "
            "region and delivered through NASA Mars Trek as a WMTS layer."
        ),
        data_type="Visible optical imagery (orthomosaic)",
        region="Jezero region, Mars",
        resolution=None,
        resolution_unit=None,
        projection=(
            f"{MARS_PROJECTION_CODE} (Mars equirectangular, degrees)"
        ),
        bounding_box=[
            75.1537692,
            15.9058484,
            78.8717121,
            19.4453003,
        ],
        source_url=(
            "https://trek.nasa.gov/tiles/Mars/EQ/"
            f"{CTX_JEZERO_PRELIM_ID}/1.0.0/WMTSCapabilities.xml"
        ),
        acquisition_date=None,
        processing_level=(
            "Preliminary block-adjusted CTX mosaic; not the controlled Mars "
            "2020 Lander Vision System product."
        ),
        limitations=(
            "The WMTS document does not state a per-pixel resolution or "
            "acquisition dates for this preliminary mosaic. Its footprint is "
            "larger than the controlled Jezero CTX product. Verify the "
            "underlying PDS products before scientific use."
        ),
        attribution="NASA/JPL-Caltech/MSSS · NASA Mars Trek",
        status="available",
        visualizable=True,
        spatial_reference=MARS_SPATIAL_REFERENCE,
        provenance=DataProvenance(
            provider="NASA Mars Trek (NASA/JPL)",
            source_url=_MARS_TREK_URL,
            citation=(
                f"MRO CTX, Jezero Preliminary Mosaic ({CTX_JEZERO_PRELIM_ID}). "
                "NASA Mars Trek."
            ),
            attribution="NASA/JPL-Caltech/MSSS",
            verified=True,
            verified_at=WMTS_VERIFIED_AT,
            verification_notes=VERIFIED_TILE_ACCESS_NOTE,
        ),
        wmts=build_verified_capabilities(CTX_JEZERO_PRELIM_ID),
    ),
)

# Verified native WMTS snapshots; visual products never supply physical values.
from pathlib import Path

def _additional_visual_layers():
    layers = []
    for identifier, instrument in [("TES_Thermal_Inertia", "TES"), ("TES_Dust", "TES"), ("mola_roughness", "MOLA")]:
        xml = (Path(__file__).resolve().parents[1] / "data/wmts" / f"{identifier}.xml").read_text()
        capabilities = parse_wmts_capabilities(xml, retrieved_at="2026-11-15")
        layers.append(MarsLayer(
            id=identifier, name=identifier, source="nasa-mars-trek", mission="Mars Global Surveyor",
            instrument=instrument, description="NASA Mars Trek visual reference; colors are not quantitative samples.",
            data_type="Colorized scientific map", region="Mars global", projection=MARS_PROJECTION_CODE,
            bounding_box=[-180, -90, 180, 90], source_url=capabilities.capabilities_url,
            attribution="NASA/MGS/TES/MOLA · NASA Mars Trek", status="available", visualizable=True,
            spatial_reference=MARS_SPATIAL_REFERENCE, wmts=capabilities,
            limitations="Native WMTS zoom range only. Visual colors are not physical values; numeric products are queried separately.",
            provenance=DataProvenance(provider="NASA Mars Trek",source_url=capabilities.capabilities_url,
                verified=True,verified_at="2026-11-15",verification_notes="Downloaded and parsed original GetCapabilities XML; native matrices preserved.")))
    return tuple(layers)

_LAYERS = _LAYERS + _additional_visual_layers()

_LOCATIONS: tuple[MarsLocation, ...] = (
    MarsLocation(
        id="jezero",
        name="Jezero Crater",
        region="Northeast Syrtis Major, Mars",
        latitude=18.38,
        longitude=77.58,
        diameter_km=45.0,
        description=(
            "An impact crater on Mars selected as the landing site for NASA's "
            "Mars 2020 Perseverance rover. The area includes a delta and "
            "lacustrine deposits relevant to studies of past habitability."
        ),
        source_ids=[
            "nasa-mars-2020",
            "nasa-mro",
            "nasa-mars-odyssey",
            "nasa-mgs",
            "nasa-pds",
            "nasa-mars-trek",
        ],
        layer_ids=[HIRISE_JEZERO_ID, CTX_JEZERO_ID],
        bounding_box=[
            77.1604655,
            18.2110274,
            77.6991776,
            18.7211945,
        ],
        spatial_reference=MARS_SPATIAL_REFERENCE,
        limitations=(
            "Reference metadata for the MARS OPS interface. The bounding box "
            "is the union of the two verified Jezero WMTS layer extents and is "
            "not an official crater boundary. No active human mission or live "
            "telemetry is represented."
        ),
    ),
)


class MarsUpstreamError(RuntimeError):
    """Raised when a NASA service cannot be queried or parsed."""


class MarsDataService:
    """Catalog and WMTS metadata service for Mars layers.

    Static catalog data is always available offline. Live WMTS capabilities
    are fetched only when explicitly requested by the capabilities endpoint;
    no mosaic tiles or large products are downloaded by the application.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._sources = {source.id: source for source in _SOURCES}
        self._layers = {layer.id: layer for layer in _LAYERS}
        self._locations = {location.id: location for location in _LOCATIONS}

    def list_sources(self) -> list[MarsDataSource]:
        return list(self._sources.values())

    def list_layers(self) -> list[MarsLayer]:
        return list(self._layers.values())

    def get_layer(self, layer_id: str) -> MarsLayer | None:
        return self._layers.get(layer_id)

    def get_location(self, location_id: str) -> MarsLocation | None:
        return self._locations.get(location_id)

    def get_verified_capabilities(
        self, layer_id: str
    ) -> WMTSCapabilities | None:
        layer = self.get_layer(layer_id)
        if layer is None or layer.wmts is None:
            return None
        return layer.wmts

    async def fetch_live_capabilities(
        self, layer_id: str
    ) -> WMTSCapabilities | None:
        layer = self.get_layer(layer_id)
        if layer is None:
            return None
        if layer.wmts is None:
            return None

        try:
            async with self.create_http_client() as client:
                response = await client.get(layer.wmts.capabilities_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MarsUpstreamError(
                "Unable to retrieve WMTS capabilities from NASA Mars Trek."
            ) from exc

        retrieved_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        try:
            return parse_wmts_capabilities(
                response.text,
                retrieved_at=retrieved_at,
            )
        except WMTSParseError as exc:
            raise MarsUpstreamError(
                "NASA Mars Trek returned an invalid WMTS capabilities document."
            ) from exc

    def create_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(
                self._settings.nasa_request_timeout_seconds
            ),
            headers={
                "User-Agent": (
                    f"{self._settings.app_name}/{self._settings.app_version}"
                )
            },
        )


@lru_cache
def get_mars_data_service() -> MarsDataService:
    return MarsDataService()
