import pytest

from app.services.mars_wmts import (
    CTX_JEZERO_ID,
    HIRISE_JEZERO_ID,
    WMTSParseError,
    build_verified_capabilities,
    parse_wmts_capabilities,
)

MINIMAL_CAPABILITIES = """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
              xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink"
              version="1.0.0">
  <ows:OperationsMetadata>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="https://example.test/tiles/DEMO/1.0.0/"/>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
  </ows:OperationsMetadata>
  <Contents>
    <Layer>
      <ows:Identifier>DEMO_LAYER</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <TileMatrixSetLink>
        <TileMatrixSet>default028mm</TileMatrixSet>
      </TileMatrixSetLink>
      <ResourceURL format="image/png" resourceType="tile"
        template="https://example.test/tiles/DEMO/1.0.0/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"/>
    </Layer>
    <TileMatrixSet>
      <ows:Identifier>default028mm</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::104905</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>279227636.29807472</ScaleDenominator>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>2</MatrixWidth>
        <MatrixHeight>1</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>139613818.14903736</ScaleDenominator>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>4</MatrixWidth>
        <MatrixHeight>2</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
  </Contents>
</Capabilities>
"""


def test_parse_wmts_capabilities() -> None:
    capabilities = parse_wmts_capabilities(
        MINIMAL_CAPABILITIES,
        retrieved_at="2026-11-14T00:00:00Z",
    )

    assert capabilities.source == "live"
    assert capabilities.retrieved_at == "2026-11-14T00:00:00Z"
    assert capabilities.layer_identifier == "DEMO_LAYER"
    assert capabilities.style == "default"
    assert capabilities.format == "image/png"
    assert capabilities.tile_matrix_set == "default028mm"
    assert capabilities.supported_crs == "urn:ogc:def:crs:EPSG::104905"
    assert capabilities.endpoint == "https://example.test/tiles/DEMO"
    assert capabilities.capabilities_url == (
        "https://example.test/tiles/DEMO/1.0.0/WMTSCapabilities.xml"
    )
    assert len(capabilities.tile_matrices) == 2
    assert capabilities.tile_matrices[0].id == "0"
    assert capabilities.tile_matrices[0].resolution_degrees == pytest.approx(
        0.703125
    )
    assert capabilities.tile_matrices[1].id == "1"
    assert capabilities.tile_matrices[1].resolution_degrees == pytest.approx(
        0.3515625
    )


def test_parse_invalid_xml_raises() -> None:
    with pytest.raises(WMTSParseError):
        parse_wmts_capabilities("<not-valid")


def test_parse_missing_tile_matrix_set_raises() -> None:
    xml = MINIMAL_CAPABILITIES.replace(
        "<TileMatrixSet>default028mm</TileMatrixSet>",
        "<TileMatrixSet>missing</TileMatrixSet>",
    )

    with pytest.raises(WMTSParseError):
        parse_wmts_capabilities(xml)


def test_verified_snapshot_uses_distinct_zoom_ranges() -> None:
    hirise = build_verified_capabilities(HIRISE_JEZERO_ID)
    ctx = build_verified_capabilities(CTX_JEZERO_ID)

    assert hirise is not None
    assert ctx is not None
    assert len(hirise.tile_matrices) == 18
    assert len(ctx.tile_matrices) == 14
    assert hirise.tile_matrix_set == ctx.tile_matrix_set == "default028mm"
    assert hirise.tile_matrices[0].resolution_degrees == pytest.approx(
        ctx.tile_matrices[0].resolution_degrees
    )


def test_verified_snapshot_unknown_layer_returns_none() -> None:
    assert build_verified_capabilities("missing") is None
