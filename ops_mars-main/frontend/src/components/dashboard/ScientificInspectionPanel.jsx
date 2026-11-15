import Panel from '../Panel.jsx'
import { useApi } from '../hooks/useApi.jsx'
import { useState, useEffect, useRef } from 'react'
import { formatCoordinate } from '../pages/MarsExplorer.jsx'

const VARIABLE_DISPLAY_ORDER = [
  'scientific_elevation',
  'slope',
  'aspect',
  'roughness',
  'dust_optical_depth',
  'mobility_difficulty',
  'solar_exposure',
  'ionizing_radiation',
]

export default function ScientificInspectionPanel({
  position,
  variables,
  terrainMetadata,
  onClose,
  onConvertToMarker,
  onUseAsOrigin,
  onUseAsDestination,
  onUseAsWaypoint,
}) {
  const { api } = useApi()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  [panelWidth, setPanelWidth] = useState(380)

  // Close panel on unmount
  useEffect(() => {
    return () => {
      onClose()
    }
  }, [onClose])

  if (!position) {
    return null
  }

  if (loading) {
    return (
      <Panel
        title="Scientific Inspection"
        eyebrow="Querying data..."
        icon={LoaderCircle}
        onClose={onClose}
      >
        <div className="panel__body" style={{ padding: 20 }}>
          <p>Loading scientific data for position ({position.x}, {position.z})...</p>
        </div>
      </Panel>
    )
  }

  if (error) {
    return (
      <Panel
        title="Scientific Inspection"
        eyebrow="Error loading data"
        icon={AlertTriangle}
        onClose={onClose}
      >
        <div className="panel__body" style={{ padding: 20 }}>
          <p>{error}</p>
          <p className="panel__note">Showing geometric inspection only.</p>
        </div>
      </Panel>
    )
  }

  // Build variable display from available data
  const variableCards = Object.entries(variables || {}).map(
    ([varId, varData], index) => {
      const varDef = VARIABLE_DISPLAY_ORDER.indexOf(varId)
      const displayIndex = varId === 'position' ? -1 : varDef >= 0 ? varDef : VARIABLE_DISPLAY_ORDER.length + index

      // Sort: known variables first, then unknown
      const sortedByDisplay = () => {
        if (varDef >= 0) return varDef
        return VARIABLE_DISPLAY_ORDER.length + index
      }

      const isAvailable = varData.availability === 'Available' && varData.value !== null
      const isUnavailable = varData.availability === 'Unavailable'

      return (
        <div
          key={varId}
          className="variable-card"
          style={{ 
            order: sortedByDisplay(),
            marginBottom: 8,
            borderLeft: isAvailable ? '3px solid #4ade80' : isUnavailable ? '3px solid #f87171' : '3px solid #e2e8f0',
          }}
        >
          <div className="variable-header">
            <span className="variable-name">{varId.replace(/_/g, ' ')}</span>
            <span className="variable-status">
              {isAvailable ? 'Available' : isUnavailable ? 'Unavailable' : 'Partial'}
            </span>
          </div>
          <div className="variable-value">
            {isAvailable ? (
              <span className="value">{formatValue(varId, varData.value, varData.unit)}</span>
            ) : (
              <span className="value-unavailable">{varData.reason || 'No data'}</span>
            )}
          </div>
          <div className="variable-metadata">
            <span className="metadata-item">
              <strong>Source:</strong> {varData.source || 'N/A'}
            </span>
            <span className="metadata-item">
              <strong>Unit:</strong> {varData.unit || 'N/A'}
            </span>
            <span className="metadata-item">
              <strong>Resolution:</strong> {varData.spatial_resolution?.nominal_m || varData.spatial_resolution || 'Variable'}
            </span>
          </div>
        </div>
      )
    }
  )

  // Determine panel width based on content
  useEffect(() => {
    setPanelWidth(420)
  }, [variableCards.length])

  return (
    <Panel
      title="Scientific Inspection"
      eyebrow="Position data from terrain analysis"
      icon={Search}
      onClose={onClose}
      style={{ maxWidth: 460 }}
    >
      <div className="inspection-header">
        <div className="position-info">
          <strong>Coordinates:</strong> {formatCoordinate(position.latitude, 'N', 'S')},
          {formatCoordinate(position.longitude, 'E', 'W')}
          <br />
          <strong>Elevation:</strong> {position.visual_elevation !== null ? 
            `${position.visual_elevation} m visual (${position.scientific_elevation !== null ? 
              `${position.scientific_elevation} m scientific` : 'N/A'} )` : 'N/A'}
          <br />
          <strong>Grid:</strong> {position.grid?.row !== undefined ? 
            `Row ${position.grid.row}, Column ${position.grid.column}` : 'N/A'}
        </div>
        <button
          className="btn-convert-to-marker"
          onClick={onConvertToMarker}
          style={{ marginLeft: 'auto', padding: '4px 8px', fontSize: '12px' }}
          title="Convert this point to a marker"
        >
          ↓ Marker
        </button>
      </div>

      <div className="variable-cards">
        {variableCards}
      </div>

      {terrainMetadata && (
        <div className="terrain-metadata">
          <strong>Terrain coverage:</strong> {terrainMetadata.availability}
          {terrainMetadata.reason && <br />
          <small>{terrainMetadata.reason}</small>}
        </div>
      )}

      <div className="panel-actions">
        <button
          className="btn-action"
          onClick={onClose}
          style={{ width: '100%', marginTop: 8 }}
        >
          Close panel
        </button>
        <button
          className="btn-action"
          onClick={onUseAsOrigin}
          style={{ width: '100%', marginTop: 4, background: '#e2e8f0' }}
          title="Use as route origin"
        >
          Use as origin
        </button>
        <button
          className="btn-action"
          onClick={onUseAsDestination}
          style={{ width: '100%', marginTop: 4, background: '#e2e8f0' }}
          title="Use as route destination"
        >
          Use as destination
        </button>
        <button
          className="btn-action"
          onClick={onUseAsWaypoint}
          style={{ width: '100%', marginTop: 4, background: '#e2e8f0' }}
          title="Use as waypoint"
        >
          Use as waypoint
        </button>
      </div>
    </Panel>
  )
}

function formatValue(varId, value, unit) {
  if (value === null || value === undefined) return 'N/A'
  
  const unitMap = {
    'scientific_elevation': { multiplier: 1, suffix: 'm' },
    'slope': { multiplier: 1, suffix: '°' },
    'aspect': { multiplier: 1, suffix: '°' },
    'roughness': { multiplier: 1, suffix: 'm' },
    'dust_optical_depth': { multiplier: 1, suffix: ' Pa/Pa' },
    'mobility_difficulty': { multiplier: 1, suffix: '' },
    'solar_exposure': { multiplier: 1, suffix: ' W/m²' },
    'ionizing_radiation': { multiplier: 1, suffix: ' μSv/day' },
  }
  
  const map = unitMap[varId] || { multiplier: 1, suffix: unit || '' }
  return `${Number(value).toFixed(3)}${map.suffix}`
}