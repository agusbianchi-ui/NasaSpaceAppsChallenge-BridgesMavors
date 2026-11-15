from dataclasses import dataclass
from xml.etree import ElementTree

from app.schemas.mars import WMTSCapabilities, WMSTileMatrix

HIRISE_JEZERO_ID = (
    "JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd"
)
CTX_JEZERO_ID = "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0"

MARS_EQUIRECTANGULAR_CRS = "urn:ogc:def:crs:EPSG::104905"
MARS_PROJECTION_CODE = "IAU2000:104905"
DEFAULT_TILE_MATRIX_SET = "default028mm"
DEFAULT_TILE_SIZE = 256
BASE_SCALE_DENOMINATOR = 279227636.29807472
BASE_RESOLUTION_DEGREES = 0.703125
WMTS_VERIFIED_AT = "2026-11-14"

_NS = {
    "wmts": "http://www.opengis.net/wmts/1.0",
    "ows": "http://www.opengis.net/ows/1.1",
}


class WMTSParseError(ValueError):
    """Raised when a GetCapabilities document lacks required WMTS fields."""


@dataclass(frozen=True)
class WMTSLayerConfig:
    layer_identifier: str
    endpoint: str
    style: str
    format: str
    tile_matrix_set: str
    supported_crs: str
    max_tile_matrix: int
    notes: str

    @property
    def capabilities_url(self) -> str:
        return f"{self.endpoint}/1.0.0/WMTSCapabilities.xml"

    @property
    def resource_url_template(self) -> str:
        return (
            f"{self.endpoint}/1.0.0/{{Style}}/{{TileMatrixSet}}/"
            "{TileMatrix}/{TileRow}/{TileCol}.png"
        )


def _build_tile_matrices(max_zoom: int) -> list[WMSTileMatrix]:
    matrices: list[WMSTileMatrix] = []
    for zoom in range(max_zoom + 1):
        matrices.append(
            WMSTileMatrix(
                id=str(zoom),
                scale_denominator=BASE_SCALE_DENOMINATOR / (2**zoom),
                resolution_degrees=BASE_RESOLUTION_DEGREES / (2**zoom),
                tile_width=DEFAULT_TILE_SIZE,
                tile_height=DEFAULT_TILE_SIZE,
                matrix_width=2 ** (zoom + 1),
                matrix_height=2**zoom,
            )
        )
    return matrices


def _config(
    *,
    layer_identifier: str,
    max_tile_matrix: int,
    notes: str,
) -> WMTSLayerConfig:
    return WMTSLayerConfig(
        layer_identifier=layer_identifier,
        endpoint=(
            "https://trek.nasa.gov/tiles/Mars/EQ/" + layer_identifier
        ),
        style="default",
        format="image/png",
        tile_matrix_set=DEFAULT_TILE_MATRIX_SET,
        supported_crs=MARS_EQUIRECTANGULAR_CRS,
        max_tile_matrix=max_tile_matrix,
        notes=notes,
    )


WMTS_LAYER_CONFIGS: dict[str, WMTSLayerConfig] = {
    HIRISE_JEZERO_ID: _config(
        layer_identifier=HIRISE_JEZERO_ID,
        max_tile_matrix=17,
        notes=(
            "Verified from the Mars Trek GetCapabilities document on "
            f"{WMTS_VERIFIED_AT}. TileMatrix identifiers 0-17 are advertised "
            "for this product."
        ),
    ),
    CTX_JEZERO_ID: _config(
        layer_identifier=CTX_JEZERO_ID,
        max_tile_matrix=13,
        notes=(
            "Verified from the Mars Trek GetCapabilities document on "
            f"{WMTS_VERIFIED_AT}. TileMatrix identifiers 0-13 are advertised "
            "for this product; the TileMatrixSet name matches HiRISE but the "
            "zoom range does not."
        ),
    ),
}


def build_verified_capabilities(
    layer_id: str,
) -> WMTSCapabilities | None:
    config = WMTS_LAYER_CONFIGS.get(layer_id)
    if config is None:
        return None
    return WMTSCapabilities(
        endpoint=config.endpoint,
        capabilities_url=config.capabilities_url,
        resource_url_template=config.resource_url_template,
        layer_identifier=config.layer_identifier,
        style=config.style,
        format=config.format,
        tile_matrix_set=config.tile_matrix_set,
        supported_crs=config.supported_crs,
        tile_matrices=_build_tile_matrices(config.max_tile_matrix),
        source="verified_snapshot",
        retrieved_at=None,
        notes=config.notes,
    )


def _text(element: ElementTree.Element | None, path: str) -> str | None:
    if element is None:
        return None
    value = element.findtext(path, namespaces=_NS)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _float(value: str | None, field: str) -> float:
    if value is None:
        raise WMTSParseError(f"Missing WMTS field: {field}.")
    try:
        return float(value)
    except ValueError as exc:
        raise WMTSParseError(f"Invalid WMTS field: {field}.") from exc


def _int(value: str | None, field: str) -> int:
    if value is None:
        raise WMTSParseError(f"Missing WMTS field: {field}.")
    try:
        return int(float(value))
    except ValueError as exc:
        raise WMTSParseError(f"Invalid WMTS field: {field}.") from exc


def parse_wmts_capabilities(
    xml_text: str,
    *,
    retrieved_at: str | None = None,
) -> WMTSCapabilities:
    """Normalize an OGC WMTS GetCapabilities document.

    This parser supports the Mars Trek equirectangular products used by MARS
    OPS. Resolution values are derived from each TileMatrix width assuming the
    advertised 360-degree global extent.
    """

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise WMTSParseError("Invalid WMTS XML.") from exc

    layer = root.find(".//wmts:Layer", _NS)
    if layer is None:
        raise WMTSParseError("WMTS document has no Layer element.")

    layer_identifier = _text(layer, "ows:Identifier")
    style = _text(layer, "wmts:Style/ows:Identifier")
    data_format = _text(layer, "wmts:Format")
    tile_matrix_set = _text(
        layer, "wmts:TileMatrixSetLink/wmts:TileMatrixSet"
    )
    if not layer_identifier or not style or not data_format:
        raise WMTSParseError("WMTS Layer is missing identifier, style or format.")
    if not tile_matrix_set:
        raise WMTSParseError("WMTS Layer is missing a TileMatrixSet link.")

    tile_matrix_set_element = None
    for candidate in root.findall(".//wmts:TileMatrixSet", _NS):
        if _text(candidate, "ows:Identifier") == tile_matrix_set:
            tile_matrix_set_element = candidate
            break
    if tile_matrix_set_element is None:
        raise WMTSParseError(
            f"TileMatrixSet '{tile_matrix_set}' is not present in the document."
        )

    supported_crs = _text(tile_matrix_set_element, "ows:SupportedCRS")
    if not supported_crs:
        raise WMTSParseError("TileMatrixSet is missing SupportedCRS.")

    matrices: list[WMSTileMatrix] = []
    for matrix in tile_matrix_set_element.findall("wmts:TileMatrix", _NS):
        matrix_id = _text(matrix, "ows:Identifier")
        if not matrix_id:
            raise WMTSParseError("TileMatrix is missing an identifier.")
        matrix_width = _int(_text(matrix, "wmts:MatrixWidth"), "MatrixWidth")
        tile_width = _int(_text(matrix, "wmts:TileWidth"), "TileWidth")
        matrices.append(
            WMSTileMatrix(
                id=matrix_id,
                scale_denominator=_float(
                    _text(matrix, "wmts:ScaleDenominator"),
                    "ScaleDenominator",
                ),
                resolution_degrees=360.0 / (matrix_width * tile_width),
                tile_width=tile_width,
                tile_height=_int(
                    _text(matrix, "wmts:TileHeight"), "TileHeight"
                ),
                matrix_width=matrix_width,
                matrix_height=_int(
                    _text(matrix, "wmts:MatrixHeight"), "MatrixHeight"
                ),
            )
        )

    if not matrices:
        raise WMTSParseError("TileMatrixSet has no TileMatrix entries.")

    resource_url = layer.find("wmts:ResourceURL", _NS)
    endpoint = None
    template = None
    if resource_url is not None:
        template = resource_url.get("template")
        if template:
            endpoint = template.split("/1.0.0/", 1)[0]
    if not endpoint:
        get_tile = root.find(
            ".//wmts:Operation[@name='GetTile']//ows:Get", _NS
        )
        if get_tile is not None:
            href = get_tile.get(
                "{http://www.w3.org/1999/xlink}href"
            )
            if href:
                endpoint = href.rstrip("/")
    if not endpoint:
        raise WMTSParseError("Unable to determine the WMTS endpoint.")
    if not template:
        template = (
            f"{endpoint}/1.0.0/{{Style}}/{{TileMatrixSet}}/"
            "{TileMatrix}/{TileRow}/{TileCol}.png"
        )

    return WMTSCapabilities(
        endpoint=endpoint,
        capabilities_url=f"{endpoint}/1.0.0/WMTSCapabilities.xml",
        resource_url_template=template,
        layer_identifier=layer_identifier,
        style=style,
        format=data_format,
        tile_matrix_set=tile_matrix_set,
        supported_crs=supported_crs,
        tile_matrices=matrices,
        source="live",
        retrieved_at=retrieved_at,
        notes=(
            "Parsed from a live WMTS GetCapabilities response. Resolution "
            "values are derived from the advertised equirectangular matrix "
            "widths."
        ),
    )
