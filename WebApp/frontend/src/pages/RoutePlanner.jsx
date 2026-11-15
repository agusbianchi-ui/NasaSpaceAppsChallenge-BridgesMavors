import MarsTerrainViewer from '../components/map/MarsTerrainViewer.jsx'
import { useEffect, useRef, useState } from 'react'
import SurfaceExplorationPanel from '../components/dashboard/SurfaceExplorationPanel'
import {
  AlertTriangle,
  LoaderCircle,
  Map as MapIcon,
  RefreshCw,
  Route as RouteIcon,
  ShieldAlert,
} from 'lucide-react'
import Panel from '../components/Panel.jsx'
import SimulationNotice from '../components/SimulationNotice.jsx'
import StatusPill from '../components/StatusPill.jsx'
import DataAttribution from '../components/map/DataAttribution.jsx'
import LayerInformation from '../components/map/LayerInformation.jsx'
import LayerSelector from '../components/map/LayerSelector.jsx'
import MapControls from '../components/map/MapControls.jsx'
import MapLegend from '../components/map/MapLegend.jsx'
import MarsMap from '../components/map/MarsMap.jsx'
import {
  fetchMarsLayerCapabilities,
  fetchMarsLayers,
} from '../services/marsApi.js'
import {
  MARS_RADIUS_METERS,
  geodesicDistanceMeters,
  geodesicLengthMeters,
} from '../services/marsGeo.js'
import { routeNote, routeWaypoints } from '../services/missionData.js'

const IDLE_STATUS = { loading: false, warning: null }
const ROUTE_EXTENT_PADDING = 0.02

function buildCumulativeDistances(points) {
  let total = 0

  return points.map((point, index) => {
    if (index > 0) {
      total += geodesicDistanceMeters(points[index - 1], point)
    }
    return total
  })
}

function buildRouteExtent(points) {
  const longitudes = points.map((point) => point.longitude)
  const latitudes = points.map((point) => point.latitude)

  return [
    Math.max(-180, Math.min(...longitudes) - ROUTE_EXTENT_PADDING),
    Math.max(-90, Math.min(...latitudes) - ROUTE_EXTENT_PADDING),
    Math.min(180, Math.max(...longitudes) + ROUTE_EXTENT_PADDING),
    Math.min(90, Math.max(...latitudes) + ROUTE_EXTENT_PADDING),
  ]
}

function layerCoversRoute(layer, points) {
  const boundingBox = layer?.bounding_box
  if (!boundingBox || boundingBox.length !== 4) {
    return true
  }

  const [west, south, east, north] = boundingBox
  return points.every(
    (point) =>
      point.longitude >= west &&
      point.longitude <= east &&
      point.latitude >= south &&
      point.latitude <= north,
  )
}

function formatCoordinate(value, positive, negative) {
  if (!Number.isFinite(value)) {
    return 'n/a'
  }
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positive : negative}`
}

function formatDistance(meters) {
  if (!Number.isFinite(meters) || meters <= 0) {
    return '0.0 km'
  }
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(2)} km`
  }
  return `${meters.toFixed(0)} m`
}

function waypointRole(index, total) {
  if (index === 0) {
    return 'Origin'
  }
  if (index === total - 1) {
    return 'Destination'
  }
  return 'Waypoint'
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

function ErrorOverlay({ title, message, onRetry }) {
  return (
    <div className="map-overlay map-overlay--error" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <div>
        <h4>{title}</h4>
        <p>{message}</p>
      </div>
      <button type="button" className="map-button" onClick={onRetry}>
        <RefreshCw size={14} aria-hidden="true" />
        Retry
      </button>
    </div>
  )
}

const CUMULATIVE_DISTANCES = buildCumulativeDistances(routeWaypoints)
const ROUTE_EXTENT = buildRouteExtent(routeWaypoints)
const ROUTE_LENGTH_METERS = geodesicLengthMeters(routeWaypoints)

export default function RoutePlanner() {
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

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    fetchMarsLayers({ signal: controller.signal })
      .then((data) => {
        if (!active) {
          return
        }
        const visualizable = data.filter((layer) => layer.visualizable)
        const preferred =
          visualizable.find(
            (layer) => layer.instrument === 'CTX' && layer.resolution === 6,
          ) ?? visualizable[0]

        setLayers(visualizable)
        setSelectedLayerId(preferred?.id ?? null)
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
    if (!selectedLayerId) {
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
  const routeCovered = layerCoversRoute(selectedLayer, routeWaypoints)
  const cursorText = pointer
    ? `${formatCoordinate(pointer.latitude, 'N', 'S')}, ${formatCoordinate(
        pointer.longitude,
        'E',
        'W',
      )}`
    : 'Move the cursor over the map'

  const summary = [
    {
      id: 'waypoints',
      label: 'Waypoints',
      value: String(routeWaypoints.length),
      detail: 'Simulated route points',
    },
    {
      id: 'length',
      label: 'Geometric Length',
      value: formatDistance(ROUTE_LENGTH_METERS),
      detail: 'Great-circle · Mars radius',
    },
    {
      id: 'basemap',
      label: 'Basemap',
      value: selectedLayer?.instrument ?? '—',
      detail: selectedLayer?.name ?? 'NASA Mars Trek',
    },
  ]

  return (
    <div className="page">
      <h1>Route Planner</h1>
      <p>Shared mission, points, scientific hazards and route comparison. The same terrain and assumptions are used in Mars Explorer.</p>
      <MarsTerrainViewer />
      <details><summary>Previous simulated demonstration / 2D reference</summary>
      <div className="page-heading">
        <div>
          <p className="page-heading__eyebrow">Traverse visualization</p>
          <h1>Route Planner</h1>
          <p className="page-heading__description">
            Graphical overlay of the simulated Jezero traverse on verified NASA
            Mars Trek mosaics. Route editing and terrain analysis are not
            enabled.
          </p>
        </div>
        <span className="page-heading__phase">ROUTE · SIM-01</span>
      </div>

      <SimulationNotice compact />

      <div className="metric-grid">
        {summary.map((item) => (
          <div className="metric-card" key={item.id}>
            <span className="metric-card__label">{item.label}</span>
            <strong className="metric-card__value">{item.value}</strong>
            <span className="metric-card__detail">{item.detail}</span>
          </div>
        ))}
      </div>

      <Panel
        title="Jezero Traverse Overlay"
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
                route={routeWaypoints}
                viewExtent={ROUTE_EXTENT}
                onPointerMove={setPointer}
                onStatusChange={setMapStatus}
                onResolutionChange={setMetersPerPixel}
              />

              <div className="map-frame__topbar">
                
                <MapControls
                  mapRef={mapRef}
                  disabled={mapDisabled}
                  fitLabel="Fit to simulated route"
                />
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
                <ErrorOverlay
                  title="NASA layer catalog unavailable"
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
                  <ErrorOverlay
                    title="WMTS metadata unavailable"
                    message={capabilitiesState.error}
                    onRetry={handleRetryCapabilities}
                  />
                )}
            </div>

            <div className="map-layers-below"><LayerSelector
                  layers={layers}
                  selectedId={selectedLayerId}
                  onSelect={handleSelectLayer}
                  disabled={catalogState.status === 'loading'}
                /></div>

            {mapStatus.warning && (
              <p className="map-warning" role="status">
                <AlertTriangle size={13} aria-hidden="true" />
                {mapStatus.warning}
              </p>
            )}

            {capabilitiesReady && !routeCovered && (
              <p className="map-warning" role="status">
                <AlertTriangle size={13} aria-hidden="true" />
                The selected basemap does not cover the full simulated route.
                Choose CTX or MOLA to see all waypoints.
              </p>
            )}

            <p className="map-warning" role="note">
              <ShieldAlert size={13} aria-hidden="true" />
              Visualization only. The route is simulated; no terrain, slope,
              obstacle, or trafficability analysis is performed. It is not an
              operational traverse.
            </p>

            <div className="map-caption">
              <span>
                Tiles are requested directly from{' '}
                <code>trek.nasa.gov</code>. The route overlay is illustrative
                and does not modify the NASA imagery.
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
              showRoute
            />
            <DataAttribution layer={selectedLayer} />
          </aside>
        </div>
      </Panel>

      <Panel
        title="Simulated Route Waypoints"
        eyebrow="Graphical overlay only"
        icon={RouteIcon}
        action={<span className="panel__tag">Simulated</span>}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Waypoint</th>
                <th scope="col">Role</th>
                <th scope="col">Location</th>
                <th scope="col">Coordinates</th>
                <th scope="col">Distance from start</th>
              </tr>
            </thead>
            <tbody>
              {routeWaypoints.map((waypoint, index) => {
                const role = waypointRole(index, routeWaypoints.length)
                const tone =
                  role === 'Origin'
                    ? 'ok'
                    : role === 'Destination'
                      ? 'danger'
                      : 'accent'

                return (
                  <tr key={waypoint.id}>
                    <td className="mono">{waypoint.id}</td>
                    <td>
                      <StatusPill tone={tone}>{role}</StatusPill>
                    </td>
                    <td>
                      <span className="data-table__primary">
                        {waypoint.name}
                      </span>
                    </td>
                    <td className="mono">{waypoint.coordinates}</td>
                    <td className="mono">
                      {formatDistance(CUMULATIVE_DISTANCES[index])}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className="panel__note">
          {routeNote} Distances are geometric great-circle values derived from
          the simulated coordinates using a Mars radius of{' '}
          {MARS_RADIUS_METERS.toLocaleString('en-US')} m; they are not
          traversed distances.
        </p>
      </Panel>

      <SurfaceExplorationPanel />
      </details>
    </div>
  )
}
