import { Info } from 'lucide-react'
import StatusPill from '../StatusPill.jsx'

function valueOrUnknown(value) {
  return value ?? 'Not verified / not available'
}

function formatBoundingBox(boundingBox) {
  if (!boundingBox || boundingBox.length !== 4) {
    return 'Not verified'
  }
  const [west, south, east, north] = boundingBox
  return `W ${west.toFixed(6)} · S ${south.toFixed(6)} · E ${east.toFixed(6)} · N ${north.toFixed(6)}`
}

function formatResolution(layer) {
  if (layer.resolution == null) {
    return 'Not published'
  }
  return `${layer.resolution} ${layer.resolution_unit ?? ''}`.trim()
}

function formatZoomRange(capabilities) {
  const matrices = capabilities?.tile_matrices
  if (!matrices?.length) {
    return 'Not available'
  }
  return `${matrices[0].id}–${matrices[matrices.length - 1].id}`
}

export default function LayerInformation({ layer, capabilities }) {
  if (!layer) {
    return (
      <section className="map-card" aria-label="Layer information">
        <header className="map-card__header">
          <Info size={14} aria-hidden="true" />
          <h3>Layer information</h3>
        </header>
        <p className="map-note">
          Select a NASA orbital layer to inspect its verified metadata.
        </p>
      </section>
    )
  }

  const statusTone =
    layer.status === 'available'
      ? 'ok'
      : layer.status === 'planned'
        ? 'muted'
        : 'accent'

  return (
    <section className="map-card" aria-label="Layer information">
      <header className="map-card__header">
        <Info size={14} aria-hidden="true" />
        <h3>Layer information</h3>
        <StatusPill tone={statusTone}>{layer.status}</StatusPill>
      </header>

      <dl className="map-meta">
        <div>
          <dt>Instrument</dt>
          <dd>{layer.instrument}</dd>
        </div>
        <div>
          <dt>Mission</dt>
          <dd>{layer.mission}</dd>
        </div>
        <div>
          <dt>Data type</dt>
          <dd>{layer.data_type}</dd>
        </div>
        <div>
          <dt>Resolution</dt>
          <dd>{formatResolution(layer)}</dd>
        </div>
        <div>
          <dt>Region</dt>
          <dd>{layer.region}</dd>
        </div>
        <div>
          <dt>Coordinate system</dt>
          <dd>
            {layer.spatial_reference
              ? `${layer.spatial_reference.code} · ${layer.spatial_reference.units}`
              : 'Not verified'}
          </dd>
        </div>
        <div>
          <dt>Bounding box</dt>
          <dd className="map-meta__wide">
            {formatBoundingBox(layer.bounding_box)}
          </dd>
        </div>
        <div>
          <dt>Acquisition date</dt>
          <dd>{valueOrUnknown(layer.acquisition_date)}</dd>
        </div>
        <div>
          <dt>Processing level</dt>
          <dd>{valueOrUnknown(layer.processing_level)}</dd>
        </div>
      </dl>

      {capabilities && (
        <div className="map-subsection">
          <h4>
            WMTS metadata{' '}
            <StatusPill tone="ok">
              {capabilities.source === 'live' ? 'live' : 'verified'}
            </StatusPill>
          </h4>
          <dl className="map-meta map-meta--compact">
            <div>
              <dt>Service</dt>
              <dd>
                {capabilities.service} {capabilities.version}
              </dd>
            </div>
            <div>
              <dt>Style / format</dt>
              <dd>
                {capabilities.style} / {capabilities.format}
              </dd>
            </div>
            <div>
              <dt>TileMatrixSet</dt>
              <dd>{capabilities.tile_matrix_set}</dd>
            </div>
            <div>
              <dt>Zoom range</dt>
              <dd>{formatZoomRange(capabilities)}</dd>
            </div>
            <div>
              <dt>Supported CRS</dt>
              <dd className="map-meta__wide">
                {capabilities.supported_crs}
              </dd>
            </div>
          </dl>
          {layer.provenance?.verified_at && (
            <p className="map-note">
              Verified against GetCapabilities on{' '}
              {layer.provenance.verified_at}.
            </p>
          )}
        </div>
      )}

      <div className="map-subsection">
        <h4>Source</h4>
        <p className="map-note map-note--break">{layer.source_url}</p>
        <a
          className="map-link"
          href={layer.source_url}
          target="_blank"
          rel="noreferrer"
        >
          Open NASA product metadata
        </a>
      </div>

      <div className="map-subsection">
        <h4>Limitations</h4>
        <p className="map-note">{layer.limitations}</p>
      </div>
    </section>
  )
}
