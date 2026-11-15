import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  LoaderCircle,
  Map as MapIcon,
  Orbit,
  RefreshCw,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import Panel from '../components/Panel.jsx'
import SimulationNotice from '../components/SimulationNotice.jsx'
import StatusPill from '../components/StatusPill.jsx'
import ExplorationPanel from '../components/dashboard/ExplorationPanel.jsx'
import ScientificTargetsPanel from '../components/dashboard/ScientificTargetsPanel.jsx'
import ScientificInspectionPanel from '../components/dashboard/ScientificInspectionPanel.jsx'
import DataAttribution from '../components/map/DataAttribution.jsx'
import LayerInformation from '../components/map/LayerInformation.jsx'
import LayerSelector from '../components/map/LayerSelector.jsx'
import MapControls from '../components/map/MapControls.jsx'
import MapLegend from '../components/map/MapLegend.jsx'
import MarsMap from '../components/map/MarsMap.jsx'
import MarsTerrainViewer from '../components/map/MarsTerrainViewer.jsx'
import {
  fetchMarsLayerCapabilities,
  fetchMarsLayers,
} from '../services/marsApi.js'

const IDLE_STATUS = { loading: false, warning: null }

function formatCoordinate(value, positive, negative) {
  if (!Number.isFinite(value)) {
    return 'n/a'
  }
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positive : negative}`
}

function CatalogError({ message, onRetry }) {
  return (
    <div className="map-overlay map-overlay--error" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <h4>NASA layer catalog unavailable</h4>
        <p>{message}</p>
        <p className="map-overlay__hint">
          Start the backend with{' '}
          <code>venv/bin/uvicorn app.main:app --port 8000</code> from the
          <code>backend/</code> directory.
        </p>
      </div>
      <button type="button" className="map-button" onClick={onRetry}>
        <RefreshCw size={14} aria-hidden="true" />
        Retry
      </button>
    </div>
  )
}

function CapabilitiesError({ message, onRetry }) {
  return (
    <div className="map-overlay map-overlay--error" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <h4>WMTS metadata unavailable</h4>
        <p>{message}</p>
      </div>
      <button type="button" className="map-button" onClick={onRetry}>
        <RefreshCw size={14} aria-hidden="true" />
        Retry
      </button>
    </div>
  )
}

function LoadingOverlay({ label }) {
  return (
    <div className="map-overlay" role="status">
      <LoaderCircle
        size={20}
        className="map-spinner"
        aria-hidden="true"
      />
      <p>{label}</p>
    </div>
  )
}

export default function MarsExplorer() {
  const mapRef = useRef(null)
  const [layers, setLayers] = useState([])
  const [selectedLayerId, setSelectedLayerId] = useState(null)
  const [catalogState, setCatalogState] = useState({
    status: 'loading',
    error: null,
  })
  const [catalogAttempt, setCatalogAttempt] = useState(0)
  const [capabilities, setCapabilities] = useState(null)
  const [capabilitiesState, setCapabilitiesState] = useState({
    status: 'idle',
    error: null,
  })
  const [capabilitiesAttempt, setCapabilitiesAttempt] = useState(0)
  const [mapStatus, setMapStatus] = useState(IDLE_STATUS)
  const [pointer, setPointer] = useState(null)
  const [metersPerPixel, setMetersPerPixel] = useState(null)
  const [inspectionPosition, setInspectionPosition] = useState(null)
  const [inspectionVariables, setInspectionVariables] = useState({})
  const [terrainMetadata, setTerrainMetadata] = useState({})
  const [showInspectionPanel, setShowInspectionPanel] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    fetchMarsLayers({ signal: controller.signal })
      .then((data) => {
        if (!active) {
          return
        }
        const visualizable = data.filter((layer) => layer.visualizable)
        setLayers(visualizable)
        setSelectedLayerId((current) =>
          visualizable.some((layer) => layer.id === current)
            ? current
            : (visualizable[0]?.id ?? null),
        )
        setCapabilities(null)
        setCapabilitiesState({ status: 'loading', error: null })
        setCapabilitiesAttempt((value) => value + 1)
        setPointer(null)
        setMetersPerPixel(null)
        setMapStatus(IDLE_STATUS)
        setCatalogState({ status: 'ready', error: null })
      })
      .catch((error) => {
        if (!active || error.name === 'AbortError') {
          return
        }
        setLayers([])
        setSelectedLayerId(null)
        setCapabilities(null)
        setCapabilitiesState({ status: 'idle', error: null })
        setPointer(null)
        setMetersPerPixel(null)
        setMapStatus(IDLE_STATUS)
        setCatalogState({
          status: 'error',
          error:
            error.message ??
            'The NASA layer catalog could not be retrieved.',
        })
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [catalogAttempt])

  useEffect(() => {
    const inspectorController = new AbortController()
    let active = True

    return () => {
      active = False
      inspectorController.abort()
    }
  }, [])
      return undefined
    }

    const controller = new AbortController()
    let active = true

    fetchMarsLayerCapabilities(selectedLayerId, {
      signal: controller.signal,
    })
      .then((data) => {
        if (!active) {
          return
        }
        setCapabilities(data)
        setCapabilitiesState({ status: 'ready', error: null })
      })
      .catch((error) => {
        if (!active || error.name === 'AbortError') {
          return
        }
        setCapabilities(null)
        setCapabilitiesState({
          status: 'error',
          error:
            error.message ??
            'The WMTS metadata for this layer could not be retrieved.',
        })
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [selectedLayerId, capabilitiesAttempt])

  function handleSelectLayer(layerId) {
    if (layerId === selectedLayerId) {
      return
    }
    setSelectedLayerId(layerId)
    setCapabilities(null)
    setCapabilitiesState({ status: 'loading', error: null })
    setPointer(null)
    setMetersPerPixel(null)
    setMapStatus(IDLE_STATUS)
  }

  function handleRetryCatalog() {
    setCatalogState({ status: 'loading', error: null })
    setCatalogAttempt((value) => value + 1)
  }

  function handleRetryCapabilities() {
    setCapabilities(null)
    setCapabilitiesState({ status: 'loading', error: null })
    setCapabilitiesAttempt((value) => value + 1)
  }

  const selectedLayer =
    layers.find((layer) => layer.id === selectedLayerId) ?? null
  const capabilitiesReady =
    capabilitiesState.status === 'ready' && Boolean(capabilities)
  const mapDisabled = !capabilitiesReady
  const cursorText = pointer
    ? `${formatCoordinate(pointer.latitude, 'N', 'S')}, ${formatCoordinate(
        pointer.longitude,
        'E',
        'W',
      )}`
    : 'Move the cursor over the map'

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">Surface navigation</p>
          <h1>Mars Explorer</h1>
          <p className="page-heading__description">
            Real NASA orbital mosaics of Jezero Crater streamed from Mars Trek,
            paired with the simulated scientific point network used by the
            operations interface.
          </p>
        </div>
        <span className="page-heading__phase">AREA · JZ-REF-001</span>
      </div>

      <SimulationNotice compact />

      <Panel
        title="Jezero Crater Orbital Basemap"
        eyebrow="NASA Mars Trek · OGC WMTS"
        icon={MapIcon}
        className="map-panel"
        action={
          <span className="panel__tag">
            {layers.length > 0
              ? `${layers.length} verified layer${layers.length === 1 ? '' : 's'}`
              : 'Verified catalog'}
          </span>
        }
      >
        <div className="map-layout">
          <div className="map-main">
            <div className="map-frame">
              <MarsMap
                ref={mapRef}
                layer={capabilitiesReady ? selectedLayer : null}
                capabilities={capabilitiesReady ? capabilities : null}
                onPointerMove={setPointer}
                onStatusChange={setMapStatus}
                onResolutionChange={setMetersPerPixel}
              />

              <div className="map-frame__topbar">
                <LayerSelector
                  layers={layers}
                  selectedId={selectedLayerId}
                  onSelect={handleSelectLayer}
                  disabled={catalogState.status === 'loading'}
                />
                <MapControls mapRef={mapRef} disabled={mapDisabled} />
              </div>

              <div className="map-frame__coords" aria-live="polite">
                <span className="map-frame__crs">
                  {selectedLayer?.spatial_reference?.code ??
                    'IAU2000:104905'}
                </span>
                <span>{cursorText}</span>
              </div>

              {mapStatus.loading && (
                <div className="map-frame__badge" role="status">
                  <LoaderCircle
                    size={13}
                    className="map-spinner"
                    aria-hidden="true"
                  />
                  Loading NASA tiles
                </div>
              )}

              {catalogState.status === 'loading' && (
                <LoadingOverlay label="Loading NASA layer catalog…" />
              )}

              {catalogState.status === 'error' && (
                <CatalogError
                  message={catalogState.error}
                  onRetry={handleRetryCatalog}
                />
              )}

              {catalogState.status === 'ready' &&
                capabilitiesState.status === 'loading' && (
                  <LoadingOverlay label="Loading WMTS metadata…" />
                )}

              {catalogState.status === 'ready' &&
                capabilitiesState.status === 'error' && (
                  <CapabilitiesError
                    message={capabilitiesState.error}
                    onRetry={handleRetryCapabilities}
                  />
                )}
            </div>

            {mapStatus.warning && (
              <p className="map-warning" role="status">
                <AlertTriangle size={13} aria-hidden="true" />
                {mapStatus.warning}
              </p>
            )}

            <div className="map-caption">
              <span>
                Tiles are requested directly from{' '}
                <code>trek.nasa.gov</code>. This interface does not cache,
                reproject, or modify the imagery.
              </span>
              {selectedLayer?.provenance?.verified && (
                <StatusPill tone="ok">
                  Verified {selectedLayer.provenance.verified_at}
                </StatusPill>
              )}
            </div>
          </div>

          <aside className="map-sidebar" aria-label="Map details">
            <LayerInformation
              layer={selectedLayer}
              capabilities={capabilities}
            />
            <MapLegend
              layer={selectedLayer}
              metersPerPixel={metersPerPixel}
            />
            <DataAttribution layer={selectedLayer} />
          </aside>
        </div>
      </Panel>

      <Panel title="3D Surface Viewer" eyebrow="Voxel terrain · local coordinates" icon={Orbit} className="terrain-panel">
        <MarsTerrainViewer />
      </Panel>
      <ExplorationPanel />

      <ScientificTargetsPanel
        limit={4}
        action={
          <Link className="text-link" to="/targets">
            Open target catalogue
          </Link>
        }
      />

      {/* Scientific inspection panel - appears on right-click inspection */}
      {showInspectionPanel && (
        <ScientificInspectionPanel
          position={inspectionPosition}
          variables={inspectionVariables}
          terrainMetadata={terrainMetadata}
          onClose={() => setShowInspectionPanel(false)}
          onConvertToMarker={() => setShowInspectionPanel(false)}
          onUseAsOrigin={() => setShowInspectionPanel(false)}
          onUseAsDestination={() => setShowInspectionPanel(false)}
          onUseAsWaypoint={() => setShowInspectionPanel(false)}
        />
      )}
    </div>
  )
}
