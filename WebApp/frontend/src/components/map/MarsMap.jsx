import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import Feature from 'ol/Feature.js'
import Map from 'ol/Map.js'
import View from 'ol/View.js'
import LineString from 'ol/geom/LineString.js'
import Point from 'ol/geom/Point.js'
import Polygon from 'ol/geom/Polygon.js'
import TileLayer from 'ol/layer/Tile.js'
import VectorLayer from 'ol/layer/Vector.js'
import Projection from 'ol/proj/Projection.js'
import VectorSource from 'ol/source/Vector.js'
import WMTS from 'ol/source/WMTS.js'
import { Circle as CircleStyle, Fill, Stroke, Style } from 'ol/style.js'
import WMTSTileGrid from 'ol/tilegrid/WMTS.js'
import { MARS_RADIUS_METERS } from '../../services/marsGeo.js'
import 'ol/ol.css'

export const MARS_PROJECTION_CODE = 'IAU2000:104905'
export { MARS_RADIUS_METERS }

const MARS_EXTENT = [-180, -90, 180, 90]
const DEFAULT_CENTER = [77.43, 18.47]
const EMPTY_ROUTE = []
const FALLBACK_RESOLUTIONS = Array.from(
  { length: 18 },
  (_, zoom) => 0.703125 / 2 ** zoom,
)

const MARS_PROJECTION = new Projection({
  code: MARS_PROJECTION_CODE,
  units: 'degrees',
  extent: MARS_EXTENT,
  global: true,
})

const BBOX_STYLE = new Style({
  stroke: new Stroke({
    color: 'rgba(232, 117, 50, 0.95)',
    width: 1.5,
    lineDash: [7, 6],
  }),
  fill: new Fill({ color: 'rgba(232, 117, 50, 0.06)' }),
})

const ROUTE_LINE_STYLE = new Style({
  stroke: new Stroke({
    color: 'rgba(232, 117, 50, 0.95)',
    width: 2.5,
    lineDash: [8, 6],
  }),
})

const ROUTE_POINT_STYLES = {
  origin: new Style({
    image: new CircleStyle({
      radius: 6,
      fill: new Fill({ color: '#3dd68c' }),
      stroke: new Stroke({ color: '#e8edf4', width: 2 }),
    }),
  }),
  destination: new Style({
    image: new CircleStyle({
      radius: 6,
      fill: new Fill({ color: '#e0574a' }),
      stroke: new Stroke({ color: '#e8edf4', width: 2 }),
    }),
  }),
  waypoint: new Style({
    image: new CircleStyle({
      radius: 5,
      fill: new Fill({ color: '#e87532' }),
      stroke: new Stroke({ color: '#e8edf4', width: 1.5 }),
    }),
  }),
}

function routeStyle(feature) {
  if (feature.get('role') === 'route-line') {
    return ROUTE_LINE_STYLE
  }
  return ROUTE_POINT_STYLES[feature.get('role')] ?? ROUTE_POINT_STYLES.waypoint
}

function buildView(resolutions, boundingBox) {
  const usableResolutions =
    resolutions.length > 0 ? resolutions : FALLBACK_RESOLUTIONS
  const maxZoom = Math.max(usableResolutions.length - 1, 0)
  const center = boundingBox
    ? [
        (boundingBox[0] + boundingBox[2]) / 2,
        (boundingBox[1] + boundingBox[3]) / 2,
      ]
    : DEFAULT_CENTER

  return new View({
    projection: MARS_PROJECTION,
    center,
    resolutions: usableResolutions,
    zoom: Math.min(9, maxZoom),
    minZoom: 0,
    maxZoom,
    constrainResolution: true,
    extent: MARS_EXTENT,
  })
}

function boundingBoxRing(boundingBox) {
  const [west, south, east, north] = boundingBox
  return [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ]
}

const MarsMap = forwardRef(function MarsMap(
  {
    layer,
    capabilities,
    route = EMPTY_ROUTE,
    viewExtent = null,
    onPointerMove,
    onStatusChange,
    onResolutionChange,
  },
  ref,
) {
  const targetRef = useRef(null)
  const mapRef = useRef(null)
  const tileLayerRef = useRef(null)
  const bboxFeatureRef = useRef(null)
  const routeLayerRef = useRef(null)
  const focusBoundingBoxRef = useRef(null)
  const callbacksRef = useRef({
    onPointerMove,
    onStatusChange,
    onResolutionChange,
  })

  useEffect(() => {
    callbacksRef.current = {
      onPointerMove,
      onStatusChange,
      onResolutionChange,
    }
  })

  useEffect(() => {
    const target = targetRef.current
    if (!target) {
      return undefined
    }

    const map = new Map({
      target,
      controls: [],
      view: buildView([], null),
    })
    mapRef.current = map

    const bboxFeature = new Feature()
    bboxFeatureRef.current = bboxFeature
    const bboxLayer = new VectorLayer({
      source: new VectorSource({ features: [bboxFeature] }),
      style: BBOX_STYLE,
      zIndex: 20,
    })
    map.addLayer(bboxLayer)

    const routeLayer = new VectorLayer({
      source: new VectorSource(),
      style: routeStyle,
      zIndex: 30,
    })
    routeLayerRef.current = routeLayer
    map.addLayer(routeLayer)

    const emitResolution = () => {
      const resolution = map.getView().getResolution()
      if (resolution == null) {
        return
      }
      const metersPerPixel =
        resolution * (Math.PI / 180) * MARS_RADIUS_METERS
      callbacksRef.current.onResolutionChange?.(metersPerPixel)
    }

    const handlePointerMove = (event) => {
      if (event.dragging) {
        return
      }
      const [longitude, latitude] = event.coordinate
      callbacksRef.current.onPointerMove?.({ longitude, latitude })
    }

    const handlePointerLeave = () => {
      callbacksRef.current.onPointerMove?.(null)
    }

    map.on('pointermove', handlePointerMove)
    map.on('moveend', emitResolution)
    target.addEventListener('mouseleave', handlePointerLeave)
    map.updateSize()

    return () => {
      target.removeEventListener('mouseleave', handlePointerLeave)
      map.un('pointermove', handlePointerMove)
      map.un('moveend', emitResolution)
      map.setTarget(undefined)
      mapRef.current = null
      tileLayerRef.current = null
      bboxFeatureRef.current = null
      routeLayerRef.current = null
      focusBoundingBoxRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) {
      return undefined
    }

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current)
      tileLayerRef.current = null
    }

    const bboxFeature = bboxFeatureRef.current
    const boundingBox = layer?.bounding_box
    const focusBoundingBox =
      viewExtent?.length === 4 ? viewExtent : (boundingBox ?? null)
    focusBoundingBoxRef.current = focusBoundingBox

    if (bboxFeature) {
      bboxFeature.setGeometry(
        boundingBox?.length === 4
          ? new Polygon([boundingBoxRing(boundingBox)])
          : null,
      )
    }

    if (
      !layer ||
      !capabilities ||
      !capabilities.tile_matrices?.length
    ) {
      callbacksRef.current.onStatusChange?.({
        loading: false,
        warning: null,
      })
      return undefined
    }

    const matrices = capabilities.tile_matrices
    const resolutions = matrices.map((matrix) => matrix.resolution_degrees)
    const matrixIds = matrices.map((matrix) => matrix.id)
    const tileSize = [
      matrices[0].tile_width,
      matrices[0].tile_height,
    ]

    const tileGrid = new WMTSTileGrid({
      origin: [-180, 90],
      resolutions,
      matrixIds,
      tileSize,
    })

    const source = new WMTS({
      url: capabilities.resource_url_template,
      layer: capabilities.layer_identifier,
      matrixSet: capabilities.tile_matrix_set,
      format: capabilities.format,
      style: capabilities.style,
      projection: MARS_PROJECTION,
      tileGrid,
      requestEncoding: 'REST',
      wrapX: false,
      crossOrigin: 'anonymous',
      attributions: layer.attribution,
    })

    const tileLayer = new TileLayer({
      source,
      zIndex: 10,
      extent: boundingBox?.length === 4 ? boundingBox : undefined,
    })
    tileLayerRef.current = tileLayer
    map.addLayer(tileLayer)

    const view = buildView(resolutions, focusBoundingBox)
    map.setView(view)

    const stats = { started: 0, settled: 0, loaded: 0, errors: 0 }

    const handleTileStart = () => {
      stats.started += 1
      callbacksRef.current.onStatusChange?.({
        loading: true,
        warning: null,
      })
    }

    const settle = () => {
      stats.settled += 1
      if (stats.settled < stats.started) {
        return
      }
      callbacksRef.current.onStatusChange?.({
        loading: false,
        warning:
          stats.loaded === 0 && stats.errors > 0
            ? 'NASA Mars Trek returned no imagery for the current view. Tiles may be outside the published footprint, or the tile service may be unavailable.'
            : null,
      })
    }

    const handleTileEnd = () => {
      stats.loaded += 1
      settle()
    }

    const handleTileError = () => {
      stats.errors += 1
      settle()
    }

    source.on('tileloadstart', handleTileStart)
    source.on('tileloadend', handleTileEnd)
    source.on('tileloaderror', handleTileError)

    const emitResolution = () => {
      const resolution = map.getView().getResolution()
      if (resolution == null) {
        return
      }
      const metersPerPixel =
        resolution * (Math.PI / 180) * MARS_RADIUS_METERS
      callbacksRef.current.onResolutionChange?.(metersPerPixel)
    }
    view.on('change:resolution', emitResolution)

    const frame = window.requestAnimationFrame(() => {
      map.updateSize()
      if (focusBoundingBox?.length === 4) {
        view.fit(focusBoundingBox, {
          padding: [52, 52, 52, 52],
          duration: 0,
        })
      }
      emitResolution()
    })

    return () => {
      window.cancelAnimationFrame(frame)
      source.un('tileloadstart', handleTileStart)
      source.un('tileloadend', handleTileEnd)
      source.un('tileloaderror', handleTileError)
      view.un('change:resolution', emitResolution)
      map.removeLayer(tileLayer)
      if (tileLayerRef.current === tileLayer) {
        tileLayerRef.current = null
      }
      callbacksRef.current.onStatusChange?.({
        loading: false,
        warning: null,
      })
    }
  }, [layer, capabilities, viewExtent])

  useEffect(() => {
    const routeLayer = routeLayerRef.current
    if (!routeLayer) {
      return
    }

    const source = routeLayer.getSource()
    source.clear()

    if (route.length === 0) {
      return
    }

    const coordinates = route.map((point) => [
      point.longitude,
      point.latitude,
    ])

    if (coordinates.length > 1) {
      source.addFeature(
        new Feature({
          geometry: new LineString(coordinates),
          role: 'route-line',
        }),
      )
    }

    route.forEach((point, index) => {
      const role =
        index === 0
          ? 'origin'
          : index === route.length - 1
            ? 'destination'
            : 'waypoint'

      source.addFeature(
        new Feature({
          geometry: new Point([point.longitude, point.latitude]),
          role,
          name: point.name,
        }),
      )
    })
  }, [route])

  useImperativeHandle(
    ref,
    () => ({
      zoomIn() {
        const view = mapRef.current?.getView()
        if (!view) {
          return
        }
        const zoom = view.getZoom()
        if (zoom == null) {
          return
        }
        view.animate({
          zoom: Math.min(zoom + 1, view.getMaxZoom()),
          duration: 180,
        })
      },
      zoomOut() {
        const view = mapRef.current?.getView()
        if (!view) {
          return
        }
        const zoom = view.getZoom()
        if (zoom == null) {
          return
        }
        view.animate({
          zoom: Math.max(zoom - 1, view.getMinZoom()),
          duration: 180,
        })
      },
      fitToLayer() {
        const map = mapRef.current
        const boundingBox = focusBoundingBoxRef.current
        if (!map || boundingBox?.length !== 4) {
          return
        }
        map.getView().fit(boundingBox, {
          padding: [52, 52, 52, 52],
          duration: 250,
        })
      },
    }),
    [],
  )

  return (
    <div
      ref={targetRef}
      className="mars-map"
      role="application"
      aria-label="Interactive NASA Mars Trek map of Jezero Crater"
    />
  )
})

export default MarsMap
